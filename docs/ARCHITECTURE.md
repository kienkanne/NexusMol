# Architecture

NexusMol is organized as a thin orchestration layer around external scientific programs. The Python package owns command parsing, YAML configuration, path resolution, staged execution, logging, state tracking, score parsing, and result collection. Computational work is performed by domain tools such as ChimeraX, RDKit, Meeko, Vina, DOCK6, Open Babel, AmberTools, and Amber.

## Component Map

| Layer | Modules | Responsibility |
| --- | --- | --- |
| CLI | `src/nexus/cli/` | Typer command groups and options. |
| Global config | `src/nexus/config.py` | Loads `~/.config/nexus/config.yaml`. |
| Workflow config | `*_config.py`, `core/utils/load_config.py` | YAML parsing, Pydantic validation, global config attachment, job directory setup. |
| Fetch | `src/nexus/fetch/` | RCSB structure and ligand retrieval. |
| Prep | `src/nexus/prep/` | Receptor cleaning, mutation/protonation, ligand preparation. |
| Dock | `src/nexus/dock/` | Vina and DOCK6 docking orchestration plus score/cluster summaries. |
| MD | `src/nexus/md/` | System construction, AMBER and OpenMM MD pipelines, CPPTRAJ analysis (dynamic input generation), and MMPBSA free energy (dynamic input generation). |
| Executors | `src/nexus/core/executors/` | Shell and Python-parallel execution helpers. |
| Trackers | `src/nexus/core/trackers/` | Run logs, manifests, state files, and stage tracking. |
| Utilities | `src/nexus/core/utils/` | YAML config loader and file extractor. |

## CLI Entrypoint

The package exposes one console script:

```text
nexus = nexus.cli.main:main
```

Root help:

```text
nexus [OPTIONS] COMMAND [ARGS]...
```

Global option:

| Option | Description |
| --- | --- |
| `--silence INTEGER` | `0` default, `1` mutes info logs, `2` mutes info/debug/warning logs. Tracker stage messages remain visible. |

`src/nexus/cli/main.py` registers five command groups:

| Command group | Status | Main commands |
| --- | --- | --- |
| `nexus config` | Active | `init`, `show`, `validate` |
| `nexus fetch` | Active | `rcsb` |
| `nexus prep` | Active | `rec`, `mutate`, `lig`|
| `nexus dock` | Active | `run` |
| `nexus md` | Active | `build`, `run`, `analyze`, `mmpbsa`|

The command hierarchy is intentionally workflow-oriented. Backends are selected in config files:

- `dock run` uses `engine.program: vina` or `engine.program: dock6`.
- `md run` uses `engine.program: amber` or `engine.program: openmm`.

## Configuration Lifecycle

Tracked workflow commands follow this pattern:

1. The CLI receives `-c/--config`.
2. `load_config(Model, path)` reads YAML with PyYAML.
3. Pydantic validates the model and applies defaults.
4. The global config is loaded from `~/.config/nexus/config.yaml`.
5. The config object receives `_global`.
6. If the model has `common.job_name`, nexus creates:

```text
<common.output_dir>/<job_name>/
<global path.scratch_dir>/<job_name>/
```

7. `setup_context()` installs a `TrackerContext` with logger, manifest, and run state.
8. The pipeline executes tracked stages.

Prep and fetch commands support optional YAML plus direct CLI flags. Their configs do not require `common.job_name`.

## Global Config Responsibilities

Global config contains machine-specific values that should not be duplicated in every workflow YAML:

```yaml
software:
  chimerax: /path/to/ChimeraX
  chimera: /path/to/chimera
  dock6: /path/to/dock6
path:
  scratch_dir: /path/to/scratch
  clear: false
```

The `path.clear` boolean (default `false`) controls whether pipelines perform an automatic deletion of the parent scratch directory during cleanup; enabling it will remove all job subdirectories and should be used with caution.

This replaced per-workflow software-path blocks and scratch/workspace settings.

## Pipeline Design

Pipelines are small orchestration classes. They validate high-level assumptions, call helper functions, and let `main_tracker()` record stage state.

## Executors

| Helper | Behavior |
| --- | --- |
| `shell()` | Runs one external command, logs stdout/stderr, raises on non-zero exit. |
| `python_parallel()` | Runs Python callables in a `ProcessPoolExecutor`; with `skip=True`, failed tasks are logged and omitted. |

The old `base` and GNU Parallel executor modules have been removed from the current source tree.

## Tracking

`main_tracker(stage_name)` wraps major pipeline stages:

- Logs stage start/completion/failure.
- Updates `<job_name>_manifest.json`.
- Updates `<job_name>_state.json`.
- Finalizes the manifest as failed and re-raises on errors.

`final_copy_trackers(output_dir)` finalizes a successful manifest and copies trackers from scratch to results.

Stage logs emitted by the tracker bypass `--silence` so critical progress remains visible.

## Removed or Reorganized Commands

These older commands are no longer the documented interface:

```text
nexus prep ligdock
nexus prep sysmd
nexus dock vina
nexus dock dock6
nexus md amber
nexus md openmm
nexus md fbe
```

Use the current staged commands instead:

```text
nexus prep lig
nexus dock run
nexus md build
nexus md run
nexus md analyze
```