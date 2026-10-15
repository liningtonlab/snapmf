import pytest

from snapmf.matching_tools import match_compounds as mc
from snapmf.matching_tools.CompoundMatch import CompoundMatch


def test_calculate_error_default():
    mass = 18.0
    ppm = 10.0
    expected = 0.0002
    assert mc.calculate_error(mass, ppm) == pytest.approx(expected)


def test_calculate_error_high_precision():
    mass = 423.123
    ppm = 10.0
    expected = 0.00423123
    assert mc.calculate_error(mass, ppm, precision=8) == pytest.approx(expected)


def test_remove_duplicates_no_overlap():
    mass_list = [
        420.1421,
        422.1585,
        438.1752,
        440.133,
        454.1481,
        474.2021,
        491.0763,
        492.213,
    ]
    assert mc.remove_mass_duplicates(mass_list, 10.0) == mass_list


def test_remove_duplicates_overlap_large_ppm_error():
    mass_list = [
        420.1421,
        422.1585,
        438.1752,
        440.133,
        454.1481,
        474.2021,
        491.0763,
        492.213,
    ]
    expected = [420.1421, 438.1752, 454.1481, 474.2021, 491.0763]
    assert mc.remove_mass_duplicates(mass_list, 5000.0) == expected


def test_compound_match():
    data = {
        "npaid": "NPA018705",
        "coconut_id": "",
        "exact_mass": 419.1369,
        "smiles": "CCC(C)[C@H]1C(=O)O[C@@H]2N1C3=C(C4=C(C=C(C=C24)C)O)C(=O)C5=C(C3=O)C(=CC=C5)O",
        "name": "Jadomycim\u00b3",
        "mass": 420.1421,
        "compound_number": 1,
        "adduct": "m_plus_h",
        "origin_organism_type": "Bacterium",
    }
    compound = CompoundMatch(**data)
    # test provided props
    assert compound.npaid == "NPA018705"
    assert compound.adduct == "m_plus_h"
    # test computed prop
    assert compound.npatlas_url == "https://www.npatlas.org/explore/compounds/NPA018705"
    assert compound.friendly_name() == "Unknown"
