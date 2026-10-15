import csv

import pandas as pd

from snapmf.config import CYTOSCAPE_DATADIR, Parameters
from snapmf.matching_tools import data_import, match_compounds
from snapmf.network_tools import create_networks
from snapmf.network_tools import cytoscape as cy


def network_from_mass_list(atlas_df: pd.DataFrame, parameters: Parameters):
    """Tool to generate compound prediction network from a single mass list. Saves graphML file"""

    target_mass_list = []

    with open(parameters.file_path, encoding="utf-8") as f:
        csv_f = csv.reader(f)
        next(f)

        for row in csv_f:
            target_mass_list.append(float(row[0]))

    if parameters.remove_duplicates:
        target_mass_list = match_compounds.remove_mass_duplicates(
            target_mass_list, parameters.ppm_error
        )
    compound_list = match_compounds.compute_adduct_matches(
        target_mass_list, parameters, atlas_df
    )
    print(f"Found {len(compound_list)} candidate adduct masses")
    compound_network = create_networks.match_compound_network(compound_list, parameters)
    create_networks.remove_small_subgraphs(compound_network, parameters)
    create_networks.annotate_top_candidates(compound_network)
    output_fpath = (
        parameters.output_path / f"{parameters.file_name}_snapms_output.graphml"
    )
    create_networks.export_graphml(compound_network, parameters, output_fpath)
    if cy.cyrest_is_available():
        print("Inserting mass list data into Cytoscape")
        # If there is a job_id in the params, use this to save the output file
        # For this to work, the snapmf datadir should be mounted to the CYTOSCAPE_DATADIR
        # Else use a default
        if parameters.job_id is not None:
            output_path = CYTOSCAPE_DATADIR / parameters.job_id / "snapmf.cys"
        else:
            output_path = CYTOSCAPE_DATADIR / "snapmf.cys"
        create_networks.add_cluster_to_cytoscape(
            compound_network,
            "snapms_mass_list",
        )
        cy.cyrest_save_session(output_path)
        cy.cyrest_delete_session()
    else:
        print("WARNING - Cytoscape Unavailable!")


def network_from_formula_list(atlas_df: pd.DataFrame, parameters: Parameters):
    """Tool to generate a compound prediction network from a single formula list. Saves graphML file"""

    target_formula_list = []

    with open(parameters.file_path, encoding="utf-8") as f:
        csv_f = csv.reader(f)
        next(f)

        for row in csv_f:
            target_formula_list.append(row[0])

    if parameters.remove_duplicates:
        target_formula_list = list(set(target_formula_list))
    compound_list = match_compounds.find_formula_matches(target_formula_list, parameters, atlas_df)
    print(f"Found {len(compound_list)} candidate formula matches")
    print("starting match_compound_network")
    compound_network = create_networks.match_compound_network(compound_list, parameters)
    create_networks.remove_small_subgraphs(compound_network, parameters)
    create_networks.annotate_top_candidates(compound_network)
    output_fpath = (
        parameters.output_path / f"{parameters.file_name}_snapms_output.graphml"
    )
    create_networks.export_graphml(compound_network, parameters, output_fpath)
    if cy.cyrest_is_available():
        print("Inserting mass list data into Cytoscape")
        # If there is a job_id in the params, use this to save the output file
        # For this to work, the snapmf datadir should be mounted to the CYTOSCAPE_DATADIR
        # Else use a default
        if parameters.job_id is not None:
            output_path = CYTOSCAPE_DATADIR / parameters.job_id / "snapmf.cys"
        else:
            output_path = CYTOSCAPE_DATADIR / "snapmf.cys"
        create_networks.add_cluster_to_cytoscape(
            compound_network,
            "snapms_formula_list",
        )
        cy.cyrest_save_session(output_path)
        cy.cyrest_delete_session()
    else:
        print("WARNING - Cytoscape Unavailable!")


def create_gnps_network_annotations(atlas_df: pd.DataFrame, parameters: Parameters):
    """Function to predict identities of all clusters in GNPS graphML file using cluster mapping algorithm"""

    # Analyze each gnps subgraph to create predictions about possible compound families from atlas data.
    # This is the core function of this suite of tools.
    compound_networks = match_compounds.annotate_gnps_network(atlas_df, parameters)

    # write outputs
    parameters.output_path.mkdir(exist_ok=True)
    filtered_networks = {}
    for cluster_id, network in compound_networks.items():
        if create_networks.graph_size_check(
            network,
            parameters.min_compound_group_count,
            parameters.min_atlas_annotation_cluster_size,
            parameters.max_node_count,
            parameters.max_edge_count,
        ):
            create_networks.remove_small_subgraphs(network, parameters)
            create_networks.annotate_top_candidates(network)
            output_fpath = (
                parameters.output_path / f"GNPS_componentindex_{cluster_id}.graphml"
            )
            create_networks.export_graphml(network, parameters, output_fpath)
            filtered_networks[cluster_id] = network
        else:
            print(
                f"ERROR: Atlas annotation graph {cluster_id} either too small or too large. "
                "Skipping insert."
            )

    # TODO: Append all Atlas annotation networks to GNPS original network file
    if cy.cyrest_is_available():
        print("Cytoscape detected - performing network annotation")
        original_gnps_network = data_import.import_gnps_network(parameters)
        create_networks.insert_atlas_clusters_to_cytoscape(
            original_gnps_network, filtered_networks, parameters
        )
    else:
        print("WARNING - Cytoscape Unavailable!")
    if parameters.compress_output:
        create_networks.compress_gnps_graphml_outputs(parameters)
