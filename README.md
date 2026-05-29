# NexusMol

NexusMol is a command-line toolkit for structure-based drug discovery workflows. It brings common preparation, docking, molecular dynamics, and analysis steps behind one Python CLI while delegating scientific heavy lifting to established tools such as ChimeraX, RDKit, Meeko, AutoDock Vina, DOCK6, Open Babel, and Amber.

Current package version: `2.2.1`.

## What NexusMol Does

NexusMol currently supports:

- Fetching receptor assemblies and non-covalent ligands from RCSB.
- Cleaning receptors and changing residue names or protonation states with ChimeraX.
- Preparing ligands from SMILES CSV files or SDF files for Vina (`.pdbqt`) or DOCK6 (`.mol2`).
- Running AutoDock Vina and DOCK6 docking batches in parallel.
- Building solvated Amber systems from prepared receptors and docked ligand poses.
- Running Amber minimization, heating, equilibration, and production workflows.
- Running a CPPTRAJ-based analysis workflow for existing Amber trajectories.

## Prerequisites

Use the conda environment in this repository as the primary installation path. It installs the Python scientific stack and several command-line tools used by the pipelines.

Required for the base CLI and most workflows:

- Conda or Mamba.
- Python 3.11.
- Open Babel.
- RDKit.
- Meeko.
- PyYAML, Pydantic, and Typer.

