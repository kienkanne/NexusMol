# Developer Guide

This guide is for contributors working on NexusMol locally. It focuses on the current codebase rather than historical documentation.

## Local Environment Setup

1. Create and activate the conda environment:

```bash
conda env create -f environment.yaml
conda activate nexus
```

2. Install NexusMol in editable mode with test dependencies:

```bash
pip install -e ".[test]"
```

3. Confirm the package imports:

```bash
python -c "import nexus; print('nexus import ok')"
```

`nexus --help` should be the normal smoke test, but it can currently fail offline because the fetch command imports `rcsb-api` at CLI import time. That import-time network behavior is tracked in `SECURITY_AND_BUGS.md`.

4. Install or load workflow-specific external tools:

| Tool | Needed for |
| --- | --- |
| ChimeraX | receptor cleaning, mutation, Vina and DOCK6 pocket generation |
| Legacy UCSF Chimera | DOCK6 DMS generation |
| DOCK6 | `nexus dock dock6` |
| AmberTools/Amber | `nexus prep sysmd`, `nexus md amber`, `nexus md analyze` |
| OpenMM | `nexus md openmm` |
| Vina | `nexus dock vina` |
| Open Babel | ligand conversion and pose splitting |
| GNU Parallel | legacy compatibility only; new workflows do not depend on it directly |

5. Set required environment variables when applicable:

```bash
module load amber/24
echo "$AMBERHOME"
```

6. Update YAML config paths for your machine:

```yaml
libs:
  chimerax: /usr/local/chimerax/bin/ChimeraX
  chimera: /usr/local/chimera/chimera-1.8/bin/chimera
  dock_home: /path/to/dock6
```

## Repository Tour

```text
src/nexus/cli/          Typer commands
src/nexus/core/         execution wrappers, trackers, logging/state
src/nexus/fetch/        RCSB fetch pipeline
src/nexus/prep/         receptor, mutation, ligand, and sysmd preparation
src/nexus/dock/         docking configs, Vina, DOCK6, score summaries
src/nexus/md/           Amber pipeline, OpenMM pipeline, and CPPTRAJ analysis
src/nexus/validate/     disabled validation code path
examples/*.yaml         example config templates
```

## Development Workflow

Use short-lived topic branches:

| Change type | Branch pattern |
| --- | --- |
| Feature | `feat/<area>-<short-name>` |
| Bug fix | `fix/<area>-<short-name>` |
| Documentation | `docs/<topic>` |
| Maintenance | `chore/<topic>` |

Recommended loop:

1. Start from a clean working tree.
2. Make a small, focused change.
3. Add or update tests when the behavior can be tested without proprietary tools or large data.
4. Run fast checks locally.
5. Update the relevant root-level documentation when CLI behavior, config fields, outputs, or prerequisites change.
6. Keep `CHANGELOG.md` changes for explicit release/update work only.

## Running Tests

The package defines a `test` extra with `pytest`:

```bash
pip install -e ".[test]"
pytest
```

Many workflows depend on external binaries and large scientific inputs, so unit tests should isolate pure Python behavior where possible:

- Config validation and path normalization.
- CSV parsing.
- Command construction.
- Score parsing.
- Manifest and state handling.
- Error paths for missing inputs.

For integration testing, use tiny fixtures and set `n_jobs: 1` first. Full Vina, DOCK6, Amber, and OpenMM tests should be separated from fast unit tests because they require installed external programs.

## Coding Patterns

Follow the current architecture:

- Put command-line entrypoints in `src/nexus/cli/`.
- Put YAML models in `*_config.py` files.
- Keep pipeline classes thin. They should orchestrate stages, not bury command construction.
- Put external command construction in helper functions.
- Use `pathlib.Path` for filesystem paths.
- Use Pydantic defaults and validation instead of ad hoc config mutation where practical.
- Install runtime services through `setup_context()` and read them with `PipelineContext.get_ctx()`.
- Wrap major stages with `main_tracker()` so failures update `manifest.json` and `state.json`.
- Use `shell()` and `python_parallel()` instead of raw subprocess calls unless a tool requires special handling.
- Treat `base()` and `gnu_parallel()` as deprecated compatibility shims only.

## Adding a New CLI Command

1. Add a function to the appropriate `src/nexus/cli/*.py` module.
2. Type CLI parameters with Typer annotations.
3. Load or construct a config object.
4. Import the pipeline inside the command body to keep CLI import time light.
5. Register new command groups in `src/nexus/cli/main.py` when needed.
6. Add examples and config fields to `CONFIGURATION.md`.

## Adding a Pipeline Stage

1. Decide whether the stage is pure Python, one shell command, many shell commands, or many Python tasks.
2. Use the matching executor:
   - `shell()` for one external command.
   - `python_parallel()` for independent Python callables.
   - `base()` only when maintaining old call sites.
   - `gnu_parallel()` only when maintaining old call sites.
3. Wrap the stage with `main_tracker(cfg, "Stage Name")`.
4. Return paths or simple serializable values if the stage output may be stored in `state.json`.
5. Make failures explicit with `ValueError`, `FileNotFoundError`, or `RuntimeError` before launching expensive external work.

## Debugging Tips

- Start with `nexus <group> <command> --help` to confirm CLI parsing.
- Run with the smallest possible receptor/ligand set.
- Set `common.n_jobs: 1` or `ligdock.n_jobs: 1` to simplify logs.
- Inspect `artifacts/<project>/run.log` for executed commands and stderr.
- Inspect `artifacts/<project>/manifest.json` for stage timings and failure reasons.
- Inspect `artifacts/<project>/state.json` for the last stage status.
- For ChimeraX selection issues, reproduce the selection in ChimeraX before rerunning the full pipeline.
- For Amber workflows, check `AMBERHOME`, confirm `pdb4amber`, `tleap`, `antechamber`, `parmchk2`, `pmemd.cuda`, and `cpptraj` are on `PATH`.
- For OpenMM workflows, confirm the OpenMM Python environment can import the package and that CUDA is available when the pipeline selects the CUDA platform.
- For ligand preparation failures, validate the CSV header exactly as `smiles,name` and reduce to one ligand while debugging.
- For Vina and DOCK6 score-summary failures, verify that scored pose files were created before `write_summary_csv()` runs.

## Known Development Hotspots

See `SECURITY_AND_BUGS.md` for current defects and remediation suggestions. High-priority areas include fetch config handling, sysmd receptor-only behavior, ligand-prep result/name alignment when parallel jobs fail, docking mode propagation, deprecated executor cleanup, and MD analysis working-directory restoration.

## Current Architecture Notes

- `PipelineContext` now owns the active logger, manifest, and run state.
- `shell()` and `python_parallel()` are context managers rather than simple wrappers.
- `main_tracker()` no longer depends on config objects directly.
- Docking and MD configs now derive project-scoped output folders from `common.project_name`.
- The OpenMM pipeline is the new MD path alongside the Amber pipeline.
