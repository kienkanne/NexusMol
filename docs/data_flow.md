# Data Flow

This document explains the per-run data flow from inputs to final outputs.

1. Inputs

   - Receptor PDB file (`common.receptor`)
   - Docking config YAML that points to executables, receptor input, and common parameters
   - Ligand config YAML that either points to a `smiles,name` CSV or a directory of prepared ligands

2. Configuration loading

   - `load_docking_config(path)` builds a `RootConfig` and augments `cfg.common` with:
     - `working_dir` and `results_dir` (each appended with `project_name`)
     - `logger` (file + stdout)
     - `manifest` (writes `manifest.json`)
     - `runstate` (writes `state.json` for checkpoints)
   - `load_ligands_config(path, program=...)` builds a `LigandsConfig`; the CLI passes `vina` or `dock6` from the selected command.

3. Pipeline orchestration

   - CLI triggers one of the pipeline classes (e.g., `VinaPipeline`, `DOCK6Pipeline`).
   - Each pipeline executes a fixed sequence of stages (resolve or prepare ligands, prepare receptor, docking, write summary, copy outputs).

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



