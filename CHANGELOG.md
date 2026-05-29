# Changelog

## 2.3.0
- Overhauled `src/nexus/core` to use global `PipelineContext` setup, context-managed `shell()` and `python_parallel()`, and simplified stage tracking.
- Marked `core/executors/base` and `core/executors/gnu_parallel` as deprecated; new workflows now use `shell()` and `python_parallel()` directly.
- GNU parallel is no longer listed as a requirement in `environment.yaml`
- MD trajectory files are removed from examples/

## 2.2.2
- Added OpenMM molecular dynamics pipeline with `nexus md openmm`
- `nexus md openmm` uses a similar config format as `nexus md amber`, running end-to-end pipelines with minimization, heating, equilibration, and production
- Output trajectories are written in the `.dcd` format, and the log file is a csv with time series details.

## 2.2.1
- `nexus prep mutate` now only changes the protonation state while keeping standard residue names.
- Added `metadata` field for docking and MD pipeline, allowing to store metadata that is dumped to a JSON file in results directory. Docking also stores csv file paths for each receptor.

## 2.2.0
- Rewrote all documentations.
- Fixed dock6 bugs on missing output docked poses.
- Fixed MD final copy missing trajectory data.
- Moved imports to inside functions, resolving the slow cli loading issue.
- Regenerated example outputs.

## 2.1.0
- Added MD analysis support with `nexus md analyze`.
- `nexus md analyze` runs the full CPPTRAJ analysis workflow on an existing Amber trajectory.
- Generated outputs include RMSD/RMSF data, hydrogen bond analysis, secondary structure analysis, PCA, clustering, and a visualization notebook.
- Added support for `--prmtop`, `--trajin`, `--mask`, optional `--name`, and optional `--output-dir` flags.

## 2.0.0
- Added Amber MD support with `nexus md amber` and sample MD config at `build/sample_configs/amber_md.yaml`.
- Added solvated system building for MD via `nexus prep sysmd` using AmberTools (`pdb4amber`, `antechamber`, `parmchk2`, `tleap`).
- Corrected documentation and examples to match current command usage and actual sample config paths.
- Updated preparation docs to reflect `nexus prep ligdock` and new sysmd config flags.
- Bumped supported package version from `1.5.3` to `2.0.0`.

## 1.5.3
- Fix inconsistencies in the dock pipeline to be compatiable with the new executors, which now is independent of configs.
- Receptor bundles now include all necessary files for DOCK6.
- `copy_to_results()` in dock pipleine now copies the pocket file.
- Config file for docking pipeline is simplified, now required readily prepared receptors and ligands from `nexus prep`
- Added simple syntax for `nexus fetch`, now can parse a file containing pdb ids.
- Valdiation pipeline is temporarily disabled.

## 1.5.2
- Separated ligands preparation from dock pipeline to prep pipeline via `nexus prep ligdock`.
- Added simple cli syntax for small tasks using `nexus prep`
- Remove dependencies of gnu_parallel and python_parallel wrappers on config object.
- Path variables must now be absolute paths, as wrappers don't change to working directory anymore.
- Added `nexus prep mutate` to allow for changing protonation states or side chains of receptors manually.

## 1.5.1
- Moved ChimeraX receptor prepration to be integrated with the rcsb fetching pipeline.
- Docking pipelines now require cleaned pdb/cif inputs.
- Selection string syntax is now ChimeraX based. PyMOL is no longer required.

## 1.5.0
- Added the new `nexus` CLI entrypoint and command grouping: `nexus dock`, `nexus validate`, `nexus fetch` (replacing `compdd retrieve`), and `nexus md` (wip).
- Renamed the top-level package namespace from `compdd` to `nexus` and restructured source code into `src/nexus/` with separate modules for CLI, docking, validation, fetch, executors, and trackers.
- Deprecated the legacy `compdd` package path and updated all documentation and reference examples to the new `nexus` syntax.
- Preserved legacy behavior while making the new module separation and loader names explicit.
- Added `nexus fetch rcsb`, `nexus validate vina`, and `nexus validate dock6` command support.
- Rewrote new unit tests for all modules.

