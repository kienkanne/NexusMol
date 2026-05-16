open $receptor
delete solvent
delete ligand
dockprep
save ${name}_prepped.pdb