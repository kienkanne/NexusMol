# Changelog

## 1.2.0

- Added CASF validation workflow with a separate `validate` CLI.
- Split docking and ligand configuration into separate YAML files.
- Replaced full pipeline commands with `compdd run_vina --config ... --ligands ...` and `compdd run_dock6 --config ... --ligands ...`.
- Added ligand `source: smiles|files`, `prepared_suffix`, and `prepare_tool: obabel|meeko` support.
- Added RDKit/Meeko ligand preparation with PDBQT output and DOCK6 MOL2 conversion.
- Made prepared receptor and ligand suffix handling configurable instead of hardcoded to `_prepped`.
- Moved config models into `compdd.configs` and renamed the sample docking config to `sample_configs/sample_docking.yaml`.

## 1.1.0

- Supported end-to-end Vina and DOCK6 docking workflows from a single config file.
- Prepared receptors and ligands, ran docking jobs through GNU parallel, copied selected outputs, and wrote summary CSV files.
