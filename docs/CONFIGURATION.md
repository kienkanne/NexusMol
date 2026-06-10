# Configuration

NexusMol uses two layers of configuration:

1. A global machine config for software paths and scratch space.
2. Per-workflow YAML files for scientific inputs, parameters, and output folders.

The previous independent loaders have been replaced by a shared YAML path through `nexus.core.utils.load_config.load_config` for tracked workflows. The shared loader reads YAML with PyYAML, validates it with the relevant Pydantic model, attaches the global config as `_global`, creates job-scoped folders, and initializes run tracking.

## Global Config

Global config lives at:

```text
~/.config/nexus/config.yaml
```

Default file shape:

```yaml
software:
  chimerax: null
  chimera: null
  dock6: null
path:
  scratch_dir: null
```

Field meanings:

| Field | Used by | Meaning |
| --- | --- | --- |
| `software.chimerax` | `prep rec`, `prep mutate`, Vina docking, DOCK6 docking | ChimeraX executable. |
| `software.chimera` | DOCK6 docking | Legacy UCSF Chimera executable. |
| `software.dock6` | DOCK6 docking | DOCK6 installation root that contains `bin/dock6`, `bin/grid`, and related tools. |
| `path.scratch_dir` | `dock run`, `md build`, `md run`, `md analyze`, `md mmpbsa` | Parent scratch/workspace directory. Nexus creates `<scratch_dir>/<job_name>/`. |

`nexus config validate` reports `OK`, `Missing path`, or `Not configured` for every global path. Missing configured paths cause a non-zero exit status.

## Workflow Directory Rules

Workflow configs with `common.job_name` use both the global scratch directory and the workflow output directory:

```yaml
common:
  job_name: vina_mpro
  output_dir: results
```

Effective directories:

```text
<global path.scratch_dir>/vina_mpro/
results/vina_mpro/
```

The loader creates both directories before the pipeline starts. Fetch and prep configs are simpler and do not require `common.job_name`.

## Command Matrix

| Command | Config | Required? | Notes |
| --- | --- | --- | --- |
| `nexus config init` | Global | No | Creates `~/.config/nexus/config.yaml`. |
| `nexus config show` | Global | No | Prints loaded global YAML. |
| `nexus config validate` | Global | No | Validates configured paths. |
| `nexus fetch rcsb` | `FetchConfig` | Optional | Flags can supply all fields. |
| `nexus prep rec` | `PrepConfig` | Optional | Flags override YAML values. |
| `nexus prep mutate` | `PrepConfig` | Optional | Flags override YAML values. |
| `nexus prep lig` | `PrepConfig` | Optional | Output suffix selects `.pdbqt` or `.mol2`. |
| `nexus dock run` | `DockConfig` | Yes | `engine.program` chooses `vina` or `dock6`. |
| `nexus md build` | `BuildConfig` | Yes | Builds Amber-compatible topology and coordinates. |
| `nexus md run` | `MDConfig` | Yes | `engine.program` chooses `amber` or `openmm`. |
| `nexus md analyze` | `AnalyzeConfig` | Yes | Runs the current CPPTRAJ template. |
| `nexus md mmpbsa` | `MMPBSAConfig` | Yes | Exposed by CLI, but current runner needs manual implementation review. |

## Fetch Config

Model: `src/nexus/fetch/fetch_config.py`

```yaml
input:
  - 6W63
  - 7K40
ligand_name: ligand
output_dir: receptors/fetched
```

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `input` | list of strings or path | `null` | PDB IDs, or a text file containing one ID per line. |
| `ligand_name` | string or null | `null` | Optional ligand filename label. If omitted, the CCD ligand ID is used. |
| `output_dir` | path or null | current directory at runtime | Output folder for CIF and SDF files. |

Outputs:

```text
<output_dir>/<PDB_ID>.cif
<output_dir>/<PDB_ID>_<LIGAND>.sdf
```

## Prep Config

Model: `src/nexus/prep/prep_config.py`

Shared fields:

```yaml
common:
  input: receptors/fetched
  output_dir: receptors/cleaned
  suffix: "_cleaned.pdb"
```

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `common.input` | path or null | `null` | Input file or directory. |
| `common.output_dir` | path or null | current working directory | Destination folder. |
| `common.suffix` | string or null | command-specific | Suffix appended to output stems. |

### Receptor Cleaning

```yaml
common:
  input: receptors/fetched
  output_dir: receptors/cleaned
  suffix: "_cleaned.pdb"
rec:
  dry: true
```

