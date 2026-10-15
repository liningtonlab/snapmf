from pathlib import Path

import networkx as nx
import responses  # mocking out requests

from snapmf.network_tools import cytoscape as cy

CWD = Path(__file__).parent


@responses.activate
def test_cyrest_is_available():
    """Tests expected repsonse when cyrest is online"""
    responses.add(
        responses.GET,
        f"{cy.BASE_URL}",
        json={
            "allAppsStarted": True,
            "apiVersion": "v1",
            "numberOfCores": 24,
            "memoryStatus": {
                "usedMemory": 532,
                "freeMemory": 1446,
                "totalMemory": 1979,
                "maxMemory": 30013,
            },
        },
        status=200,
    )

    assert cy.cyrest_is_available()


@responses.activate
def test_cyrest_is_available_unavailable():
    """Tests expected repsonse when cyrest is offline"""
    responses.add(
        responses.GET,
        f"{cy.BASE_URL}",
        json={},
        status=404,
    )

    assert not cy.cyrest_is_available()


@responses.activate
def test_networkx_to_cyrest():
    """Tests expected repsonse when creating a new network from networkX"""
    responses.add(
        responses.POST,
        f"{cy.BASE_URL}/networks",
        json={"networkSUID": 1},
        status=200,
        match=[],  # ignore collection name in query params
    )
    G = nx.karate_club_graph()  # simple network
    assert isinstance(G, nx.Graph)
    network_id = cy.networkx_to_cyrest(G)
    assert network_id == 1


@responses.activate
def test_cyrest_apply_layout():
    """Tests expected response when succesfully applying layout to network"""
    responses.add(
        responses.GET,
        f"{cy.BASE_URL}/apply/layouts/force-directed/1",
        json={"message": "Layout finished."},
        status=200,
    )
    status, _ = cy.cyrest_apply_layout(1)
    assert status == 200
    status, _ = cy.cyrest_apply_layout(1, name="force-directed")
    assert status == 200


@responses.activate
def test_cyrest_apply_layout_invalid():
    """Tests expected response when invalid style name provided"""
    responses.add(
        responses.GET,
        f"{cy.BASE_URL}/apply/layouts/NONE/1",
        json={
            "data": {},
            "errors": [
                {
                    "status": 404,
                    "type": "urn:cytoscape:ci:cyrest-core:v1:apply:errors:4",
                    "message": "Visual Style does not exist: default1",
                    "link": "file:/C:/Users/jeffv/CytoscapeConfiguration/3/framework-cytoscape.log",
                }
            ],
        },
        status=404,
    )
    status, _ = cy.cyrest_apply_layout(1, name="NONE")
    assert status == 404


@responses.activate
def test_cyrest_style_exists():
    """Tests expected response when a style exists in cytoscape"""
    name = "default"
    responses.add(
        responses.GET,
        f"{cy.BASE_URL}/styles/{name}",
        json={"title": "default", "defaults": [], "mappings": []},
        status=200,
    )
    assert cy.cyrest_style_exists(name, verbose=True)


@responses.activate
def test_cyrest_style_exists_does_not_exist():
    """Tests expected response when a style does not exists in cytoscape"""
    name = "BAD"
    responses.add(
        responses.GET,
        f"{cy.BASE_URL}/styles/{name}",
        json={
            "data": {},
            "errors": [
                {
                    "status": 404,
                    "type": "urn:cytoscape:ci:cyrest-core:v1:styles:errors:3",
                    "message": "Could not find Visual Style: default1",
                    "link": "file:/C:/Users/jeffv/CytoscapeConfiguration/3/framework-cytoscape.log",
                }
            ],
        },
        status=404,
    )
    assert not cy.cyrest_style_exists(name, verbose=True)


@responses.activate
def test_cyrest_create_style():
    """Tests expected response when creating a style in cytoscape
    Requires two API calls
    """
    name = cy.SNAP_MS_STYLE.get("title")
    # not present
    responses.add(
        responses.GET,
        f"{cy.BASE_URL}/styles/{name}",
        json={},
        status=404,
    )
    responses.add(
        responses.POST,
        f"{cy.BASE_URL}/styles",
        json={"title": name},
        status=201,
    )
    status, _ = cy.cyrest_create_style(cy.SNAP_MS_STYLE)
    assert status == 201


@responses.activate
def test_cyrest_create_style_already_exists():
    """Tests expected response when creating a style in cytoscape
    Requires two API calls
    """
    name = cy.SNAP_MS_STYLE.get("title")
    # not present
    responses.add(
        responses.GET,
        f"{cy.BASE_URL}/styles/{name}",
        json=cy.SNAP_MS_STYLE,
        status=200,
    )
    responses.add(
        responses.POST,
        f"{cy.BASE_URL}/styles",
        json={"title": name},
        status=403,
    )
    status, _ = cy.cyrest_create_style(cy.SNAP_MS_STYLE)
    assert status == 403


