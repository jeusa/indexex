import pandas as pd
import numpy as np
import re

import util
import lines
import group


def extract_records(lines_df):
    df = group_records(lines_df)

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
    

def group_records(lines_df):
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

    for index, row in df.iterrows():

        if row[label_col] == "country":
            cur_country = row["line_text"]
            cur_region = ""
            cur_no = -1

        if row[label_col] == "region":
            cur_region = row["line_text"]
            cur_no = -1

        if not cur_country == "":
            df.loc[index, "country"] = cur_country
            df.loc[index, "region"] = cur_region

            if row[label_col] == "start":
                record_no = record_no + 1
                cur_no = record_no

            if (cur_no > -1):
                df.loc[index, "record_no"] = cur_no

    return df
