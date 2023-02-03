import argparse
import os

import extract

def defineArgumentParser():
    parser = argparse.ArgumentParser(description="This tool can be used to extract indexes of legal texts published by the ILO (International Labour Organisation).")

    parser.add_argument("input_path")
    parser.add_argument("output_dir")
    parser.add_argument("-v", "--verbose", help="print infos during extraction", action="store_true", default=False)

    return parser.parse_args()


if __name__=="__main__":
    args = defineArgumentParser()

    if os.path.isdir(args.input_path):
        extract.extract_indexes_dir(args.input_path, args.output_dir, verbose=args.verbose)
    elif os.path.isfile(args.input_path):
        extract.extract_indexes_file(args.input_path, args.output_dir, verbose=args.verbose)
    else:
        print("Input path is not valid.")
