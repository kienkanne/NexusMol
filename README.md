# SARS-CoV-2 Docking Pipeline

## Merged Platform Migration

This repo now includes a merged docking + AMBER MD platform package at
`src/molsim_platform`. The older `src/docking` package and `docking` CLI remain
available for compatibility, while new development should target:

```bash
molsim run-vina --config configs/vina.yaml
molsim run-dock6 --config configs/dock6.yaml
molsim amber-full-run --config configs/amber_md.yaml
molsim amber-generate-system --config configs/amber_md.yaml
```

The new architecture is documented in
[docs/platform_architecture.md](docs/platform_architecture.md).

This repository runs end-to-end molecular docking workflows for a receptor PDB and a CSV of ligands. It currently supports:

- AutoDock Vina
- DOCK6

The pipeline prepares the receptor, prepares each ligand from SMILES, docks ligands in parallel with GNU parallel, copies selected outputs to a results folder, and writes a docking summary CSV sorted by the best pose score.

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

Most command-line tools can be installed into the active conda/mamba environment and referenced by executable name in the config:

```yaml
obabel: "obabel"
parallel: "parallel"
vina: "vina"
```

Some tools usually need explicit paths:

- `prepare_receptor` and `prepare_ligand` must include the MGLTools `pythonsh` executable plus the full script path.
- DOCK6 tools such as `dock6`, `sphgen`, `sphere_selector`, `showbox`, and `grid` are usually installed outside conda and should be absolute paths.
- `chimerax` should point to the ChimeraX executable if it is not on `PATH`.
- Some environment variables can be exported to make the paths easier to read, for example:

```bash
export MGLTOOLS=$HOME/Apps/mgltools_1.5.7/mgltools_x86_64Linux2_1.5.7
export DOCK_HOME=$HOME/Apps/dock6
```

## Running

Use the CLI with a config file:

```bash
docking run_vina --config configs/docking_config.yaml
docking run_dock6 --config configs/docking_config.yaml
```

There are also thin scripts:

```bash
python scripts/run_vina.py
python scripts/run_dock6.py
```

Those scripts load `configs/docking_config.yaml` by default.

## Ligand CSV

The ligand file must be a CSV with exactly this header:

```csv
smiles,name
CC(=O)OC1=CC=CC=C1C(=O)O,aspirin
CC1=C(C=C(C=C1)C(C)C)O,carvacrol
```

Ligand names are used in output filenames, so keep them short and file-friendly. The loader sanitizes names and raises an error for duplicate names after sanitization. Each SMILES string is validated with Open Babel before docking starts.

## Config Format

See [configs/docking_config.yaml](configs/docking_config.yaml) for a working example.

### `libs`

Tool locations and executable names.

```yaml
libs:
  chimerax: "/usr/local/chimerax/bin/ChimeraX"
  obabel: "obabel"
  parallel: "parallel"
  vina: "vina"
  prepare_receptor: "$MGLTOOLS/bin/pythonsh $MGLTOOLS/MGLToolsPckgs/AutoDockTools/Utilities24/prepare_receptor4.py"
  prepare_ligand: "$MGLTOOLS/bin/pythonsh $MGLTOOLS/MGLToolsPckgs/AutoDockTools/Utilities24/prepare_ligand4.py"
  dock6: "$DOCK_HOME/bin/dock6"
  sphgen: "$DOCK_HOME/bin/sphgen"
  sphere_selector: "$DOCK_HOME/bin/sphere_selector"
  showbox: "$DOCK_HOME/bin/showbox"
  grid: "$DOCK_HOME/bin/grid"
```

### `common`

Inputs, scratch directory, results directory, and batch settings.

```yaml
common:
  working_dir: "/path/to/scratch/sample_vina"
  receptor: "/path/to/data/6W63.pdb"
  ligand: "/path/to/data/sample_ligands.csv"
  results_dir: "/path/to/results/results_vina"
  pocket_name: "catalytic_site"
  total_cpu: 16
  max_poses: 8
```

- `working_dir`: scratch space where intermediate files are written.
- `receptor`: starting receptor PDB.
- `ligand`: CSV path with `smiles,name`.
- `results_dir`: final selected outputs and summary CSV are copied here.
- `total_cpu`: total CPU budget for ligand docking.
- `max_poses`: maximum number of scores to parse per ligand into the summary CSV.

### `vina`

Vina-specific settings.

```yaml
vina:
  exhaustiveness: 32
  num_modes: 8
  cpu: 1
  padding: 5.0
  pocket_option: "res"
  reference: "/path/to/ref_ligand.pdb"
  residue_selection: "chain A and resi 41+145"
```

- `cpu` is the CPU count per ligand job.
- Vina parallel job count is `common.total_cpu // vina.cpu`.
- `pocket_option: "res"` uses `residue_selection`.
- `pocket_option: "lig"` uses `reference`.

### `dock6`

DOCK6-specific settings.

```yaml
dock6:
  max_orientations: 5000
  radius: 10.0
  padding: 5.0
  residue_selection: "chain A and resi 41+145"
```

DOCK6 jobs are single-core, so the parallel job count is `common.total_cpu`.

## Outputs

The results directory contains selected final files:

- Vina poses: `*_docked.pdbqt`
- Vina docking logs: `*_docked.log`
- DOCK6 poses: `*_scored.mol2`
- DOCK6 docking logs: `*_scored.log`
- Pipeline logs: `run.log`, `manifest.json`, `state.json`
- Summary CSV: `<receptor_stem>_docking_summary.csv`

The summary CSV has this format:

```csv
name,pose1,pose2,pose3,...
aspirin,-2.383,-1.596,-1.454,...
carvacrol,-1.917,-1.528,-1.319,...
```

Rows are sorted by `pose1`, with lower scores first.

## More Documentation

- [Architecture](docs/architecture.md)
- [Data Flow](docs/data_flow.md)
- [Configuration Reference](docs/configuration.md)
