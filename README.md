# NexusMol: Computational tools for drug discovery

## Introduction

Current package version: `1.5.3`.

This repository runs end-to-end computational workflows for drug discovery using YAML config files. It currently supports:

- AutoDock Vina
- DOCK6
- Validation workflows for Vina and DOCK6
- Receptors and ligands fetching from RCSB.org
- Receptors and ligands custom preparation and cleaning

The docking pipelines docks ligands in parallel with GNU parallel, copies selected outputs to a results folder, and writes a docking summary CSV sorted by the best pose score.

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

Some librares are needed to be pointed at their installed directories:

```yaml
chimerax: "/usr/local/chimerax/bin/ChimeraX"
dock_home: "$HOME/Apps/dock6/"
```

## Running

Use the CLI with a single unified config YAML file:

```bash
nexus dock vina -c sample_configs/sample_docking.yaml
nexus dock dock6 -c sample_configs/sample_docking.yaml
```

Retrieve receptor assemblies and ligand SDFs directly from RCSB with the fetch command:

```bash
nexus fetch rcsb -i 6LU7 -i 6W63 -o output_dir/
```

The fetch module downloads biological assemblies in mmCIF format and writes cleaned `.cif` receptor outputs.

Prepare/clean receptors or mutate/change protonation state of receptors wth the prep command:

```bash
nexus prep rec -i 6LU7.cif -i 6W63.pdb -o output_dir/
nexus prep mutate -i 6LU7.cif -o output_dir/ -m "/A:41&:HIS-HIP" -m "/A:145&:CYS-CYM"

nexus prep ligdock -i smiles_list.csv -o output_dir/ -s "prepared.pdbqt"
nexus prep ligdock -i path_to_sdf_folder/ -o output_dir -s "prepared.mol2"
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

See [sample_configs/sample_docking.yaml](sample_configs/sample_docking.yaml) and [sample_configs/sample_ligands.yaml](sample_configs/sample_ligands.yaml) for working examples.

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
- `suffix`: the pattern to search for if the provided source is a folder.
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

## Validation (currently disabled)

The repository now supports dedicated validation workflows via:

```bash
nexus validate vina -c sample_configs/sample_docking.yaml
nexus validate dock6 -c sample_configs/sample_docking.yaml
```

Validation specific settings.

```yaml
validation:
  data: "/localscratch/kbui/coreset"
  protein_suffix: "_protein.pdb"
  pocket_suffix: "_pocket.pdb"
  ligand_suffix: "_ligand.sdf"
```

Validation mode reuses the same config file, but `validation.data` is used to load receptor proteins, reference pockets, and ligands. These files are searched recursively in the input folder path. All should have matching names. All settings in `receptors` and `ligands` are ignored when validation is used. 

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
