# Configuration Reference

NexusMol uses YAML files for the larger workflows and command-line flags for smaller utility commands. YAML is parsed with PyYAML and validated with Pydantic models in the corresponding `*_config.py` modules.

## Command Configuration Matrix

| Command | Config file | Important flags | Notes |
| --- | --- | --- | --- |
| `nexus fetch rcsb` | Optional `-c/--config` | `-i/--input`, `-o/--output_dir`, `-l/--ligand_name` | Use flags for current fetch runs. |
| `nexus prep rec` | Optional `-c/--config` | `-i`, `-o`, `-s`, `-d/--dry` | Flags override config values. |
| `nexus prep mutate` | Optional `-c/--config` | `-i`, `-o`, `-s`, `-m/--mutations` | Flags override config values. |
| `nexus prep ligdock` | Optional `-c/--config` | `-i`, `-o`, `-s`, `-t/--ctype` | Input type is inferred from file extension. |
| `nexus prep sysmd` | Required `-c/--config` | None beyond `-c` | Requires `AMBERHOME`. |
| `nexus dock vina` | Required `-c/--config` | None beyond `-c` | Requires prepared `.pdbqt` ligands. |
| `nexus dock dock6` | Required `-c/--config` | None beyond `-c` | Requires prepared `.mol2` ligands and `libs.dock_home`. |
| `nexus md amber` | Required `-c/--config` | None beyond `-c` | Requires `AMBERHOME` and `pmemd.cuda`. |
| `nexus md analyze` | No YAML config | `-p`, `-t`, `-m`, `-n`, `-o` | Runs CPPTRAJ analysis directly from flags. |

## Path Handling

Docking config loading expands environment variables and `~` for declared `Path` fields. Prep, fetch, and MD config loaders do not perform the same global expansion. Prefer absolute paths or paths relative to the current working directory when launching the command.

Docking and MD loaders append `common.project_name` to the configured parent directories:

```yaml
common:
  project_name: vina_mpro
  working_dir: artifacts
  results_dir: results
```

Effective directories:

```text
artifacts/vina_mpro/
results/vina_mpro/
```

## Fetch Flags

Current implementation:

```bash
nexus fetch rcsb -i 6W63 -i 7K40 -o fetched_structures -l ligand
```

| Flag | Type | Description |
| --- | --- | --- |
| `-i`, `--input` | Repeatable string | PDB ID values, or one text file path containing one ID per line. |
| `-o`, `--output_dir` | Path | Output directory. Defaults to current directory if omitted. |
| `-l`, `--ligand_name` | String | Optional output ligand name used in SDF filenames. |
| `-c`, `--config` | Path | Path to YAML config. |

Fetch outputs:

- `<PDB_ID>.cif`
- `<PDB_ID>_<LIGAND>.sdf` or `<PDB_ID>_<ligand_name>.sdf`

## Preparation Config

Preparation commands use `PrepConfig` from `src/nexus/prep/prep_config.py`.

### `common`

| Field | Type | Default | Used by | Description |
| --- | --- | --- | --- | --- |
| `input` | Path | `null` | all prep commands | Input file or directory. |
| `output_dir` | Path | current directory | `rec`, `mutate`, `ligdock`, `sysmd` | Destination directory. Created during config validation. |
| `suffix` | String | command-specific | `rec`, `mutate`, `ligdock` | Output filename suffix. |
| `chimerax` | Path | `/usr/local/chimerax/bin/ChimeraX` | `rec`, `mutate` | ChimeraX executable. |
| `working_dir` | Path | current directory | `sysmd` | SysMD scratch parent directory. |

### `rec`

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `dry` | Boolean | `false` | Passed to the ChimeraX cleaning script to remove water. |

Example with flags:

```bash
nexus prep rec -i fetched_structures -o cleaned_receptors -s "_cleaned.pdb" -d
```

Example YAML:

```yaml
common:
  input: fetched_structures
  output_dir: cleaned_receptors
  suffix: "_cleaned.pdb"
  chimerax: /usr/local/chimerax/bin/ChimeraX

rec:
  dry: true
```

### `mutate`

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `mutations` | List of strings | `null` | Each item uses `selection-NEW_RES`. |

Example:

```bash
nexus prep mutate \
  -i cleaned_receptors/6W63_cleaned.pdb \
  -o mutated_receptors \
  -s "_mutated.pdb" \
  -m ":41-HIP" \
  -m ":145-CYM"
```

YAML:

```yaml
common:
  input: cleaned_receptors/6W63_cleaned.pdb
  output_dir: mutated_receptors
  suffix: "_mutated.pdb"

mutate:
  mutations:
    - ":41-HIP"
    - ":145-CYM"
```

### `ligdock`

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `n_jobs` | Integer | `1` | Number of Python/Open Babel preparation workers. |
| `type` | `GAFF` or `AM1-BCC` | `GAFF` | Exposed as `--ctype`; currently not used deeply by the implementation. |
| `source` | Internal | `smiles` | The pipeline infers CSV versus SDF. Do not set `source: sdf` in YAML because the model does not currently accept it. |

