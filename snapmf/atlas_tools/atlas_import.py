#!/usr/bin/env python3

"""Tools to import and reformat NP Atlas data"""

import unicodedata
from typing import List, Optional

import numpy as np
import pandas as pd

from snapmf.config import AtlasFilter, Parameters
from snapmf.exceptions import AdductNotFound


def import_atlas(parameters: Parameters):
    """Import Atlas data from Advanced search output, and reformat as a pandas df with cleaned headers and additional
    adducts (if selected)
    """
    # input_df = pd.read_csv(
    #     parameters.reference_db, sep="\t", header=0, encoding="utf-8"
    # )
    if parameters.atlas_filter != AtlasFilter.coconut:
        input_df = normalize_dataframe(pd.read_json(parameters.reference_db))
        input_df = apply_db_filter(
            input_df, parameters.atlas_filter, parameters.custom_filter
    )
        input_df = clean_names(input_df)
        print("Imported NP Atlas DB")
    else:
        input_df = pd.read_json(parameters.reference_db)
        print("Imported COCONUT DB")
    input_df = extend_adducts(input_df, parameters.adduct_list)
    print("Finished reference database import")
    return input_df


def apply_db_filter(
    df: pd.DataFrame, filter_type: AtlasFilter, custom_value: Optional[str] = None
) -> pd.DataFrame:
    """Apply filtering to NP Atlas standard dataframe POST normalization"""
    if filter_type == AtlasFilter.bacteria:
        print("Filtering for bacteria")
        return df[df.origin_organism_type == "Bacterium"].copy()
    elif filter_type == AtlasFilter.fungi:
        print("Filtering for fungi")
        return df[df.origin_organism_type == "Fungus"].copy()
    elif filter_type == AtlasFilter.custom:
        assert isinstance(custom_value, str), "Custom value not valid"
        print(f"Filtering for custom {custom_value}")
        names = map(lambda x: x.strip(), custom_value.split("|"))
        masks = []
        for n in names:
            masks.append(df["origin_organism_taxon_name"] == n)
            masks.append(
                df["origin_organism_taxon_ancestors"].apply(
                    lambda x: any([a["name"] == n for a in x])
                )
            )
        mask = np.array(masks).any(axis=0)
        df1 = df[mask].copy()
        print(f"Custom filtered DF has {len(df1)} compounds")
        return df1
    return df


def normalize_dataframe(
    df: pd.DataFrame, cols: List[str] = ["origin_reference", "origin_organism"]
) -> pd.DataFrame:
    """Normalize columns for nested JSON/dict data inside a dataframe
    NOTE: These data are currently not used by snapmf.
    """
    df = df.copy()
    for c in cols:
        a = pd.json_normalize(df[c], sep="_")
        names = [f"{c}_{x}" for x in a.columns]
        df[names] = a
        del df[c]
    return df


def clean_names(
    df: pd.DataFrame, name_col: str = "name", input_name_col: str = "original_name"
) -> pd.DataFrame:
    """Perform unicode normalization on compound names as well as move names from `original_name` to `name` col"""
    df[name_col] = [unicodedata.normalize("NFKC", n) for n in df[input_name_col]]
    # If resulting name is None replace with "Unknown" because networkX does not accept None as node attribute value
    df["name"] = df["name"].fillna("Unknown")
    del df[input_name_col]
    return df


def clean_headers(df: pd.DataFrame) -> pd.DataFrame:
    """Tidy up headers in dataframe containing whitespace"""
    df.columns = (
        c.strip().lower().replace(" ", "_").replace("(", "").replace(")", "")
        for c in df.columns
    )
    return df


def adduct_compute(exact_mass: pd.Series, name: str) -> pd.Series:
    """Compute the adduct mass given and pandas series.
    To add new adducts, simply add a new `if name == 'new_adduct_name'` statement.
    Returns a new series.

    This method should also work for pure floats/ints or numpy arrays, but is not tested for them.

    Raises AdductNotFound if adduct name not recognized.
    """
    if name == "m_plus_nh4":
        return exact_mass + 18.033823
    if name == "m_plus_h_minus_h2o":
        return exact_mass - 17.00328
    if name == "m_plus_k":
        return exact_mass + 38.963158
    if name == "2m_plus_h":
        return (2 * exact_mass) + 1.007276
    if name == "2m_plus_na":
        return (2 * exact_mass) + 22.989218
    if name == "m_minus_h":
        return exact_mass - 1.007276
    if name == "m_plus_cl":
        return exact_mass + 34.969402
    if name == "m_plus_coo":
        return exact_mass + 44.998201
    raise AdductNotFound("Adduct not recognized")


def extend_adducts(atlas_df: pd.DataFrame, adduct_list: List[str]) -> pd.DataFrame:
    """Tool to include additional adducts in Atlas dataframe, beyond m_plus_h and m_plus_na provided in Atlas download"""
    for adduct_name in adduct_list:
        # skip pre-computed values
        if adduct_name in ["m_plus_h", "m_plus_na"]:
            continue
        atlas_df[adduct_name] = adduct_compute(atlas_df["exact_mass"], adduct_name)
    return atlas_df
