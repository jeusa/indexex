import pandas as pd
import re

import util
import lines
import group
import label
import records
import date


def extract_indexes(pdf_df, file_name, verbose=True, double_paged=None, save_to=None):
    df = lines.make_lines_df_from_ocr(pdf_df)

    bins_x0, bins_x1, x0_n = group.group_line_starts_ends(df)
    borders = lines.make_borders_df(bins_x0, bins_x1)

    if double_paged:
        return extract_double_paged_indexes(pdf_df, borders, verbose)

    elif double_paged == None:
        if is_double_paged(pdf_df, borders):
            return extract_double_paged_indexes(pdf_df, borders, verbose)

    df = label.assign_types(df, bins_x0, bins_x1, x0_n)
    df = label.assign_labels(df, x0_n)

    ind_df, p_l, p_g = label.correct_x0_types(df, bins_x0, bins_x1, x0_n)
    ind_df = label.assign_labels(ind_df, x0_n)
    ind_df = label.approve_correction(df, ind_df, p_l)

    ind_df["new_label"] = ind_df["label"]
    ind_df = label.improve_country_classification(ind_df)

    ind_df = records.extract_records(ind_df)
    ind_df = date.extract_dates(ind_df, file_name)

    if not save_to == None:
        ind_df.to_csv(save_to, index=False)

        if verbose:
            print(f"Saved extracted indexes to {save_to}.")

    return ind_df



def extract_double_paged_indexes(pdf_df, borders, verbose=True):

    if verbose:
        print("Extracting indexes from document with double-pages.")

    df = pdf_df.copy()
    pdf_l = pd.DataFrame()
    pdf_r = pd.DataFrame()

    for p, b in borders.groupby("page"):
        middle = b.iloc[0]["x0"] + b.iloc[0]["dx"]/2
        pdf_p = df.loc[df["page_num"] == p]

        l = pdf_p.loc[pdf_p["left"] <= middle]
        r = pdf_p.loc[pdf_p["left"] > middle]

        pdf_l = pd.concat([pdf_l, l])
        pdf_r = pd.concat([pdf_r, r])


    ind_l = extract_indexes(pdf_l, double_paged=False)
    ind_r = extract_indexes(pdf_r, double_paged=False)

    idx_s = ind_l.shape[0]
    idx_e = idx_s + ind_r.shape[0]
    ind_r = ind_r.set_index(pd.Index(list(range(idx_s, idx_e))))

    ind_df = pd.concat([ind_l, ind_r])
    ind_df = ind_df.rename_axis("idx").sort_values(by=["page", "idx"])
    ind_df = ind_df.reset_index(drop=True)

    return ind_df


def is_double_paged(pdf_df, borders):
    m = 100
    double_p = []

    for p, b in borders.groupby("page"):
        middle = b.iloc[0]["x0"] + b.iloc[0]["dx"]/2

        middle_words = pdf_df.loc[(pdf_df["page_num"]==p) & (pdf_df["left"] > middle-m) & (pdf_df["left"] < middle+m)]
        if middle_words.shape[0] <= 1:
            double_p.append(True)
        else:
            double_p.append(False)

    if double_p.count(True) > 0.8 * len(double_p):
        return True

    return False
