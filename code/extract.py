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
    df = label.assign_labels(df, x0_n)

    df_c, p_l, p_g = label.correct_x0_types(df, bins_x0, bins_x1, x0_n)
    df_c = label.assign_labels(df_c, x0_n)
    df_c = label.approve_correction(df, df_c, p_l)

    df_c["new_label"] = df_c["label"]
    df_c = label.improve_country_classification(df_c)

    df_c = records.extract_records(df_c)

    if not save_to == None:
        df_c.to_csv(save_to, index=False)

        if verbose:
            print(f"Saved extracted indexes to {save_to}.")

    return df_c
