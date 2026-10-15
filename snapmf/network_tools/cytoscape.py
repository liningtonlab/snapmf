"""Conversion and API access tools for the Cytoscape CyREST API"""
import os
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import quote

import networkx as nx
import requests

# Response custom datatype
Response = Tuple[int, Dict]

BASE_URL = os.getenv("CYTOSCAPE_BASEURL", "http://localhost:1234/v1")
HEADERS = {"Content-Type": "application/json"}

# Converters derived from (under MIT License)
# https://github.com/cytoscape/py2cytoscape/blob/develop/py2cytoscape/util/util_networkx.py

# Special Keys
ID = "id"
NAME = "name"
DATA = "data"
ELEMENTS = "elements"

NODES = "nodes"
EDGES = "edges"

SOURCE = "source"
TARGET = "target"
DEF_SCALE = 100


def __build_empty_graph():
    return {DATA: {}, ELEMENTS: {NODES: [], EDGES: []}}


def __build_edge(edge_tuple):
    source = edge_tuple[0]
    target = edge_tuple[1]
    data = edge_tuple[2]

    data["source"] = str(source)
    data["target"] = str(target)
    return {DATA: data}


def __map_table_data(columns, graph_obj):
    data = {}
    for col in columns:
        if col == 0:
            break

        data[col] = graph_obj[col]

    return data


def __create_node(node, node_id):
    new_node = {}
    node_columns = node.keys()
    data = __map_table_data(node_columns, node)
    # Override special keys
    data[ID] = str(node_id)
    data[NAME] = str(node_id)

    if "position" in node.keys():
        position = node["position"]
        new_node["position"] = position

    new_node[DATA] = data
    return new_node


def cyjson_from_networkx(
    g: nx.Graph, layout: Optional[str] = None, scale: int = DEF_SCALE
):
    """Construct a cyjson dictionary from a networkx Graph"""
    # Dictionary Object to be converted to Cytoscape.js JSON
    cygraph = __build_empty_graph()

    if layout is not None:
        pos = map(
            lambda position: {"x": position[0] * scale, "y": position[1] * scale},
            layout.values(),
        )

    nodes = g.nodes()
    # Not interested in supporting Multi / MultiDi graphs for now
    # if isinstance(g, nx.MultiDiGraph) or isinstance(g, nx.MultiGraph):
    #     edges = g.edges(data=True, keys=True)
    #     edge_builder = __build_multi_edge
    # else:
    edges = g.edges(data=True)
    edge_builder = __build_edge

    # Map network table data
    cygraph[DATA] = __map_table_data(g.graph.keys(), g.graph)

    for i, node_id in enumerate(nodes):
        new_node = __create_node(g.nodes[node_id], node_id)
        if layout is not None:
            new_node["position"] = pos[i]

        cygraph["elements"]["nodes"].append(new_node)

    for edge in edges:
        cygraph["elements"]["edges"].append(edge_builder(edge))

    return cygraph


def cyjson_to_networkx(cyjs):
    """
    Convert Cytoscape.js-style JSON object into NetworkX object.
    By default, data will be handles as a directed graph.
    """

    g = nx.Graph()

    network_data = cyjs[DATA]
    if network_data is not None:
        for key in network_data.keys():
            g.graph[key] = network_data[key]

    nodes = cyjs[ELEMENTS][NODES]
    edges = cyjs[ELEMENTS][EDGES]

    for node in nodes:
        data = node[DATA]
        g.add_node(data[ID], attr_dict=data)

    for edge in edges:
        data = edge[DATA]
        source = data[SOURCE]
        target = data[TARGET]

        g.add_edge(source, target, attr_dict=data)

    return g


def networkx_to_cyrest(
    G: nx.Graph, name: str = "snapmf network", collection="snapmf collection"
) -> Optional[int]:
    """Create network in Cytoscape from a networkx network.

    Returns the Network ID used for applying layouts, styles, or getting back data.
    """
    cyjson = cyjson_from_networkx(G)
    cyjson[DATA]["name"] = name

    r = requests.post(
        f"{BASE_URL}/networks?collection={quote(collection)}",
        json=cyjson,
        headers=HEADERS,
    )
    return r.json().get("networkSUID")


def cyrest_to_networkx(network: int) -> Optional[nx.Graph]:
    """Get a networkx graph object from the networkx"""
    r = requests.get(f"{BASE_URL}/networks/{network}", headers=HEADERS)
    cyjs = r.json()
    if not cyjs:
        return None
    return cyjson_to_networkx(cyjs)


def cyrest_is_available() -> bool:
    """Check if Cytoscape is available"""
    try:
        r = requests.get(f"{BASE_URL}", headers=HEADERS)
        return r.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


def cyrest_apply_layout(network: int, name="force-directed") -> Response:
    """Apply a layout to a network in Cytoscape given the network ID
    Returns JSON response.
    """
    r = requests.get(f"{BASE_URL}/apply/layouts/{name}/{network}", headers=HEADERS)
    return r.status_code, r.json()


