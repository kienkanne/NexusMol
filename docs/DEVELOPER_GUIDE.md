# Developer Guide

This guide is for contributors working on the current Nexus codebase.

## Local Setup

```bash
conda env create -f environment.yaml
conda activate nexus
pip install -e ".[test]"
```

Smoke tests:

```bash
nexus --help
nexus config --help
python -c "import nexus; print('nexus import ok')"
```

Run tests:

```bash
pytest
```

## External Tools

The conda environment covers the Python stack and several open-source tools, but full workflow testing also requires external scientific software:

| Tool | Needed for |
| --- | --- |
| ChimeraX | `prep rec`, `prep mutate`, Vina receptor prep, DOCK6 receptor prep |
| Legacy UCSF Chimera | DOCK6 receptor prep |
| DOCK6 | `dock run` with `engine.program: dock6` |
| AmberTools/Amber | `md build`, Amber `md run`, `md analyze` |
| OpenMM | `md run` with `engine.program: openmm` |
| Open Babel | ligand preparation and MD-build ligand pose processing |
| Vina | `dock run` with `engine.program: vina` |

Machine-specific paths belong in `~/.config/nexus/config.yaml`, not in workflow configs.

## Repository Tour

```text
src/nexus/cli/          Typer command groups
src/nexus/config.py     global config model and helpers
src/nexus/core/         executors, config loading, tracking
src/nexus/fetch/        RCSB fetching
src/nexus/prep/         receptor, mutation, ligand prep
src/nexus/dock/         Vina and DOCK6 workflows
src/nexus/md/build/     Amber system building
src/nexus/md/run/       Amber and OpenMM MD engines
src/nexus/md/analyze/   CPPTRAJ analysis
src/nexus/md/mmpbsa/    MM-PBSA/GBSA
examples/configs/       runnable example YAMLs
docs/                   user and developer documentation
```

## Current Patterns

- Put CLI commands in `src/nexus/cli/`.
- Keep imports for heavy workflow modules inside command functions where practical.
- Define user-facing YAML with Pydantic models in `*_config.py`.
- Use `load_config(Model, path)` for tracked YAML workflows.
- Use the global config for machine-specific software and scratch paths.
- Keep pipeline classes thin; put command construction in helper modules.
- Use `pathlib.Path` for filesystem paths.
- Use `shell()` for external commands and `python_parallel()` for independent Python work.
- Wrap major stages with `main_tracker()`.
- Copy trackers to results with `final_copy_trackers()`.

## Adding a Command

1. Add the Typer function in the correct `src/nexus/cli/*.py` file.
2. Decide whether it uses flags, YAML, or both.
3. Add or update a Pydantic config model if YAML is needed.
4. For tracked workflows, call `load_config(Model, config_path)`.
5. Instantiate a small pipeline or call a focused runner.
6. Update `docs/CLI_REFERENCE.md`, `docs/CONFIGURATION.md`, and relevant examples.

## Adding a Pipeline Stage

1. Validate cheap preconditions before launching external tools.
2. Use `shell()` or `python_parallel()`.
3. Return paths or simple serializable values if checkpoint output may be needed later.
4. Decorate major stages with `@main_tracker("Stage name")`.
5. Keep intermediate files in `cfg._global.path.scratch_dir`.
6. Copy only user-relevant outputs to `cfg.common.output_dir`.

## Testing Guidance

Fast tests should cover:

- Config model validation.
- File discovery with `extract_files()`.
- CSV parsing and filename sanitization.
- Command construction.
- Score parsing and cluster-summary utilities.
- Manifest and run-state behavior.
- Error paths for missing inputs.

Integration tests that call Vina, DOCK6, ChimeraX, Amber, or OpenMM should be isolated because they require external programs and real scientific inputs.

## Debugging

- Start with `nexus <group> <command> --help`.
- Run with one receptor, one ligand, and `n_jobs: 1`.
- Check `<scratch_dir>/<job_name>/<job_name>_run.log` or terminal outputs.
- Check `<scratch_dir>/<job_name>/<job_name>_manifest.json`.
- Check `<scratch_dir>/<job_name>/<job_name>_state.json`.
- For global path issues, run `nexus config show` and `nexus config validate`.
- For ChimeraX selection issues, reproduce the selection inside ChimeraX.
- For Amber workflows, verify `AMBERHOME`, `pdb4amber`, `tleap`, `antechamber`, `parmchk2`, `pmemd`, and `cpptraj` are exported to PATH.

## Manual Review Hotspots

- `nexus md analyze` and `nexus md mmpbsa` now build their pipeline inputs dynamically from flexible YAML or CLI inputs; update tests and examples that assumed static template files and verify notebook filenames in examples.
- Several Pydantic defaults still use mutable list literals in MD run config; those are worth tightening in a code-focused cleanup.
- Fetch/prep commands attach global config differently from tracked YAML workflows; this is intentional today but should be kept consistent in future refactors.
