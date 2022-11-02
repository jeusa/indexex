import pandas as pd
import numpy as np
import re

from sklearn.cluster import KMeans

import util
import lines


def cluster(lines_df, column, n_clusters):

    X = lines_df[column].to_numpy()
    X = [[e] for e in X]

    kmeans = KMeans(n_clusters=n_clusters).fit(X)

    return kmeans


def generate_cluster_labels(lines_df, dicts, n_clusters_x0=2, remove_big_x0=True):

    df = lines_df.copy()
    page_size = (dicts[0]["width"], dicts[1]["height"])

    # Remove very big x0s so they dont affect clustering
    if remove_big_x0:
        df = df.loc[df["x0"] < page_size[0]*0.4]

    # Kmeans clustering with x0 (start of line) and x1 (end of line)
    kmeans0 = cluster(df, "x0", n_clusters=n_clusters_x0)
    kmeans1 = cluster(df, "x1", n_clusters=3)

    df["label_kmeans_0"] = kmeans0.labels_
    df["label_kmeans_1"] = kmeans1.labels_

    clusters_x0 = util.flatten(kmeans0.cluster_centers_)
    clusters_x1 = util.flatten(kmeans1.cluster_centers_)

    cl_x0 = pd.DataFrame({"clusters_x0": clusters_x0}).reset_index().sort_values(by="clusters_x0").reset_index(drop=True).rename(columns={"index": "label"})
    cl_x1 = pd.DataFrame({"clusters_x1": clusters_x1}).reset_index().sort_values(by="clusters_x1").reset_index(drop=True).rename(columns={"index": "label"})

    # Define line class depending on the combination of the clustering labels
    labels_meaning = []
    labels_meaning.append((int(cl_x0.iloc[0]["label"]), int(cl_x1.iloc[0]["label"]), "country"))
    labels_meaning.append((int(cl_x0.iloc[0]["label"]), int(cl_x1.iloc[2]["label"]), "start"))
    labels_meaning.append((int(cl_x0.iloc[1]["label"]), int(cl_x1.iloc[2]["label"]), "middle"))
    labels_meaning.append((int(cl_x0.iloc[1]["label"]), int(cl_x1.iloc[1]["label"]), "end"))

    df["label"] = "other"

    for l in labels_meaning:
        df.loc[(df["label_kmeans_0"]==l[0]) & (df["label_kmeans_1"]==l[1]), "label"] = l[2]

    return df

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

    bins_x1 =  bins_x1.sort_values(by=["page", "count"], ascending=[True, False])

    x0_types = bins_x0.loc[bins_x0["count"]>=4].groupby("page").count().groupby("count").count()["x0"] # count bins with at least 4 elements per page to determine number of types for x_0 (2 or 3)
    pages_count = x0_types.sum()

    x0_n = 2
    if x0_types.loc[3] > pages_count * 0.3:
        x0_n = 3

    return bins_x0, bins_x1, x0_n


def group_line_starts_ends(lines_df):
    df = lines_df.copy()

    bins_x0, bins_x1, x0_n = get_line_start_end_bins(df)

    bins_x1_max = pd.DataFrame()
    for p_no, frame in bins_x1.groupby("page"):
        bins_x1_max = pd.concat([bins_x1_max, frame.loc[frame["count"]>=4].iloc[0:1]]) # all lines that end by the right text border

    # keep only the x0_n relevant bins per page
    bins_x0_rel = pd.DataFrame(columns=bins_x0.columns)
    for p_no, p in bins_x0.groupby("page"):
        x = p.sort_values(by="last_x0")
        bins_x0_rel = pd.concat([bins_x0_rel, x.iloc[0:1]]) # add lines that start by the left text border

        z = p.drop(x.iloc[0].name)
        z = z.sort_values(by="count", ascending=False).iloc[0:x0_n-1].sort_values(by="last_x0")
        bins_x0_rel = pd.concat([bins_x0_rel, z]) # add the other x0_n-1 bins

    return bins_x0_rel, bins_x1_max, x0_n


def assign_types(lines_df, bins_x0_df, bins_x1_df, x0_n):
    df = lines_df.copy()
    df["x0_type"] = -1 # valid types: {0, ..., x0_n}
    df["x1_type"] = -1 # valid types: {0,1,2}

    bins_x0 = bins_x0_df.copy()
    bins_x1 = bins_x1_df.copy()

    borders = []

    # assign x0_type to lines
    for p_no, p in bins_x0.groupby("page"):
        for i in range(x0_n):
            df.loc[p.iloc[i]["lines"], "x0_type"] = i

        borders.append(calc_text_borders(p, bins_x1.loc[bins_x1["page"] == p_no]))

    # assign x1_type to lines
    for p_no, p in df.groupby("page"):
        max_x1 = bins_x1.loc[bins_x1["page"]==p_no]["lines"].values[0]

        for index, row in p.iterrows():
            x1_type = -1

            if index in max_x1:
                x1_type = 2 # line ends by the right text border
            else:
                l_x1 = row["x1"]
                if l_x1 < borders[p_no-util.page_start][0] + 0.5*(borders[p_no-util.page_start][1] - borders[p_no-util.page_start][0]):
                    x1_type = 0 # line ends before the first half of the text width
                else:
                    x1_type = 1 # line ends after the first half of the text width but before the border

            df.loc[index, "x1_type"] = x1_type

    return df


def correct_x0_types(lines_df, bins_x0, bins_x1):
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
    p_g = [a for w, a in p if w>width_median] # TODO: correction

    df.loc[df["page"].isin(p_l) & (df["x0_type"]>=0), "x0_type"] +=1 # correct wrong x0_type

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
