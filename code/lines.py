import pandas as pd
import re

import util
import group


def make_lines_df_from_ocr(pdf_df):
    df = pdf_df.copy()

    df = df.dropna(subset=["text"])
    df = df.rename(columns={"left": "x0", "top": "y0", "page_num": "page"})
    df["x1"] = df["x0"] + df["width"]
    df["y1"] = df["y0"] + df["height"]
    reg_art = "^[\W_]*([oeau]{2,})?\s?[\W_]*(?<!\()"    # regex for artifacts

    page, lines_text, x0, x1, y0, y1 = [], [], [], [], [], []
    art = []

    for p_no, page_frame in df.groupby("page"):
        for b, block in page_frame.groupby("block_num"):
            for p, par in block.groupby("par_num"):
                for no, line in par.groupby("line_num"):

                    art_text = ""
                    artifact_start = True

                    line_text = ""
                    l_x0 = 0
                    l_y0 = 0

                    for i, word in line.iterrows():

                        if artifact_start: # to filter out artifacts in the beginning of a line
                            a = re.search(reg_art, word["text"])
                            if a != None:
                                art_text += a.group()
                                rest = re.sub(reg_art, "", word["text"])

                                if len(rest.strip()) == 0:
                                    if i+1 in line.index:
                                        l_x0 = line.loc[i+1]["x0"]
                                        l_y0 = line.loc[i+1]["y0"]
                                else:
                                    line_text += rest + " "
                                    word_len = len(word["text"])
                                    art_len = len(art_text)/2
                                    l_x0 = int(word["x0"] + (word["x1"] - word["x0"]) * art_len/word_len)
                                    artifact_start = False

                                continue

                            artifact_start = False
                            if l_x0 == 0:
                                l_x0 = word["x0"]

                        line_text += word["text"] + " "

                    line_text = line_text.strip()

                    l_x1 = line["x1"].max()
                    l_y0 = line["y0"].min()
                    l_y1 = line["y1"].max()

                    if len(line_text) > 2:
                        art.append(art_text)
                        lines_text.append(line_text)
                        page.append(p_no)
                        x0.append(l_x0)
                        x1.append(l_x1)
                        y0.append(l_y0)
                        y1.append(l_y1)

    lines_df = pd.DataFrame({
        "line_text": lines_text,
        "artifact_text": art,
        "x0": x0,
        "y0": y0,
        "x1": x1,
        "y1": y1,
        "page": page
    })
    lines_df["dx"] = lines_df["x1"] - lines_df["x0"]

    lines_df = remove_useless_lines(lines_df)

    return lines_df


def make_words_df(words_list, start_page=1):

    page, words, x0, y0, x1, y1 = [], [], [], [], [], []

    for i, p in enumerate(words_list):
        for w in p:
            page.append(i+start_page)
            words.append(w[4])
            x0.append(w[0])
            y0.append(w[1])
            x1.append(w[2])
            y1.append(w[3])

    words_df = pd.DataFrame({
        "text": words,
        "x0": x0,
        "y0": y0,
        "x1": x1,
        "y1": y1,
        "page": page
    })

    return words_df


def make_lines_df_from_dicts(dicts, page_start=1):

    page_lines = []
    lines_bbox = []
    page_no = []
    page_counter = page_start

    for p in dicts:
        for b in p["blocks"]:
            for l in b["lines"]:
                line = []
                bbox = l["bbox"]
                for s in l["spans"]:
                    line.append(s["text"])

                page_lines.append(" ".join(line))
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

        lines.append(" ".join(line))
        line_spans.append(line)

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


# Returns the mean x0 value for the page middle, used for double paged documents. Also filters out
# wrong borders, so they won´t be used in the calculation.
def get_mean_dx(words_df, borders, mode):

    d = 0
    if mode=="fitz":
        d = 15
    elif mode=="tess":
        d = 75

    bins_dx = group.group_lines(borders, "dx", d=d)
    bins_dx = bins_dx.sort_values("last_dx_mean", ascending=False)
    pages = bins_dx["count"].sum()
    bins_dx = bins_dx.loc[bins_dx["count"] > 0.25*pages]
    big_dx = bins_dx.iloc[0]["dx"]

    return sum(big_dx) / len(big_dx)
