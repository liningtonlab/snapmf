"""Tools to import peak lists or gnps networks to SNAP-MS"""

import tempfile
from pathlib import Path

import networkx as nx

from snapmf.config import Parameters


def fix_long_dtype(fpath: Path) -> tempfile.TemporaryFile:
    temp_f = tempfile.TemporaryFile()
    with open(fpath, encoding="utf-8") as f:
        for l in f.readlines():
            temp_f.write(l.replace('attr.type="long"', 'attr.type="int"').encode())
    temp_f.seek(0)
    return temp_f


def import_gnps_network(parameters: Parameters):
    """Import the original GNPS network file (graphML) downloaded from the GNPS output site"""
    # Networkx 2.5 has a bug which fails to read `long` data from graphML
    # Read in the file and replace any `long` with `int` dtypes
    # Create temp file
    try:
        with open(parameters.file_path, encoding="utf-8") as f:
            import_network = nx.read_graphml(f)
    except KeyError:
        temp_f = fix_long_dtype(parameters.file_path)
        import_network = nx.read_graphml(temp_f)
        temp_f.close()

    if nx.is_directed(import_network):
        gnps_network = import_network.to_undirected()
    else:
        gnps_network = import_network

    return gnps_network
