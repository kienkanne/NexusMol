# NexusMol

NexusMol is a command-line toolkit for structure-based drug discovery workflows. It coordinates common fetching, preparation, docking, molecular dynamics, and trajectory-analysis tasks while delegating scientific work to established tools such as ChimeraX, RDKit, Meeko, AutoDock Vina, DOCK6, Open Babel, AMBER, and OpenMM.

Current package version: `2.4.0`.

## What NexusMol Does

NexusMol currently supports:

- Fetching receptor assemblies and non-covalent ligands from RCSB.
- Cleaning receptors and changing residue names or protonation states with ChimeraX.
- Preparing ligands from SMILES CSV files or SDF files for Vina (`.pdbqt`) or DOCK6 (`.mol2`).
- Running AutoDock Vina and DOCK6 docking batches in parallel.
- Building solvated AMBER systems from prepared receptors and docked ligand poses.
- Running AMBER and OpenMM minimization, heating, equilibration, and production workflows.
- Running a CPPTRAJ-based analysis workflow for existing trajectories.

## Install

```bash
git clone https://github.com/kienkanne/NexusMol
cd NexusMol
conda env create -f environment.yaml
conda activate nexus
pip install -e ".[test]"
```

Verify the install:

```bash
nexus --help
python -c "import nexus; print('nexus import ok')"
```

The conda environment installs the Python dependencies plus Open Babel, Vina, Meeko, RDKit, OpenMM, and `rcsb-api`. Some workflows still require separately installed external programs:

| Workflow | External tools |
| --- | --- |
| Receptor prep and mutation | ChimeraX |
| Vina docking | ChimeraX, Meeko receptor tools, AutoDock Vina |
| DOCK6 docking | ChimeraX, legacy UCSF Chimera, DOCK6 |
| MD build | AmberTools, `AMBERHOME`, Open Babel |
| Amber MD | AmberTools, `AMBERHOME`, `pmemd.cuda` or `pmemd` |
| OpenMM MD | OpenMM and a suitable platform such as CUDA or CPU |
| MD analysis | AmberTools `cpptraj`, `AMBERHOME` |

To install the external programs, see the links below:

- AMBER: [https://ambermd.org/GetAmber.php](https://ambermd.org/GetAmber.php)
- UCSF DOCK6: [https://github.com/docking-org/dock6](https://github.com/docking-org/dock6)
- UCSF ChimeraX: [https://www.cgl.ucsf.edu/chimerax/download.html](https://www.cgl.ucsf.edu/chimerax/download.html)
- UCSF Legacy Chimera: [https://www.cgl.ucsf.edu/chimera/download.html](https://www.cgl.ucsf.edu/chimera/download.html) 

## Global Configuration

Nexus now keeps machine-specific paths in:

```text
~/.config/nexus/config.yaml
```

Create and edit it:

```bash
nexus config init
nexus config show
nexus config validate
```

The global config stores executable paths and the parent scratch directory used by tracked workflows:

```yaml
software:
  chimerax: /path/to/ChimeraX
  chimera: /path/to/chimera
  dock6: /path/to/dock6
path:
  scratch_dir: /path/to/nexus_scratch
```

Tracked workflows create a job-scoped scratch folder under `path.scratch_dir` and a job-scoped results folder under each workflow config's `common.output_dir`.

## CLI Overview

```text
nexus
  config init|show|validate
  fetch rcsb
  prep rec|mutate|lig
  dock run
  md build|run|analyze|mmpbsa
```

If you use Amber through an environment module, load it before running `nexus prep build`, `nexus md amber`, or `nexus md analyze`:

```bash
module load amber/24
echo "$AMBERHOME"
```

## Quick Start

Start with [examples/EXAMPLES.md](examples/EXAMPLES.md). The sample workflow configs live in [examples/configs](examples/configs). The config files in `examples/*.yaml` are useful templates, but their absolute paths are machine-specific, so copy them and adjust paths before running.

## Configuration Loading

YAML handling has been consolidated around Pydantic models and `nexus.core.utils.load_config.load_config`. Workflow configs are validated by the active model, then the loader attaches the global config and creates job directories when the config has `common.job_name`.

The current workflow config models are:

| Area | Model | Command |
| --- | --- | --- |
| Fetch | `FetchConfig` | `nexus fetch rcsb` |
| Prep | `PrepConfig` | `nexus prep rec`, `mutate`, `lig` |
| Docking | `DockConfig` | `nexus dock run` |
| MD build | `BuildConfig` | `nexus md build` |
| MD run | `MDConfig` | `nexus md run` |
| MD analysis | `AnalyzeConfig` | `nexus md analyze` |
| MM-PBSA/GBSA | `MMPBSAConfig` | `nexus md mmpbsa` |

The previous independent loaders and old command-specific config blocks are no longer documented as user-facing entry points.

## Output Conventions

For configs with `common.job_name`, Nexus creates:

```text
<global scratch_dir>/<job_name>/
<common.output_dir>/<job_name>/
```

Tracked workflows write:

- `<job_name>_run.log`
- `<job_name>_manifest.json`
- `<job_name>_state.json`

Docking results are grouped by receptor:

```text
results/<job_name>/<receptor>/
  <receptor>.pdb or <receptor>.cif
  <receptor>_pocket.pdb or <receptor>_pocket.mol2
  Scores_<job_name>_<receptor>.csv
  Clusters_<job_name>_<receptor>.csv
  poses/
```

MD build writes `<job_name>.prmtop`, `<job_name>.inpcrd`, and `<job_name>.pdb`. MD run copies the input topology, production trajectories/restarts/logs, and trackers into the job results folder.

## Documentation

- [Configuration](docs/CONFIGURATION.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Data Flow](docs/DATA_FLOW.md)
- [Developer Guide](docs/DEVELOPER_GUIDE.md)
- [Changelog](CHANGELOG.md)

## Development

```bash
conda activate nexus
pip install -e ".[test]"
pytest
```

Most scientific workflows require external tools and real input data, so fast tests focus on config validation, file discovery, command construction, score parsing, and utility behavior.