`rec.dry` defaults to `false`. When true, waters are removed by the ChimeraX cleaning script.

Command equivalent:

```bash
nexus prep rec -i receptors/fetched -o receptors/cleaned -s "_cleaned.pdb" -d
```

### Mutation and Protonation

```yaml
common:
  input: receptors/cleaned/7K40_cleaned.pdb
  output_dir: receptors/mutated
  suffix: "_mutated.pdb"
mutate:
  mutations:
    - ":64,80-HIE"
    - ":41-HIP"
    - ":145-CYM"
```

Each mutation string uses `selection-NEW_RES`. The selection is passed to ChimeraX. Nexus then rewrites Amber protonation labels back to standard residue names in the PDB while preserving protonation through hydrogens.

### Ligand Preparation

```yaml
common:
  input: inputs/ligand_list.csv
  output_dir: ligands/vina
  suffix: "_prepared.pdbqt"
lig:
  n_jobs: 4
```

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `lig.n_jobs` | integer | `1` | Number of ligand-preparation workers. |

Input can be:

- CSV with exact header `smiles,name`.
- One SDF file.
- A directory searched recursively for `.sdf` files.

Suffix controls output format:

| Suffix | Output | Toolchain |
| --- | --- | --- |
| `.pdbqt` | Vina ligand files | RDKit plus Meeko |
| `.mol2` | DOCK6 ligand files | RDKit plus Open Babel |

## Dock Config

Model: `src/nexus/dock/dock_config.py`

The same command runs Vina or DOCK6:

```bash
nexus dock run -c configs/vina_config.yaml
nexus dock run -c configs/dock6_config.yaml
```

The selected engine is declared in YAML.

### Vina Example

```yaml
common:
  job_name: vina_mpro
  output_dir: results
  padding: 4.0
  n_jobs: 8
  max_poses: 8

receptors:
  source: receptors/final
  suffix: ".pdb"
  pocket_option: selection
  selection: "/A:41,145,163,164,172"

ligands:
  source: ligands/vina
  suffix: "_prepared.pdbqt"

engine:
  program: vina
  exhaustiveness: 32
  num_modes: 8

metadata:
  tool: vina
  grid: catalytic_site
```

### DOCK6 Example

```yaml
common:
  job_name: dock6_mpro
  output_dir: results
  padding: 4.0
  n_jobs: 8
  max_poses: 8

receptors:
  source: receptors/final
  suffix: ".pdb"
  pocket_option: selection
  selection: "/A:41,145,163,164,172"

ligands:
  source: ligands/dock6
  suffix: "_prepared.mol2"

engine:
  program: dock6
  max_orientations: 1000
  radius: 10.0

metadata:
  tool: dock6
  grid: catalytic_site
```

Field reference:

| Field | Default | Description |
| --- | --- | --- |
| `common.job_name` | `docking` | Job folder and tracker basename. |
| `common.output_dir` | `<cwd>/results` | Parent results folder. |
| `common.padding` | `5.0` | Search-box or pocket padding in angstroms. |
| `common.n_jobs` | `1` | Parallel worker count. |
| `common.max_poses` | `8` | Maximum pose scores parsed into CSV summaries. |
| `receptors.source` | `null` | Receptor file or directory. |
| `receptors.suffix` | `.pdb` | Receptor suffix when source is a directory. Must include `.pdb` or `.cif`. |
| `receptors.pocket_option` | `selection` | `selection` or `reference`. |
| `receptors.selection` | `null` | ChimeraX selection string or CSV mapping receptor stem to selection. |
| `receptors.reference` | `null` | Reference pocket file or directory. |
| `receptors.reference_suffix` | `_pocket.pdb` | Suffix for matching multiple reference pockets. |
| `ligands.source` | `null` | Prepared ligand file or directory. |
| `ligands.suffix` | `.sdf` | Prepared ligand suffix. Use `.pdbqt` for Vina and `.mol2` for DOCK6. |
| `engine.program` | required | `vina` or `dock6`. |
| `metadata` | empty object | Extra values copied to `<job_name>_metadata.json`. |

Docking pairs every receptor with every ligand.

## MD Build Config

Model: `src/nexus/md/build/build_config.py`

```yaml
common:
  receptor: inputs/6W63.pdb
  output_dir: results
  job_name: 6W63_mol4_solvated

ligand:
  ligand: inputs/6W63_mol4_prepared_scored.pdbqt
  pose_num: 1

system:
  force_field: ff19SB
  water_model: tip3p
  box_type: Oct
  box_size: 12.0
  salt_conc: 0.15
```

