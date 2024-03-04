from script_maker2000.molecule_preperation import Molecule_Preparation


def test_molecule_preperation(temp_work_dir):
    main_config_path = temp_work_dir / "example_config.json"

    mol_prep = Molecule_Preparation(main_config_path)

    test_conversion = mol_prep.convert_smiles_to_sdf()
    print(test_conversion)
    assert len(test_conversion[0]) == 30
    assert len(test_conversion[1]) == 30
    1 / 0