Suffix selects the output format:

| Suffix contains | Output | Tool path |
| --- | --- | --- |
| `.pdbqt` | Vina ligand | RDKit/Meeko |
| `.mol2` | DOCK6 ligand | RDKit/Open Babel |

CSV input must have exactly this header:

```csv
smiles,name
CC(=O)OC1=CC=CC=C1C(=O)O,aspirin
```

The parser rejects empty rows, duplicate SMILES, and duplicate names after filename sanitization.

Examples:

```bash
nexus prep ligdock -i ligands.csv -o vina_ligands -s "_prepared.pdbqt"
nexus prep ligdock -i ligand_sdfs -o dock6_ligands -s "_prepared.mol2"
```

### `sysmd`

`nexus prep sysmd` builds Amber topology and coordinate files through AmberTools.

```yaml
common:
  input: receptors/6W63.pdb
  working_dir: artifacts
  output_dir: results

sysmd:
  system_name: 6W63_mol4_solvated
  ligand: poses/6W63_mol4_prepared_scored.pdbqt
  pose_num: 1
  force_field: ff14SB
  water_model: tip3p
  box_type: Oct
  box_size: 12.0
  salt_conc: 0.15
```

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `system_name` | String | `null` | Subdirectory and output file base name. |
| `ligand` | Path or null | `null` | Prepared ligand pose file. Current receptor-only behavior has a known bug; see `SECURITY_AND_BUGS.md`. |
| `pose_num` | Integer | `1` | Pose number selected after Open Babel splits the ligand file. |
| `force_field` | String | `ff19SB` | Amber protein force field suffix used in `leaprc.protein.<force_field>`. |
| `water_model` | String | `opc` | Amber water model suffix used in `leaprc.water.<water_model>`. |
| `box_type` | `Box` or `Oct` | `Oct` | Produces `solvateBox` or `solvateOct`. |
| `box_size` | Float | `12.0` | Solvent padding distance in angstrom. |
| `salt_conc` | Float | `0.15` | Salt concentration used to estimate ion pairs from the initial `tleap` volume. |

## Docking Config

Docking commands use `DockConfig` from `src/nexus/dock/dock_config.py`.

### Minimal Vina Config

```yaml
libs:
  chimerax: /usr/local/chimerax/bin/ChimeraX

common:
  project_name: vina_mpro
  working_dir: artifacts
  results_dir: results
  padding: 4.0
  n_jobs: 8
  max_poses: 8

receptors:
  source: final_receptors
  suffix: ".pdb"
  pocket_option: selection
  selection: "/A:41,145"

ligands:
  source: vina_ligands
  suffix: "_prepared.pdbqt"

vina:
  exhaustiveness: 32
  num_modes: 8
```

### Minimal DOCK6 Config

```yaml
libs:
  chimerax: /usr/local/chimerax/bin/ChimeraX
  chimera: /usr/local/chimera/chimera-1.8/bin/chimera
  dock_home: /path/to/dock6

common:
  project_name: dock6_mpro
  working_dir: artifacts
  results_dir: results
  padding: 4.0
  n_jobs: 8
  max_poses: 8

receptors:
  source: final_receptors
  suffix: ".pdb"
  pocket_option: selection
  selection: "/A:41,145"

ligands:
  source: dock6_ligands
  suffix: "_prepared.mol2"

dock6:
  max_orientations: 1000
  radius: 10.0
```

### `libs`

| Field | Type | Default | Required for | Description |
| --- | --- | --- | --- | --- |
| `chimerax` | Path | `/usr/local/chimerax/bin/ChimeraX` | Vina, DOCK6 receptor prep | ChimeraX executable. |
| `chimera` | Path | `/usr/local/chimera/chimera-1.8/bin/chimera` | DOCK6 | Legacy UCSF Chimera executable. |
| `dock_home` | Path | `null` | DOCK6 | DOCK6 installation root containing `bin/dock6`, `bin/grid`, etc. |

### `common`

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `project_name` | String | `docking` | Added to working/results parent directories. |
| `working_dir` | Path | `<cwd>/artifacts` | Parent scratch directory. |
| `results_dir` | Path | `<cwd>/results` | Parent results directory. |
| `padding` | Float | `5.0` | Extra receptor pocket padding in angstrom. |
| `n_jobs` | Integer | `1` | GNU Parallel or Python worker count. |
| `max_poses` | Integer | `8` | Number of scores parsed into summaries. |
| `mode` | `mix` or `match` | `mix` | `mix` is the active, reliable mode. `match` is incompletely wired in current pipelines. |
| `program` | Runtime string | `null` | Set internally to `vina` or `dock6`. |

