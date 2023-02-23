"""This script contains methods to extract the indexes from a single or double paged document."""

import pandas as pd
import re
import os

import util
import lines
import group
import label
import records
import date


def extract_indexes_dir(path_dir, output_dir, mode=None, recursive=False, remove_wrong=True, verbose=True):
    """Extracts the indexes of all files in a directory and writes the csv files to the specified path.

    Generates one output file containing the extracted indexes for each input file.

    Mode fitz: Uses existing ocr of the pdf files. Does not work with double paged documents. Input must be pdf.
    Mode tess: Uses the tesseract engine to generate ocr for a pdf or gets a tesseract data frame as input.

    Parameters
    ----------
    path_dir
        directory containing pdf files and/or tesseract data frames as csv
    output_dir
        directory where the indexes will be written to
    mode, optional
        mode of operation, "fitz" or "tess", if None it will be determined based on file type: pdf->fitz, csv->tess, by default None
    recursive, optional
        True if path_dir should be searched for files recursively, if type is integer: how many levels of subdirectories
        should be searched, by default False
    remove_wrong, optional
        True if indexes where no date could be extracted should be removed, by default True
    verbose, optional
        print infos, by default True

    Raises
    ------
    ValueError
        if path_dir is not a directory
    """
    if not os.path.isdir(path_dir):
        raise ValueError(f"{path_dir} is not a directory.")

    suffix = [".csv", ".pdf"]
    if mode == "fitz":
        suffix.remove(".csv")

    files = []
    for s in suffix:
        files += util.list_files(path_dir, recursive=recursive, suffix=s)

    for f in files:
        extract_indexes_file(f, output_dir=output_dir, mode=mode, remove_wrong=remove_wrong, verbose=verbose)


def extract_indexes_file(path, output_dir=None, mode=None, start_page=1, remove_wrong=True, verbose=True, double_paged=None):
    """Extracts and returns the indexes of a single file.

    Mode fitz: Uses existing ocr of the pdf files. Does not work with double paged documents. Input must be pdf.
    Mode tess: Uses the tesseract engine to generate ocr for a pdf or gets a tesseract data frame as input.

    Parameters
    ----------
    path
        path to file, pdf or tesseract data frame as csv
    output_dir, optional
        if specified: directory where the indexes csv file will be written to, by default None
    mode, optional
        mode of operation, "fitz" or "tess", if None it will be determined based on file type: pdf->fitz, csv->tess, by default None
    start_page, optional
        page from which the extraction should start, by default 1
    remove_wrong, optional
        True if indexes where no date could be extracted should be removed, by default True
    verbose, optional
        print infos, by default True
    double_paged, optional
        if True: document is treated as double paged, if False: document is treated as singe paged, 
        if None: document will be checked to see if it is single or double paged, by default None

    Returns
    -------
        indexes data frame

    Raises
    ------
    ValueError
        if path is not an existing file
    ValueError
        if the file type is not supported
    ValueError
        if fitz is used with a csv file
    ValueError
        if output_dir is not an existing directory
    ValueError
        if the mode is neither fitz nor tess
    """
    if not os.path.isfile(path):
        raise ValueError(f"{path} is not an existing file.")

    f_name, f_suffix = os.path.splitext(path)
    f_name = os.path.basename(f_name)

    if (not f_suffix == ".pdf") & (not f_suffix == ".csv"):
        raise ValueError(f"{f_suffix} is not a supported file type.")

    if mode == None:
        if f_suffix == ".pdf":
            mode = "fitz"
        elif f_suffix == ".csv":
            mode = "tess"
    elif (mode == "fitz") & (not f_suffix == ".pdf"):
        raise ValueError("Mode fitz can only be used with pdf files.")

    save_path = output_dir
    if output_dir != None:

        if not os.path.isdir(output_dir):
            raise ValueError(f"{output_dir} is not a directory.")

        save_path = os.path.join(output_dir, f_name + f"_{mode}.csv")

    if mode=="fitz":
        return extract_indexes_pdf(path, start_page=start_page, save_to=save_path, remove_wrong=remove_wrong, verbose=verbose)
    elif mode=="tess":
        return extract_indexes_tess(path, file_type=f_suffix, start_page=start_page, save_to=save_path, remove_wrong=remove_wrong, verbose=verbose, double_paged=double_paged)
    else:
        raise ValueError(f"{mode} is not a supported mode.")


