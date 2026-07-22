# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.6.0] - 2026-07-22

### Added

- `nexus md buildpep`, a tleap-based peptide system builder for short sequences: reads a plain-text list of one-letter sequences and builds each one directly via tleap (sequence + solvate + addIonsRand + saveamberparm), skipping the PDB/PDBQT/antechamber ligand-prep path used by `nexus md build`.

### Changed

- Rehauled `CHANGELOG.md` to follow the Keep a Changelog format: every historical entry is now dated and categorized (Added/Changed/Fixed/Removed/Deprecated), and releases are tracked with git tags going forward.

## [2.5.1] - 2026-07-22

### Changed

- Optimized `nexus md analyze`'s cpptraj script to a two-pass execution: one expensive disk read (RMSD/RMSF, hbonds, secondary structure, and caching coordinates for PCA/clustering into memory), followed by a second RAM-speed pass for PCA, clustering, and hbond dataset post-processing.
- `nexus md analyze` now strips water/ions up front, and the PCA/clustering atom mask (`pca_cluster_mask`) and trajectory read interval (`interval`) are configurable instead of hardcoded.
- Made Langevin friction (gamma) configurable per MD stage (heat/eq/prod) for AMBER and OpenMM, instead of fixed values in code.
- Ligand parameterization now uses GAFF2 atom types.

### Removed

- Removed the protein-water (`pw`) hydrogen bond option from `nexus md analyze`: it required retaining solvent, which conflicted with stripping water for the rest of the pipeline, and its output could exceed a fraction of 1.0 from solvent double-counting.

### Fixed

- Fixed `nexus md mmpbsa` to copy the energy and (when enabled) decomposition CSVs to the output directory; previously only the summary `.out` file was copied, silently dropping the per-frame energy/decomposition data.
- Fixed the favourable/unfavourable color legend on MMPBSA per-residue contribution plots, which had blue and red swapped.

## [2.5.0] - 2026-07-22

### Added

- Protein-ligand interaction fingerprints (PLIF) computed for every docked pose via RDKit/ProLIF.

### Changed

- Docking pipelines (`vina`, `dock6`) now write a single PLIF-enriched master dataframe (CSV + pickle) per run instead of the old per-receptor summary CSV; the pickle retains the actual pose molecule objects for downstream work like re-clustering, without redocking.

### Removed

- Removed the post-docking RMSD clustering step: it added little value on top of the pose objects now retained in the master dataframe pickle.

## [2.4.3] - 2026-07-22

### Added

- Added a `no_setup` flag to `load_config` for validating a config without touching directories or the tracker context.

### Fixed

- Fixed `shell()`/`python_parallel()` executors falling back to `DummyLogger`: the tracker context lookup happened outside the try/except meant to catch it.
- Fixed a pydantic issue where `TrackerContext._active_context` was treated as a per-instance field instead of class-level state.
- Fixed `load_config` path handling: `scratch_dir` is now resolved/expanded before creation, and an `output_dir` existence check that never actually ran (a missing method call) now works correctly.

## [2.4.2] - 2026-06-16

### Added

- Added `path.clear` global config option to optionally clear the global scratch directory during pipeline cleanup (use with caution).
- Added option to specify ligand charge in `nexus md build`.

### Changed

- Rewrote unit tests in `tests/`.

## [2.4.1] - 2026-06-10

### Added

- Added options for `nexus md analyze`, giving customizable cpptraj outputs.
- Added options for `nexus md mmpbsa`, such as `gb`, `pb`, or `decomp` for free energy calculation methods.
- Added visualization figures for `nexus md mmpbsa`.

### Changed

- Updated visualization figures for `nexus md analyze` to higher quality, utilizing the cpptraj outputs more.

## [2.4.0] - 2026-06-09

### Added

- Added global configuration at `~/.config/nexus/config.yaml`; added `nexus config init`, `nexus config show`, and `nexus config validate`.

### Changed

- Moved machine-specific paths to global config fields: `software.chimerax`, `software.chimera`, `software.dock6`, and global scratch configuration with `path.scratch_dir`.
- Unified YAML loading through `nexus.core.utils.load_config.load_config`, which attaches global config and creates job-scoped scratch/results directories for configs with `common.job_name`.
- Reorganized MD source modules into `md/build`, `md/run`, `md/analyze`, and `md/mmpbsa`.
- `engine.program` now selects `vina` or `dock6` for `dock`; `amber` or `openmm` for `md`.
- Replaced old top-level example YAML files with `examples/configs/` and moved reusable inputs into `examples/inputs/`.
- Rewrote README, docs, and examples for the current architecture, command hierarchy, configuration models, and workflow outputs.

### Fixed

- Fixed Pydantic `default_factory` usage for prep, docking, and MD run sub-configs so optional YAML sections can be omitted safely.

## [2.3.2] - 2026-06-08

### Added

- Added RMSD clustering analysis for docking pipelines.
- Added MM-PBSA for free energy calculation of an MD trajectory via `nexus md fbe`.