### `receptors`

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `source` | Path | `null` | Receptor file, receptor directory, or list of receptor files. |
| `suffix` | String | `.pdb` | File suffix used when `source` is a directory. Must contain `.pdb` or `.cif`. |
| `pocket_option` | `selection` or `reference` | `selection` | How to define the docking pocket. |
| `selection` | String or CSV path | `null` | ChimeraX selection string, or CSV mapping receptor stem to selection. |
| `reference` | Path | `null` | Reference pocket file or directory. |
| `reference_suffix` | String | `_pocket.pdb` | Suffix used to match multiple reference pockets to receptors. |

Selection CSV format has no header:

```csv
receptor1,/A:41,145
receptor2,/B:50,100,150
```

Reference matching uses the receptor stem before the first underscore. For receptor `6W63_cleaned.pdb` and `reference_suffix: _pocket.pdb`, the expected reference name is `6W63_pocket.pdb`.

### `ligands`

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `source` | Path | `null` | Prepared ligand file, directory, or list of files. |
| `suffix` | String | `.sdf` | File suffix used when `source` is a directory. Vina requires `.pdbqt`; DOCK6 requires `.mol2`. |

### `vina`

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `exhaustiveness` | Integer | `32` | Appended to the generated Vina config. |
| `num_modes` | Integer | `8` | Appended to the generated Vina config. |

The code also appends `cpu = 1` to each receptor-specific Vina config, because concurrency is controlled externally by GNU Parallel.

### `dock6`

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `max_orientations` | Integer | `1000` | Used in the DOCK6 flex input template. |
| `radius` | Float | `10.0` | Sphere selection radius around the generated pocket. |

## Amber MD Config

`nexus md amber` uses `MDConfig` from `src/nexus/md/md_config.py`.

```yaml
common:
  project_name: MD_Dialanine
  working_dir: artifacts
  results_dir: results
  prmtop: md_input/ALA.prmtop
  inpcrd: md_input/ALA.inpcrd
  temp: 300.0
  dt: 0.002
  cut: 10.0
  mask: ":1-3"

min:
  n_min_runs: 7
  ncyc: 1000
  maxcyc: 1000
  restraints: [10.0, 5.0, 2.0, 1.0, 0.5, 0.1, 0.0]

heat:
  mid_temp: 100.0
  time1: 100.0
  time2: 500.0
  total_time: 2000.0
  restraint: 10.0

eq:
  n_eq_runs: 7
  eq_time: 100.0
  restraints: [10.0, 5.0, 2.0, 1.0, 0.5, 0.1, 0.0]

prod:
  num_seeds: 1
  rand_time: 200.0
  prod_time: 2500.0
  prod_freq: 10.0
```

### `common`

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `project_name` | String | `md` | Added to working/results parent directories. |
| `working_dir` | Path | `<cwd>/artifacts` | Parent scratch directory. |
| `results_dir` | Path | `<cwd>/results` | Parent results directory. |
| `prmtop` | Path | `null` | Amber topology file. Required. |
| `inpcrd` | Path | `null` | Amber coordinate file. Required. |
| `temp` | Float | `300.0` | Target temperature. |
| `dt` | Float | `0.002` | MD timestep. |
| `cut` | Float | `10.0` | Nonbonded cutoff. |
| `mask` | String | `null` | Amber atom mask used in generated templates. |

### Stage Sections

| Section | Fields |
| --- | --- |
| `min` | `n_min_runs`, `ncyc`, `maxcyc`, `restraints` |
| `heat` | `mid_temp`, `time1`, `time2`, `total_time`, `restraint` |
| `eq` | `n_eq_runs`, `eq_time`, `restraints` |
| `prod` | `num_seeds`, `rand_time`, `prod_time`, `prod_freq` |

`prod_freq` is used as a divisor when calculating `ntpr`, `ntwx`, and `ntwr` from total production steps. For example, `prod_freq: 10` creates roughly ten reporting intervals, not an every-10-steps output interval.

## MD Analysis Flags

`nexus md analyze` renders and runs a CPPTRAJ input file.

```bash
nexus md analyze -p system.prmtop -t prod1.nc -m ":1-198" -n run1 -o analysis_output
```

| Flag | Required | Description |
| --- | --- | --- |
| `-p`, `--prmtop` | Yes | Amber topology file. |
| `-t`, `--trajin` | Yes | Trajectory file. |
| `-m`, `--mask` | Yes | CPPTRAJ mask expression. |
| `-n`, `--name` | No | Analysis name. Defaults to `prmtop.stem`. |
| `-o`, `--output-dir` | No | Output directory. Defaults to current directory. |

The analysis writes RMSD/RMSF, hydrogen-bond, secondary-structure, PCA, clustering, and notebook outputs. The clustering mask is currently hard-coded in the template; see `SECURITY_AND_BUGS.md`.

## Validation Config Status

`src/nexus/validate/validate_config.py` contains a validation loader, and `src/nexus/validate/rmsd.py` contains RMSD helpers. The Typer commands `nexus validate vina` and `nexus validate dock6` currently return before invoking those functions. Treat validation config as inactive until the CLI path is re-enabled and tested.
