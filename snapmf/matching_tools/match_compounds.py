#!/usr/bin/env python3

"""Tools to match masses from mass list to compounds from Atlas"""
from typing import Dict, List

import networkx as nx
import pandas as pd
import re

from snapmf.config import Parameters
from snapmf.matching_tools import data_import
from snapmf.matching_tools.CompoundMatch import CompoundMatch
from snapmf.network_tools import create_networks


def calculate_error(mass: float, mass_error: float, precision: int = 4) -> float:
    """Calculate ppm error for a given mass and error"""

    return round((mass * mass_error) / 1e6, precision)


def remove_mass_duplicates(mass_list: List[float], ppm_error: float) -> List[float]:
    """Remove masses in mass list within ppm error of existing masses
    Keeps the first.
    """

    deduplicated_mass_list = []

    for mass in mass_list:
        insert_mass = True
        mass_error = calculate_error(mass, ppm_error)
        for deduplicated_mass in deduplicated_mass_list:
            if mass - mass_error <= deduplicated_mass <= mass + mass_error:
                insert_mass = False
                break
        if insert_mass:
            deduplicated_mass_list.append(mass)

    return deduplicated_mass_list


def compute_adduct_matches(
    mass_list: List[float], parameters: Parameters, atlas_df: pd.DataFrame
) -> List[CompoundMatch]:
    """Tool to search the Atlas for a given mass, and return all compounds with that mass as a specific adduct,
    within a given mass error

    mass_list should be a list of masses accurate to four decimal places
    ppm error should be the required parts per million error. Modern spectrometers are accurate to sub-two ppm.
    Five or ten are conservative values
    adduct list should be a list of adducts that are present in the Atlas dataframe. By default only 'H' and 'Na' are
    present
    atlas_df is the dataframe from atlas_tools.atlas_import after cleaning/processing has been applied
    """
    output_list = []
    for index, mass in enumerate(mass_list):
        mass_error = calculate_error(mass, parameters.ppm_error)

        if parameters.atlas_filter == "coconut":
            for adduct in parameters.adduct_list:
                selected_compounds = atlas_df[
                    atlas_df[adduct].between(mass - mass_error, mass + mass_error)
                ][
                    [
                        "coconut_id",
                        "exact_mass",
                        "smiles",
                        "name",
                        "origin_organism_type",
                    ]
                ]
                if not selected_compounds.empty:
                    selected_compounds["mass"] = mass
                    selected_compounds["compound_number"] = index + 1
                    selected_compounds["adduct"] = adduct
                    selected_compounds["npaid"] = str(None)
                    selected_compounds["molecular_formula"] = str(None)
                    # Use a dataclass for verbosity in other code
                    # avoids needing to know list indices
                    output_list += [
                        CompoundMatch(**c)
                        for c in selected_compounds.to_dict(orient="records")
                    ]
        else:
            for adduct in parameters.adduct_list:
                selected_compounds = atlas_df[
                    atlas_df[adduct].between(mass - mass_error, mass + mass_error)
                ][["npaid", "exact_mass", "smiles", "name", "origin_organism_type"]]
                if not selected_compounds.empty:
                    selected_compounds["mass"] = mass
                    selected_compounds["compound_number"] = index + 1
                    selected_compounds["adduct"] = adduct
                    selected_compounds["coconut_id"] = str(None)
                    selected_compounds["molecular_formula"] = str(None)
                    # Use a dataclass for verbosity in other code
                    # avoids needing to know list indices
                    output_list += [
                        CompoundMatch(**c)
                        for c in selected_compounds.to_dict(orient="records")
                    ]

    return output_list


def standardize_formula(formula: str) -> list:
    """Split the formula string into elements and counts"""
    # Check for charge in formula
    if "+" in formula:
        print("WARNING: Formula contains a charge. Charge will be ignored.")
    # Check for unexpected characters in formula
    if re.findall(r"[^A-Za-z0-9+]", formula):
        print(f"WARNING: Formula {formula} contains invalid characters.")

    pattern = r"([A-Z][a-z]*)(\d*)"
    atom_counts = {}

    for element, count in re.findall(pattern, formula):
        # If count is empty (e.g., 'Na' in NaCl), default it to 1
        atom_count = int(count) if count else 1
        atom_counts[element] = atom_count

    element_list = []
    for element, count in atom_counts.items():
        if element not in ["C", "H"]:
            element_list.append([element, count])
    sorted_element_list = sorted(element_list, key=lambda x: x[0])

    standardized_formula = f"C{atom_counts['C']}H{atom_counts['H']}" + "".join([f"{element}{count}" for element, count in sorted_element_list])

    return standardized_formula


