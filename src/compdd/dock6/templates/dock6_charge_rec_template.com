open $receptor
delete solvent
delete ligand
dockprep
save ${name}_prepped.mol2
delete H
save ${name}_prepped_noH.mol2
save ${name}_prepped_noH.pdb