def extract_indexes_pdf(pdf_path, start_page=1, remove_wrong=True, verbose=True, save_to=None):
    """Extracts and returns the indexes of a single pdf file using existing ocr.

    Parameters
    ----------
    pdf_path
        path to pdf file
    start_page, optional
        page from which the extraction should start, by default 1
    remove_wrong, optional
        True if indexes where no date could be extracted should be removed, by default True
    verbose, optional
        print infos, by default True
    save_to, optional
        if specified: path where the indexes csv file will be written to, by default None

    Returns
    -------
        indexes data frame
    """
    pdf_words, pdf_dicts = util.read_pdf(pdf_path, start_page, verbose)

    words_df = lines.make_words_df(pdf_words, start_page)

    lines_df = words_df.rename(columns={"text": "line_text"}) # make lines_df from words_df
    lines_df["x0"] = [round(x, 2) for x in lines_df["x0"]]
    lines_df["y0"] = [round(x, 2) for x in lines_df["y0"]]
    lines_df["x1"] = [round(x, 2) for x in lines_df["x1"]]
    lines_df["y1"] = [round(x, 2) for x in lines_df["y1"]]
    #lines_df = lines.make_lines_df_from_dicts(pdf_dicts, start_page) # make lines_df from pdf_dicts
    lines_df = lines.merge_close_lines(lines_df)
    lines_df = lines.remove_useless_lines(lines_df)

    ind_df = extract_indexes(words_df, lines_df, file_name=os.path.basename(pdf_path), mode="fitz", remove_wrong=remove_wrong, verbose=verbose, double_paged=None, save_to=save_to)

    return ind_df


def extract_indexes_tess(file_path, file_type="csv", start_page=1, remove_wrong=True, verbose=True, double_paged=None, save_to=None):
    """Extracts and returns the indexes of a single pdf file or a tesseract data frame saved as a csv file.

    If the file is a pdf, the tesseract engine is used to generate ocr.

    Parameters
    ----------
    file_path
        path of the file, pdf or tesseract dataframe as csv file
    file_type, optional
        pdf or csv, by default "csv"
    start_page, optional
        page from which the extraction should start, by default 1
    remove_wrong, optional
        True if indexes where no date could be extracted should be removed, by default True
    verbose, optional
        print infos, by default True
    double_paged, optional
        if True: document is treated as double paged, if False: document is treated as single paged, 
        if None: document will be checked to see if it is single or double paged, by default None
    save_to, optional
        if specified: path where the indexes csv file will be written to, by default None

    Returns
    -------
        indexes data frame

    Raises
    ------
    ValueError
        if file_type is not supported
    """
    file_type = re.sub("\.", "", file_type)
    if file_type == "csv":
        pdf_df = pd.read_csv(file_path)
    elif file_type == "pdf":
        pdf_df = util.ocr(file_path, verbose=verbose)
    else:
        raise ValueError(f"{file_type} is not a supported file type.")

    pdf_df = pdf_df.loc[pdf_df["page_num"] >= start_page]
    lines_df = lines.make_lines_df_from_ocr(pdf_df)

    ind_df = extract_indexes(pdf_df, lines_df, file_name=os.path.basename(file_path), mode="tess", remove_wrong=remove_wrong, verbose=verbose, double_paged=double_paged, save_to=save_to)

    return ind_df


def extract_indexes(words_df, lines_df, file_name, mode, verbose=True, double_paged=None, save_to=None, remove_wrong=False):
    """Extracts and returns indexes from the words data frame and the lines data frame of a document.

    Extraction works for single paged and double paged documents. In mode fitz, extraction does not work for double paged
    documents but double paged documents should be identified as such.

    Parameters
    ----------
    words_df
        words data frame, needed for double paged extraction
    lines_df
        lines data frame
    file_name
        name of the document, used to extract the year from the file_name
    mode
        mode of operation, fitz or "tess"
    verbose, optional
        print infos, by default True
    double_paged, optional
        if True: document is treated as double paged, if False: document is treated as single paged, 
        if None: document will be checked to see if it is single or double paged, by default None
    save_to, optional
        if specified: path where the indexes csv file will be written to, by default None
    remove_wrong, optional
        True if indexes where no date could be extracted should be removed, by default True

    Returns
    -------
        indexes data frame
    """    
    if verbose:
        print(f"Starting extraction for {file_name}...")

    bins_x0, bins_x1, x0_n = group.group_line_starts_ends(lines_df, mode)
    borders = lines.make_borders_df(bins_x0, bins_x1)

    if double_paged:
        if mode=="tess":
            return extract_double_paged_indexes(words_df, borders, file_name, verbose=verbose, save_to=save_to)
        else:
            print("Extraction for double paged documents only works in mode 'tess'. Extraction failed.")
            return None

    elif double_paged == None:
        if is_double_paged(words_df, borders, mode):

            if mode=="tess":
                return extract_double_paged_indexes(words_df, borders, file_name, verbose=verbose, save_to=save_to)
            else:
                print("Extraction for double paged documents only works in mode 'tess'. Extraction failed.")
                return None

    df = label.assign_types(lines_df, bins_x0, bins_x1, x0_n)
    df = label.assign_labels(df, x0_n)

    ind_df, p_l, p_g = label.correct_x0_types(df, bins_x0, bins_x1, x0_n, mode)
    ind_df = label.assign_labels(ind_df, x0_n)
    ind_df = label.approve_correction(df, ind_df, p_l)
    ind_df = label.improve_country_classification(ind_df)

    ind_df = records.extract_records(ind_df)
    ind_df = date.extract_dates(ind_df, file_name)
    ind_df = clean_text(ind_df)

    if remove_wrong:
        ind_df = ind_df.loc[ind_df["extracted_date"]!=""]

    if verbose:
        print("Finished extraction")

    if not save_to == None:
        ind_df.to_csv(save_to, index=False)

        if verbose:
            print(f"Saved extracted indexes to {save_to}.")

    return ind_df


