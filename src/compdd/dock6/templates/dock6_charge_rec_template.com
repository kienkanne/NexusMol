open $receptor
dockprep
save ${prepped_receptor_mol2}
delete H
save ${prepped_receptor_noH_mol2}
save ${prepped_receptor_noH_pdb}