To install anaconda (or miniconda), see [https://www.anaconda.com/download](https://www.anaconda.com/download). Other required libraries are automatically installed on setup.

Workflow-specific external software:

| Workflow | External requirements |
| --- | --- |
| Fetch | Network access to RCSB services through `rcsb-api`. |
| Receptor prep and mutation | ChimeraX executable path configured as `common.chimerax` or `libs.chimerax`. |
| Vina docking | AutoDock Vina, Meeko receptor preparation tools, ChimeraX. |
| DOCK6 docking | DOCK6 installation, legacy UCSF Chimera, ChimeraX. |
| System building and Amber MD | AmberTools/Amber on `PATH`, `AMBERHOME` set, and `pmemd.cuda` available for MD runs. |
| MD analysis | AmberTools `cpptraj` and `AMBERHOME` set. |

## Installation

Go to your desired folder to install the repository:

```bash
git clone https://github.com/kienkanne/NexusMol
```

From the repository root:

```bash
conda env create -f environment.yaml
conda activate nexus
pip install -e ".[test]"
```

Verify that the package imports:

```bash
python -c "import nexus; print('nexus import ok')"
```

If you use Amber through an environment module, load it before running `nexus prep sysmd`, `nexus md amber`, or `nexus md analyze`:

```bash
module load amber/24
echo "$AMBERHOME"
```

Configure executable paths in YAML files when they are not available at the defaults:

```yaml
libs:
  chimerax: /usr/local/chimerax/bin/ChimeraX
  chimera: /usr/local/chimera/chimera-1.8/bin/chimera
  dock_home: /path/to/dock6
```

To install these tools, see the links below:

- AMBER: [https://ambermd.org/GetAmber.php](https://ambermd.org/GetAmber.php)
- UCSF DOCK6: [https://github.com/docking-org/dock6](https://github.com/docking-org/dock6)
- UCSF ChimeraX: [https://www.cgl.ucsf.edu/chimerax/download.html](https://www.cgl.ucsf.edu/chimerax/download.html)
- UCSF Legacy Chimera: [https://www.cgl.ucsf.edu/chimera/download.html](https://www.cgl.ucsf.edu/chimera/download.html) 

## Quick Start

The examples below show the intended command flow. The config files in `examples/*.yaml` are useful templates, but their absolute paths are machine-specific, so copy them and adjust paths before running.

### 1. Fetch Structures

```bash
nexus fetch rcsb -i 6W63 -i 7K40 -o fetched_structures -l ligand
```

`fetch rcsb` accepts one or more PDB IDs, or a text file path where each line is an ID. The command downloads biological assemblies as `.cif` files and non-covalent ligands as `.sdf` files.

### 2. Prepare Receptors

```bash
nexus prep rec -i fetched_structures -o cleaned_receptors -s "_cleaned.pdb" -d
```

`-d/--dry` removes water during ChimeraX cleaning. The command accepts one receptor file or a folder containing `.pdb` and `.cif` files.

Change protonation states or residue names:

```bash
nexus prep mutate \
  -i cleaned_receptors/6W63_cleaned.pdb \
  -o mutated_receptors \
  -s "_mutated.pdb" \
  -m ":41-HIP" \
  -m ":145-CYM"
```

Mutation strings use `selection-NEW_RES`, where `selection` is passed to ChimeraX and `NEW_RES` is the residue name to assign. Note that if the protonation state is changed, `NEW_RES` is used only to change the protonation state, while the residue stays standardized. See [examples/REFERENCES.md](examples/REFERENCES.md) for detailed selection syntax and AMBER residue naming conventions.

### 3. Prepare Ligands

For Vina:

```bash
nexus prep ligdock -i ligands.csv -o vina_ligands -s "_prepared.pdbqt"
```

For DOCK6:

```bash
nexus prep ligdock -i ligands.csv -o dock6_ligands -s "_prepared.mol2"
```

The CSV format must be exactly:

```csv
smiles,name
CC(=O)OC1=CC=CC=C1C(=O)O,aspirin
CC1=C(C=C(C=C1)C(C)C)O,carvacrol
```

The command also accepts an SDF file or a directory of `.sdf` files. Output format is selected by the suffix: `.pdbqt` uses Meeko, and `.mol2` uses Open Babel.

### 4. Dock Ligands

Vina:

```bash
nexus dock vina -c vina_config.yaml
```

DOCK6:

```bash
nexus dock dock6 -c dock6_config.yaml
```

Both docking commands load a YAML config, prepare receptor-specific docking inputs, run ligand/receptor pairs through GNU Parallel, write score summaries, and copy selected files to the configured results directory.

### 5. Build and Simulate an Amber System

Build a solvated system:

```bash
nexus prep sysmd -c sysmd_config.yaml
```

Run Amber MD:

```bash
nexus md amber -c amber_md.yaml
```

Analyze an existing trajectory:

```bash
nexus md analyze -p system.prmtop -t prod1.nc -m ":1-198" -n run1 -o analysis_output
```

## Output Conventions

Docking and MD config loaders append `common.project_name` to both the working and results parent directories:

```text
artifacts/<project_name>/
results/<project_name>/
```

Working directories contain intermediate files plus:

- `<project_name>_run.log` - combined console and file log.
- `<project_name>_manifest.json` - stage status and timing metadata.
- `<project_name>_state.json` - per-stage status and optional checkpoint output.

Docking results are copied into receptor-specific folders in `results/<project_name>/` when using the default `mix` behavior.

## Project Structure

```text
src/nexus/
  cli/                  Typer command groups and entrypoint
  core/
    executors/          Shell, GNU Parallel, and Python parallel wrappers
    trackers/           Logging, manifest, and state helpers
  dock/                 Docking configs, Vina, DOCK6, and shared utilities
  fetch/                RCSB fetch config and pipeline
  md/                   Amber MD and CPPTRAJ analysis workflows
  prep/                 Receptor, mutation, ligand, and sysmd preparation
  validate/             Disabled validation loader and RMSD helpers
examples/
  EXAMPLES.md           Example command walkthrough
  *.yaml                Example config templates with local paths
docs/
  *.md                  Pointers to the canonical root-level docs
```

## Documentation

- [Architecture](ARCHITECTURE.md)
- [Configuration Reference](CONFIGURATION.md)
- [Developer Guide](DEVELOPER_GUIDE.md)
- [Data Flow](DATA_FLOW.md)
- [Security and Bug Analysis](SECURITY_AND_BUGS.md)
- [Changelog](CHANGELOG.md)

## Development and Tests

Install the editable package with test dependencies:

```bash
conda activate nexus
pip install -e ".[test]"
pytest
```

Many integration paths require external scientific tools and real structure inputs. For fast local iteration, start with CLI help checks, config loading, and small ligand/receptor fixtures before launching full docking or MD jobs.

Contribution setup, branch naming, debugging tips, and extension guidance live in [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md).
