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
