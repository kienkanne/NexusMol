# Examples

This directory contains example inputs, configs, generated artifacts, and results for the current Nexus CLI.

Run the examples from this directory:

```bash
cd examples
```

The workflow configs in `configs/` use paths relative to `examples/`. See the config files for details about each input parameter.

## 1. Global Config

Create the global config:

```bash
nexus config init
```

Edit `~/.config/nexus/config.yaml`. For example:

```yaml
software:
  chimerax: /usr/local/chimera/chimera-1.8/bin/chimera
  chimera: /usr/local/chimerax/bin/ChimeraX
  dock6: ~/apps/dock6
path:
  scratch_dir: /localscratch/$USER
  clear: false
```

Check it:

```bash
nexus config show
nexus config validate
```

## 2. Fetch and Prepare Receptors

Fetch biological assemblies and non-covalent ligands from RCSB:

```bash
nexus fetch rcsb -i inputs/id_list.txt -o receptors/fetched -l "ligand"
```

> The `-l` flag is the suffix you want to attach to the fetched ligand. If it's not specified, the ligand's original name from RCSB is used.

Clean receptors with ChimeraX:

```bash
nexus prep rec -i receptors/fetched -o receptors/cleaned -s "_cleaned.pdb" -d
```

> The `-d` flag is to dry, and you almost always want to use it to remove crystallographic waters to prepare receptors for docking. For molecular dynamics, you might want to keep those near the binding site manually.

Review the generated `.log` files. They report chain spans and non-standard protonation states assigned by ChimeraX.

## 3. Adjust Protonation States

Based on the output from `nexus prep rec`, we adjust the protonation state of the receptors based on biological knowledge of the receptor. 

```bash
nexus prep mutate -i receptors/cleaned/6W63_cleaned.pdb -o receptors/mutated -s "_mutated.pdb" -m ":145-CYM"
nexus prep mutate -i receptors/cleaned/7K40_cleaned.pdb -o receptors/mutated -s "_mutated.pdb" -m ":64,80-HIE" -m ":41-HIP" -m ":145-CYM"
```

> For example, 6W63 and 7K40 are protein structures of the SARS-CoV-2 main protease (mpro), and if we want to model the ionic pair at the catalytic side, we can assign His41 to be doubly protonated (HIP) and Cys145 to be deprotonated (CYM). We can also adjust other histidines that was assigned to be HIP by chimerax to be neutral (HIE/HID), for example.

Mutation strings use `selection-NEW_RES`, where `selection` is passed to ChimeraX and `NEW_RES` is the residue name to assign. Note that if the protonation state is changed, `NEW_RES` is used only to change the protonation state, while the residue stays standardized. See [examples/REFERENCES.md](examples/REFERENCES.md) for detailed selection syntax and AMBER residue naming conventions.

After this step, our receptor names are quite long, so we might want to simplify their naming and put in a folder specified by the docking configs, and in this example they were put in receptors/final/.

```bash
mkdir -p receptors/final
cp receptors/mutated/6W63_cleaned_mutated.pdb receptors/final/6W63.pdb
cp receptors/mutated/7K40_cleaned_mutated.pdb receptors/final/7K40.pdb
```

## 4. Prepare Ligands

Vina requires the .pdbqt format, while dock6 requires .mol2.

```bash
nexus prep lig -i inputs/ligand_list.csv -o ligands/vina/ -s "_prepared.pdbqt"
nexus prep lig -i inputs/ligand_list.csv -o ligands/dock6/ -s "_prepared.mol2"
```

The CSV format is:

```csv
smiles,name
CC(=O)OC1=CC=CC=C1C(=O)O,aspirin
```

## 5. Molecular Docking

Both docking engines use `nexus dock run`. In the config file, `engine.program` field selects `vina` or `dock6`.

```bash
nexus dock run -c configs/vina_config.yaml
nexus dock run -c configs/dock6_config.yaml
```

Outputs are grouped by receptor:

