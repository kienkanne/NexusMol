# Configuration Reference

CompDD now uses two Pydantic-backed YAML configs:

- Root config: loaded with `load_config(path)` from `src/compdd/configs/root_config.py` (unified docking config). The loader calls `validate_and_normalize_receptors()` which parses per-receptor selection CSVs and matches references at config-load time, building receptor bundles and attaching them to `cfg.receptors.bundles`.
- Ligand config: loaded internally by the pipeline based on the program selected from the CLI.

Run commands use a single unified config YAML file, and validation commands reuse the same config with test-set data:

```bash
compdd run_vina --config sample_configs/sample_docking.yaml
compdd run_dock6 --config sample_configs/sample_docking.yaml
compdd validate_run_vina --config sample_configs/sample_docking.yaml
compdd validate_run_dock6 --config sample_configs/sample_docking.yaml
```

## Docking Config

- `libs` — locations or executable names for external programs: `obabel`, `parallel`, `vina`, `mgltools`, `dock_home`, `chimerax`, and `chimera`.
- `common.project_name` — appended to `working_dir` and `results_dir`.
- `common.working_dir` — parent path for scratch; the loader appends `project_name`.
- `common.results_dir` — parent path for final results; the loader appends `project_name`.
- `common.prepared_suffix` — suffix used as `<name>_<prepared_suffix>.<ext>` for prepared receptor files.
- `common.padding`, `common.n_jobs`, `common.max_poses` — shared runtime options.

### Receptor Configuration (resolved at config-load time)

- `receptors.pdbs` — path to a single PDB file, a directory, or a list of paths.
- `receptors.pocket_option` — `selection` (use PyMOL selection string or CSV mapping) or `reference` (use reference pocket files).
- `receptors.selection` — PyMOL selection string used for all receptors, or path to a per-receptor selection CSV file.
- `receptors.reference` — single reference pocket file, directory of references, or path; matched to receptors by base name.
- `receptors.reference_suffix` — file suffix used when matching references (default: `_pocket.pdb`).

At config-load time, `validate_and_normalize_receptors()` normalizes these fields:
- Extracts all PDB files from the provided paths/directories.
- If `pocket_option: selection` and a CSV file is provided, parses it to map receptor names to selection strings.
- If `pocket_option: reference` and multiple references are provided, matches them to receptors by base name.
- Builds `ReceptorConfigBundle` objects containing the resolved selection string or reference path for each receptor.
- Attaches these bundles to `cfg.receptors.bundles` so prep functions can use them directly.

### Docking options

- `vina` — `exhaustiveness`, `num_modes`, `cpu`, and `write_box`.
- `dock6` — `max_orientations` and `radius`.

The config loader attaches runtime-only objects to `cfg.common`: `logger`, `manifest`, and `runstate`. The CLI also sets `cfg.common.program` to `vina` or `dock6`. Receptor bundles are attached to `cfg.receptors.bundles` after validation and normalization.

## Ligand Config

- `source: smiles` prepares ligands from `smiles_csv`.
- `source: files` reads prepared ligands from `ligands_dir`.
- `prepared_suffix` is interpreted as `<ligand_name>_<prepared_suffix>.<ext>`.
- `prepare_tool: obabel` uses Open Babel and, for Vina, MGLTools.
- `prepare_tool: meeko` uses RDKit/Meeko to produce PDBQT and converts to MOL2 with Open Babel for DOCK6.
- Vina reads `*_<prepared_suffix>.pdbqt`.
- DOCK6 reads `*_<prepared_suffix>.mol2`.

See `sample_configs/sample_docking.yaml` and `sample_configs/sample_ligands.yaml` for practical examples.


## Validation Config

Validation mode reuses the same unified config file, but the validation loader overwrites receptor and ligand inputs when `cfg.validation.data` is set.

- `validation.data` — path to a validation dataset root.

The validation loader expects a recursive data tree containing:

- receptor proteins as `*_protein.pdb`
- reference pockets as `*_pocket.pdb`
- ligand definitions as `*_ligand.sdf`

For example, the recommended structure under `/localscratch/kbui/coreset` is:

```text
/localscratch/kbui/coreset/
  entry1/
    entry1_protein.pdb
    entry1_pocket.pdb
    entry1_ligand.sdf
  entry2/
    entry2_protein.pdb
    entry2_pocket.pdb
    entry2_ligand.sdf
```

This layout is recommended for other test sets as well, since the validation loader scans recursively and matches entries by suffix.

During validation:

- receptors are loaded from `*_protein.pdb`
- reference pockets are loaded from `*_pocket.pdb`
- ligands are loaded from `*_ligand.sdf`
- `common.mode` is set to `match`

See `docs/validation.md` for the validation workflow, command usage, and expected dataset structure.
