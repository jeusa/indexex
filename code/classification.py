import pandas as pd
import numpy as np
import re

import util
import lines


def get_line_start_end_bins(lines_df):
    df = lines_df.copy()

    bins_x0 = pd.DataFrame(columns=["x0", "lines", "last_x0", "count", "page"])
    bins_x1 = pd.DataFrame(columns=["x1", "lines", "last_x1", "count", "page"])

    for page, frame in df.groupby("page"):
        b = lines.group_lines(frame, "x0")
        b["page"] = page
        bins_x0 = pd.concat([bins_x0, b])

        c = lines.group_lines(frame, "x1")
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

        if drop_first & (x.iloc[0]["count"] <= 2):
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
        p_x1_max = frame.loc[frame["count"]>=4].iloc[0:1]

        if p_x1_max.empty:
            bins_x1_max = pd.concat([bins_x1_max, frame.iloc[0:1]])
        else:
            bins_x1_max = pd.concat([bins_x1_max, p_x1_max]) # all lines that end by the right text border


    bins_x0_rel = get_relevant_x0_bins(bins_x0, x0_n)

    return bins_x0_rel, bins_x1_max, x0_n


def assign_types(lines_df, bins_x0_df, bins_x1_df, x0_n):
    df = lines_df.copy()
    df["x0_type"] = -1 # valid types: {0, ..., x0_n}
    df["x1_type"] = -1 # valid types: {0,1,2}

    bins_x0 = bins_x0_df.copy()
    bins_x1 = bins_x1_df.copy()

    pages, p_x0, p_x1 = [], [], []

    # assign x0_type to lines
    for p_no, p in bins_x0.groupby("page"):
        for i in range(x0_n):
            if i < p.shape[0]:
                df.loc[p.iloc[i]["lines"], "x0_type"] = i

        border_x0, border_x1 = calc_text_borders(p, bins_x1.loc[bins_x1["page"] == p_no])
        pages.append(p_no)
        p_x0.append(border_x0)
        p_x1.append(border_x1)

    borders = pd.DataFrame({
        "page": pages,
        "x0": p_x0,
        "x1": p_x1
        })

    # assign x1_type to lines
    for p_no, p in df.groupby("page"):
        max_x1 = bins_x1.loc[bins_x1["page"]==p_no]["lines"].values[0]
        if type(max_x1) is not list:
            max_x1 = [max_x1]

        for index, row in p.iterrows():
            x1_type = -1

            if index in max_x1:
                x1_type = 2 # line ends by the right text border
            else:
                l_x1 = row["x1"]

                if l_x1 < borders.loc[borders["page"]==p_no]["x0"].values[0] + 0.5*(borders.loc[borders["page"]==p_no]["x1"].values[0] - borders.loc[borders["page"]==p_no]["x0"].values[0]):
                    x1_type = 0 # line ends before the first half of the text width
                else:
                    x1_type = 1 # line ends after the first half of the text width but before the border

            df.loc[index, "x1_type"] = x1_type

    return df


def correct_x0_types(lines_df, bins_x0, bins_x1, x0_n):
    df = lines_df.copy()

    text_widths = [] # difference between mean of first and last bin for x0 for every page
    for index, row in bins_x1.iterrows():
        x1_p = row.to_frame().T
        borders = calc_text_borders(bins_x0.loc[bins_x0["page"]==row["page"]], x1_p)
        text_widths.append(borders[1]-borders[0])

    width_mean = sum(text_widths)/len(text_widths)

    tw = text_widths.copy()
    tw.sort()
    width_median = tw[int(len(tw)/2)]

    f = filter(lambda w: (not util.similar_to(w, width_median, 5)), text_widths) # filter widths that differ from the rest
    f = list(f)

    p = []
    for w in range(len(f)):
        p.append((f[w], text_widths.index(f[w]) + util.page_start)) # add page to strange width

    p_l = [a for w, a in p if w<width_median]
    p_g = [a for w, a in p if w>width_median]

    print(p, width_median)

    df.loc[df["page"].isin(p_l) & (df["x0_type"]>=0), "x0_type"] +=1 # correct wrong x0_type for p_l

    # correct wrong x0_type (and x1_type) for p_g
    bins = get_line_start_end_bins(df.loc[df["page"].isin(p_g)])
    bins_x0_cor = get_relevant_x0_bins(bins[0], x0_n, drop_first=True) # drop bin on the very left
    df_cor = assign_types(df.loc[df["page"].isin(p_g)], bins_x0_cor, bins_x1.loc[bins_x1["page"].isin(p_g)], x0_n)
    df.loc[df["page"].isin(p_g), ["x0_type", "x1_type"]] = df_cor[["x0_type", "x1_type"]]

    return df


def assign_labels(lines_df, x0_n):
    df = lines_df.copy()

    # assign labels to lines based on x0_type and x1_type
    df["label"] = "other"
    for index, row in df.iterrows():
        x0_t = row["x0_type"]
        x1_t = row["x1_type"]

        x0_start = 1
        if x0_n == 2:
            x0_start = 0

        df.loc[(df["x0_type"]==0) & (df["x1_type"]==0), "label"] = "country"
        df.loc[(df["x0_type"]==x0_start) & (df["x1_type"]==2), "label"] = "start"
        df.loc[(df["x0_type"]==x0_start+1) & (df["x1_type"]==2), "label"] = "middle"
        df.loc[(df["x0_type"]==x0_start+1) & (df["x1_type"]<2), "label"] = "end"

    return df


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


def improve_classification(lines_df):

    df = lines_df.copy()
    df["new_label"] = df["label"]

    df = improve_start_classification(df)
    df = improve_country_classification(df)

    return df


def improve_country_classification(lines_df):

    df = lines_df.copy()
    regex_cont = "(\(cont.\)|\(coni.\)|\(continued\)|\(coniinued\))"

    for row in df.loc[lines_df["label"] == "country"].iterrows():

        text = row[1]["line_text"]

        if re.search("[0-9]{2}", text):
            df.at[row[0], "new_label"] = "other"
            continue

        if row[1]["new_label"] == "country":
            text = re.sub(regex_cont, "", text)
            text = re.sub("1and", "land", text)
            text = re.sub("[,.:;]", "", text)
            text = text.strip()

            df.at[row[0], "line_text"] = text

        if sum(map(str.isupper, text)) < sum(map(str.islower, text)):
            df.at[row[0], "new_label"] = "region"

    return df


def improve_start_classification(lines_df):

    df = lines_df.copy()
    regex_date = "[A-Z]([a-z]{2}.?|[a-z]{3}.?) [0-9]{1,2}"
    df["date"] = ""

    for row in df.loc[df["label"] == "start"].iterrows():

        text = row[1]["line_text"]
        date_match = re.search(regex_date, text[:12])

        if date_match:
            df.at[row[0], "date"] = date_match.group()
        if date_match == None:
            df.at[row[0], "new_label"] = "other"

    return df
