# Changelog

## 2.4.2

- Added `path.clear` global config option to optionally clear the global scratch directory during pipeline cleanup (use with caution).
- Added option to specifiy ligand charge in `nexus md build`.
- Rewrote unit tests in `tests/`.

## 2.4.1

- Added options for `nexus md analyze`, giving customizable cpptraj outputs
- Added options for `nexus md mmpbsa`, such as `gb`, `pb`, or `decomp` for free energy calculation methods.
- Updated visualization figures for `nexus md analyze` to a higher quailty and utilizing the cpptraj outputs more.
- Added visualization figures for `nexus md mmpbsa`.

## 2.4.0

- Added global configuration at `~/.config/nexus/config.yaml`; added `nexus config init`, `nexus config show`, and `nexus config validate`.
- Moved machine-specific paths to global config fields: `software.chimerax`, `software.chimera`,  `software.dock6`, and global scratch configuration with `path.scratch_dir`.
- Unified YAML loading through `nexus.core.utils.load_config.load_config`, which attaches global config and creates job-scoped scratch/results directories for configs with `common.job_name`.
- Reorganized MD source modules into `md/build`, `md/run`, `md/analyze`, and `md/mmpbsa`.
- `engine.program` now selects `vina` or `dock6` for `dock`; `amber` or `openmm` for `md`.
- Replaced old top-level example YAML files with `examples/configs/` and moved reusable inputs into `examples/inputs/`.
- Fixed Pydantic `default_factory` usage for prep, docking, and MD run sub-configs so optional YAML sections can be omitted safely.
- Rewrote README, docs, and examples for the current architecture, command hierarchy, configuration models, and workflow outputs.

## 2.3.2

- Added RMSD clustering analysis for docking pipelines.
- Updated docking summary outputs to per-receptor `Scores_<job_name>_<receptor>.csv` and `Clusters_<job_name>_<receptor>.csv`.
- Added MM-PBSA for free energy calculation of an MD trajectory via `nexus md fbe`.
- Improved consistency in the MD analysis notebook.

## 2.3.1

- OpenMM now runs NVT heating and NPT heating.
- Added safe fallback for AMBER and OpenMM on machines without GPU.
- Added more explanatory comments to `examples/`.
- Added global CLI verbosity control: `--silence`. Levels: `0` prints informational messages, `1` mutes `INFO`, and `2` mutes `INFO`, `DEBUG`, and `WARNING`.

## 2.3.0

- Overhauled `src/nexus/core` to use global `PipelineContext` setup, context-managed `shell()` and `python_parallel()`, and simplified stage tracking.
- Marked `core/executors/base` and `core/executors/gnu_parallel` as deprecated.
- Removed GNU Parallel from `environment.yaml`.
- Removed MD trajectory files from examples.
- Removed the `validate` module.

## 2.2.2

- Added OpenMM molecular dynamics pipeline with `nexus md openmm`.
- `nexus md openmm` uses a similar config format as `nexus md amber`, running minimization, heating, equilibration, and production.
- Output trajectories are written in `.dcd` format, and the log file is a CSV-like time series.

## 2.2.1

- `nexus prep mutate` now changes protonation state while keeping standard residue names.
- Added `metadata` fields for docking and MD pipelines.

## 2.2.0

- Rewrote documentation.
- Fixed DOCK6 bugs on missing output docked poses.
- Fixed MD final copy missing trajectory data.
- Moved imports inside functions to reduce CLI load time.
- Regenerated example outputs.

## 2.1.0

- Added MD analysis support with `nexus md analyze`.
- Added CPPTRAJ outputs for RMSD/RMSF, hydrogen bonds, secondary structure, PCA, clustering, and visualization.

## 2.0.0

- Added Amber MD support with `nexus md amber`.
- Added solvated system building through `nexus prep sysmd`.
- Updated preparation docs for `nexus prep ligdock` and SysMD config flags.

## 1.5.3

- Fixed inconsistencies in the dock pipeline to be compatible with the new executors.
- Added receptor bundles for DOCK6.
- Simplified docking config to require prepared receptors and ligands from `nexus prep`.
- Added simple syntax for `nexus fetch`.
- Temporarily disabled the validation pipeline.

## 1.5.2

- Separated ligand preparation into `nexus prep ligdock`.
- Added simple CLI syntax for small `nexus prep` tasks.
- Added `nexus prep mutate`.

## 1.5.1

- Integrated ChimeraX receptor preparation with the RCSB fetching pipeline.
- Docking pipelines now require cleaned PDB/CIF inputs.
- Selection strings are now ChimeraX based.

## 1.5.0

- Added the `nexus` CLI entrypoint.
- Renamed the package namespace from `compdd` to `nexus`.
- Added `nexus fetch rcsb`, `nexus validate vina`, and `nexus validate dock6`.

## 1.4.1

- Added `compdd retrieve` CLI support for RCSB retrieval.
- Added CIF support for docking inputs.
- Simplified validation configuration.

## 1.4.0

- Added validation workflows with `compdd validate_run_vina` and `compdd validate_run_dock6`.
- Added RMSD analysis for validation outputs.

## 1.3.2

- Normalized receptor configuration at config-load time.
- Added per-receptor selection CSV parsing.
- Added reference pocket matching by base name.

## 1.3.1

- Refreshed docs for the 1.3.0 pipeline refactor.
- Removed non-working CASF validation and RCSB parsing documentation.

## 1.3.0

- Re-merged docking and ligand configuration into one YAML file.
- Added per-receptor bundle support.
- Parallelized multi-receptor docking workflows.
- Improved Vina and DOCK6 ligand preparation.

## 1.2.0

- Split docking and ligand configuration into separate YAML files.
- Added ligand source, prepared suffix, and preparation tool support.
- Added RDKit/Meeko ligand preparation with PDBQT output and DOCK6 MOL2 conversion.

## 1.1.0

- Supported end-to-end Vina and DOCK6 docking workflows from a single config file.
