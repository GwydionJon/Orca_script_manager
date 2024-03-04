import pandas as pd
from script_maker2000.files import create_working_dir_structure, read_config
from tqdm import tqdm
from joblib import Parallel, delayed
from rdkit import Chem
from rdkit.Chem import AllChem


import logging

script_maker_log = logging.getLogger("Script_maker_log")
script_maker_error = logging.getLogger("Script_maker_error")


# this module will read the molecular inputs and unify them in an xyz format.
# it also serves as a setp class to setup the dir structure


class Molecule_Preparation:

    def __init__(self, main_config_path) -> None:

        self.main_config = read_config(main_config_path)

        # after this step we will only work with the copied input files.

        self.output_dir, self.config_path, self.input_path = (
            create_working_dir_structure(self.main_config, main_config_path)
        )

        self.read_csv_input()
        self.create_output_overview_file()

    def read_csv_input(
        self,
    ):
        smiles_column_name = self.main_config["main_config"]["csv_smiles_column"]
        input_df = pd.read_csv(self.input_path)
        smiles_list = input_df[smiles_column_name].values
        self.smiles_list = smiles_list
        return smiles_list

    def create_output_overview_file(self):
        df = pd.DataFrame()
        df["mol_id"] = [
            "mol_" + str(id_).zfill(8) for id_ in range(len(self.smiles_list))
        ]
        df["smiles"] = self.smiles_list

        df.to_csv(self.output_dir / "reference_list.csv")

    def convert_smiles_to_sdf(self):
        def _convert_single_smile(smile):
            molecule = Chem.MolFromSmiles(smile)
            molecule = Chem.AddHs(molecule)

            AllChem.EmbedMolecule(molecule)
            AllChem.MMFFOptimizeMolecule(molecule)
            return (
                molecule,
                smile,
            )

        script_maker_log.info("Starting smiles to 3d conversion")
        molecules_and_smiles = Parallel(n_jobs=-1)(
            delayed(_convert_single_smile)(smile) for smile in tqdm(self.smiles_list)
        )

        # get reference_list csv
        ref_df = pd.read_csv(self.output_dir / "reference_list.csv")

        molecules, orig_smiles = zip(*molecules_and_smiles)
        print(ref_df.loc[orig_smiles])

        script_maker_log.info("finished smiles to 3d conversion")

        return molecules, orig_smiles
