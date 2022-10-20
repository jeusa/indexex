import pandas as pd
import numpy as np

from sklearn.cluster import KMeans

import util

def cluster(lines_df, column, n_clusters):

    X = lines_df[column].to_numpy()
    X = [[e] for e in X]

    kmeans = KMeans(n_clusters=n_clusters).fit(X)

    return kmeans


def generate_cluster_labels(lines_df):

    df = lines_df.copy()

    # Kmeans clustering with x0 (start of line) and x1 (end of line)
    kmeans0 = cluster(df, "x0", n_clusters=2)
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
