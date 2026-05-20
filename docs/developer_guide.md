# Developer Guide

Quick notes for contributors and developers.

## Local setup

1. Create the conda environment and activate it:

```bash
conda env create -n compdd -f environment.yaml
conda activate compdd
pip install -e .
```

2. Run a pipeline locally for quick testing:

```bash
compdd run_vina --config sample_configs/sample_docking.yaml
compdd run_dock6 --config sample_configs/sample_docking.yaml
```

Check `artifacts/` and `results/` for produced files during development.

## Receptor Bundle Architecture (1.3.2+)

As of 1.3.2, receptor configuration is fully normalized at config-load time:

1. `load_config()` calls `validate_and_normalize_receptors()` in `src/compdd/configs/config_helpers.py`.
2. This function:
   - Extracts all PDB files from the configured paths/directories.
   - Parses per-receptor selection CSVs (if provided) to map receptor names → selection strings.
   - Matches reference pocket files to receptors by base name (if multiple references are provided).
   - Builds `ReceptorConfigBundle` objects (defined in `config_helpers.py`) with:
     - `receptor: Path` — the PDB file path.
     - `name: str` — the receptor name (stem of the PDB file).
     - `selection_string: Optional[str]` — the resolved PyMOL selection (or `None` for reference mode).
     - `reference_path: Optional[Path]` — the matched reference pocket file (or `None` for selection mode).
   - Attaches the list of bundles to `cfg.receptors.bundles`.
3. Prep functions (e.g., `_prep_rec` in Vina and DOCK6 backends) accept receptor bundles and prefer their pre-resolved values:
   - If a bundle has `selection_string`, it is used directly (no CSV parsing at runtime).
   - If a bundle has `reference_path`, it is used directly (no base-name matching at runtime).
   - Fallback to legacy `cfg.receptors.selection`/`cfg.receptors.reference` parsing is preserved for backward compatibility.

This design ensures that all selection CSV parsing and reference matching happens once at config-load time, making errors visible immediately and avoiding confusing runtime failures.

## Adding a new pipeline backend

1. Create a new package `compdd.<backend>` with a `<backend>_pipeline.py` implementing a dataclass with a `run()` method mirroring `VinaPipeline`/`DOCK6Pipeline`.
2. Implement backend helpers and decorate IO/exec functions with `@main_tracker` and `@base`/`@gnu_parallel`.
3. Add a subparser in `src/compdd/cli/main.py` and call your pipeline when the subcommand is used.

## Testing

- The repository includes basic tests under `tests/`. Run them with `pytest`.
- When testing receptor configuration, verify that `validate_and_normalize_receptors()` correctly parses selection CSVs and matches references before the pipeline runs.
- Test multiple receptors with per-receptor selection CSVs to ensure the bundle-building logic handles CSV parsing correctly.

## Debugging tips

- Check `run.log` in the configured `working_dir` for runtime output and stack traces.
- Inspect `manifest.json` and `state.json` to see which stages completed and their timings.
- When developing, use small ligand CSVs and reduce `n_jobs` to iterate quickly.


## Validation Development

Version 1.4.0 introduces the new validation module. The validation workflow is implemented in `src/compdd/validation_coreset` and includes:

- `validation_config.py` for loading a validation dataset and overwriting receptor/ligand inputs.
- `rmsd.py` for computing per-pose RMSDs for Vina (`.pdbqt`) and DOCK6 (`.mol2`).
- CLI support via `validate_run_vina` and `validate_run_dock6`.

The validation dataset structure is intentionally generic and is recommended for future test sets. Use a single root folder containing recursive validation entries with `_protein.pdb`, `_pocket.pdb`, and `_ligand.sdf` files.