def cyrest_style_exists(name: str, verbose: bool = False) -> bool:
    """Check if a style exists by name. If verbose, print the style"""
    r = requests.get(f"{BASE_URL}/styles/{name}", headers=HEADERS)
    style = r.json()
    if verbose:
        print(style)
    if r.status_code == 200:
        return True
    return False


def cyrest_create_style(style: Dict, force: bool = False) -> Response:
    """Create a cytoscape style with a given name.
    See http://manual.cytoscape.org/en/stable/Styles.html#importing-styles for details on style and mapping objects.

    style: style dict with (title, defaults, mappings) fields
    force: if a style already exists, delete it and create a new one

    Return response JSON.
    """
    name = style.get("title", "Unnamed")
    if cyrest_style_exists(name):
        print(f"Style {name} exists")
        if not force:
            # fake HTTP Reponse
            # 403 = already exists
            return 403, {"title": name}
        requests.delete(f"{BASE_URL}/styles/{name}", headers=HEADERS)

    r = requests.post(
        f"{BASE_URL}/styles",
        json=style,
        headers=HEADERS,
    )
    return r.status_code, r.json()


def cyrest_apply_style(network: int, style: str = "default") -> Response:
    """Apply a named style to a network in Cytoscape
    Returns JSON response.
    """
    r = requests.get(f"{BASE_URL}/apply/styles/{style}/{network}", headers=HEADERS)
    return r.status_code, r.json()


def cyrest_install_app(app_name: str) -> Response:
    """Install a cytoscape app by name
    Returns JSON response

    WARNING: CyREST DOES NOT REPORT ERRORS FOR APP INSTALLATION.

    Example:
    ```
    cyrest_install_app(app_name="chemViz2")
    ```
    """
    r = requests.post(
        f"{BASE_URL}/commands/apps/install", json={"app": app_name}, headers=HEADERS
    )
    return r.status_code, r.json()


def cyrest_load_session(file_path: Path) -> Response:
    """Load the a Cytoscape session from a file.
    Raises a `FileNotFoundError` if file does not exist.

    Returns JSON response
    """
    # This doesn't make sense with CyREST in a container
    # if not file_path.exists():
    #     raise FileNotFoundError("Session file does not exist")
    r = requests.get(
        f"{BASE_URL}/session?file={quote(str(file_path.absolute()))}", headers=HEADERS
    )
    return r.status_code, r.json()


def cyrest_save_session(file_path: Path) -> Response:
    """Save the current Cytoscape session to a given path.
    Makes sure the parent directory of the specified path exists.
    Raises a `FileNotFoundError` if parent directory does not exist.

    Returns JSON response
    """
    # This doesn't make sense with CyREST in a container
    # if not file_path.parent.exists():
    #     raise FileNotFoundError("Directory to save file does not exist")
    r = requests.post(
        f"{BASE_URL}/session?file={quote(str(file_path.absolute()))}", headers=HEADERS
    )
    return r.status_code, r.json()


def cyrest_delete_session() -> Response:
    """Close the current Cytoscape session, starting a new one.
    Returns JSON response
    """
    r = requests.delete(f"{BASE_URL}/session", headers=HEADERS)
    return r.status_code, r.json()


####################
###### STYLES ######
####################
SNAP_MS_STYLE = {
    "title": "Undirected",
    "defaults": [
        {"visualProperty": "NODE_SHAPE", "value": "ELLIPSE"},
        {"visualProperty": "NODE_FILL_COLOR", "value": "white"},
        {"visualProperty": "NODE_SIZE", "value": 75},
        {"visualProperty": "NODE_BORDER_WIDTH", "value": 2},
        {"visualProperty": "NODE_BORDER_PAINT", "value": "blue"},
        {"visualProperty": "NODE_TRANSPARENCY", "value": 255},
        {"visualProperty": "NODE_LABEL_COLOR", "value": "black"},
        {"visualProperty": "EDGE_WIDTH", "value": 3},
        {"visualProperty": "EDGE_LINE_TYPE", "value": "LINE"},
        {"visualProperty": "EDGE_LINE_COLOR", "value": "black"},
        {"visualProperty": "EDGE_TRANSPARENCY", "value": 120},
        {"visualProperty": "NETWORK_BACKGROUND_PAINT", "value": "white"},
    ],
    "mappings": [
        {
            "mappingType": "passthrough",
            "mappingColumn": "compound_name",
            "mappingColumnType": "String",
            "visualProperty": "NODE_LABEL",
        },
        {
            "mappingType": "passthrough",
            "mappingColumn": "chemViz Passthrough",
            "mappingColumnType": "String",
            "visualProperty": "NODE_CUSTOMGRAPHICS_2",
        },
        {
            "mappingType": "discrete",
            "mappingColumn": "top_candidate",
            "mappingColumnType": "Boolean",
            "visualProperty": "NODE_BORDER_WIDTH",
            "map": [{"key": "false", "value": "2.0"}, {"key": "true", "value": "10.0"}],
        },
    ],
}

