# Architecture

NexusMol is organized as a thin orchestration layer around external scientific programs. The Python package owns command parsing, YAML configuration, path resolution, staged execution, logging, state tracking, score parsing, and result collection. Computational work is performed by domain tools such as ChimeraX, RDKit, Meeko, Vina, DOCK6, Open Babel, AmberTools, and Amber.

## Component Map

| Layer | Main modules | Responsibility |
| --- | --- | --- |
| CLI | `src/nexus/cli/` | Defines the `nexus` Typer app and command groups. |
| Configuration | `*_config.py` modules | Loads YAML into Pydantic models and performs path/default setup. |
| Pipelines | `fetch/`, `prep/`, `dock/`, `md/` | Coordinates ordered workflow stages. |
| Executors | `src/nexus/core/executors/` | Runs shell commands and Python-parallel tasks through context-managed wrappers. Deprecated `base()` and `gnu_parallel()` shims remain only for compatibility. |
| Trackers | `src/nexus/core/trackers/` | Provides the global `PipelineContext`, writes logs, manifests, and stage state files. |
| Utilities | `dock/utils/`, prep helpers | Shared file extraction, score parsing, copying, and format handling. |

## CLI Entrypoint

The package exposes one console script:

```text
nexus = nexus.cli.main:main
```

`src/nexus/cli/main.py` registers five command groups:

| Command group | Status | Main commands |
| --- | --- | --- |
| `nexus fetch` | Active | `rcsb` |
| `nexus prep` | Active | `rec`, `mutate`, `ligdock`, `sysmd` |
| `nexus dock` | Active | `vina`, `dock6` |
| `nexus md` | Active | `amber`, `analyze`|
| `nexus validate` | Disabled | `vina`, `dock6` return immediately |

## Configuration Lifecycle

Most commands follow this pattern:

1. The CLI receives flags and/or a YAML config path.
2. A loader parses YAML with PyYAML.
3. Pydantic validates known fields and applies defaults.
4. Loader-specific setup resolves paths, creates working directories, and attaches runtime helpers.
5. A pipeline class receives the config object and executes ordered stages.

Docking has the richest loader:

```text
load_dock_config(path)
  -> DockConfig.model_validate(data)
  -> _setup_dirs()
  -> _find_files()
  -> validate_and_normalize_receptors()
  -> setup_context()
```

`_setup_dirs()` appends `common.project_name` to `common.working_dir` and `common.results_dir`, expands environment variables for declared `Path` fields, and prepares runtime paths before `setup_context()` installs:

- `common.logger`
- `common.manifest`
- `common.runstate`

`_find_files()` converts receptor and ligand sources into lists of `Path` objects.

`validate_and_normalize_receptors()` builds receptor bundles that contain the receptor path plus either a resolved ChimeraX selection string or a reference pocket path. Downstream Vina and DOCK6 receptor prep functions consume these bundles directly.

## Pipeline Design

Pipelines are small orchestration classes. They validate high-level assumptions, call helper functions in sequence, and let decorators handle logging and state.

### Fetch

`FetchPipeline` normalizes `fcfg.input` into a list of PDB IDs, defaults `output_dir` to the current directory, and calls `rcsb_fetch()`. `rcsb_fetch()` uses `rcsb-api` to discover non-covalent ligands, downloads ligand SDF files, and downloads biological assembly CIF files.

### Preparation

`RecPipeline` finds `.pdb` and `.cif` inputs, chooses an output suffix, and runs a generated ChimeraX cleaning script.

`MutatePipeline` converts each `selection-RESNAME` string into ChimeraX commands that delete hydrogens, assign residue names, add hydrogens and charges, and save the mutated receptor.

`LigdockPipeline` detects CSV versus SDF input. CSV input is parsed as `smiles,name`; RDKit generates 3D conformers. SDF input is loaded through RDKit. Meeko writes `.pdbqt` outputs for Vina, while Open Babel writes `.mol2` outputs for DOCK6.

