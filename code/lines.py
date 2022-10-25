import pandas as pd
import re

import util


def make_lines_df(dicts):

    page_lines = []
    lines_bbox = []
    page_no = []
    page_counter = 1

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
    df["line_no"] = df["dy"].gt(4).cumsum()

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
