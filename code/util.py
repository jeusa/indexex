import fitz
import os


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


def flatten(t):
    return [item for sublist in t for item in sublist]

def similar_to(a, b, d):
    if ((a+d>b) & (a-d<b)):
        return True
    return False
