"""This script contains some helpful methods for pdfs, files and other things."""

import fitz # PyMuPDF
import os
import pytesseract
import pandas as pd

from pdf2image import convert_from_path


def list_files(directory, suffix='', recursive=True):
    """ Lists all files in directory (and its subdirectories) that end with suffix. 

    Parameters
    ----------
    directory
        path to directory that should be searched for files
    suffix, optional
        suffix for the files, by default ''
    recursive, optional
        defines if the path should be searched recursively, if type=int: how many
        levels of subdirectories should be searched, by default True

    Returns
    -------
        list with path to files in directory
    """
    files = []
    dir_files = os.listdir(directory)

    rec = recursive
    if type(recursive) is int:
        rec = recursive-1

    for f in dir_files:
        cur_path = os.path.join(directory, f)

        if ((recursive == True) | (recursive >= 1)) & os.path.isdir(cur_path):
            sub_dir_files = list_files(cur_path, suffix, rec)
            files = files + sub_dir_files
        elif f.lower().endswith(suffix) & (not os.path.isdir(cur_path)):
            files.append(cur_path)

    return files


def read_pdf(path, start_page=1, verbose=True):
    """Reads a pdf file with fitz.

    Parameters
    ----------
    path
        path to pdf fle
    start_page, optional
        page from which reading should start, by default 1
    verbose, optional
        print infos, by default True

    Returns
    -------
        list containing all pages and the words on that page with their coordinates,
        list containing all pages and their corresponding dictionary
    """
    pdf_words = []
    pdf_dicts = []

    if verbose:
        print("Reading pdf from", path)
        print("...")

    with fitz.open(path) as pdf:
        for page in pdf:
            pdf_words.append(page.get_text("words"))
            pdf_dicts.append(page.get_text('dict', flags=~fitz.TEXT_PRESERVE_IMAGES))

    if verbose:
        print("Finished reading", len(pdf_words)-(start_page-1), "page(s)")

    return pdf_words[start_page-1:], pdf_dicts[start_page-1:]


def ocr(file_path, start_page=1, verbose=True, save_to=None):
    """Uses tesseract for optical character recognition of the content of a pdf file.

    Parameters
    ----------
    file_path
        path to pdf file
    start_page, optional
        page from which ocr should start, by default 1
    verbose, optional
        print infos, by default True
    save_to, optional
        path where the tesseract data frame should be saved to, by default None

    Returns
    -------
        tesseract data frame
    """    
    if verbose:
        print(f"Converting pdf pages for {file_path} to images.")

    pdf_pages = convert_from_path(file_path, 400)[start_page-1:]
    pdf_df = pd.DataFrame()

    if verbose:
        print("Starting OCR...")

    for i, page_img in enumerate(pdf_pages):
        df = pytesseract.image_to_data(page_img, config="--psm 4 --dpi 400", output_type="data.frame")
        df["page_num"] = i + start_page
        pdf_df = pd.concat([pdf_df, df])

        if verbose:
            print(f"Done with page {i+start_page}")

    if verbose:
        print(f"OCR done for {i+1} pages.")

    if not save_to == None:
        if os.path.isdir(save_to):

            save_path = os.path.join(save_to, os.path.basename(file_path).replace(".pdf", ".csv"))
            pdf_df.to_csv(save_path, index=False)

            if verbose:
                print(f"Saved data frame to {save_path}.")
        else:
            print(f"Cannot save to {save_to}. Not a directory.")

    return pdf_df


def flatten(t):
    """Flattens a list of list to a list.

    Parameters
    ----------
    t
        list of list

    Returns
    -------
        list
    """    
    return [item for sublist in t for item in sublist]

def similar_to(a, b, d):
    """Checks if a-d < b < a+d.

    Parameters
    ----------
    a
        numeric value
    b
        numeric value
    d
        numeric value

    Returns
    -------
        True if a-d < b < a+d, else False
    """    
    if ((a+d>b) & (a-d<b)):
        return True
    return False
