"""This script implements the command line tool for the index extraction."""

import argparse
import os

import extract

def defineArgumentParser():
    """Defines the arguments of the command line tool.

    Returns
    -------
        parser with arguments
    """    
    parser = argparse.ArgumentParser(description="This tool can be used to extract indexes of legal texts published by the ILO (International Labour Organisation).")

    parser.add_argument("input_path", help="path to the file (pdf or tesseract data frame as csv) or directory containing the files")
    parser.add_argument("output_dir", help="path to the directory where the extracted indexes will be written to")
    parser.add_argument("-v", "--verbose", help="print infos during extraction", action="store_true", default=False)
    parser.add_argument("-m", "--mode", help="define mode to be used to read the file, FITZ: reads a pdf which has ocr imbedded, TESS: uses the tesseract ocr engine to create new ocr for a pdf or the input file is a csv file containing a tesseract data frame")
    parser.add_argument("-p", "--start_page", type=int, help="only works when input path is a file, set the page of the document from which the extraction should start", default=1)
    parser.add_argument('-r', '--recursive', type=int, help='only when input path is a directory, define if path should be searched recursively, optional: how many levels of subdirectories should be searched', nargs='?', default=False, const=True)
    parser.add_argument("-k", "--keep_all", help="indexes found based on line indentation where no date could be found are not removed, default is that they are removed", action="store_true", default=False)
    parser.add_argument("-c", "--country_centered", help="only works when input path is a file, country headlines in this document are centered", action="store_true", default=False)
    parser.add_argument("-s", "--start_indented", help="only works when input path is a file, the first line of an index is indented in this document", action="store_true", default=False)
    parser.add_argument("-t", "--tesseract_path", help="define path to tesseract executable")

    return parser.parse_args()


if __name__=="__main__":
    args = defineArgumentParser()

    m = None
    if args.mode != None:
        m = str.lower(args.mode)

    if os.path.isdir(args.input_path):
        extract.extract_indexes_dir(args.input_path, args.output_dir, verbose=args.verbose, remove_wrong=not args.keep_all, mode=m, recursive=args.recursive, tesseract_path=args.tesseract_path)
    elif os.path.isfile(args.input_path):
        extract.extract_indexes_file(args.input_path, args.output_dir, verbose=args.verbose, start_page=args.start_page, remove_wrong=not args.keep_all, mode=m, country_centered=args.country_centered, start_indented=args.start_indented, tesseract_path=args.tesseract_path)
    else:
        print("Input path is not valid.")
