import pandas as pd
import re

import util


def make_lines_df(dicts, page_no_start=1):

    page_lines = []
    lines_bbox = []
    page_no = []
    page_counter = util.page_start

    for p in dicts:
        for b in p["blocks"]:
            for l in b["lines"]:
                line = []
                bbox = l["bbox"]
                for s in l["spans"]:
                    line.append(s["text"])

                page_lines.append(line)
                lines_bbox.append(bbox)
                page_no.append(page_counter)
        page_counter += 1

    d = 2
    lines_df = pd.DataFrame({
        "line_text": page_lines,
        "x0": [round(b[0], d) for b in lines_bbox],
        "y0": [round(b[1], d) for b in lines_bbox],
        "x1": [round(b[2], d) for b in lines_bbox],
        "y1": [round(b[3], d) for b in lines_bbox],
        "page": page_no
    })

    return lines_df


def merge_close_lines(lines_df, distance=4):

    df = lines_df.copy()
    df["dy"] = df["y0"].diff(periods=1).abs()
    df["line_no"] = df["dy"].gt(3).cumsum()

    lines = []
    line_spans = []
    x0 = []
    y0 = []
    x1 = []
    y1 = []
    page_no = []

    for l in df.groupby("line_no"):
        line = []

        for r in l[1].iterrows():
            line.append(r[1]["line_text"])

        lines.append(" ".join(util.flatten(line)))
        line_spans.append(util.flatten(line))

        x0.append(l[1]["x0"].min())
        y0.append(l[1]["y0"].min())
        x1.append(l[1]["x1"].max())
        y1.append(l[1]["y1"].max())
        page_no.append(r[1]["page"])

    blines_df = pd.DataFrame({
        "line_text": lines,
        "spans": line_spans,
        "x0": x0,
        "y0": y0,
        "x1": x1,
        "y1": y1,
        "page": page_no
    })

    return blines_df


def remove_useless_lines(lines_df):

    dumb_lines = []
    for row in lines_df.iterrows():
        if not re.search("[a-zA-Z0-9]", row[1]["line_text"]):
            dumb_lines.append(row[0])

    blines_df = lines_df.drop(dumb_lines)

    return blines_df


# Sort the lines into bins containing lines with similar values for parameter by
def group_lines(df, by):
    d = 4
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


def make_borders_df(bins_x0, bins_x1):

    pages, p_x0, p_x1 = [], [], []
    for p_no, p in bins_x0.groupby("page"):
        border_x0, border_x1 = calc_text_borders(p, bins_x1.loc[bins_x1["page"] == p_no])
        pages.append(p_no)
        p_x0.append(border_x0)
        p_x1.append(border_x1)

    borders = pd.DataFrame({
            "page": pages,
            "x0": p_x0,
            "x1": p_x1
            })
    borders["dx"] = borders["x1"] - borders["x0"]

    return borders


def calc_text_borders(bins_x0, bins_x1):
    df_x0 = bins_x0.copy()
    df_x1 = bins_x1.copy()

    x0 = df_x0.iloc[0]["x0"]
    if type(x0) is not list:
        x0 = [x0]
    x0 = sum(x0)/len(x0)
    x1 = df_x1.iloc[0]["x1"]
    if type(x1) is not list:
        x1 = [x1]
    x1 = sum(x1)/len(x1)

    return (x0, x1)
