from pathlib import Path

import pandas as pd
import pytest
from deepdiff import DeepDiff
from pandas.testing import assert_series_equal

from snapmf.atlas_tools import atlas_import
from snapmf.config import Parameters
from snapmf.exceptions import AdductNotFound

# Test data has an intentional non-unicode name corruption in first compound
TEST_FILE_PATH = Path(__file__).parent / "test_atlas.json"
test_atlas = pd.read_json(TEST_FILE_PATH)


def test_clean_names_default():
    df = test_atlas.copy()
    expected = [
        "Curvularide C",
        "Homopetasinic acid",
        "A-503083 F",
        "Aqabamycin E2",
        "Hymenopsin A",
        "Hibarimicin E",
        "Chaetoxanthone A",
        "Dihydroxydione 13",
        "Viticolin B",
        "Botryorhodine G",
    ]
    assert atlas_import.clean_names(df)["name"].to_list() == expected


def test_clean_names_explicit():
    df = test_atlas.copy()
    expected = [
        "Curvularide C",
        "Homopetasinic acid",
        "A-503083 F",
        "Aqabamycin E2",
        "Hymenopsin A",
        "Hibarimicin E",
        "Chaetoxanthone A",
        "Dihydroxydione 13",
        "Viticolin B",
        "Botryorhodine G",
    ]
    assert atlas_import.clean_names(df, name_col="name")["name"].to_list() == expected


def test_clean_headers():
    df = pd.DataFrame([], columns=["(Bad", "Bad Col", "Worse)"])
    expected = ["bad", "bad_col", "worse"]
    assert list(atlas_import.clean_headers(df).columns) == expected


def test_adduct_compute():
    test_masses = pd.Series([18.010564683, 21.059762, 30.0469501914])
    m_plus_nh4 = pd.Series([36.04438768, 39.093585, 48.08077319])
    m_plus_h_minus_h2o = pd.Series(
        [1.0072846829999982, 4.056481999999999, 13.0436701914]
    )
    m_plus_k = pd.Series([56.973722683, 60.02292, 69.01010819140001])
    _2m_plus_h = pd.Series([37.028405365999994, 43.126799999999996, 61.1011763828])
    _2m_plus_na = pd.Series([59.010347366, 65.108742, 83.0831183828])
    assert_series_equal(
        atlas_import.adduct_compute(test_masses, "m_plus_nh4"), m_plus_nh4
    )
    assert_series_equal(
        atlas_import.adduct_compute(test_masses, "m_plus_h_minus_h2o"),
        m_plus_h_minus_h2o,
    )
    assert_series_equal(
        atlas_import.adduct_compute(test_masses, "m_plus_k"),
        m_plus_k,
    )
    assert_series_equal(
        atlas_import.adduct_compute(test_masses, "2m_plus_h"),
        _2m_plus_h,
    )
    assert_series_equal(
        atlas_import.adduct_compute(test_masses, "2m_plus_na"),
        _2m_plus_na,
    )
    with pytest.raises(AdductNotFound):
        atlas_import.adduct_compute(test_masses, "3m_plus_fake")


def test_adduct_compute_raises_adductnotfound():
    test_masses = pd.Series([18.010564683, 21.059762, 30.0469501914])
    with pytest.raises(AdductNotFound):
        atlas_import.adduct_compute(test_masses, "3m_plus_fake")


# The next two tests are basically equivalent since a returned
# dataframe is just a pointed if no copy is made
def test_extend_adducts_all_options_inplace():
    df = test_atlas.copy()
    adduct_list = [
        "m_plus_nh4",
        "m_plus_h_minus_h2o",
        "m_plus_k",
        "2m_plus_h",
        "2m_plus_na",
    ]
    atlas_import.extend_adducts(df, adduct_list)
    out_cols = df.columns
    for adduct in adduct_list:
        assert adduct in out_cols


def test_extend_adducts_all_options_returned():
    df = test_atlas.copy()
    adduct_list = [
        "m_plus_nh4",
        "m_plus_h_minus_h2o",
        "m_plus_k",
        "2m_plus_h",
        "2m_plus_na",
    ]
    df = atlas_import.extend_adducts(df, adduct_list)
    out_cols = df.columns
    for adduct in adduct_list:
        assert adduct in out_cols


def test_extend_adducts_bad_option():
    df = test_atlas.copy()
    adduct_list = [
        "m_plus_nh4",
        "m_plus_h_minus_h2o",
        "3m_plus_h",
    ]
    with pytest.raises(AdductNotFound):
        atlas_import.extend_adducts(df, adduct_list)


def test_extend_adducts_subset():
    df = test_atlas.copy()
    adduct_list = [
        "m_plus_nh4",
        "m_plus_h_minus_h2o",
        "m_plus_k",
    ]
    not_added = [
        "2m_plus_h",
        "2m_plus_na",
    ]
    atlas_import.extend_adducts(df, adduct_list)
    out_cols = df.columns
    for adduct in adduct_list:
        assert adduct in out_cols
    for adduct in not_added:
        assert adduct not in out_cols


def test_import_atlas_columns():
    params = Parameters(
        file_path=Path("."), atlas_db_path=TEST_FILE_PATH, output_path=Path(".")
    )
    # fmt: off
    expected = ["id", "npaid", "mol_formula", "mol_weight", "exact_mass", "inchikey", "smiles",
        "cluster_id", "node_id", "synonyms", "inchi", "m_plus_h", "m_plus_na",
        "syntheses", "reassignments", "external_ids", "classyfire", "npclassifier",
        "origin_reference_doi", "origin_reference_pmid", "origin_reference_authors",
        "origin_reference_title", "origin_reference_journal",
        "origin_reference_year", "origin_reference_volume",
        "origin_reference_issue", "origin_reference_pages", "origin_organism_id",
        "origin_organism_type", "origin_organism_genus", "origin_organism_species",
        "origin_organism_taxon_id", "origin_organism_taxon_name",
        "origin_organism_taxon_rank", "origin_organism_taxon_taxon_db",
        "origin_organism_taxon_external_id", "origin_organism_taxon_ncbi_id",
        "origin_organism_taxon_ancestors", "name", "m_plus_nh4",
        "m_plus_h_minus_h2o", "m_plus_k", "2m_plus_h", "2m_plus_na",
    ]
    # fmt: on
    actual = atlas_import.import_atlas(params)
    print(actual.columns.values)
    assert not DeepDiff(expected, actual.columns.to_list(), ignore_order=True)
