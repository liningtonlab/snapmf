#!/usr/bin/env python3

"""Tools to create networks of various types for SNAP-MS platform"""
import zipfile
from pathlib import Path
from typing import Dict, List

import networkx as nx
from rdkit import Chem, DataStructs
from rdkit.Chem import AllChem

from snapmf.config import CYTOSCAPE_DATADIR, AtlasFilter, Parameters
from snapmf.matching_tools.CompoundMatch import CompoundMatch
from snapmf.network_tools import cytoscape as cy


def tanimoto_matrix(smiles_list: List[str]) -> List[List[float]]:
    """Creates square matrix of Tanimoto scores for all SMILES strings in the input list"""
    fingerprints = [
        AllChem.GetMorganFingerprint(Chem.MolFromSmiles(compound), 2)
        for compound in smiles_list
    ]
    matrix = [DataStructs.BulkDiceSimilarity(fp, fingerprints) for fp in fingerprints]

    return matrix


def match_compound_network(
    compound_match_list: List[CompoundMatch], parameters: Parameters
) -> nx.Graph:
    """Tool to create a network illustrating relatedness of candidate structures for masses in a GNPS cluster
    Requires the output list from matching_tools.match_compounds.return_compounds
    """

    # Similarity score required to create an edge in the network graph
    tanimoto_cutoff = 0.66

    # Create a list of just the SMILES strings, for the Tanimoto grid generation
    smiles_list = [c.smiles for c in compound_match_list]

    tanimoto_grid = tanimoto_matrix(smiles_list)

    # Create network graph
    compound_graph = nx.Graph()

    # Add compound nodes. index_group_dict indicates which compound group each compound derives from.
    # Used to prevent inclusion of edges between compounds from the same group
    # (i.e. candidates for the same original mass)
    node_list = []
    adduct_dict = {
        "m_plus_h": "[M+H]+",
        "m_plus_na": "[M+Na]+",
        "m_plus_nh4": "[M+NH4]+",
        "m_plus_h_minus_h2o": "[M-H2O+H]+",
        "m_plus_k": "[M+K]+",
        "2m_plus_h": "[2M+H]+",
        "2m_plus_na": "[2M+Na]+",
        "m_minus_h": "[M-H]+",
        "m_plus_cl": "[M+Cl]+",
        "m_plus_coo": "[M+COO]+",
    }
    index_group_dict = {}
    for index, compound in enumerate(compound_match_list):
        if parameters.analysis_mode == "snapmf":
            adduct = str(None)
        else:
            adduct = adduct_dict[compound.adduct]
        if parameters.atlas_filter == AtlasFilter.coconut:
            node_list.append(
                (
                    index,
                    {
                        "coconut_id": compound.coconut_id,
                        "exact_mass": compound.exact_mass,
                        "smiles": compound.smiles,
                        "compound_name": compound.friendly_name(),
                        "coconut_url": compound.coconut_url,
                        "original_gnps_mass": compound.mass,
                        "compound_group": compound.compound_number,
                        "adduct": adduct,
                        "origin_organism_type": "Unknown",
                    },
                )
            )
        elif parameters.atlas_filter in [
            AtlasFilter.full,
            AtlasFilter.bacteria,
            AtlasFilter.fungi,
            AtlasFilter.custom,
        ]:
            try:
                node_list.append(
                (
                    index,
                    {
                        "npaid": compound.npaid,
                        "exact_mass": compound.exact_mass,
                        "smiles": compound.smiles,
                        "compound_name": compound.friendly_name(),
                        "npatlas_url": compound.npatlas_url,
                        "original_gnps_mass": compound.mass,
                        "compound_group": compound.compound_number,
                        "adduct": adduct,
                        "origin_organism_type": compound.origin_organism_type,
                    },
                )
            )
            except:
                print(f"ERROR: compound {compound.compound_number} not found")
        else:
            print("ERROR: atlas_filter not found")
        index_group_dict[index] = compound.compound_number
    compound_graph.add_nodes_from(node_list)

    # Add edges if above Dice threshold and not between compounds in the same compound group
    # (i.e. compounds that are included because they are candidates for the same original mass from GNPS)
    edge_list = []
    for row_idx, row in enumerate(tanimoto_grid):
        for col_idx, value in enumerate(row):
            if row_idx == col_idx:
                continue
            if (
                value >= tanimoto_cutoff
                and index_group_dict[row_idx] != index_group_dict[col_idx]
            ):
                edge_list.append((row_idx, col_idx))
    compound_graph.add_edges_from(edge_list)

    return compound_graph


