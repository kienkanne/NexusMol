# Data Flow

This document explains the per-run data flow from inputs to final outputs.

1. Inputs

   - Receptor PDB file (`common.receptor`)
   - Docking config YAML that points to executables, receptor input, and common parameters
   - Ligand config YAML that either points to a `smiles,name` CSV or a directory of prepared ligands

2. Configuration loading

   - `load_config(path)` builds a `RootConfig` and:
     - Calls `validate_and_normalize_receptors()` to:
       - Parse per-receptor selection CSVs (if `pocket_option: selection` and CSV file is provided).
       - Match reference pocket files to receptors by base name (if `pocket_option: reference` and multiple references are provided).
       - Build `ReceptorConfigBundle` objects with resolved selection/reference for each receptor.
       - Attach bundles to `cfg.receptors.bundles`.
     - Augments `cfg.common` with:
       - `working_dir` and `results_dir` (each appended with `project_name`)
       - `logger` (file + stdout)
       - `manifest` (writes `manifest.json`)
       - `runstate` (writes `state.json` for checkpoints)
   - The pipeline (e.g., `VinaPipeline`) uses receptor bundles from `cfg.receptors.bundles` directly when calling prep functions.

3. Pipeline orchestration

   - CLI triggers one of the pipeline classes (e.g., `VinaPipeline`, `DOCK6Pipeline`) or validation workflows (`validate_run_vina`, `validate_run_dock6`).
   - Each pipeline executes a fixed sequence of stages:
     - Resolve or prepare ligands.
     - Prepare receptors (using pre-built bundles from `cfg.receptors.bundles` that already contain resolved selections/references).
     - Docking.
     - Write summary CSV.
     - Copy outputs.
   - Validation workflows additionally compute per-receptor RMSD CSVs for the scored poses.

4. Parallel execution

   - Per-ligand external steps are executed via `compdd.executors.gnu_parallel` which builds command lists and invokes GNU `parallel` with `common.n_jobs`.

5. Outputs

   - The working directory contains intermediate files and the `run.log`, `manifest.json`, and `state.json`.
   - The results directory mirrors selected outputs and contains a `poses/` folder and the `<receptor>_docking_summary.csv`.

6. Checkpointing and resume

   - `main_tracker` and `State` allow stages to be checkpointed; `State.get_output()` can be used by later stages to resume from saved outputs.

7. Example files

   - `run.log` — combined console/file log produced by `setup_logger`.
   - `manifest.json` — stage timings and final status.
   - `state.json` — per-stage checkpoint outputs.



