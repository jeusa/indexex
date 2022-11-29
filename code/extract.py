import util
import lines
import group
import label
import records

def extract_indexes(pdf_df, verbose=True, save_to=None):
    df = lines.make_lines_df_from_ocr(pdf_df)

    bins_x0, bins_x1, x0_n = group.group_line_starts_ends(df)
    borders = lines.make_borders_df(bins_x0, bins_x1)

    df = label.assign_types(df, bins_x0, bins_x1, x0_n)
    df = label.correct_x0_types(df, bins_x0, bins_x1, x0_n)
    df = label.assign_labels(df, x0_n)

    df["new_label"] = df["label"]
    df = label.improve_country_classification(df)

    df = records.extract_records(df)

    if not save_to == None:
        df.to_csv(save_to, index=False)

        if verbose:
            print(f"Saved extracted indexes to {save_to}.")

    return df
