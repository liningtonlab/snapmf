from pathlib import Path

import networkx as nx
import pytest

from snapmf.network_tools import create_networks

CWD = Path(__file__).parent


def load_test_graph() -> nx.Graph:
    """Load the test dataset file into a networkx graph"""
    return nx.read_graphml(CWD / "test_snapms.graphml")


def test_load_test_graph():
    """Test the helper function"""
    G = load_test_graph()
    assert isinstance(G, nx.Graph)
    assert len(G.nodes) == 63


def test_tanimoto_matrix():
    # trivial test SMILES
    smiles = ["C", "CC", "CCC"]
    expected = [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.4444444444444444],
        [0.0, 0.4444444444444444, 1.0],
    ]
    matrix = create_networks.tanimoto_matrix(smiles)
    # Try and exact comparison for speed
    # if it fails, compare each element approximately
    try:
        assert matrix == expected
    except AssertionError:
        for ri in range(len(matrix)):
            for ci in range(len(matrix[ri])):
                assert matrix[ri] == pytest.approx(expected[ci])


def test_compound_group_counter_all_the_same():
    """Tests counting of compound groups when all values the same"""
    nodes = [
        (1, dict(compound_group=1)),
        (2, dict(compound_group=1)),
        (3, dict(compound_group=1)),
    ]
    G = nx.Graph()
    G.add_nodes_from(nodes)
    assert create_networks.compound_group_counter(G) == 1


def test_compound_group_counter_all_different():
    """Tests counting of compound groups when all values are different"""
    nodes = [
        (1, dict(compound_group=1)),
        (2, dict(compound_group=2)),
        (3, dict(compound_group=3)),
    ]
    G = nx.Graph()
    G.add_nodes_from(nodes)
    assert create_networks.compound_group_counter(G) == 3


def test_compound_group_counter_mixed():
    """Tests counting of compound groups when not some values are the same"""
    nodes = [
        (1, dict(compound_group=1)),
        (2, dict(compound_group=2)),
        (3, dict(compound_group=1)),
    ]
    G = nx.Graph()
    G.add_nodes_from(nodes)
    assert create_networks.compound_group_counter(G) == 2


def test_get_compound_group_count():
    """Tests the counting of unique compound_group's in the test dataset"""
    G = load_test_graph()
    counts = create_networks.get_compound_group_count(G)
    # fmt: off
    expected = {0: 1, 1: 1, 2: 1, 3: 1, 4: 1, 5: 2, 6: 1, 7: 1, 8: 3, 9: 1, 10: 1, 11: 1, 12: 2, 13: 2, 14: 1, 15: 1, 16: 1, 17: 1, 18: 1, 19: 2, 20: 1, 21: 2, 22: 3, 23: 1, 24: 1, 
25: 1, 26: 1, 27: 1, 28: 1, 29: 1, 30: 1, 31: 1, 32: 1, 33: 2, 34: 1, 35: 1, 36: 1, 37: 1, 38: 1, 39: 1, 40: 1}
    # fmt: on
    assert counts == expected


def test_annotate_top_candidates():
    """Test the annotation of a real dataset based on the rules surrounding top candidates"""
    G = load_test_graph()
    expected_top_candidates = (8, 22)
    create_networks.annotate_top_candidates(G)
    # make sure only the correct subgraphs were annotated
    candidate_data = nx.get_node_attributes(G, "top_candidate")
    for idx, sg in enumerate(nx.connected_components(G)):
        if idx in expected_top_candidates:
            assert all(candidate_data[c] == True for c in sg)
        else:
            assert all(candidate_data[c] == False for c in sg)


def test_extract_cluster_id():
    """Test extraction of cluster id from output filename"""
    fp = Path("GNPS_componentindex_1.graphml")
    assert create_networks.extract_cluster_id(fp) == 1


def test_extract_cluster_id_fails():
    """This function is expected to fail if the graphml file name does not end in an int"""
    fp = Path("GNPS_componentindex_AA.graphml")
    with pytest.raises(ValueError):
        assert create_networks.extract_cluster_id(fp)


def test_graph_size_check():
    """Test the testset which should not fail the graph_size_check with real default values"""
    G = load_test_graph()
    assert create_networks.graph_size_check(G, min_group_count=3, min_cluster_size=3)


def test_graph_size_check_too_small():
    """Test the a fake small graph which should fail the graph_size_check with real default values"""
    nodes = [
        (1, dict(compound_group=1)),
        (2, dict(compound_group=2)),
        (3, dict(compound_group=1)),
    ]
    G = nx.Graph()
    G.add_nodes_from(nodes)
    assert not create_networks.graph_size_check(
        G, min_group_count=3, min_cluster_size=3
    )


def test_graph_size_check_too_large():
    """Test the a fake large graph which should fail the graph_size_check with real default values"""
    from random import randint

    nodes = [(i, dict(compound_group=randint(1, 5))) for i in range(10000)]
    G = nx.Graph()
    G.add_nodes_from(nodes)
    assert not create_networks.graph_size_check(
        G, min_group_count=3, min_cluster_size=3
    )


def test_add_chemviz_passthrough_column():
    """Tests adding extra chemviz col to graph"""
    nodes = [
        (1, dict(smiles="C")),
        (2, dict(smiles="CC")),
        (3, dict(smiles="CCCC")),
    ]
    G = nx.Graph()
    G.add_nodes_from(nodes)
    create_networks.add_chemviz_passthrough_column(G, smiles_col="smiles")
    assert all(nd.get("chemViz Passthrough") for _, nd in G.nodes(data=True))
