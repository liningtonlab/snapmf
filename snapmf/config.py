from enum import Enum
from os import getenv
from pathlib import Path
from typing import List, Optional

CYTOSCAPE_DATADIR = Path(getenv("CYTOSCAPE_DATADIR", "/root/data"))

# Defaults
DEFAULT_ADDUCT_LIST = [
    "m_plus_h",
    "m_plus_na",
    "m_plus_nh4",
    "m_plus_h_minus_h2o",
    "m_plus_k",
    "2m_plus_h",
    "2m_plus_na",
]


class AtlasFilter(str, Enum):
    full = "full"
    bacteria = "bacteria"
    fungi = "fungi"
    custom = "custom"
    coconut = "coconut"


class Parameters:
    """Class containing all of the setup parameters from SNAP-MS"""

    def __init__(
        self,
        analysis_mode: str,
        file_path: Path,
        atlas_db_path: Path,
        output_path: Path,
        ppm_error: int = 10,
        adduct_list: List[str] = DEFAULT_ADDUCT_LIST,
        adduct_mode: str = "positive",
        remove_duplicates: bool = True,
        min_gnps_size: int = 3,
        max_gnps_size: int = 5000,
        min_atlas_size: int = 3,
        min_group_size: int = 3,
        max_node_count: int = 2000,
        max_edge_count: int = 10000,
        job_id: Optional[str] = None,
        compress_output: bool = False,
        atlas_filter: AtlasFilter = AtlasFilter.full,
        custom_filter: Optional[str] = None,
    ):
        # I/O options
        # pathlib.Path gives convenient methods for getting name and extension
        self.analysis_mode = analysis_mode
        self.file_path = file_path
        self.file_name = file_path.stem
        self.file_type = file_path.suffix.lstrip(".").lower()
        self.reference_db = atlas_db_path
        self.output_path = output_path
        # comparison parameters
        self.ppm_error = ppm_error
        self.adduct_list = adduct_list
        self.adduct_mode = adduct_mode
        self.remove_duplicates = remove_duplicates
        self.min_gnps_cluster_size = min_gnps_size
        self.max_gnps_cluster_size = max_gnps_size
        # used in graph_size_check for outputs
        self.min_atlas_annotation_cluster_size = min_atlas_size
        self.min_compound_group_count = min_group_size
        self.max_node_count = max_node_count
        self.max_edge_count = max_edge_count
        self.job_id = job_id
        self.init_output_directory()
        self.compress_output = compress_output
        # filter options
        self.atlas_filter = atlas_filter
        self.custom_filter = custom_filter

    def init_output_directory(self) -> Path:
        file_path = self.output_path
        return file_path.mkdir(exist_ok=True, parents=True)
