"""This script contains methods to label the individual lines based on where they start and end."""

import pandas as pd
import numpy as np
import re

import util
import lines
import group


def assign_types(lines_df, bins_x0_df, bins_x1_df, x0_n, country_centered=False):
    """Assigns types for x0 and types for x1 coordinates of individual lines. 
    
    Based on the x0 and x1 bins they were sorted into. Types are later used for labeling.

    Parameters
    ----------
    lines_df
        lines data frame
    bins_x0_df
        bins x0 data frame
    bins_x1_df
        bins x1 data frame
    x0_n
        quantity of x0 types (2 or 3)

    Returns
    -------
        lines data frame with x0 types and x1 types
    """    
    df = lines_df.copy()
    df["x0_type"] = -1 # valid types: {0, ..., x0_n, 4}
    df["x1_type"] = -1 # valid types: {0,1,2}

    bins_x0 = bins_x0_df.copy()
    bins_x1 = bins_x1_df.copy()

    if country_centered:
        x0_n = 2

    # assign x0_type to lines
    for p_no, p in bins_x0.groupby("page"):
        for i in range(x0_n):
            if i < p.shape[0]:
                df.loc[p.iloc[i]["lines"], "x0_type"] = i

    borders = lines.make_borders_df(bins_x0, bins_x1)
    
    # assign x0_type 4: lines that do not have a type yet and start in the first half of the text page
    for i, b in borders.iterrows():
        text_middle = b["x0"] + b["dx"]/2
        df.loc[(df["page"]==b["page"]) & (df["x0"]<text_middle) & (df["x0_type"]==-1), "x0_type"] = 4

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
                
                borders_p =borders.loc[borders["page"]==p_no]
                if l_x1 < borders_p["x0"].values[0] + 0.7*(borders_p["x1"].values[0] - borders_p["x0"].values[0]):
                    x1_type = 0 # line ends before the first 0.7 text width
                else:
                    x1_type = 1 # line ends after the first 0.7 text width but before the border

            df.loc[index, "x1_type"] = x1_type

    return df


def correct_x0_types(lines_df, bins_x0, bins_x1, x0_n, mode):
    """Corrects x0 types for the pages where something went wrong.

    The text widths of the pages are compared to determine the pages where something went wrong. This can happen if there is no country name on a page for example.

    Parameters
    ----------
    lines_df
        lines data frame with x0 types and x1 types
    bins_x0
        x0 bins data frame
    bins_x1
        _description_
    x0_n
        x1 bins data frame
    mode
        mode of operation, "fitz" or "tess"

    Returns
    -------
        lines data frame with corrected x0 types, pages where the text width is smaller than the rest,
        pages where the text width is larger than the rest

    Raises
    ------
    ValueError
        if mode is neither "fitz" nor "tess"
    """    

    d = 0
    if mode=="fitz":
        d = 4
    elif mode=="tess":
        d = 20
    else:
        raise ValueError(f"groups_lines() got an unknown value for parameter mode: {mode}")

    df = lines_df.copy()
    start_page = lines_df["page"].min()

    text_widths = list(lines.make_borders_df(bins_x0, bins_x1)["dx"]) # difference between mean of first and last bin for x0 for every page

    tw = text_widths.copy()
    tw.sort()
    width_median = tw[int(len(tw)/2)]

    f = filter(lambda w: (not util.similar_to(w, width_median, d)), text_widths) # filter widths that differ from the rest
    f = list(f)

    p = []
    for w in range(len(f)):
        p.append((f[w], text_widths.index(f[w]) + start_page)) # add page to pages with strange width

    p_l = [a for w, a in p if w<width_median] # pages where the text width is significantly smaller than the median
    p_g = [a for w, a in p if w>width_median] # pages where the text width is significantly larger than the median

    df.loc[df["page"].isin(p_l) & (df["x0_type"]>=0) & (df["x0_type"] < 4), "x0_type"] +=1 # correct wrong x0_type for p_l

    # correct wrong x0_type (and x1_type) for p_g
    bins = group.get_line_start_end_bins(df.loc[df["page"].isin(p_g)], mode)
    bins_x0_cor = group.get_relevant_x0_bins(bins[0], x0_n, drop_first=True) # drop bin on the very left
    df_cor = assign_types(df.loc[df["page"].isin(p_g)], bins_x0_cor, bins_x1.loc[bins_x1["page"].isin(p_g)], x0_n)
    df.loc[df["page"].isin(p_g), ["x0_type", "x1_type"]] = df_cor[["x0_type", "x1_type"]]

    return df, p_l, p_g