`SysmdPipeline` requires `AMBERHOME`, runs `pdb4amber`, optionally selects a docked ligand pose, charges/checks ligand parameters with AmberTools, and runs `tleap` to write `.prmtop` and `.inpcrd`.

### Docking

Both docking backends share this sequence:

1. Set `common.program` to `vina` or `dock6`.
2. Validate ligand suffix (`.pdbqt` for Vina, `.mol2` for DOCK6).
3. Prepare receptor-specific backend inputs.
4. Pair receptors and ligands.
5. Run docking commands through the current executor layer.
6. Parse score files and write CSV summaries.
7. Copy selected artifacts and metadata to results.

Vina receptor prep uses ChimeraX to create a pocket file, then `mk_prepare_receptor.py` to write receptor PDBQT and Vina box config. Vina-specific settings are appended to the config file before docking.

DOCK6 receptor prep uses ChimeraX and legacy Chimera to create receptor/pocket files, then DOCK6 utilities (`sphgen`, `sphere_selector`, `showbox`, `grid`) before running `dock6`.

The docking loaders now normalize receptor bundles through `PipelineContext`-backed config setup, and docs should treat GNU Parallel as a deprecated implementation detail rather than the primary execution model.

### Molecular Dynamics

`AmberPipeline` requires `AMBERHOME`, validates `prmtop` and `inpcrd`, then runs:

```text
minimize -> heat -> equilibrate -> produce -> copy_to_results
```

Each stage renders an Amber input template and launches `pmemd.cuda` through the shared shell executor.

`OpenMMPipeline` uses the same tracked runtime pattern but builds and mutates an OpenMM `Simulation` object directly across setup, minimization, heating, equilibration, production, and final copy.

`nexus md analyze` is not YAML-driven. It renders a CPPTRAJ script from CLI flags, runs `cpptraj`, and copies a visualization notebook into the output directory.

## Executors

| Executor | Behavior |
| --- | --- |
| `shell()` | Context manager that runs one command with `subprocess.run()`, captures stdout/stderr, logs output, and raises on non-zero exit. |
| `python_parallel()` | Context manager that runs Python callables through `ProcessPoolExecutor` and preserves result order. |
| `base()` | Deprecated Python-call wrapper retained for compatibility only. |
| `gnu_parallel()` | Deprecated GNU Parallel wrapper retained for compatibility only. |

`python_parallel(skip=True)` keeps successful jobs and filters/logs failed jobs instead of failing the whole stage. Strict mode raises when a job fails.

## Tracking and Failure Handling

The `main_tracker()` decorator wraps major stages and reads runtime services from the global `PipelineContext`. On start it marks the stage as running in both `manifest.json` and `state.json`. On success it marks the stage done and records timing. On failure it marks the stage failed, records the exception string in the manifest, finalizes the manifest as failed, logs the stack trace, and re-raises the exception.

The current code supports checkpoint-style state storage, but most stages call `main_tracker()` with default `checkpoint=False`, so completed stages are recorded but not skipped automatically on a rerun.

## Runtime Files

For docking and MD workflows, the effective working directory is:

```text
<common.working_dir>/<common.project_name>/
```

The effective results directory is:

```text
<common.results_dir>/<common.project_name>/
```

Common runtime files:

- `<project_name>_run.log`
- `<project_name>_manifest.json`
- `<project_name>_state.json`

## Extending NexusMol

To add a new workflow:

1. Add or extend a Pydantic config model if the workflow needs YAML input.
2. Implement a small pipeline class that owns orchestration only.
3. Put external command construction in helper functions.
4. Use `shell()` and/or `python_parallel()` for execution.
5. Wrap major stages with `main_tracker()`.
6. Add a Typer command in the appropriate `src/nexus/cli/` module.
7. Document config fields in `CONFIGURATION.md` and data movement in `DATA_FLOW.md`.
