import pandas as pd
import numpy as np
import re

import util
import lines


# Sort the lines into bins containing lines with similar values for parameter by
def group_lines(df, by):
    #d = 4 old value without ocr
    d = 20
    last = "last_" + by
    bins = pd.DataFrame(columns=[by, "lines", last, "count"])

    for index, row in df.iterrows():
        x0 = row[by]
        poss_bin = bins.loc[(bins[last]-d <= x0) & (bins[last]+d >= x0)]

        if poss_bin.empty:
            new_row = pd.DataFrame({
                by: [x0],
                "lines": [index],
                last: x0,
                "count": 1
            })
            bins = pd.concat([new_row, bins.loc[:]]).reset_index(drop=True)
        else:
            b = bins.iloc[poss_bin.index[-1]]

            if not type(b[0]) is list:
                b[0] = [b[0]]
                b[1] = [b[1]]

            b[0].append(x0)
            b[1].append(index)
            b[2] = x0
            b[3] += 1

    return bins


def get_line_start_end_bins(lines_df):
    df = lines_df.copy()

    bins_x0 = pd.DataFrame(columns=["x0", "lines", "last_x0", "count", "page"])
    bins_x1 = pd.DataFrame(columns=["x1", "lines", "last_x1", "count", "page"])

    for page, frame in df.groupby("page"):
        b = group_lines(frame, "x0")
        b["page"] = page
        bins_x0 = pd.concat([bins_x0, b])

        c = group_lines(frame, "x1")
        c["page"] = page
        bins_x1 = pd.concat([bins_x1, c])

    bins_x1 =  bins_x1.sort_values(by=["page", "last_x1"], ascending=[True, False])

    x0_types = bins_x0.loc[bins_x0["count"]>=4].groupby("page").count().groupby("count").count()["x0"] # count bins with at least 4 elements per page to determine number of types for x_0 (2 or 3)
    pages_count = x0_types.sum()

    x0_n = 2
    if 3 in x0_types.index:
        if x0_types.loc[3] > pages_count * 0.3:
            x0_n = 3

    return bins_x0, bins_x1, x0_n


def get_relevant_x0_bins(bins_x0, x0_n, drop_first=False):

    bins_x0_rel = pd.DataFrame(columns=bins_x0.columns)
    for p_no, p in bins_x0.groupby("page"):
        x = p.sort_values(by="last_x0")

        if drop_first:
            x = x.drop(x.iloc[0].name)

        bins_x0_rel = pd.concat([bins_x0_rel, x.iloc[0:1]]) # add lines that start by the left text border

        z = x.drop(x.iloc[0].name)
        z = z.sort_values(by="count", ascending=False).iloc[0:x0_n-1].sort_values(by="last_x0")
        bins_x0_rel = pd.concat([bins_x0_rel, z]) # add the other x0_n-1 bins

    return bins_x0_rel


def group_line_starts_ends(lines_df):
    df = lines_df.copy()

    bins_x0, bins_x1, x0_n = get_line_start_end_bins(df)

    bins_x1_max = pd.DataFrame()
    for p_no, frame in bins_x1.groupby("page"):

        p_x1_max = frame.sort_values(by="count", ascending=False).iloc[0:1]
        bins_x1_max = pd.concat([bins_x1_max, p_x1_max]) # all lines that end by the right text border


    bins_x0_rel = get_relevant_x0_bins(bins_x0, x0_n)

    return bins_x0_rel, bins_x1_max, x0_n