@responses.activate
def test_cyrest_create_style_already_exists_force():
    """Tests expected response when creating a style in cytoscape
    Requires three API calls
    """
    name = cy.SNAP_MS_STYLE.get("title")
    # not present
    responses.add(
        responses.GET,
        f"{cy.BASE_URL}/styles/{name}",
        json=cy.SNAP_MS_STYLE,
        status=200,
    )
    responses.add(
        responses.DELETE,
        f"{cy.BASE_URL}/styles/{name}",
        json=cy.SNAP_MS_STYLE,
        status=200,
    )
    responses.add(
        responses.POST,
        f"{cy.BASE_URL}/styles",
        json={"title": name},
        status=201,
    )
    status, _ = cy.cyrest_create_style(cy.SNAP_MS_STYLE, force=True)
    assert status == 201


@responses.activate
def test_cyrest_create_style_does_not_exists_force():
    """Tests expected response when creating a style in cytoscape
    Requires two API calls
    """
    name = cy.SNAP_MS_STYLE.get("title")
    # not present
    responses.add(
        responses.GET,
        f"{cy.BASE_URL}/styles/{name}",
        json={},
        status=404,
    )
    responses.add(
        responses.POST,
        f"{cy.BASE_URL}/styles",
        json={"title": name},
        status=201,
    )
    status, _ = cy.cyrest_create_style(cy.SNAP_MS_STYLE, force=True)
    assert status == 201


@responses.activate
def test_cyrest_apply_style():
    """Tests expected response when applying a style which exists in cytoscape"""
    name = "default"
    responses.add(
        responses.GET,
        f"{cy.BASE_URL}/apply/styles/{name}/1",
        json={"message": "Visual Style applied."},
        status=200,
    )
    status, _ = cy.cyrest_apply_style(1)
    assert status == 200
    status, _ = cy.cyrest_apply_style(1, style=name)
    assert status == 200


@responses.activate
def test_cyrest_apply_style_does_not_exists():
    """Tests expected response when applying a style which exists in cytoscape"""
    name = "BAD"
    responses.add(
        responses.GET,
        f"{cy.BASE_URL}/apply/styles/{name}/1",
        json={
            "data": {},
            "errors": [
                {
                    "status": 404,
                    "type": "urn:cytoscape:ci:cyrest-core:v1:apply:errors:4",
                    "message": "Visual Style does not exist: ClassDefault_",
                    "link": "file:/C:/Users/jeffv/CytoscapeConfiguration/3/framework-cytoscape.log",
                }
            ],
        },
        status=404,
    )
    status, _ = cy.cyrest_apply_style(1, style=name)
    assert status == 404


@responses.activate
def test_cyrest_install_app():
    name = "chemViz2"
    responses.add(
        responses.POST,
        f"{cy.BASE_URL}/commands/apps/install",
        json={"data": {}, "errors": []},
        status=200,
    )
    status, _ = cy.cyrest_install_app(name)
    assert status == 200


@responses.activate
def test_cyrest_install_app_fails():
    name = "chemVizNonExistent"
    responses.add(
        responses.POST,
        f"{cy.BASE_URL}/commands/apps/install",
        json={"data": {}, "errors": []},
        status=200,
    )
    status, _ = cy.cyrest_install_app(name)
    assert status == 200


@responses.activate
def test_cyrest_load_session():
    file_path = CWD / "test_session.cys"
    responses.add(
        responses.GET,
        f"{cy.BASE_URL}/session",
        json={"file": str(file_path.absolute)},
        status=200,
        match=[],  # ignore collection name in query params
    )
    status, _ = cy.cyrest_load_session(file_path)
    assert status == 200


# @responses.activate
# def test_cyrest_load_session_non_existant_session():
#     file_path = CWD / "test_session_NOT_EXIST.cys"
#     responses.add(
#         responses.GET,
#         f"{cy.BASE_URL}/session",
#         json={"file": str(file_path.absolute)},
#         status=200,
#         match_querystring=False,  # ignore collection name
#     )
#     with pytest.raises(FileNotFoundError):
#         cy.cyrest_load_session(file_path)


@responses.activate
def test_cyrest_save_session():
    file_path = CWD / "test_session_save.cys"
    responses.add(
        responses.POST,
        f"{cy.BASE_URL}/session",
        json={"file": str(file_path.absolute)},
        status=200,
        match=[],  # ignore collection name in query params
    )
    status, _ = cy.cyrest_save_session(file_path)
    assert status == 200


# @responses.activate
# def test_cyrest_save_session_bad_parent_dir():
#     file_path = CWD / "NOTEXIST" / "test_session_save.cys"
#     responses.add(
#         responses.POST,
#         f"{cy.BASE_URL}/session",
#         json={"file": str(file_path.absolute)},
#         status=200,
#         match_querystring=False,  # ignore collection name
#     )
#     with pytest.raises(FileNotFoundError):
#         cy.cyrest_save_session(file_path)


@responses.activate
def test_cyrest_delete_session():
    responses.add(
        responses.DELETE,
        f"{cy.BASE_URL}/session",
        json={"message": "New session created."},
        status=200,
    )
    status, _ = cy.cyrest_delete_session()
    assert status == 200
