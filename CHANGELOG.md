# Changelog

## 1.4.0
- Added the new validation module with `compdd validate_run_vina` and `compdd validate_run_dock6`.
- Validation mode now loads receptor and ligand sets from a validation data root and forces matched docking mode.
- Added RMSD analysis for validation outputs:
  - Vina uses `pdbqt` pose parsing.
  - DOCK6 uses `mol2` pose parsing.
- Recommended validation dataset layout: a coreset root with recursive `_protein.pdb`, `_pocket.pdb`, and `_ligand.sdf` entries.
- Added dedicated docs for validation and test-set structure.

## 1.3.2
- Receptor configuration is now fully normalized and resolved at config-load time via `validate_and_normalize_receptors()` in `src/compdd/configs/config_helpers.py`.
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
