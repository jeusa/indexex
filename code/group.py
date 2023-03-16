"""This script contains methods to group lines togetheter based on where they start and where they end."""

import pandas as pd
import numpy as np
import re

import util
import lines


def group_rows(df, by, mode=None, d=0):
    """Sorts the rows into bins containing rows with similar values for the specified parameter.

    The algorithm iterates through the rows of the given data frame. If a bin exists where the row
    can be sorted into, it is added to the bin. Otherwise, a new bin is created and the row is added
    to the new bin. 
    To determine wheter a row fits into a bin, the mean value of the last two rows that have been added
    to the bin is compared to the value of the current row.

    Parameters
    ----------
    df
        data frame 
    by
        column of the data frame, based on this parameter the rows are grouped
    mode, optional
        mode of operation, "fitz" or "tess", fitz sets d=4, tess sets d=20, by default None
    d, optional
        max difference between value of last row(s) and following row to be grouped together, 
        by default 0

    Returns
    -------
        bins data frame, contains the different bins, the indexes of the respective rows that
        are grouped together in this bin, their quantity
    """    

    if mode=="fitz":
        d = 4
    elif mode=="tess":
        d = 20

    last = "last_" + by
    last_m = last + "_mean"
    bins = pd.DataFrame(columns=[by, "lines", last, last_m, "count"])

    for index, row in df.iterrows():
        x0 = row[by]
        poss_bin = bins.loc[(bins[last_m]-d <= x0) & (bins[last_m]+d >= x0)]

        if poss_bin.empty:
            new_row = pd.DataFrame({
                by: [[x0]],
                "lines": [[index]],
                last: [[x0]],
                last_m: [x0],
                "count": 1
            })
            bins = pd.concat([new_row, bins.loc[:]]).reset_index(drop=True)
        else:
            b = bins.iloc[poss_bin.index[-1]].copy()

            b[by].append(x0)
            b["lines"].append(index)
            b["count"] += 1

            if len(b[last]) >= 2:
                b[last].pop(0)
            b[last].append(x0)

            last_mean = sum(b[last]) / len(b[last])
            b[last_m] = last_mean
            bins.loc[b.name] = b

    return bins


def get_line_start_end_bins(lines_df, mode):
    """Creates bins for the lines based on their x0 and x1 coordinates individually for every page.

    Parameters
    ----------
    lines_df
        lines data frame
    mode
        mode of operation, "fitz" or "tess"

    Returns
    -------
        bins created based on similarity of x0, bins created based on similarity of x1, most common quantity of x0 bins per page (2 or 3)
    """    
    df = lines_df.copy()

    bins_x0 = pd.DataFrame(columns=["x0", "lines", "last_x0", "last_x0_mean", "count", "page"])
    bins_x1 = pd.DataFrame(columns=["x1", "lines", "last_x1", "last_x1_mean", "count", "page"])

    for page, frame in df.groupby("page"):
        b = group_rows(frame, "x0", mode)
        b["page"] = page
        bins_x0 = pd.concat([bins_x0, b])

        c = group_rows(frame, "x1", mode)
        c["page"] = page
        bins_x1 = pd.concat([bins_x1, c])

    bins_x1 =  bins_x1.sort_values(by=["page", "last_x1_mean"], ascending=[True, False])

    x0_types = bins_x0.loc[bins_x0["count"]>=4].groupby("page").count().groupby("count").count()["x0"] # count bins with at least 4 elements per page to determine number of types for x_0 (2 or 3)
    pages_count = x0_types.sum()

    x0_n = 2
    if 3 in x0_types.index:
        if x0_types.loc[3] > pages_count * 0.3:
            x0_n = 3

    return bins_x0, bins_x1, x0_n


def get_relevant_x0_bins(bins_x0, x0_n, drop_first=False):
    """Returns the relevant x0 bins for every page.
    
    Relevance is based on the quantity of x0 types for the document and the quantity of lines in a bin.
    The bin containing lines that start right by the left text border of the page are always labeled as relevant.

    Parameters
    ----------
    bins_x0
        bins x0 data frame
    x0_n
        quantity of x0 types (2 or 3), max x0_n bins per page are chosen to be relevant
    drop_first, optional
        if True, the first bin on the very left is dropped, used to correct wrong bin creation, by default False

    Returns
    -------
        bins x0 data frame
    """    

    bins_x0_rel = pd.DataFrame(columns=bins_x0.columns)
    for p_no, p in bins_x0.groupby("page"):
        x = p.sort_values(by="last_x0_mean")

        if drop_first:
            x = x.drop(x.iloc[0].name)

        bins_x0_rel = pd.concat([bins_x0_rel, x.iloc[0:1]]) # add lines that start by the left text border

        z = x.drop(x.iloc[0].name)
        z = z.sort_values(by="count", ascending=False).iloc[0:x0_n-1].sort_values(by="last_x0_mean")
        bins_x0_rel = pd.concat([bins_x0_rel, z]) # add the other x0_n-1 bins

    return bins_x0_rel


def group_line_starts_ends(lines_df, mode):
    """Returns the lines sorted into bins based on x0 and x1 coordinates for every page.

    Only the relevant x0 and x1 bins are returned. For the x1 bins, only one bin per page is returned.
    It is the bin where the lines end right by the right text border.

    Parameters
    ----------
    lines_df
        lines data frame
    mode
        mode of operation, "fitz" or "tess"

    Returns
    -------
        relevant bins created based on similarity of x0, relevant bins created based on similarity of x1, most common quantity of x0 bins per page (2 or 3)
    """    
    df = lines_df.copy()

    bins_x0, bins_x1, x0_n = get_line_start_end_bins(df, mode)

    bins_x1_max = pd.DataFrame()
    for p_no, frame in bins_x1.groupby("page"):

        p_x1_max = frame.sort_values(by="count", ascending=False).iloc[0:1]
        bins_x1_max = pd.concat([bins_x1_max, p_x1_max]) # all lines that end by the right text border


    bins_x0_rel = get_relevant_x0_bins(bins_x0, x0_n)

    return bins_x0_rel, bins_x1_max, x0_n
