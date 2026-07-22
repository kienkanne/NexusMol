from openmm import LangevinMiddleIntegrator
from openmm.app import AmberInpcrdFile, AmberPrmtopFile, HBonds, PME, Simulation
from openmm.unit import nanometer, picosecond
from openmm import Platform
import re

from nexus.md.run.md_config import MDConfig
from nexus.core.trackers.main_tracker import main_tracker, TrackerContext

@main_tracker("Setup")
def setup(cfg: MDConfig):
    prmtop = AmberPrmtopFile(cfg.common.prmtop)
    inpcrd = AmberInpcrdFile(cfg.common.inpcrd)

    dt = cfg.common.dt * picosecond
    cut = cfg.common.cut * nanometer / 10 # Convert angstroms to nanometers

    mask = cfg.common.mask

    system = prmtop.createSystem(
        nonbondedMethod=PME,
        nonbondedCutoff=cut,
        constraints=HBonds,            # Equivalent to AMBER ntc=2, ntf=2 (SHAKE on H-bonds)
        rigidWater=True               
                                 )
    
    mask_pattern = r":(\d+)-(\d+)"

    match = re.search(mask_pattern, mask)
    if match:
        first_residue_i=int(match.group(1))
        stop_residue_i=int(match.group(2))
    else:
        raise ValueError(f"Invalid mask: {mask}. Currently only supports masks of the form ':first-last' to specify a contiguous residue range.")

    # Add restraints for minimization, heating, and equilibration
    add_positional_restraints(topology=prmtop.topology,
                              positions=inpcrd.positions,
                              system=system,
                              first_residue_i=first_residue_i,
                              stop_residue_i=stop_residue_i,
                              k_kcal_per_mol_a2=10)

    # Set high friction (5 ps^-1) initially for safe heating stage
    friction = cfg.heat.friction
    gamma = friction / picosecond
    # Initial temperature set to 0, gradually changed by heating step to temp
    integrator = LangevinMiddleIntegrator(0, gamma, dt)

    logger = TrackerContext.get_ctx().logger
    try:
        # Try to load CUDA with mixed precision
        platform = Platform.getPlatformByName("CUDA")
        properties = {'Precision': 'mixed'}
        
        simulation = Simulation(topology=prmtop.topology,
                                system=system,
                                integrator=integrator,
                                platform=platform,
                                platformProperties=properties)
        logger.info("Running simulation on CUDA (Mixed Precision)")

    except Exception as e:
        logger.info(f"CUDA not available ({e}). Falling back to the fastest available platform.")

        simulation = Simulation(topology=prmtop.topology,
                                system=system,
                                integrator=integrator)
        
        # Print what it actually ended up choosing
        logger.info(f"Running simulation on: {simulation.context.getPlatform().getName()}")
        
    simulation.context.setPositions(inpcrd.getPositions())

    # AMBER restart files may contain periodic box vectors; copy them into the
    # Context so PME and pressure coupling use the intended unit cell.
    if inpcrd.boxVectors is not None:
        simulation.context.setPeriodicBoxVectors(*inpcrd.boxVectors)

    return simulation


from openmm import CustomExternalForce
from openmm.unit import kilojoule_per_mole


def kcal_per_mol_a2_to_openmm(k_kcal_per_mol_a2):
    """Convert kcal/(mol A^2) force constants to OpenMM kJ/(mol nm^2)."""

    # 1 kcal/mol = 4.184 kJ/mol and 1 A^2 = 0.01 nm^2, so multiply by 418.4.
    return k_kcal_per_mol_a2 * 418.4 * kilojoule_per_mole / nanometer**2


def add_positional_restraints(
    topology,
    positions,
    system,
    first_residue_i,
    stop_residue_i,
    k_kcal_per_mol_a2,
):
    """Add harmonic restraints on atoms whose residue index is in the interval."""

    k = kcal_per_mol_a2_to_openmm(k_kcal_per_mol_a2)
    restraint = CustomExternalForce(
        "0.5*positional_restraint_k*((x-x0)^2 + (y-y0)^2 + (z-z0)^2)"
    )
    # Store each atom's reference coordinates as per-particle parameters.
    restraint.addPerParticleParameter("x0")
    restraint.addPerParticleParameter("y0")
    restraint.addPerParticleParameter("z0")
    # The global force constant lets protocols update restraint strength cheaply.
    restraint.addGlobalParameter("positional_restraint_k", k)

    for atom, position in zip(topology.atoms(), positions):
        amber_index = int(atom.residue.id)
        if first_residue_i <= amber_index <= stop_residue_i:
            x0, y0, z0 = position.value_in_unit(nanometer)
            restraint.addParticle(atom.index, [x0, y0, z0])

    system.addForce(restraint)
    return restraint


def set_positional_restraint_strength(simulation, k_kcal_per_mol_a2):
    """Update the existing restraint force constant in the active Context."""

    k = kcal_per_mol_a2_to_openmm(k_kcal_per_mol_a2)
    simulation.context.setParameter("positional_restraint_k", k)
