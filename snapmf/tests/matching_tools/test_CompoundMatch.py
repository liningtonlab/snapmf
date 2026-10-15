from snapmf.matching_tools.CompoundMatch import CompoundMatch

TEST_DAT = dict(
    npaid="1",
    coconut_id="1",
    exact_mass=123.4,
    smiles="C",
    name="Fakamycin",
    mass="123",
    compound_number=1,
    adduct="m_plus_h",
    origin_organism_type="Bacterium",
)


def test_CompoundMatch_has_attributes():
    comp = CompoundMatch(**TEST_DAT)
    assert comp.npaid == "1"
    assert comp.name == "Fakamycin"


def test_CompoundMatch_has_extra_attributes():
    comp = CompoundMatch(**TEST_DAT)
    assert comp.npaid == "1"
    assert comp.npatlas_url == "https://www.npatlas.org/explore/compounds/1"
    assert comp.friendly_name() == "Fakamycin"


def test_CompoundMatch_cleans_bad_name():
    test_data = TEST_DAT.copy()
    test_data["name"] = "Jadomycim\u00b3"
    comp = CompoundMatch(**test_data)
    assert comp.npaid == "1"
    assert comp.friendly_name() == "Unknown"
