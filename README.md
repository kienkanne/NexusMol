# NexusMol: Computational tools for drug discovery

## Introduction

Current package version: `2.1.0`.

This repository runs end-to-end computational workflows for drug discovery using YAML config files. It currently supports:

- AutoDock Vina
- DOCK6
- Molecular dynamics with AmberTools (`nexus md amber`)
- Solvated system building for MD using `nexus prep sysmd`
- Validation workflows for Vina and DOCK6
- Receptors and ligands fetching from RCSB.org
- Receptors and ligands custom preparation and cleaning

The docking pipelines dock ligands in parallel with GNU parallel, copy selected outputs to a results folder, and write a docking summary CSV sorted by the best pose score.

## Installation

Install Conda (Miniconda or Anaconda), then create the environment:

```bash
conda env create -n myproject -f environment.yaml
conda activate myproject
```

Install the Python package in editable mode from the repository root:

```bash
pip install -e .
```

Other needed tools that have to be installed:

- DOCK6: See [https://github.com/docking-org/dock6](https://github.com/docking-org/dock6)
- ChimeraX: See [https://www.cgl.ucsf.edu/chimerax/download.html](https://www.cgl.ucsf.edu/chimerax/download.html)
- Chimera: See [https://www.cgl.ucsf.edu/chimera/download.html](https://www.cgl.ucsf.edu/chimera/download.html) 
- AMBER: See [https://ambermd.org/GetAmber.php](https://ambermd.org/GetAmber.php)
Some librares are needed to be pointed at their installed directories:

```yaml
chimerax: "/usr/local/chimerax/bin/ChimeraX"
dock_home: "$HOME/Apps/dock6/"
```

AMBER has to be loaded in as a module, for example:

```bash
module load amber/24
```

## Running

Use the CLI with a single unified config YAML file:

```bash
nexus dock vina -c build/sample_configs/sample_docking.yaml
nexus dock dock6 -c build/sample_configs/sample_docking.yaml
nexus prep sysmd -c examples/sysmd_config.yaml
nexus md amber -c build/sample_configs/amber_md.yaml
nexus md analyze -p /path/to/prmtop -t /path/to/trajin -m ":1-198" [-n analysis_name] [-o /path/to/output]
```

The `nexus md analyze` command runs the full CPPTRAJ analysis workflow and writes RMSD/RMSF, hydrogen bond, secondary structure, PCA, and clustering outputs, plus a visualization notebook.

Retrieve receptor assemblies and ligand SDFs directly from RCSB with the fetch command:

```bash
nexus fetch rcsb -i 6LU7 -i 6W63 -o output_dir/
```

The fetch module downloads biological assemblies in mmCIF format and writes cleaned `.cif` receptor outputs.

Prepare/clean receptors or mutate/change protonation state of receptors with the prep command:

```bash
nexus prep rec -i 6LU7.cif -i 6W63.pdb -o output_dir/
nexus prep mutate -i 6LU7.cif -o output_dir/ -m "/A:41&:HIS-HIP" -m "/A:145&:CYS-CYM"

nexus prep ligdock -i smiles_list.csv -o output_dir/ -s "_prepared.pdbqt"
nexus prep ligdock -i path_to_sdf_folder/ -o output_dir -s "_prepared.mol2"
```

## Ligand CSV

The suffix determines the output of the ligand, and it must contain either `.pdbqt` (format for vina, prepared by meeko) or `.mol2` (format for dock6, prepared by obabel)

The input for `nexus prep ligdock` can be a sdf file, a folder containing many sdf files, or a csv file. The CSV file must have exactly this header:

```csv
smiles,name
CC(=O)OC1=CC=CC=C1C(=O)O,aspirin
CC1=C(C=C(C=C1)C(C)C)O,carvacrol
```

Ligand names are used in output filenames, so keep them short and file-friendly. The loader sanitizes names and raises an error for duplicate names after sanitization. RDKIT is used to generate the 3D conformations of ligands from smiles.

## Docking Config Format

See `build/sample_configs/sample_docking.yaml`, `examples/vina_config.yaml`, and `examples/dock6_config.yaml` for working examples.

### `libs`

Tool locations and executable names.

```yaml
libs:
  chimerax: "/usr/local/chimerax/bin/ChimeraX"
  chimera: "/usr/local/chimera/chimera-1.8/bin/chimera"

  dock_home: "/localscratch/kbui/Apps/dock6/"
```

### `common`

Scratch directory, results directory, and batch settings.

```yaml
common:
  project_name: Mpro_vina_docking
  working_dir: "/path/to/nexus/artifacts"
  results_dir: "/path/to/nexus/results"

  padding: 4.0
  n_jobs: 16
  max_poses: 16
```

- `project_name`: name of the folder in working_dir and results_dir
- `working_dir`: parent folder of scratch space where intermediate files are written.
- `results_dir`: parent folder of where final selected outputs and summary CSV are copied.
- `padding`: extra buffer space (in Angstroms) added to the outer edges of the docking grid box.
- `n_jobs`: total concurrent jobs.
- `max_poses`: maximum number of scores to parse per ligand into the summary CSV.

### `receptors`

Receptor input and pocket definition (resolved at config-load time).

```yaml
receptors:
  source: "/localscratch/kbui/NexusMol/data/"
  suffix: "_protein.cif"
```

Alternatively, use a reference pocket file:

```yaml
receptors:
  pocket_option: "reference"
  reference: "/localscratch/kbui/NexusMol/data/6W63_pocket.pdb"
```

Or use multiple receptors with per-receptor selections (from a CSV):

```yaml
receptors:
  source:
    - "/path/to/receptor1.pdb"
    - "/path/to/receptor2.pdb"
  pocket_option: "selection"
  selection: "/path/to/selection_strings.csv"
```

Where `selection_strings.csv` has the format:

```csv
receptor1,chain A and resi 41+145
receptor2,chain B and resi 50+100+150
```

- `source`: single file, directory of files, or list of file paths.
- `suffix`: the pattern to search for if the provided source is a folder.
- `pocket_option`: `selection` (use PyMOL selection string) or `reference` (use reference pocket file).
- `selection`: PyMOL selection string (applied to all receptors) or path to a per-receptor CSV file.
- `reference`: single reference pocket file (for all receptors) or path to a directory of reference files.
- `reference_suffix`: suffix used when matching multiple receptor files to reference files by base name (default: `_pocket.pdb`).

**Note (1.3.2+):** All receptor configuration (selection CSV parsing and reference matching) is resolved at config-load time. The resolved receptor bundles are immediately available to the pipeline and prep functions, eliminating runtime parsing errors.

### `ligands`

```yaml
ligands:
  source: "existing"
  suffix: "/path/to/prepped/ligands"
```

- `source`: single file, directory of files, or list of file paths.
- `suffix`: the file suffix used to find prepared ligand files.
- Vina reads `.pdbqt` ligands, and DOCK6 reads `.mol2` ligands.

### `vina`

Vina-specific settings.

```yaml
vina:
  exhaustiveness: 32
  num_modes: 8
```

- `exhaustiveness`: search exhaustiveness (higher = more thorough but slower).
- `num_modes`: maximum number of output poses per ligand

### `dock6`

DOCK6-specific settings.

```yaml
dock6:
  max_orientations: 1000
  radius: 10.0
```

- `max_orientations`: maximum number of ligand orientations to sample.
- `radius`: radius of the binding sphere (in Angstroms) around the selected atoms.

## System Setup for MD Config Format

The `nexus prep sysmd` command builds solvated Amber systems from receptor and optional ligand inputs.

```yaml
common:
  input: /localscratch/kbui/NexusMol/examples/sysmd_input/6W63.pdb
  working_dir: /localscratch/kbui/NexusMol/examples/artifacts
  output_dir: /localscratch/kbui/NexusMol/examples/results

sysmd:
  system_name: 6W63_mol4_solvated
  ligand: /localscratch/kbui/NexusMol/examples/sysmd_input/6W63_mol4_prepared_scored.pdbqt
  pose_num: 1
  force_field: "ff14SB"
  water_model: "tip3p"
  box_type: "Oct"
  box_size: 12.0
  salt_conc: 0.15
```

### `common`

- `input` — input receptor file (`.pdb`, `.cif`, or prepared receptor structure).
- `working_dir` — parent directory for intermediate sysmd artifacts.
- `output_dir` — destination directory for generated solvated system files.

### `sysmd`

- `system_name` — base name appended to `working_dir` and `output_dir`.
- `ligand` — optional prepared ligand pose file used to build a receptor-ligand complex.
- `pose_num` — pose index to select from the supplied ligand file.
- `force_field` — Amber force field for the system, e.g. `ff14SB` or `ff19SB`.
- `water_model` — water model for solvation, e.g. `tip3p` or `opc`.
- `box_type` — solvent box type: `Box` or `Oct`.
- `box_size` — padding distance in Angstroms around the solute.
- `salt_conc` — salt concentration in molar units.

`nexus prep sysmd` creates the working and output directories under the configured paths and writes the solvated system files there.

## Molecular Dynamics Config Format

The MD config is used by `nexus md amber` to run Amber minimization, heating, equilibration, and production.

```yaml
common:
  project_name: MD_Dialanine
  working_dir: /localscratch/kbui/NexusMol/examples/artifacts
  results_dir: /localscratch/kbui/NexusMol/examples/results
  prmtop: /localscratch/kbui/NexusMol/examples/md_input/ALA.prmtop
  inpcrd: /localscratch/kbui/NexusMol/examples/md_input/ALA.inpcrd
  temp: 300.0
  dt: 0.002
  cut: 10.0
  mask: ":1-3"

min:
  n_min_runs: 7
  ncyc: 1000
  maxcyc: 1000
  restraints: [10.0, 5.0, 2.0, 1.0, 0.5, 0.1, 0.0]

heat:
  mid_temp: 100.0
  time1: 100.0
  time2: 500.0
  total_time: 2000.0
  restraint: 10.0

eq:
  n_eq_runs: 7
  eq_time: 100.0
  restraints: [10.0, 5.0, 2.0, 1.0, 0.5, 0.1, 0.0]

prod:
  num_seeds: 1
  rand_time: 200.0
  prod_time: 2500.0
  prod_freq: 10.0
```

### `common`

- `project_name` — appended to `working_dir` and `results_dir`.
- `working_dir` — parent path for MD scratch and intermediate files.
- `results_dir` — parent path for final MD outputs.
- `prmtop` — Amber topology file.
- `inpcrd` — Amber coordinate file.
- `temp` — base temperature for MD stages.
- `dt` — time step in picoseconds.
- `cut` — nonbonded cutoff distance in Angstroms.
- `mask` — optional atom mask used for analysis and restraints.

### `min`

- `n_min_runs` — number of minimization stages.
- `ncyc` — steepest-descent minimization steps.
- `maxcyc` — conjugate-gradient minimization steps.
- `restraints` — per-stage restraint force constants.

### `heat`

- `mid_temp` — intermediate heating temperature.
- `time1` — first heating interval duration.
- `time2` — second heating interval duration.
- `total_time` — total heating duration.
- `restraint` — positional restraint force constant during heating.

### `eq`

- `n_eq_runs` — number of equilibration stages.
- `eq_time` — equilibration time per stage.
- `restraints` — per-stage restraint force constants.

### `prod`

- `num_seeds` — number of independent production seeds.
- `rand_time` — randomization time before production.
- `prod_time` — production run duration.
- `prod_freq` — production output frequency.

## Examples

- [Examples](examples/EXAMPLES.md)

## More Documentation

- [Changelog](CHANGELOG.md)
- [Architecture](docs/architecture.md)
- [Data Flow](docs/data_flow.md)
- [Configuration Reference](docs/configuration.md)
