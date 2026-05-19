def _meeko_charge(mol_with_h, name, output_dir, prepared_suffix):
    from meeko import MoleculePreparation, PDBQTWriterLegacy

    preparator = MoleculePreparation()
    mol_setups = preparator.prepare(mol_with_h)
    setup = mol_setups[0]

    pdbqt_string, is_valid, error_msg = PDBQTWriterLegacy.write_string(setup)
    if not is_valid:
        raise RuntimeError(f"Meeko failed to generate PDBQT: {error_msg}")

    output_pdbqt_path = output_dir / f"{name}_{prepared_suffix}.pdbqt"
    with open(output_pdbqt_path, "w") as handle:
        handle.write(pdbqt_string)
    return output_pdbqt_path