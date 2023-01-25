import pandas as pd
import re

from difflib import get_close_matches


def extract_dates(rec_df, file_name):
    df = rec_df.copy()
    df["extracted_date"] = ""
    df["extracted_day"] = ""
    df["extracted_month"] = ""
    df["extracted_year"] = ""
    df["full_text"] = df["text"]

    digits = "[0-9oOIltriSQzZ]"
    re_d1 = "^(([A-Za-z]{3}[.:,]{0,3}|[A-Za-z]{4}.?) ([1-3IlzZr]?" + digits + ")(?![0-9])(st|nd|rd|fd|th)?)" # in the beginning, example: Nov. 4 | July 25th
    re_d2 = "^(([1-3IirltzZ]?" + digits + ")[/,;.]{1,2}([I1l]{0,3}[VX]?[I1l]{0,3})[/,;.]{1,2}" + digits + "{4})" # in the beginning, example: 13/III/1986 | 7/11/198S
    re_d3 = "(([1-3IirltzZr]?" + digits + ")(st|nd|rd|fd|th)? ([A-Za-z]{3,})[,.]? ?([Ii1lrt]" + digits + "{3})\.?)" # towards the end, example: 25th February, 1929
    re_d4 = "^(([1-3IlzZr]?" + digits + ")(st|nd|rd|fd|th)? ([A-Za-z]{3}[.:,]{0,3}|[A-Za-z]{4}.?) ([Ii1lrt]" + digits + "{3})\.?)" # in the beginning, example: 16 Dec. 1965

    dt = get_date_type(df)
    re_d = None
    day_g = 0
    month_g = 0

    if dt > -1:
        if dt==1:
            re_d = re_d1
            day_g = 3
            month_g = 2
        elif dt==2:
            re_d = re_d2
            day_g = 2
            month_g = 3
        elif dt==3:
            re_d = re_d3
            day_g = 2
            month_g = 3
        elif dt==4:
            re_d = re_d4
            day_g = 2
            month_g = 4


        for i, row in df.iterrows():
            text = re.sub("[\"'`“´‘]", "", row["text"])
            d = None

            if dt != 2:
                text = re.sub("[,.]", "", text)
            if dt != 3:
                d = re.search(re_d, text)
            if dt == 3:
                for m in re.finditer(re_d, text):
                    d = m

            if not d == None:
                df.loc[i, "extracted_date"] = d.group(1)
                df.loc[i, "extracted_day"] = d.group(day_g)
                df.loc[i, "extracted_month"] = d.group(month_g)

                if dt != 1:
                    y = re.search(digits + "{4}", d.group(1))
                    df.loc[i, "extracted_year"] = y.group()

                df.loc[i, "text"] = re.sub(re_d, "", row["text"])

    df = norm_dates(df, dt, file_name)
    df = df.drop(columns=["extracted_day", "extracted_month", "extracted_year"])

    return df


def get_date_type(rec_df):

    # stricter version of the date regex's
    digits = "[0-9]"
    re_d1 = "^(([A-Za-z]{3}[.:,]{0,3}|[A-Za-z]{4}.?) [1-3]?" + digits + "(?![0-9])(st|nd|rd|th)?)" # in the beginning, example: Nov. 4 | July 25th
    re_d2 = "^([1-3]?" + digits + "/[I1l]{0,3}[VX]?[I1l]{0,3}/" + digits + "{4})" # in the beginning, example: 13/III/1986 | 7/IX/1985
    re_d3 = "([1-3]?" + digits + "(st|nd|rd|th)? [A-Za-z]{3,}[,.] ?[I1l]" + digits + "{3})" # towards the end, example: 25th February, 1929
    re_d4 = "^([1-3]?" + digits + "(st|nd|rd|th)? ([A-Za-z]{3}[.:,]{0,3}|[A-Za-z]{4}.?) 1" + digits + "{3})" # in the beginning, example: 16 Dec. 1965

    samp = rec_df.sample(frac=1/10)
    samp["date_type"] = -1

    for i, row in samp.iterrows():
        t = row["text"]
        dt = -1

        d1 = re.search(re_d1, t)
        d2 = re.search(re_d2, t)
        d3 = None
        d4 = re.search(re_d4, t)

        for m in re.finditer(re_d3, t):
            d3 = m

        if d3 != None:
            dt = 3
        if d2 != None:
            dt = 2
        if d1 != None:
            dt = 1
        if d4 != None:
            dt = 4

        samp.loc[i, ["date_type"]] = dt

    date_type = samp.groupby("date_type").count().sort_values("country", ascending=False)

    if not date_type.empty:
        date_type = date_type.iloc[0].name
    else:
        date_type = -1

    return date_type


def norm_dates(rec_df, date_type, file_name):
    df = rec_df.copy()

    df.insert(3, "date", "")
    df.insert(4, "year", "")

    for i, row in df.iterrows():
        da = row["extracted_day"]
        mo = row["extracted_month"]
        ye = row["extracted_year"]

        day = correct_digit_recognition(da)
        year = correct_digit_recognition(ye)
        month = norm_month(mo,date_type)

        if month != None:
            df.loc[i, "year"] = year
            df.loc[i, "date"] = f"{day}.{month}."

    if date_type == 1:
        file_year = re.search("\d{4}", file_name)
        year =  0

        if file_year != None:
            year = file_year.group()
            df.loc[df["date"] != "", "year"] = year

    return df


def correct_digit_recognition(dig):

    cor = re.sub("[Iiltr]", "1", dig)
    cor = re.sub("[Zz]", "2", cor)
    cor = re.sub("S", "5", cor)
    cor = re.sub("[OoQ]", "0", cor)

    if cor=="0":
        cor = "9"

    return cor


def norm_month(month, date_type, ignore_case=True):
    mon_l = list()
    month = str(month)

    if date_type == 1:
        mon_l = ["Jan", "Feb", "Mar", "Apr", "May", "June", "July", "Aug", "Sep", "Oct", "Nov", "Dec"]

    elif date_type == 2:
        mon_l = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]
        month = re.sub("[1il]", "I", month)
        ignore_case = False

    elif date_type == 3:
        mon_l = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

    else:
        return None

    if (month == "") | (month == None):
        return None

    if ignore_case:
        mon_l = [x.lower() for x in mon_l]

    sim = get_close_matches(month, mon_l, n=1, cutoff=0.2)

    if len(sim) == 0:
        return None

    return mon_l.index(sim[0])+1