def export_graphml(graph: nx.Graph, parameters: Parameters, output_path: Path):
    """Exports networkx graph from match_compound_network as graphML for use in external visualization tools"""
    if graph_size_check(
        graph,
        parameters.min_compound_group_count,
        parameters.min_atlas_annotation_cluster_size,
        parameters.max_node_count,
        parameters.max_edge_count,
    ):
        nx.write_graphml(graph, output_path)
    else:
        print(
            f"WARNING - {output_path} is outside size parameters and is not being written"
        )


def compress_gnps_graphml_outputs(parameters: Parameters):
    """Compress the graphml output files for cytoscape job"""
    output_zip = parameters.output_path / "GNPS_components_snapms.zip"
    with zipfile.ZipFile(output_zip, "w") as zipf:
        for f in parameters.output_path.glob("GNPS*[0-9].graphml"):
            if parameters.job_id is not None:
                arcname = Path(f"snapms_{parameters.job_id}") / f.name
            else:
                arcname = Path("snapmf") / f.name
            # get path relative to CWD
            zipf.write(f.relative_to(Path().absolute()), arcname=arcname)
            f.unlink()


def insert_atlas_clusters_to_cytoscape(
    original_gnps_graph, filtered_networks: Dict[int, nx.Graph], parameters: Parameters
):
    """Tool to create a new collection in an existing Cytoscape file, and to append all Atlas GNPS annotation networks
    as separate network views.

    Networks should be pre-filtered for size and annotated with top candidates already.
    """
    # Import original gnps network (currently not implemented)
    print("Adding original GNPS network to Cytoscape file")
    add_original_gnps_graph_to_cytoscape(original_gnps_graph, "Original_GNPS_graph")
    # Open each Atlas annotation network in turn. Glob function includes [0-9] in order to exclude the modified original
    # gnps network (if present)

    for cluster_id, atlas_graph in sorted(filtered_networks.items()):
        network_title = f"GNPS_componentindex_{cluster_id}"

        print(f"Starting insertion of {network_title} to GNPS network file")
        # Annotate subgraphs to find those subgraphs which are top candidates for the correct compound
        # family
        add_cluster_to_cytoscape(
            atlas_graph,
            network_title,
        )

    # If there is a job_id in the params, use this to save the output file
    # For this to work, the snapmf datadir should be mounted to the CYTOSCAPE_DATADIR
    # Else use a default
    if parameters.job_id is not None:
        output_path = CYTOSCAPE_DATADIR / parameters.job_id / "snapmf.cys"
    else:
        output_path = CYTOSCAPE_DATADIR / "snapmf.cys"
    print(f"Saving {output_path}")
    cy.cyrest_save_session(output_path)
    cy.cyrest_delete_session()


def remove_small_subgraphs(G: nx.Graph, parameters: Parameters):
    """Remove subgraphs that do not have the minimum required number of nodes. Useful for removing large
    numbers of small clusters containing just one or two Atlas compounds
    """
    nodes_to_include = set()
    for subgraph in nx.connected_components(G):
        if len(subgraph) >= parameters.min_atlas_annotation_cluster_size:
            nodes_to_include.update(subgraph)
    nodes_to_remove = set(G.nodes()) - nodes_to_include
    G.remove_nodes_from(nodes_to_remove)


