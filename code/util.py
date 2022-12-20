import fitz
import os
import pytesseract
import pandas as pd

from pdf2image import convert_from_path


page_size = (0,0)
page_start = 1

def set_page_size(dicts):
    global page_size
    page_size = (dicts[0]["width"], dicts[0]["height"])

def set_first_page_no(p_no):
    global page_start
    page_start = p_no


def list_files(directory, suffix='', recursive=True):

    if not directory.endswith(os.sep):
        directory = directory + os.sep

    files = []
    dir_files = os.listdir(directory)

    rec = recursive
    if type(recursive) is int:
        rec = recursive-1

    for f in dir_files:

        if f.lower().endswith(suffix):
            files.append(directory + f)

        elif ((recursive == True) | (recursive >= 1)) & os.path.isdir(directory + f):
            sub_dir_files = list_files(directory + f, suffix, rec)
            files = files + sub_dir_files

    return files


def read_pdf(path, page_no_start=1, print_info=True):

    pdf_pages = []
    pdf_dicts = []

    if print_info:
        print("Reading pdf from", path)
        print("...")

    with fitz.open(path) as pdf:
        for page in pdf:
            pdf_pages.append(page.get_text())

            pdf_dicts.append(page.get_text('dict', flags=~fitz.TEXT_PRESERVE_IMAGES))

    if print_info:
        print("Finished reading", len(pdf_pages)-(page_no_start-1), "page(s)")

    set_page_size(pdf_dicts)
    set_first_page_no(page_no_start)

    return pdf_pages[page_no_start-1:], pdf_dicts[page_no_start-1:]


def ocr(file_path, start_page=1, verbose=True, save_to=None):
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
            if not save_to.endswith(os.sep):
                save_to += os.sep

            save_path = save_to + os.path.basename(file_path).replace(".pdf", ".csv")
            pdf_df.to_csv(save_path, index=False)

            if verbose:
                print(f"Saved data frame to {save_path}.")
        else:
            print(f"Cannot save to {save_to}. Not a directory.")

    return pdf_df


def flatten(t):
    return [item for sublist in t for item in sublist]

def similar_to(a, b, d):
    if ((a+d>b) & (a-d<b)):
        return True
    return False