| Field | Default | Description |
| --- | --- | --- |
| `common.receptor` | required | Receptor PDB passed to `pdb4amber`. |
| `common.output_dir` | `<cwd>/results` | Parent results folder. |
| `common.job_name` | `solvated_system` | Output basename and job folder. |
| `ligand.ligand` | `null` | Optional docked ligand pose file. |
| `ligand.pose_num` | `1` | Pose selected after Open Babel splits multi-pose files. |
| `system.force_field` | `ff19SB` | Amber protein force field suffix. |
| `system.water_model` | `opc` | Amber water model suffix. |
| `system.box_type` | `Oct` | `Oct` or `Box`. |
| `system.box_size` | `12.0` | Solvent padding distance. |
| `system.salt_conc` | `0.15` | Salt concentration used to estimate ion pairs. |

Outputs:

```text
<output_dir>/<job_name>/<job_name>.prmtop
<output_dir>/<job_name>/<job_name>.inpcrd
<output_dir>/<job_name>/<job_name>.pdb
```

## MD Run Config

Model: `src/nexus/md/run/md_config.py`

```yaml
common:
  prmtop: inputs/ALA.prmtop
  inpcrd: inputs/ALA.inpcrd
  mask: ":1-3"
  temp: 300.0
  dt: 0.002
  cut: 10.0
  job_name: AMBER_DiAla
  output_dir: results

min:
  n_min_runs: 7
  ncyc: 1000
  maxcyc: 5000
  restraints: [10.0, 5.0, 2.0, 1.0, 0.5, 0.1, 0.0]

heat:
  mid_temp: 100.0
  time_mid_temp: 100.0
  time_temp: 500.0
  total_time: 1000.0
  restraint: 10.0

eq:
  n_eq_runs: 7
  eq_time: 100.0
  restraints: [10.0, 5.0, 2.0, 1.0, 0.5, 0.1, 0.0]

prod:
  num_seeds: 1
  rand_time: 200.0
  prod_time: 1000.0
  prod_freq: 10.0

engine:
  program: amber
```

Set `engine.program: openmm` for the OpenMM implementation.

Important field names:

| Field | Default | Description |
| --- | --- | --- |
| `common.prmtop` | required | Amber topology. |
| `common.inpcrd` | required | Starting coordinates. |
| `common.mask` | required | Solute or restraint mask. |
| `common.temp` | `300.0` | Temperature in K. |
| `common.dt` | `0.002` | Time step in ps. |
| `common.cut` | `10.0` | Nonbonded cutoff in angstroms. |
| `heat.time_mid_temp` | `100.0` | Time to reach `mid_temp`. |
| `heat.time_temp` | `500.0` | Time to reach final `common.temp`. |
| `prod.prod_freq` | `10.0` | Reporting interval control used by the engines. |
| `engine.program` | required | `amber` or `openmm`. |

## MD Analysis Config

Model: `src/nexus/md/analyze/analyze_config.py`

```yaml
common:
  prmtop: results/AMBER_DiAla/ALA.prmtop
  trajin: results/AMBER_DiAla/prod1.nc
  mask: ":1-3"
  job_name: DiAla_analysis
  output_dir: results

trajectory:
  rmsd: true
  hbond: true
  pca: true
```

`trajectory.rmsd`, `trajectory.hbond`, and `trajectory.pca` exist in the config model, but the current runner renders one fixed CPPTRAJ template. They are not yet used to selectively enable or disable analysis blocks.

Outputs include the rendered `analysis_<job_name>.in`, RMSD/RMSF files, hydrogen-bond files, secondary-structure files, PCA files, clustering files, and `Visual_<job_name>.ipynb`.

## MM-PBSA/GBSA Config

Model: `src/nexus/md/mmpbsa/mmpbsa_config.py`

The CLI exposes:

```bash
nexus md mmpbsa -c configs/mmpbsa_config.yaml
```

Current status: the CLI loads `MMPBSAConfig`, but the runner currently expects positional arguments instead of a config object and references a notebook filename that is not present. Treat this command as requiring implementation review before use.

Config model shape:

```yaml
common:
  prmtop: system.prmtop
  trajin: prod1.nc
  mask: ":1-198"
  job_name: mmpbsa
  output_dir: results
  start_frame: 1
  end_frame: 9999999
  interval: 10
  n_cores: 1

gb:
  run: true
  igb: 5
  saltcon: 0.15

pb:
  run: false
  istrng: 0.15
  fillratio: 4.0
```