```text
results/vina_mpro/6W63/
results/vina_mpro/7K40/
results/dock6_mpro/6W63/
results/dock6_mpro/7K40/
```

Each receptor result folder contains prepared receptor/pocket files, scored poses, `Scores_...csv`, and `Clusters_...csv`.

## 6. Build a Solvated MD System

If Amber is provided by an environment module, load it before MD build/run/analyze commands:

```bash
module load amber/24
echo "$AMBERHOME"
```

Build an Amber system from `inputs/6W63.pdb` and a docked ligand pose:

```bash
nexus --silence 2 md build -c configs/build_config.yaml
```

> AmberTools can be very verbose, so the flag `--silence 2` is recommended to avoid having your terminal cluttered.

This command:
- Prepare a receptor with `pdb4amber`.
- Optionally select a docked ligand pose.
- Add ligand hydrogens and AM1-BCC charges with `obabel` and `antechamber`.
- Generate ligand parameters with `parmchk2`.
- Solvate, ionize, and write Amber files with `tleap`.

Outputs:

```text
results/6W63_mol4_solvated/6W63_mol4_solvated.prmtop
results/6W63_mol4_solvated/6W63_mol4_solvated.inpcrd
results/6W63_mol4_solvated/6W63_mol4_solvated.pdb
```

## 7. Run MD

The example MD configs use dialanine inputs because they are small enough for demonstration. In the config file, `engine.program` selects `amber` or `openmm`.

```bash
nexus --silence 2 md run -c configs/amber_config.yaml
nexus md run -c configs/openmm_config.yaml
```

These commands:
- Start from Amber topology and coordinates.
- Minimize with a restraint schedule.
- Heat to target temperature.
- Equilibrate with a restraint schedule.
- Run one or more randomized production seeds.

> Note: The sample analysis config points at the generated Amber dialanine output so the paths exist in this example tree. The dialanine system was used for illustrative purposes for the MD task above due to its small size, but it will not produce much meaningful analysis for the commands below.

> Note: The checked-in `results/2BPW_analysis/` folder is a larger representative analysis output set. 2BPW is a HIV-1 protease-inhibitor complex, and was chosen for this example over DiAlanine because DiAlanine is too small to have meaningful protein analysis. The original input files were not uploaded to the repository due to their large size.

## 8. Analyze a Trajectory

```bash
nexus --silence 2 md analyze -c configs/analyze_config.yaml
```

This command:
- Render the bundled CPPTRAJ template.
- Run RMSD and RMSF analysis.
- Run hydrogen-bond analysis.
- Run secondary-structure analysis.
- Run PCA and clustering.
- Generate professional figures from cpptraj output to output directory.

## 9. Calculate the ligand free binding energy with MMPBSA

```bash
nexus --silence 2 md mmpbsa -c configs/mmpbsa_config.yaml
```

This command:
- Prepares MMPBSA inputs with `ante-MMPBSA.py`, runs `MMPBSA.py.MPI`, and writes per-frame energy CSVs and optional decomposition CSVs (e.g. `energy_<job>.csv`, `decomp_<job>.csv`).
- Generate professional figures from MMPBSA outputs


## Example Config Index

| File | Purpose |
| --- | --- |
| `configs/global_config.yaml` | Template for `~/.config/nexus/config.yaml`. |
| `configs/vina_config.yaml` | Run Vina docking. |
| `configs/dock6_config.yaml` | Run DOCK6 docking. |
| `configs/build_config.yaml` | Build an Amber system. |
| `configs/amber_config.yaml` | Run Amber MD. |
| `configs/openmm_config.yaml` | Run OpenMM MD. |
| `configs/analyze_config.yaml` | Run CPPTRAJ analysis. |
| `configs/mmpbsa_config.yaml` | Run MM-PBSA/GBSA and generate summary figures. |

More configuration detail: [docs/CONFIGURATION.md](docs/CONFIGURATION.md).
