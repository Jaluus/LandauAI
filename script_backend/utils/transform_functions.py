import re

import pandas as pd
import tiktoken


def format_script(script: dict) -> dict:
    # TODO: Refactor this function to be more readable and maintainable
    formatted_script = {}
    for chapter in script:
        if len(chapter) == 0:
            continue

        # the first key of the first element in the list is the chapter name
        chapter_name_key = list(chapter[0].keys())[0]
        chapter_name = chapter[0][chapter_name_key].strip()
        del chapter[0][chapter_name_key]

        formatted_script[chapter_name] = {}

        for section in chapter:
            for i in range(len(section)):
                section_name_key = list(section.keys())[i]
                section_title = section[section_name_key].strip()

                section_beginning = section[section_name_key].split(" ")[1]
                section_beginning = section_beginning.split(".")

                # ensures that the section name is not a formula
                if (
                    len(section_beginning) == 2
                    and section_beginning[0].isdigit()
                    and section_beginning[1].isdigit()
                    and section[section_name_key].count("$") < 4
                ):
                    del section[section_name_key]
                    formatted_script[chapter_name][section_title] = section
                    break

    for chapter in formatted_script:
        for section in formatted_script[chapter]:
            for paragraph_anchor in formatted_script[chapter][section]:
                formatted_line = formatted_script[chapter][section][
                    paragraph_anchor
                ].strip()
                if len(formatted_line) > 0:
                    formatted_script[chapter][section][
                        paragraph_anchor
                    ] = formatted_line

    return formatted_script


def linting_script(script: dict) -> dict:
    linted_script = {}
    for key in script:
        linted_script[key] = {}
        for sub_key in script[key]:
            linted_script[key][sub_key] = {}

            current_ss = ""
            for reference_anchor in script[key][sub_key]:

                line = script[key][sub_key][reference_anchor]
                if "function" in line:
                    continue

                linted_line = line.replace("\n", " ")
                linted_line = line.replace("\r", " ")
                linted_line = line.replace("\t", "")
                linted_line = line.replace("&#13;", "")
                linted_line = line.replace("&amp;", "")
                linted_line = re.sub(r"\\;", "", linted_line)
                linted_line = re.sub(r"\\:", "", linted_line)

                linted_line = " ".join(linted_line.split())
                linted_line = re.sub(r"\s+", " ", linted_line)
                linted_line = linted_line.strip()

                line_start = linted_line.split(" ")[0]
                # if the line start only contains numbers and dots, it is a line number
                if line_start.replace(".", "").isdigit():
                    line_start = " ".join(linted_line.split(" ")[1:])
                    if not line_start.startswith("$$"):
                        current_ss = "Abschnitt: " + line_start + "\n"
                        continue
                    else:
                        linted_line = "Gl. " + linted_line

                # append the current_ss to the next line and reset the current_ss
                if current_ss != "":
                    linted_line = current_ss + linted_line
                    current_ss = ""

                if len(linted_line) == 0:
                    continue

                linted_script[key][sub_key][reference_anchor] = linted_line

    return linted_script


