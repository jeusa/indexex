import fitz
import os

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


def read_pdf(path, print_info=True):

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
        print("Finished reading", len(pdf_pages), "page(s)")

    return pdf_pages, pdf_dicts


def flatten(t):
    return [item for sublist in t for item in sublist]
