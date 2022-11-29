import pandas as pd
import numpy as np
import re

import util
import lines
import group


def assign_types(lines_df, bins_x0_df, bins_x1_df, x0_n):
    df = lines_df.copy()
    df["x0_type"] = -1 # valid types: {0, ..., x0_n}
    df["x1_type"] = -1 # valid types: {0,1,2}

    bins_x0 = bins_x0_df.copy()
    bins_x1 = bins_x1_df.copy()

    # assign x0_type to lines
    for p_no, p in bins_x0.groupby("page"):
        for i in range(x0_n):
            if i < p.shape[0]:
                df.loc[p.iloc[i]["lines"], "x0_type"] = i

    borders = lines.make_borders_df(bins_x0, bins_x1)

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

                if l_x1 < borders.loc[borders["page"]==p_no]["x0"].values[0] + 0.7*(borders.loc[borders["page"]==p_no]["x1"].values[0] - borders.loc[borders["page"]==p_no]["x0"].values[0]):
                    x1_type = 0 # line ends before the first 0.7 text width
                else:
                    x1_type = 1 # line ends after the first 0.7 text width but before the border

            df.loc[index, "x1_type"] = x1_type

    return df


# correct x0_type for pages where something went wrong
def correct_x0_types(lines_df, bins_x0, bins_x1, x0_n):
    df = lines_df.copy()
    start_page = lines_df["page"].min()

    text_widths = list(lines.make_borders_df(bins_x0, bins_x1)["dx"]) # difference between mean of first and last bin for x0 for every page

    tw = text_widths.copy()
    tw.sort()
    width_median = tw[int(len(tw)/2)]

    f = filter(lambda w: (not util.similar_to(w, width_median, 10)), text_widths) # filter widths that differ from the rest
    f = list(f)

    p = []
    for w in range(len(f)):
        p.append((f[w], text_widths.index(f[w]) + start_page)) # add page to strange width

    p_l = [a for w, a in p if w<width_median]
    p_g = [a for w, a in p if w>width_median]

    df.loc[df["page"].isin(p_l) & (df["x0_type"]>=0), "x0_type"] +=1 # correct wrong x0_type for p_l

    # correct wrong x0_type (and x1_type) for p_g
    bins = group.get_line_start_end_bins(df.loc[df["page"].isin(p_g)])
    bins_x0_cor = group.get_relevant_x0_bins(bins[0], x0_n, drop_first=True) # drop bin on the very left
    df_cor = assign_types(df.loc[df["page"].isin(p_g)], bins_x0_cor, bins_x1.loc[bins_x1["page"].isin(p_g)], x0_n)
    df.loc[df["page"].isin(p_g), ["x0_type", "x1_type"]] = df_cor[["x0_type", "x1_type"]]

    return df


# assign labels to lines based on x0_type and x1_type
def assign_labels(lines_df, x0_n):
    df = lines_df.copy()

    df["label"] = "other"
    for index, row in df.iterrows():
        x0_t = row["x0_type"]
        x1_t = row["x1_type"]

        x0_start = 1
        if x0_n == 2:
            x0_start = 0

        if x0_n==2:
            df.loc[(df["x0_type"]==x0_start) & (df["x1_type"]>0), "label"] = "start"
        elif x0_n==3:
            df.loc[(df["x0_type"]==x0_start), "label"] = "start"

        df.loc[(df["x0_type"]==0) & (df["x1_type"]==0), "label"] = "country"
        df.loc[(df["x0_type"]==x0_start+1) & (df["x1_type"]==2), "label"] = "middle"
        df.loc[(df["x0_type"]==x0_start+1) & (df["x1_type"]<2), "label"] = "end"

    return df


def improve_classification(lines_df):

    df = lines_df.copy()
    df["new_label"] = df["label"]

    df = improve_start_classification(df)
    df = improve_country_classification(df)

    return df


def improve_country_classification(lines_df):

    df = lines_df.copy()
    regex_cont = "-{0,2}—?\s?\(?(con\w*)\.?\)?"

    for row in df.loc[lines_df["label"] == "country"].iterrows():

        text = row[1]["line_text"]

        if re.search("[0-9]{2}", text):
            df.at[row[0], "new_label"] = "start"
            continue

        if row[1]["new_label"] == "country":
            text = re.sub(regex_cont, "", text, flags=re.IGNORECASE)
            text = re.sub("1and", "land", text)
            text = re.sub("5", "S", text)
            text = re.sub("[,.:;-]", "", text)
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