def find_formula_matches(
    formula_list: List[str], parameters: Parameters, atlas_df: pd.DataFrame
) -> List[CompoundMatch]:
    """Tool to search the Atlas for a given formula, and return all matches

    formula_list should be a list of formulae
    atlas_df is the dataframe from atlas_tools.atlas_import after cleaning/processing has been applied
    """
    # Standardize formulae.
    cleaned_formula_list = []
    for formula in formula_list:
        cleaned_formula_list.append(standardize_formula(formula))

    output_list = []
    for index, formula in enumerate(cleaned_formula_list):
        if parameters.atlas_filter == "coconut":
            selected_compounds = atlas_df[
                atlas_df['molecular_formula'] == formula
            ][
                [
                    "coconut_id",
                    "exact_mass",
                    "smiles",
                    "name",
                    "origin_organism_type",
                ]
            ]
            if not selected_compounds.empty:
                selected_compounds["mass"] = str(None)
                selected_compounds["compound_number"] = index + 1
                selected_compounds["adduct"] = str(None)
                selected_compounds["npaid"] = str(None)
                selected_compounds["molecular_formula"] = formula
                # Use a dataclass for verbosity in other code
                # avoids needing to know list indices
                output_list += [
                    CompoundMatch(**c)
                    for c in selected_compounds.to_dict(orient="records")
                ]
        else:
            selected_compounds = atlas_df[
                atlas_df['mol_formula'] == formula
            ][["npaid", "exact_mass", "smiles", "name", "origin_organism_type"]]
            if not selected_compounds.empty:
                selected_compounds["mass"] = str(None)
                selected_compounds["compound_number"] = index + 1
                selected_compounds["adduct"] = str(None)
                selected_compounds["coconut_id"] = str(None)
                selected_compounds["molecular_formula"] = formula
                # Use a dataclass for verbosity in other code
                # avoids needing to know list indices
                output_list += [
                    CompoundMatch(**c)
                    for c in selected_compounds.to_dict(orient="records")
                ]
    for compound in output_list:
        print(compound.__dict__)
    return output_list


def annotate_gnps_network(
    atlas_df: pd.DataFrame, parameters: Parameters
) -> Dict[int, nx.Graph]:
    """Tool to create structure class predictions from GNPS clusters by identifying the compound classes with the
    highest prevalence in the GNPS network.

    remove_node_duplicates is a bool flag that optionally filters the nodes in each GNPS cluster and removes nodes with
    very similar masses. This eliminates repetition of sets of compound matches from the Atlas, decreases the number
    of compound groups, and prevents 'annotation bloat' where many nodes become interconnected because they are
    repeated compounds, but in different compound groups (and so get edges added in annotation network).
    Leads to cleaned results files. Recommended default is True

    Returns Dict of compound graphs for each GNPS cluster indexed by cluster_id
    """

    gnps_network = data_import.import_gnps_network(parameters)
    networks = {}
    for cluster in nx.connected_components(gnps_network):
        if len(cluster) >= parameters.min_gnps_cluster_size:
            cluster_id = int(gnps_network.nodes[list(cluster)[0]]["componentindex"])
            # Create gnps mass list
            target_mass_list = [
                gnps_network.nodes[node]["parent mass"] for node in cluster
            ]
            if parameters.remove_duplicates:
                target_mass_list = remove_mass_duplicates(
                    target_mass_list, parameters.ppm_error
                )
            # if gnps mass list contains appropriate number of members, perform Atlas annotation
            if (
                parameters.min_gnps_cluster_size
                <= len(target_mass_list)
                <= parameters.max_gnps_cluster_size
            ):
                atlas_compound_list = compute_adduct_matches(
                    target_mass_list, parameters, atlas_df
                )
                compound_network = create_networks.match_compound_network(
                    atlas_compound_list, parameters
                )
                nx.set_node_attributes(
                    compound_network, cluster_id, name="componentindex"
                )
                networks[cluster_id] = compound_network
            print("Finished Atlas annotation for GNPS cluster " + str(cluster_id))
    return networks
