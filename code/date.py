import pandas as pd
import re

from difflib import get_close_matches


def extract_dates(rec_df, file_name):
    # lax versions
    digit = "[0-9oOIltriSQzZ]"
    big_i = "[I1l]"
    one = "[1Iltri]"

    day = "(?<![0-9])([1-3IltrizZ]?" + digit + ")(?![0-9])" # 4 | 31
    dayth = day + "(st|nd|rd|th)?" # 4th | 31st
    month_short = "([A-Za-z]{4}\.?|[A-Za-z]{3}[.:,]?)" # Dec. | June | Sept.
    month_long = "([A-Za-z]{3,9})" # February
    year = "(" + one + "9"  + digit + "{2})"

    # in the beginning, example: Nov. 4 | July 25th
    re_d1 = "^" + month_short + " " + dayth

    # in the beginning, example: 13/III/1986 | 7/IX/1985
    re_d2 = "^" + day + "[/,;.]{1,2}(" + big_i + "{0,3}[VX]?" + big_i + "{0,3})[/,;.]{1,2}" + year

    # towards the end, example: 25th February, 1929
    re_d3 = dayth + " " + month_long + "[,.:]? " + year

    # in the beginning, example: 16 Dec. 1965
    re_d4 = "^" + dayth + " " + month_short + "[,.:]?( " + year + ")?"

    df = rec_df.copy()
    df["extracted_date"] = ""
    df["extracted_day"] = ""
    df["extracted_month"] = ""
    df["extracted_year"] = ""
    df["full_text"] = df["text"]

    dt = get_date_type(df)
    re_d = None
    day_g = 0
    month_g = 0
    year_g = 0

    if dt > -1:
        if dt==1:
            re_d = re_d1
            day_g = 2
            month_g = 1
        elif dt==2:
            re_d = re_d2
            day_g = 1
            month_g = 2
            year_g = 3
        elif dt==3:
            re_d = re_d3
            day_g = 1
            month_g = 3
            year_g = 4
        elif dt==4:
            re_d = re_d4
            day_g = 1
            month_g = 3
            year_g = 5


        for i, row in df.iterrows():
            text = re.sub("[\"'`“´‘]", "", row["text"])
            d = None
            #text = re.sub("[,.]", "", text)

            if dt != 3:
                d = re.search(re_d, text)
            if dt == 3:
                for m in re.finditer(re_d, text):
                    d = m

            if not d == None:
                df.loc[i, "extracted_date"] = d.group()
                df.loc[i, "extracted_day"] = d.group(day_g)
                df.loc[i, "extracted_month"] = d.group(month_g)

                if year_g != 0:
                    df.loc[i, "extracted_year"] = d.group(year_g)

                df.loc[i, "text"] = re.sub(re_d, "", row["text"])

    df = norm_dates(df, dt, file_name)
    df = df.drop(columns=["extracted_day", "extracted_month", "extracted_year"])

    return df


def get_date_type(rec_df):
    # strict versions
    digit = "[0-9]"
    big_i = "[I1l]"
    one = "[1Il]"

    day = "(?<![0-9])([1-3]?" + digit + ")(?![0-9])" # 4 | 31
    dayth = day + "(st|nd|rd|th)?" # 4th | 31st
    month_short = "([A-Za-z]{4}|[A-Za-z]{3}\.?)" # Dec. | June
    month_long = "([A-Za-z]{3,9})" # February
    year = "(" + one + "9"  + digit + "{2})"

    # in the beginning, example: Nov. 4 | July 25th
    re_d1 = "^" + month_short + " " + dayth

    # in the beginning, example: 13/III/1986 | 7/IX/1985
    re_d2 = "^" + day + "/" + big_i + "{0,3}[VX]?" + big_i + "{0,3}/" + year

    # towards the end, example: 25th February, 1929
    re_d3 = dayth + " " + month_long + "[,.:]? " + year

    # in the beginning, example: 16 Dec. 1965 | 7 May, 1988 | 1st June
    re_d4 = "^" + dayth + " " + month_short + "[,.:]?( " + year + ")?"

    samp = rec_df.sample(min(max(rec_df.shape[0]//10, 10), rec_df.shape[0]))
    samp["date_type"] = -1

    for i, row in samp.iterrows():
        t = row["full_text"]
        dt = -1

        d1 = re.search(re_d1, t)
        d2 = re.search(re_d2, t)
        d3 = None
        d4 = re.search(re_d4, t)

        for m in re.finditer(re_d3, t):
            d3 = m

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

    if not "date" in df.columns:
        df.insert(3, "date", "")
        df.insert(4, "year", "")
    else:
        df["date"] = ""
        df["year"] = ""

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

    file_year = re.search("\d{4}", file_name)

    if file_year != None:
        df.loc[(df["date"]!="") & (df["year"]==""), "year"] = file_year.group()

    return df


def correct_digit_recognition(dig):

    if type(dig) is str:
        cor = re.sub("[Iiltr]", "1", dig)
        cor = re.sub("[Zz]", "2", cor)
        cor = re.sub("S", "5", cor)
        cor = re.sub("[OoQ]", "0", cor)

        if cor=="0":
            cor = "9"

        return cor

    else:
        return ""


def norm_month(month, date_type, ignore_case=True):
    mon_l = list()
    month = str(month)

    if (date_type == 1) | (date_type == 4):
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
