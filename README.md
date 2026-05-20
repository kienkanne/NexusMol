# Computational tools for drug discovery

## Introduction

Current package version: `1.4.0`.

This repository runs end-to-end molecular docking workflows from a unified YAML config file. It currently supports:

- AutoDock Vina
- DOCK6
- Validation workflows for Vina and DOCK6

The pipeline prepares the receptor, resolves or prepares ligands, docks ligands in parallel with GNU parallel, copies selected outputs to a results folder, and writes a docking summary CSV sorted by the best pose score.

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
- MGLTOOLS: See [https://ccsb.scripps.edu/mgltools/downloads](https://ccsb.scripps.edu/mgltools/downloads)
- ChimeraX: See [https://www.cgl.ucsf.edu/chimerax/download.html](https://www.cgl.ucsf.edu/chimerax/download.html)
- Chimera: See [https://www.cgl.ucsf.edu/chimera/download.html](https://www.cgl.ucsf.edu/chimera/download.html) 

Most command-line tools can be installed into the active conda/mamba environment and referenced by executable name in the config:

```yaml
obabel: "obabel"
parallel: "parallel"
vina: "vina"
```

Some others needed to be pointed at their installed directories:

```yaml
mgltools: "$HOME/Apps/mgltools_1.5.7/mgltools_x86_64Linux2_1.5.7/"
dock_home: "$HOME/Apps/dock6/"
```

## Running

Use the CLI with a single unified config YAML file:

```bash
compdd run_vina --config sample_configs/sample_docking.yaml
compdd run_dock6 --config sample_configs/sample_docking.yaml
```

Run validation workflows with the same config:

```bash
compdd validate_run_vina --config sample_configs/sample_docking.yaml
compdd validate_run_dock6 --config sample_configs/sample_docking.yaml
```

## Ligand CSV

When `sample_ligands.yaml` uses `source: smiles`, the ligand file must be a CSV with exactly this header:

```csv
smiles,name
CC(=O)OC1=CC=CC=C1C(=O)O,aspirin
CC1=C(C=C(C=C1)C(C)C)O,carvacrol
```

Ligand names are used in output filenames, so keep them short and file-friendly. The loader sanitizes names and raises an error for duplicate names after sanitization.

## Config Format

See [sample_configs/sample_docking.yaml](sample_configs/sample_docking.yaml) and [sample_configs/sample_ligands.yaml](sample_configs/sample_ligands.yaml) for working examples.

### `libs`

Tool locations and executable names.

```yaml
libs:
  chimerax: "/usr/local/chimerax/bin/ChimeraX"
  chimera: "/usr/local/chimera/chimera-1.8/bin/chimera"

  mgltools: "/localscratch/kbui/Apps/mgltools_1.5.7/mgltools_x86_64Linux2_1.5.7/"
  dock_home: "/localscratch/kbui/Apps/dock6/"

  obabel: "obabel"
  parallel: "parallel"
  vina: "vina"
```

### `common`

Scratch directory, results directory, and batch settings.

```yaml
common:
  project_name: vina_mpro_catalytic
  working_dir: "/localscratch/kbui/Comp_DD/artifacts"
  results_dir: "/localscratch/kbui/Comp_DD/results/"
  prepared_suffix: "prepped"
  padding: 5.0
  n_jobs: 16
  max_poses: 8
```

- `project_name`: name of the folder in working_dir and results_dir
- `working_dir`: parent folder of scratch space where intermediate files are written.
- `results_dir`: parent folder of where final selected outputs and summary CSV are copied.
- `prepared_suffix`: suffix used for prepared receptor files, written as `<name>_<prepared_suffix>.<ext>`.
- `n_jobs`: total concurrent jobs.
- `max_poses`: maximum number of scores to parse per ligand into the summary CSV.

### `receptors`

Receptor input and pocket definition (resolved at config-load time).

```yaml
receptors:
  pdbs: "/localscratch/kbui/Comp_DD/data/6W63.pdb"
  pocket_option: "selection"
  selection: "chain A and resi 41+145+140+143+144+145+163+166"
  reference_suffix: "_pocket.pdb"
```

Alternatively, use a reference pocket file:

```yaml
receptors:
  pdbs: "/localscratch/kbui/Comp_DD/data/6W63.pdb"
  pocket_option: "reference"
  reference: "/localscratch/kbui/Comp_DD/data/6W63_pocket.pdb"
```

Or use multiple receptors with per-receptor selections (from a CSV):

```yaml
receptors:
  pdbs:
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

- `pdbs`: single PDB file, directory of PDB files, or list of PDB file paths.
- `pocket_option`: `selection` (use PyMOL selection string) or `reference` (use reference pocket file).
- `selection`: PyMOL selection string (applied to all receptors) or path to a per-receptor CSV file.
- `reference`: single reference pocket file (for all receptors) or path to a directory of reference files.
- `reference_suffix`: suffix used when matching reference files by base name (default: `_pocket.pdb`).

**Note (1.3.2+):** All receptor configuration (selection CSV parsing and reference matching) is resolved at config-load time. The resolved receptor bundles are immediately available to the pipeline and prep functions, eliminating runtime parsing errors.

### `ligands`

Ligand inputs are configured in the same YAML file:

```yaml
ligands:
  source: "smiles" # or "sdf" or "existing"
  smiles_csv: "/localscratch/kbui/Comp_DD/data/ligands_list.csv"
  output_dir: "/localscratch/kbui/Comp_DD/results/ligands_prepped"
```

Alternatively, from SDF files:

```yaml
ligands:
  source: "sdf"
  sdfs: "/path/to/ligands.sdf"  # or a list of SDF files
  output_dir: "/localscratch/kbui/Comp_DD/results/ligands_prepped"
```

Or from pre-prepared ligands:

```yaml
ligands:
  source: "existing"
  existing_dir: "/path/to/prepped/ligands"
```

- `source: smiles` prepares ligands from a `smiles,name` CSV.
- `source: sdf` prepares ligands from SDF files.
- `source: existing` skips preparation and uses already-prepared ligands.
- Vina reads `*_<prepared_suffix>.pdbqt`; DOCK6 reads `*_<prepared_suffix>.mol2`.

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

DOCK6 jobs are single-core; set `common.n_jobs` to the total number of CPU cores you want to use (for example, the number of available CPU cores on the machine).

## Validation

The repository now supports dedicated validation workflows via:

```bash
compdd validate_run_vina --config sample_configs/sample_docking.yaml
compdd validate_run_dock6 --config sample_configs/sample_docking.yaml
```

Validation mode reuses the same config file, but `validation.data` is used to load:

- receptor proteins from `*_protein.pdb`
- reference pockets from `*_pocket.pdb`
- ligands from `*_ligand.sdf`

For recommended dataset layout and formatting, see `docs/validation.md`.

## Outputs

The results directory contains selected final files:

- Vina poses: `*_scored.pdbqt`
- DOCK6 poses: `*_scored.mol2`
- Pipeline logs: `run.log`, `manifest.json`, `state.json`
- Summary CSV: `<project_name>_<receptor_stem>_docking_summary.csv`

The summary CSV has this format:

```csv
name,pose1,pose2,pose3,...
aspirin,-2.383,-1.596,-1.454,...
carvacrol,-1.917,-1.528,-1.319,...
```

Rows are sorted by `pose1`, with lower scores first.

## More Documentation

- [Changelog](CHANGELOG.md)
- [Architecture](docs/architecture.md)
- [Data Flow](docs/data_flow.md)
- [Configuration Reference](docs/configuration.md)
