© 2023 [Jeúsa Hamer](https://orcid.org/0000-0001-8562-8806)

Contributer: [Alexander Polte](https://orcid.org/0000-0002-3733-0746)

University of Bremen

# indexex
This tool can be used to extract indexes of legal texts published by the International Labour Organisation. See *Documentation_Indexex.odt* for more information about how indexex works.

**Usage**:  
`main.py [-h] [-v] [-m MODE] [-p START_PAGE] [-r [RECURSIVE]] [-k] [-c] [-s] [-t TESSERACT_PATH] input_path output_dir`

**Positional arguments:**  
  `input_path`            : path to the file (pdf or tesseract data frame as csv) or directory containing the files  
  `output_dir`            : path to the directory where the extracted indexes will be written to  

**Optional arguments:**  
  `-h, --help`            : show this help message and exit  
  `-v, --verbose`         : print infos during extraction  
  `-m MODE, --mode MODE`  : define mode to be used to read the file, FITZ: reads a pdf which has ocr imbedded, TESS: uses the tesseract ocr engine to create new ocr for a pdf or the input file is a csv file containing a tesseract data frame  
  `-p START_PAGE, --start_page START_PAGE` : only works when input path is a file, set the page of the document from which the extraction should start  
  `-r [RECURSIVE], --recursive [RECURSIVE]` : only when input path is a directory, define if path should be searched recursively, optional: how many levels of subdirectories should be searched  
  `-k, --keep_all`        : indexes found based on line indentation where no date could be found are not removed, default is that they are removed  
  `-c, --country_centered` : only works when input path is a file, country headlines in this document are centered  
  `-s, --start_indented`  : only works when input path is a file, the first line of an index is indented in this document  
  `-t TESSERACT_PATH, --tesseract_path TESSERACT_PATH` : define path to tesseract executable 