GNPS_STYLE = {
    "title": "ClassDefault",
    "defaults": [
        {"visualProperty": "COMPOUND_NODE_PADDING", "value": 10.0},
        {"visualProperty": "COMPOUND_NODE_SHAPE", "value": "ROUND_RECTANGLE"},
        {"visualProperty": "EDGE_BEND", "value": ""},
        {"visualProperty": "EDGE_CURVED", "value": True},
        {"visualProperty": "EDGE_LABEL", "value": ""},
        {"visualProperty": "EDGE_LABEL_COLOR", "value": "#000000"},
        {"visualProperty": "EDGE_LABEL_FONT_FACE", "value": "SansSerif.plain,plain,10"},
        {"visualProperty": "EDGE_LABEL_FONT_SIZE", "value": 10},
        {"visualProperty": "EDGE_LABEL_TRANSPARENCY", "value": 255},
        {"visualProperty": "EDGE_LABEL_WIDTH", "value": 200.0},
        {"visualProperty": "EDGE_LINE_TYPE", "value": "SOLID"},
        {"visualProperty": "EDGE_PAINT", "value": "#808080"},
        {"visualProperty": "EDGE_SELECTED", "value": False},
        {"visualProperty": "EDGE_SELECTED_PAINT", "value": "#FF0000"},
        {"visualProperty": "EDGE_SOURCE_ARROW_SELECTED_PAINT", "value": "#FFFF00"},
        {"visualProperty": "EDGE_SOURCE_ARROW_SHAPE", "value": "NONE"},
        {"visualProperty": "EDGE_SOURCE_ARROW_SIZE", "value": 6.0},
        {"visualProperty": "EDGE_SOURCE_ARROW_UNSELECTED_PAINT", "value": "#000000"},
        {"visualProperty": "EDGE_STROKE_SELECTED_PAINT", "value": "#FF0000"},
        {"visualProperty": "EDGE_STROKE_UNSELECTED_PAINT", "value": "#FFFFFF"},
        {"visualProperty": "EDGE_TARGET_ARROW_SELECTED_PAINT", "value": "#FFFF00"},
        {"visualProperty": "EDGE_TARGET_ARROW_SHAPE", "value": "NONE"},
        {"visualProperty": "EDGE_TARGET_ARROW_SIZE", "value": 6.0},
        {"visualProperty": "EDGE_TARGET_ARROW_UNSELECTED_PAINT", "value": "#000000"},
        {"visualProperty": "EDGE_TOOLTIP", "value": ""},
        {"visualProperty": "EDGE_TRANSPARENCY", "value": 255},
        {"visualProperty": "EDGE_UNSELECTED_PAINT", "value": "#404040"},
        {"visualProperty": "EDGE_VISIBLE", "value": True},
        {"visualProperty": "EDGE_WIDTH", "value": 20.0},
        {"visualProperty": "NETWORK_BACKGROUND_PAINT", "value": "#EBE8E1"},
        {"visualProperty": "NODE_BORDER_PAINT", "value": "#FFFFFF"},
        {"visualProperty": "NODE_BORDER_STROKE", "value": "SOLID"},
        {"visualProperty": "NODE_BORDER_TRANSPARENCY", "value": 255},
        {"visualProperty": "NODE_BORDER_WIDTH", "value": 15.0},
        {"visualProperty": "NODE_DEPTH", "value": 0.0},
        {"visualProperty": "NODE_FILL_COLOR", "value": "#3A7FB6"},
        {"visualProperty": "NODE_HEIGHT", "value": 40.0},
        {"visualProperty": "NODE_LABEL", "value": ""},
        {"visualProperty": "NODE_LABEL_COLOR", "value": "#666666"},
        {"visualProperty": "NODE_LABEL_FONT_FACE", "value": "Dialog.plain,plain,12"},
        {"visualProperty": "NODE_LABEL_FONT_SIZE", "value": 20},
        {"visualProperty": "NODE_LABEL_POSITION", "value": "E,W,c,5.00,0.00"},
        {"visualProperty": "NODE_LABEL_TRANSPARENCY", "value": 255},
        {"visualProperty": "NODE_LABEL_WIDTH", "value": 200.0},
        {"visualProperty": "NODE_NESTED_NETWORK_IMAGE_VISIBLE", "value": True},
        {"visualProperty": "NODE_PAINT", "value": "#787878"},
        {"visualProperty": "NODE_SELECTED", "value": False},
        {"visualProperty": "NODE_SELECTED_PAINT", "value": "#FFFF00"},
        {"visualProperty": "NODE_SHAPE", "value": "ELLIPSE"},
        {"visualProperty": "NODE_SIZE", "value": 50.0},
        {"visualProperty": "NODE_TRANSPARENCY", "value": 255},
        {"visualProperty": "NODE_VISIBLE", "value": True},
        {"visualProperty": "NODE_WIDTH", "value": 60.0},
    ],
    "mappings": [
        {
            "mappingType": "passthrough",
            "mappingColumn": "Compound_Name",
            "mappingColumnType": "String",
            "visualProperty": "NODE_LABEL",
        }
    ],
}