## 1.4.1
- Added new `compdd retrieve` CLI support for direct RCSB retrieval (cif files only) using the RCSB API.
- Docking now supports `cif` input files in addition to `pdb` for modern workflows.
- Validation module updated to be more flexible and simplified by removing legacy support.
- Added unit tests for retrieval and validation configuration behavior.

## 1.4.0
- Added the new validation module with `compdd validate_run_vina` and `compdd validate_run_dock6`.
- Validation mode now loads receptor and ligand sets from a validation data root and forces matched docking mode.
- Added RMSD analysis for validation outputs:
  - Vina uses `pdbqt` pose parsing.
  - DOCK6 uses `mol2` pose parsing.
- Recommended validation dataset layout: a coreset root with recursive `_protein.pdb`, `_pocket.pdb`, and `_ligand.sdf` entries.
- Added dedicated docs for validation and test-set structure.

## 1.3.2
- Receptor configuration is now fully normalized and resolved at config-load time via `validate_and_normalize_receptors()` in `src/compdd/docking_configs/config_helpers.py`.
- Per-receptor selection CSVs are parsed during config loading (not during prep), eliminating runtime selection string parsing bugs and improving error reporting.
- Reference pocket matching by base name is now performed early; matched references are attached to receptor bundles before any prep step.
- Receptor bundles (containing receptor path, name, and pre-resolved selection string or reference path) are built and attached to `cfg.receptors.bundles` during config validation.
- Prep functions (`_prep_rec` in Vina and DOCK6 backends) now accept receptor bundles and prefer pre-resolved selection/reference values, with fallback to legacy cfg-based parsing for backward compatibility.
- `src/compdd/utils/extract_files.py` now only accepts a single file or directory for consistency.
- Improved error messages for missing selections or references to be raised at config-load time rather than during pipeline execution.

## 1.3.1

- Documentation refresh to reflect the 1.3.0 pipeline refactor and multi-receptor support.
- Removed non-working CASF validation and RCSB parsing documentation (the validation CLI remains out-of-band and is no longer advertised in the docs).
- Minor fixes to README, developer guidance, and configuration reference to show `common.mode` (mix|match) and per-receptor result layout.
- Updated examples and tests to validate receptor-bundle handling and naming conventions.

## 1.3.0

- Re-merged docking and ligand configuration into a single YAML file and restored the previous `compdd run_vina` / `compdd run_dock6` CLI workflow.
- Added per-receptor bundle support so Vina and DOCK6 can carry receptor-specific prepared files, configs, and selected-spheres metadata.
- Parallelized the full pipeline for multi-receptor workflows, including receptor preparation, pairing, and docking.
- Improved receptor/ligand matching with `mix` and `match` modes for many-to-many and name-matched docking pairs.
- Updated ligand preparation to use the optimal toolchain: Meeko for Vina ligand charging and Obabel for DOCK6 ligand conversion.
- Refactored DOCK6 docking to avoid rigid hardcoded receptor naming and to support dynamic selected-spheres handling.
- Cleaned up result copying for multi-receptor runs and fixed multiprocessing task pickling during ligand prep.

## 1.2.0

- Split docking and ligand configuration into separate YAML files.
- Replaced full pipeline commands with `compdd run_vina --config ... --ligands ...` and `compdd run_dock6 --config ... --ligands ...`.
- Added ligand `source: smiles|files`, `prepared_suffix`, and `prepare_tool: obabel|meeko` support.
- Added RDKit/Meeko ligand preparation with PDBQT output and DOCK6 MOL2 conversion.
- Made prepared receptor and ligand suffix handling configurable instead of hardcoded to `_prepped`.
- Moved config models into `compdd.configs` and renamed the sample docking config to `sample_configs/sample_docking.yaml`.

## 1.1.0

- Supported end-to-end Vina and DOCK6 docking workflows from a single config file.
- Prepared receptors and ligands, ran docking jobs through GNU parallel, copied selected outputs, and wrote summary CSV files.