def add_cluster_to_cytoscape(G: nx.Graph, title: str) -> None:
    """Add graph to cytoscape session and applying styling.

    IMPORTANT: Assumes CyREST is available.
    """
    add_chemviz_passthrough_column(G)
    # Insert Atlas annotation graph to Cytoscape file
    network_id = cy.networkx_to_cyrest(G, name=title)
    cy.cyrest_apply_layout(network_id, name="force-directed")
    cy.cyrest_create_style(cy.SNAP_MS_STYLE, force=False)
    cy.cyrest_apply_style(network_id, cy.SNAP_MS_STYLE["title"])


def add_original_gnps_graph_to_cytoscape(G: nx.Graph, title: str) -> None:
    """Add original GNPS graph to cytoscape session and applying GNPS styling.

    IMPORTANT: Assumes CyREST is available.
    """
    network_id = cy.networkx_to_cyrest(G, name=title)
    cy.cyrest_apply_layout(network_id, name="force-directed")
    cy.cyrest_create_style(cy.GNPS_STYLE, force=False)
    cy.cyrest_apply_style(network_id, cy.GNPS_STYLE["title"])


def extract_cluster_id(filepath: Path) -> int:
    """Tool to extract the GNPS componentindex (i.e. cluster id) from the Atlas annotation cluster filename.
    Used to sort the Atlas networks so that they are processed and inserted into the Cytoscape file in numerical order

    """
    filename = Path(filepath).stem
    cluster_id = int(filename.rsplit("_")[-1])
    return cluster_id


def graph_size_check(
    G: nx.Graph,
    min_group_count: int,
    min_cluster_size: int,
    max_node_count: int = 2000,
    max_edge_count: int = 10000,
) -> bool:
    """Assess overall size of networkx graphs. Used to skip graphs that are too small or too large, or that have become
    too small after filtering steps

    """
    # Assess the results graph to make sure that at least one subgraph contains the minimum number of compound groups
    # and that the nodes and edges do not violate max limits
    group_counts = get_compound_group_count(G)

    try:
        max_compound_group_count = max(group_counts.values())
    # save when max empty sequence
    except ValueError:
        return False
    if (
        max_compound_group_count >= min_group_count
        and min_cluster_size <= len(nx.nodes(G)) < max_node_count
        and len(nx.edges(G)) < max_edge_count
    ):
        return True
    return False


def compound_group_counter(G: nx.Graph) -> int:
    """Count the number of unique compound groups in any graph or subgraph
    Makes sure the graph nodes have compound_group values
    """
    compound_groups = set(
        nd
        for _, node_data in G.nodes(data=True)
        if (nd := node_data.get("compound_group")) is not None
    )

    return len(compound_groups)


def get_compound_group_count(G: nx.Graph) -> Dict[int, int]:
    """Compute the compound group count in any subgraph in the main graph.

    Returns a dictionary with subgraph index key and count value
    """
    counts = {}
    for idx, subgraph in enumerate(nx.connected_components(G)):
        S = G.subgraph(subgraph)
        counts[idx] = compound_group_counter(S)
    return counts


def annotate_top_candidates(G: nx.Graph) -> None:
    """Annotate subgraphs as top candidate answers, based on maximum compound group counts within each subgraph
    in the network. In other words, if three answers all have four compound groups and this is the highest compound
    group count, then these three answers are all equally likely to be correct.
    """
    group_counts = get_compound_group_count(G)

    # globally set top_candidate attribute to False
    nx.set_node_attributes(G, values=False, name="top_candidate")
    try:
        max_group_count = max(group_counts.values())
    except ValueError:
        max_group_count = -1
    for idx, subgraph in enumerate(nx.connected_components(G)):
        if group_counts[idx] == max_group_count:
            print(f"Subgraph {idx} is a top candidate")
            nx.set_node_attributes(
                G, values={nid: True for nid in subgraph}, name="top_candidate"
            )


def add_chemviz_passthrough_column(G: nx.Graph, smiles_col: str = "smiles"):
    """Adds a chemViz Passthrough column to the output"""
    for _, nd in G.nodes(data=True):
        nd["chemViz Passthrough"] = f"chemviz:{nd[smiles_col]}"
