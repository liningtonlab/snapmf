#!/usr/bin/env python3

""" An application to identify groups of natural products by comparing grouped mass spectrometry features and compound
groups from chemical similarity methods
"""

import sys
from pathlib import Path

from snapmf.atlas_tools.atlas_import import import_atlas
from snapmf.config import AtlasFilter, Parameters
from snapmf.core import create_gnps_network_annotations, network_from_mass_list

# current working directory for data file paths
CWD = Path(__file__).parent


def main():
    DATADIR = CWD / "data"
    assert DATADIR.exists()

    #### CONFIG
    # source_ms_data = DATADIR / "ms_input" / "mass_list.csv"
    source_ms_data = DATADIR / "ms_input" / "NIHNaturalProducts1.graphml"
    atlas_data = DATADIR / "NPAtlas_download.json"
    output_directory = DATADIR / "output" / "gnps"
    # TODO: Add all optional params explicitly for example script
    parameters = Parameters(
        source_ms_data,
        atlas_data,
        output_directory,
        atlas_filter=AtlasFilter.custom,
        custom_filter="Ascomycota|Cyanobacteria",
    )

    # Load Atlas data as Pandas dataframe
    print("Loading NP Atlas data")
    atlas_df = import_atlas(parameters)

    if parameters.file_type == "csv":
        network_from_mass_list(atlas_df, parameters)
    elif parameters.file_type == "graphml":
        create_gnps_network_annotations(atlas_df, parameters)
    else:
        print(
            "ERROR: This file type is not supported. Supported types include csv (for simple peak lists) and graphML "
            "(for standard GNPS output)"
        )
        sys.exit(-1)


if __name__ == "__main__":
    main()
