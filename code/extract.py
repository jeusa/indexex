import pandas as pd
import re

import util
import lines
import group
import label
import records

digits = "[0-9oOIlSQriz]"
re_d1 = "^(([A-Za-z]{3}[.:,]{0,3}|[A-Za-z]{4}.?) ?[1-3]?" + digits + "(?![0-9])(st|nd|rd|th)?)" # example: Nov. 4 | July 25th
re_d2 = "^([1-3IlzZ]?" + digits + "/[I1l]{0,3}[VX]?[I1l]{0,3}/" + digits + "{4})" # example: 13/III/1986 | 7/11/198S
re_d3 = "([1-3IlzZ]?" + digits + "(st|nd|rd|th)? ?[A-Za-z]{3,}[,.] ?[I1l]" + digits + "{3})"


def extract_indexes(pdf_df, verbose=True, double_paged=None, save_to=None):
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
    ind_df = extract_dates(ind_df)

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


def extract_dates(rec_df):
    df = rec_df.copy()
    df["full_date"] = ""
    df["year"] = 0

    dt = get_date_type(df)
    re_d = None

    if dt > -1:
        if dt==1:
            re_d = re_d1
        if dt==2:
            re_d = re_d2
        if dt==3:
            re_d = re_d3

        for i, row in df.iterrows():
            if dt != 3:
                d = re.search(re_d, row["text"])
            if dt == 3:
                for m in re.finditer(re_d, row["text"]):
                    d = m

            if not d == None:
                df.loc[i, "full_date"] = d.group(1)

                if dt!=1:
                    y = re.search(digits + "{4}", d.group(1))
                    df.loc[i, "year"] = y.group()

    return df


def get_date_type(rec_df):
    samp = rec_df.sample(frac=1/10)
    samp["date_type"] = -1

    for i, row in samp.iterrows():
        t = row["text"]
        dt = -1

        d1 = re.search(re_d1, t)
        d2 = re.search(re_d2, t)
        d3 = None

        for m in re.finditer(re_d3, t):
            d3 = m

        if d3 != None:
            dt = 3
        if d2 != None:
            dt = 2
        if d1 != None:
            dt = 1

        samp.loc[i, ["date_type"]] = dt

    date_type = samp.groupby("date_type").count().sort_values("country", ascending=False)

    if not date_type.empty:
        date_type = date_type.iloc[0].name
    else:
        date_type = -1

    return date_type