def formatted_script_to_pandas(
    script: dict,
    script_name: str,
    script_id: str,
) -> pd.DataFrame:
    dataframe_list = []
    encoder = tiktoken.get_encoding("o200k_base")
    for chapter_name in script:
        for section_name in script[chapter_name]:
            paragraph_ids, paragraphs = (
                list(script[chapter_name][section_name].keys()),
                list(script[chapter_name][section_name].values()),
            )

            # sorted paragraph ids
            sorted_paragraph_id_idx = sorted(
                range(len(paragraph_ids)), key=lambda k: int(paragraph_ids[k])
            )
            paragraphs = [paragraphs[i] for i in sorted_paragraph_id_idx]

            for paragraph_id, paragraph in enumerate(paragraphs):
                num_tokens = len(encoder.encode(paragraph))

                chapter_id = chapter_name.strip().split(" ")[0]
                section_id = section_name.strip().split(" ")[0]

                # the section always has the chapter index in it
                section_id = section_id.replace(f"{chapter_id}.", "")

                formula_id = ""
                # christophs format
                if paragraph.startswith("Gl. "):
                    try:
                        formula_id = (
                            paragraph.split("$$")[0].replace("Gl. ", "").strip()
                        )
                    except:
                        formula_id = ""

                dataframe_list.append(
                    {
                        # ID Keys
                        "id": f"{script_id}.{chapter_id}.{section_id}.{paragraph_id}",
                        "document_id": script_id,
                        "chapter_id": chapter_id,
                        "section_id": section_id,
                        "paragraph_id": paragraph_id,
                        "formula_id": formula_id,
                        # Name Keys
                        "document_name": script_name,
                        "chapter_name": chapter_name,
                        "section_name": section_name,
                        # Content Keys
                        "content": paragraph,
                        # Extra Keys
                        "num_tokens": num_tokens,
                    }
                )
    return pd.DataFrame(dataframe_list)


def add_embeddings(
    dataframe: pd.DataFrame,
    embedding_function,
    token_target: int = 0,
    overlap: int = 0,
) -> pd.DataFrame:
    if token_target > 0:
        # add a new column to the dataframe that contains the overlap content
        dataframe["overlap_content"] = ""

        script_df_token_limit_grouped = dataframe.groupby("section")
        # for each group
        for name, group in script_df_token_limit_grouped:
            # sort by the paragraph_id
            group = group.sort_values("paragraph_id")
            num_rows = group.shape[0]

            for idx, row in group.iterrows():
                # retrieve the rows that are within the overlap
                row_ref_idx = row["paragraph_id"]
                current_tokens = row["num_tokens"]

                added_ref_idxs = [row_ref_idx]
                current_row_index = row_ref_idx
                i = 1
                while current_tokens < token_target:

                    # we are going to alternate between adding and subtracting the paragraph_id
                    # this is to get the rows that are closest to the paragraph_id
                    # e.g. 12, 13, 11, 14, 10, 15, 9, 16, ...
                    current_row_index += i * (-1) ** i
                    i += 1
                    if current_row_index > num_rows:
                        break
                    if current_row_index >= num_rows or current_row_index < 0:
                        continue

                    # get the entrie where the paragraph_id column is equal to the current_row_index
                    current_row = group[
                        group["paragraph_id"] == current_row_index
                    ].iloc[0]
                    added_ref_idxs.append(current_row["paragraph_id"])
                    current_tokens += current_row["num_tokens"]

                overlap_rows = group[group["paragraph_id"].isin(added_ref_idxs)]
                dataframe.loc[idx, "overlap_content"] = " ".join(
                    overlap_rows["content"].values
                )
        contents = dataframe["overlap_content"].tolist()
    elif overlap > 0:
        # add a new column to the dataframe that contains the overlap content
        dataframe["overlap_content"] = ""
        script_df_overlaps_grouped = dataframe.groupby("section")
        # for each group
        for name, group in script_df_overlaps_grouped:
            # sort by the paragraph_id
            group = group.sort_values("paragraph_id")
            num_rows = group.shape[0]

            for idx, row in group.iterrows():
                # retrieve the rows that are within the overlap
                row_ref_idx = row["paragraph_id"]
                overlap_ref_idxs = [
                    i
                    for i in range(row_ref_idx - overlap, row_ref_idx + overlap + 1)
                    if i >= 0 and i < num_rows
                ]
                overlap_rows = group[group["paragraph_id"].isin(overlap_ref_idxs)]
                combined_content = " ".join(overlap_rows["content"].values)
                dataframe.loc[idx, "overlap_content"] = combined_content
        contents = dataframe["overlap_content"].tolist()
    else:
        contents = dataframe["content"].tolist()

    embeddings = embedding_function(contents)
    dataframe["embedding"] = embeddings
    return dataframe
