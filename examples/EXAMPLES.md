# Examples

This folder contains some example uses of the toolkit. In this top level folder, input files can be found. The folders are contain the results of these example pipelines.

## Fetching and receptors preparation

The `-d` flag is to dry, and you almost always want to use it to remove crystallographic waters to prepare receptors for docking. For molecular dynamics, you might want to keep those near the binding site manually.

```bash
nexus fetch rcsb -i id_list.txt -o receptors/fetched/ -l "ligand"
nexus prep rec -i receptors/fetched/ -o receptors/cleaned/ -s "_cleaned.pdb" -d
```

The output from `nexus prep rec` tells us the non-standard protonation states that ChimeraX assigned, especially histidine.

## Change protonation states of receptors

Based on the output from `nexus prep rec`, we adjust the protonation state of the receptors based on biological knowledge of the receptor. 

> For example, 6W63 and 7K40 are protein structures of the SARS-CoV-2 main protease (mpro), and if we want to model the ionic pair at the catalytic side, we can assign His41 to be doubly protonated (HIP) and Cys145 to be deprotonated (CYM). We can also adjust other histidines that was assigned to be HIP by chimerax to be neutral (HIE/HID), for example.

```bash
nexus prep mutate -i receptors/cleaned/6W63_cleaned.pdb -o receptors/mutated/ -s "_mutated.pdb" -m ":145-CYM"
nexus prep mutate -i receptors/cleaned/7K40_cleaned.pdb -o receptors/mutated/ -s "_mutated.pdb" -m ":64,80-HIE" -m ":41-HIP" -m ":145-CYM"
```

After this step, our receptor names are quite long, so we might want to simplify their naming and put in a folder for docking, and in this example they were put in receptors/final/

```bash
mkdir -p receptors/final/
cp receptors/mutated/6W63_cleaned_mutated.pdb receptors/final/6W63.pdb
cp receptors/mutated/7K40_cleaned_mutated.pdb receptors/final/7K40.pdb
```

## Ligands preparation for docking

Vina requires the .pdbqt format, while dock6 requires .mol2.

```bash
nexus prep ligdock -i ligand_list.csv -o ligands/vina/ -s "_prepared.pdbqt"
nexus prep ligdock -i ligand_list.csv -o ligands/dock6/ -s "_prepared.mol2"
```

For the large pipelines below, see the working directory [artifacts](artifacts/) and output directory [results](results/) docking, system building, and molecular dynamics outputs.

## Docking

Docking uses a config file for input, requiring prepared receptors and ligands. The results can be found in `results/vina_mpro/` and `results/dock6_mpro/`

```bash
nexus dock vina -c vina_config.yaml
nexus dock dock6 -c dock6_config.yaml
```

## Build solvated system for MD

After choosing a docked pose or using a crystal structure with ligand, build a solvated Amber-compatible system using `nexus prep sysmd`. Results can be found in `results/6W63_mol4_solvated/`

> AmberTools can be very verbose, so I suggest use the flag `--silence` to avoid having your terminal cluttered.

```bash
nexus --silence 2 prep sysmd -c sysmd_config.yaml
```

Once the system files are generated, a full molecular dynamics pipeline can be run, including minimization, heating, equilibration, and production. Results can be found in `results/AMBER_DiAla` and `results/OpenMM_DiAla`. Currently, there is no difference between `amber_config.yaml` and `openmm_config.yaml`, with the exception of the `project_name` field; both share the same parameters.

```bash
nexus --silence 2 md amber -c amber_config.yaml
nexus md openmm -c openmm_config.yaml
```

Molecular dynamics output can be analysis using the command:

```bash
nexus --silence 2 md analyze -p your.prmtop -t trajectory.nc -m ":1-198" -n name -o results/
```

Example outputs can be found in `results/2BPW_analysis_output/`. 

> 2BPW is a HIV-1 protease-inhibitor complex, and was chosen for this example over DiAlanine because DiAlanine is too small to have meaningful protein analysis. This command can also load in the dcd trajectory format, which is the output when running openmm.

> If you want to try out running these commands on your own, you can copy this folder (examples), excluding subfolders, to your desired destination and run these commands.

```bash
mkdir -p ~/your_directory
cp ./* ~/your_directory
```
