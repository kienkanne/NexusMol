# Examples

This folder contains some example input files, commands, and their results

## Fetching and receptors preparation

```bash
nexus fetch rcsb -i id_list.txt -o fetched_structures/ -l "ligand"
nexus prep rec -i fetched_structures/ -o cleaned_receptors/ -s "_cleaned.pdb"
```

The output from `nexus prep rec` tells us the non-standard protonation states that ChimeraX assigned, especially histidine.

### Change protonation states of receptors

Based on the output from `nexus prep rec`, we adjust the protonation state of the receptors based on biological knowledge of the receptor. For example, 6W63 and 7K40 are protein structures of the SARS-CoV-2 main protease (mpro), and we know that for computational studies His41 is doubly protonated (HIP) and Cys145 is deprotonated (CYM). We can also adjust other histidines that was assigned to be HIP by chimerax to be neutral (HIE/HID).

```bash
nexus prep mutate -i cleaned_receptors/6W63_cleaned.pdb -o mutated_receptors/ -s "_mutated.pdb" -m ":145-CYM"
nexus prep mutate -i cleaned_receptors/7K40_cleaned.pdb -o mutated_receptors/ -s "_mutated.pdb" -m ":64,80-HIE" -m ":41-HIP" -m ":145-CYM"
```

### Ligands preparation for docking

Vina requires the .pdbqt format, while dock6 requires .mol2.

```bash
nexus prep ligdock -i ligand_list.csv -o vina_prepared_ligands/ -s "_prepared.pdbqt"
nexus prep ligdock -i ligand_list.csv -o dock6_prepared_ligands/ -s "_prepared.mol2"
```

### Docking

Docking uses a config file for input.

```bash
nexus dock vina -c vina_config.yaml
nexus dock dock6 -c dock6_config.yaml
```