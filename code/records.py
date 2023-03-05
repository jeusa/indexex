"""This script contains methods to generate the indexes data frame from the lines data frame."""

import pandas as pd
import numpy as np
import re

import util
import lines
import group


def extract_records(lines_df, start_indented=False):
    """Extracts the indexes based on the the labeled lines.

    Parameters
    ----------
    lines_df
        lines data frame with labeled lines
    start_indented
        set True, if the first line of every index in this document is indented, by default False

    Returns
    -------
        indexes data frame
    """    
    df = group_records(lines_df, start_indented)
    rec = merge_groups(df)

    return rec


def merge_groups(lines_df):
    """Merges grouped lines and generates an index data frame.

    Parameters
    ----------
    lines_df
        lines data frame with assigend record numbers

    Returns
    -------
        indexes data frame
    """    
    df = lines_df.copy()

    texts = []
    countries = []
    regions = []
    pages = []

    for g, record in df.loc[df["record_no"]>-1].groupby("record_no"):

        t = ""
        for index, line in record.iterrows():
            t = t + line["line_text"] + " "

        texts.append(t)
        countries.append(record.iloc[0]["country"])
        regions.append(record.iloc[0]["region"])
        pages.append(record.iloc[0]["page"])

    rec = pd.DataFrame({
        "country": countries,
        "region": regions,
        "text": texts,
        "page": pages
    })

    return rec
    

def group_records(lines_df, start_indented=False):
    """Groups the lines to indexes with their corresponding country (and region).

    Groups indexes based on the label start assigned to the lines (from start to next start).
    Lines are assigned a record_no. Lines with the same record_no form an index.

    Parameters
    ----------
    lines_df
        lines data frame with labeled lines
    start_indented
        set True, if the first line of every index in this document is indented, by default False

    Returns
    -------
        lines data frame with index grouping
    """    
    df = lines_df.copy()

    df["country"] = ""
    df["region"] = ""
    df["record_no"] = -1

    cur_country = ""
    cur_region = ""
    cur_index = []
    record_no = -1
    cur_no = -1
    label_col = "new_label"
    start_counter = 1

    for index, row in df.iterrows():

        if row[label_col] == "country":
            cur_country = row["line_text"]
            cur_region = ""
            cur_no = -1
            start_counter = 1

        if row[label_col] == "region":
            cur_region = row["line_text"]
            cur_no = -1
            start_counter = 1

        if not cur_country == "":
            df.loc[index, "country"] = cur_country
            df.loc[index, "region"] = cur_region

            if row[label_col] == "start":
                if start_indented:         
                    if (re.search("^[([{]", row["line_text"])==None) | (start_counter>3):
                        start_counter = 1
                    if start_counter == 1:
                        record_no += 1
                    start_counter += 1
                    
                else:
                    record_no +=  1
                cur_no = record_no

            if (cur_no > -1):
                df.loc[index, "record_no"] = cur_no

    return df
