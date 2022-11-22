import pandas as pd
import re

import util


def make_lines_df_from_ocr(pdf_df):
    df = pdf_df.copy()

    df = df.dropna(subset=["text"])
    df = df.rename(columns={"left": "x0", "top": "y0"})
    df["x1"] = df["x0"] + df["width"]
    df["y1"] = df["y0"] + df["height"]

    page, lines_text, x0, x1, y0, y1 = [], [], [], [], [], []

    for p_no, page_frame in df.groupby("page_num"):
        for b, block in page_frame.groupby("block_num"):
            for p, par in block.groupby("par_num"):
                for no, line in par.groupby("line_num"):

                    line_text = ""
                    for i, word in line.iterrows():
                        line_text += word["text"] + " "

                    if not line_text.strip() == "":
                        lines_text.append(line_text)
                        page.append(p_no)
                        x0.append(line["x0"].min())
                        x1.append(line["x1"].max())
                        y0.append(line["y0"].min())
                        y1.append(line["y1"].max())

    lines_df = pd.DataFrame({
        "line_text": lines_text,
        "x0": x0,
        "y0": y0,
        "x1": x1,
        "y1": y1,
        "page": page
    })
    lines_df["dx"] = lines_df["x1"] - lines_df["x0"]

    return lines_df


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