def extract_double_paged_indexes(words_df, borders, file_name, save_to=None, mode="tess", verbose=True):
    """Extracts and returns indexes of a double paged document.

    Parameters
    ----------
    words_df
        words data frame
    borders
        borders data frame
    file_name
        name of the document, used to extract the year from the file_name
    save_to, optional
        if specified: path where the indexes csv file will be written to, by default None
    mode, optional
        mode of operation, "fitz" or "tess", by default "tess", does not really work in mode "fitz"
    verbose, optional
        print infos, by default True

    Returns
    -------
        indexes data frame
    """
    if verbose:
        print("Extracting indexes from document with double-pages.")

    df = words_df.copy()
    pdf_l = pd.DataFrame()
    pdf_r = pd.DataFrame()

    if mode=="tess":
        df = df.rename(columns={"left": "x0", "top": "y0", "page_num": "page"})

    mean_dx = lines.get_mean_dx(words_df, borders, mode)

    for p, b in borders.groupby("page"):
        middle = b.iloc[0]["x0"] + mean_dx/2
        pdf_p = df.loc[df["page"] == p]

        l = pdf_p.loc[pdf_p["x0"] <= middle]
        r = pdf_p.loc[pdf_p["x0"] > middle]

        pdf_l = pd.concat([pdf_l, l])
        pdf_r = pd.concat([pdf_r, r])

    lines_l = lines.make_lines_df_from_ocr(pdf_l)
    lines_r = lines.make_lines_df_from_ocr(pdf_r)

    ind_l = extract_indexes(None, lines_l, file_name, mode, verbose=False, double_paged=False)
    ind_r = extract_indexes(None, lines_r, file_name, mode, verbose=False, double_paged=False)

    idx_s = ind_l.shape[0]
    idx_e = idx_s + ind_r.shape[0]
    ind_r = ind_r.set_index(pd.Index(list(range(idx_s, idx_e))))

    ind_df = pd.concat([ind_l, ind_r])
    ind_df = ind_df.rename_axis("idx").sort_values(by=["page", "idx"])
    ind_df = ind_df.reset_index(drop=True)

    if not save_to == None:
        ind_df.to_csv(save_to, index=False)

        if verbose:
            print(f"Saved extracted indexes to {save_to}.")

    return ind_df


def is_double_paged(words_df, borders, mode):
    """Determines if a document is double paged.

    A double paged document has a gap in the middle, where no words should start.

    Parameters
    ----------
    words_df
        words data frame
    borders
        borders data frame
    mode
        mode of operation, "fitz" or "tess", by default "tess", does not really work in mode "fitz"

    Returns
    -------
        True if document is double paged, else Fals

    Raises
    ------
    ValueError
        if mode is neither "fitz" nor "tess"
    """    
    df = words_df.copy()

    m = 0
    if mode=="fitz":
        m = 20
    elif mode=="tess":
        m = 100
        df = df.rename(columns={"left": "x0", "top": "y0", "page_num": "page"})
    else:
        raise ValueError(f"groups_lines() got an unknown value for parameter mode: {mode}")

    # Max x1 values in borders not always correct for every page.
    # This determines the mean for the x1 values where the lines end.
    mean_dx = lines.get_mean_dx(words_df, borders, mode)

    double_p = []
    for p, b in borders.groupby("page"):
        middle = b.iloc[0]["x0"] + mean_dx/2

        middle_words = df.loc[(df["page"]==p) & (df["x0"] > middle-m) & (df["x0"] < middle+m)]
        if middle_words.shape[0] <= 1:
            double_p.append(True)
        else:
            double_p.append(False)

    if double_p.count(True) > 0.8 * len(double_p):
        return True

    return False


def clean_text(ind_df):
    """Cleans up the index texts a little bit.

    Parameters
    ----------
    ind_df
        indexes data frame

    Returns
    -------
        indexes data frame
    """    
    df = ind_df.copy()

    reg_s = "^[^a-zA-Z0-9]+"
    reg_w = " {2,}"
    reg_p = "( *[\.;,+] *)+$"

    for i, row in df.iterrows():
        t = row["text"]

        t = re.sub(reg_s, "", t)
        t = re.sub(reg_p, "", t)
        t = re.sub(reg_w, " ", t)

        t = t.strip()
        df.loc[i, "text"] = t

    return df