### Changed

- Updated docking summary outputs to per-receptor `Scores_<job_name>_<receptor>.csv` and `Clusters_<job_name>_<receptor>.csv`.
- Improved consistency in the MD analysis notebook.

## [2.3.1] - 2026-06-01

### Added

- Added safe fallback for AMBER and OpenMM on machines without GPU.
- Added more explanatory comments to `examples/`.
- Added global CLI verbosity control: `--silence`. Levels: `0` prints informational messages, `1` mutes `INFO`, and `2` mutes `INFO`, `DEBUG`, and `WARNING`.

### Changed

- OpenMM now runs NVT heating and NPT heating.

## [2.3.0] - 2026-05-29

### Changed

- Overhauled `src/nexus/core` to use global `PipelineContext` setup, context-managed `shell()` and `python_parallel()`, and simplified stage tracking.

### Deprecated

- Marked `core/executors/base` and `core/executors/gnu_parallel` as deprecated.

### Removed

- Removed GNU Parallel from `environment.yaml`.
- Removed MD trajectory files from examples.
- Removed the `validate` module.

## [2.2.2] - 2026-05-27

### Added

- Added OpenMM molecular dynamics pipeline with `nexus md openmm`, using a similar config format as `nexus md amber` and running minimization, heating, equilibration, and production. Output trajectories are written in `.dcd` format, with a CSV-like time series log file.

## [2.2.1] - 2026-05-26

### Added

- Added `metadata` fields for docking and MD pipelines.

### Changed

- `nexus prep mutate` now changes protonation state while keeping standard residue names.

## [2.2.0] - 2026-05-25

### Changed

- Rewrote documentation.
- Moved imports inside functions to reduce CLI load time.
- Regenerated example outputs.

### Fixed

- Fixed DOCK6 bugs on missing output docked poses.
- Fixed MD final copy missing trajectory data.

## [2.1.0] - 2026-05-25

### Added

- Added MD analysis support with `nexus md analyze`.
- Added CPPTRAJ outputs for RMSD/RMSF, hydrogen bonds, secondary structure, PCA, clustering, and visualization.

## [2.0.0] - 2026-05-25

### Added

- Added Amber MD support with `nexus md amber`.
- Added solvated system building through `nexus prep sysmd`.

### Changed

- Updated preparation docs for `nexus prep ligdock` and SysMD config flags.

## [1.5.3] - 2026-05-24

### Added

- Added receptor bundles for DOCK6.
- Added simple syntax for `nexus fetch`.

### Changed

- Simplified docking config to require prepared receptors and ligands from `nexus prep`.
- Temporarily disabled the validation pipeline.

### Fixed

- Fixed inconsistencies in the dock pipeline to be compatible with the new executors.

## [1.5.2] - 2026-05-23

### Added

- Added simple CLI syntax for small `nexus prep` tasks.
- Added `nexus prep mutate`.

### Changed

- Separated ligand preparation into `nexus prep ligdock`.

## [1.5.1] - 2026-05-22

### Changed

- Integrated ChimeraX receptor preparation with the RCSB fetching pipeline.
- Docking pipelines now require cleaned PDB/CIF inputs.
- Selection strings are now ChimeraX based.

## [1.5.0] - 2026-05-21

### Added

- Added the `nexus` CLI entrypoint.
- Added `nexus fetch rcsb`, `nexus validate vina`, and `nexus validate dock6`.

### Changed

- Renamed the package namespace from `compdd` to `nexus`.

## [1.4.1] - 2026-05-20

### Added

- Added `compdd retrieve` CLI support for RCSB retrieval.
- Added CIF support for docking inputs.

### Changed

- Simplified validation configuration.

## [1.4.0] - 2026-05-20

### Added

- Added validation workflows with `compdd validate_run_vina` and `compdd validate_run_dock6`.
- Added RMSD analysis for validation outputs.

## [1.3.2] - 2026-05-19

### Added

- Added per-receptor selection CSV parsing.
- Added reference pocket matching by base name.

### Changed

- Normalized receptor configuration at config-load time.

## [1.3.1] - 2026-05-19

### Changed

- Refreshed docs for the 1.3.0 pipeline refactor.

### Removed

- Removed non-working CASF validation and RCSB parsing documentation.

## [1.3.0] - 2026-05-19

### Added

- Added per-receptor bundle support.

### Changed

- Re-merged docking and ligand configuration into one YAML file.
- Parallelized multi-receptor docking workflows.
- Improved Vina and DOCK6 ligand preparation.

## [1.2.0] - 2026-05-18

### Added

- Added ligand source, prepared suffix, and preparation tool support.
- Added RDKit/Meeko ligand preparation with PDBQT output and DOCK6 MOL2 conversion.

### Changed

- Split docking and ligand configuration into separate YAML files.

## [1.1.0] - 2026-05-17

### Added

- Supported end-to-end Vina and DOCK6 docking workflows from a single config file.