def approve_correction(orig_df, cor_df, p_l):
    """Approves the corrected x0 types or reverses them if after the correction the results worsen.

    Only looks at pages where the text width was smaller than the one of the other pages.

    Parameters
    ----------
    orig_df
        lines df with original x0 types
    cor_df
        lines df with corrected x0 types
    p_l
        pages, where the text with was smaller than the rest

    Returns
    -------
        lines df with x0 types
    """    
    df = cor_df.copy()

    start_counts = []
    for p, frame in orig_df.loc[orig_df["page"].isin(p_l)].groupby("page"):
        c = frame.loc[frame["label"]=="start"].shape[0]
        start_counts.append(c)

    start_counts_c = []
    for p, frame in cor_df.loc[cor_df["page"].isin(p_l)].groupby("page"):
        c = frame.loc[frame["label"]=="start"].shape[0]
        start_counts_c.append(c)

    for i in range(len(start_counts)):
        if (start_counts_c[i] <= 2) & (start_counts_c[i] < start_counts[i]): # after correction significantly less start lines -> reverse correction
            cor_df.loc[cor_df["page"]==p_l[i]] = orig_df.loc[orig_df["page"]==p_l[i]]

    return cor_df


def assign_labels(lines_df, x0_n, country_centered=False, start_indented=False):
    """Based on x0 and x1 types of the lines, labels are assigned to each line.

    Labels are: country, start, middle, end.

    Parameters
    ----------
    lines_df
        lines data frame with x0 types and x1 types
    x0_n
        quantity of x0 types (2 or 3)
    country_centered
        set True, if the country headlines are centered, by default False
    start_indented
        set True, if the first line of every index in this document is indented, by default False

    Returns
    -------
        lines data frame with labels
    """    
    df = lines_df.copy()

    df["label"] = "other"
    
    if country_centered | start_indented:
        x0_n = 2
    
    x0_start = 1
    if x0_n == 2:
        x0_start = 0
    
    for index, row in df.iterrows():
        x0_t = row["x0_type"]
        x1_t = row["x1_type"]
        
        if country_centered:
            df.loc[(df["x0_type"]==4) & (df["x1_type"]<2), "label"] = "country"
        else:
            if x0_n==2:
                df.loc[(df["x0_type"]==0) & (df["x1_type"]==0), "label"] = "country"  
            elif x0_n==3:
                df.loc[(df["x0_type"]==0) & (df["x1_type"]<2), "label"] = "country"                
        
        if start_indented:
            df.loc[(df["x0_type"]==1), "label"] = "start"
            df.loc[(df["x0_type"]==0) & (df["x1_type"]==2), "label"] = "middle"
            df.loc[(df["x0_type"]==0) & (df["x1_type"]<2), "label"] = "end"
        else:
            if x0_n==2:
                df.loc[(df["x0_type"]==x0_start) & (df["x1_type"]>0), "label"] = "start"
            elif x0_n==3:
                df.loc[(df["x0_type"]==x0_start), "label"] = "start"

            df.loc[(df["x0_type"]==x0_start+1) & (df["x1_type"]==2), "label"] = "middle"
            df.loc[(df["x0_type"]==x0_start+1) & (df["x1_type"]<2), "label"] = "end"

    return df


def improve_country_classification(lines_df):
    """Changes label country to region where applicable based on quantity of lower case letters.

    Does not work well for some documents where the ocr is created with tesseract, since tesseract does not
    always recognize upper and lower cases very well.
    Also cleans up the country/region text a bit.

    Parameters
    ----------
    lines_df
        lines data frame with labels

    Returns
    -------
        lines data frame with added new_label column
    """    

    df = lines_df.copy()
    df["new_label"] = df["label"]

    regex_cont = "(?!\s?congo)-{0,2}—?\s?\(?(con\w*)\.?\)?" # regex to filter out "continued" and its variants

    for row in df.loc[lines_df["label"] == "country"].iterrows():

        text = row[1]["line_text"]

        if re.search("[0-9]{2}", text):
            df.at[row[0], "new_label"] = "start"
            continue
        
        if not re.search("[a-zA-Z]{2}", text):
            df.at[row[0], "new_label"] = "other"
            continue

        if row[1]["new_label"] == "country":
            text = re.sub(regex_cont, "", text, flags=re.IGNORECASE)
            text = re.sub("1and", "land", text)
            text = re.sub("5", "S", text)
            text = re.sub("[,.:;`'\"]", " ", text)
            text = re.sub("  ", " ", text)
            text = text.strip()

            df.at[row[0], "line_text"] = text

        if sum(map(str.isupper, text)) < sum(map(str.islower, text)):
            df.at[row[0], "new_label"] = "region"

    return df
