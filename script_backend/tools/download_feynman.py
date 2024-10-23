import json
import os
import re
import ssl
import urllib.request

import bs4


def lint_string(string):
    string = string.strip()
    string = string.replace("\r\n", " ")
    string = string.replace("\xa0", " ")
    string = string.replace("\n", " ")
    string = string.replace("—", "-")
    string = string.replace("–", "-")
    string = string.replace("…", "...")
    string = string.replace("’", "'")
    string = string.replace("”", "'")
    string = string.replace("“", "'")
    # string = string.replace(r"% ebook break", "")’
    # string = string.replace(r"% ebook insert", "")

    # find all \\label{SOMETEXT} and remove them using regex
    string = re.sub(r"\\label{.*?}", "", string)

    # find all \\begin{equation} and remove them using regex
    string = re.sub(r"\\begin{equation}", "$", string)
    string = re.sub(r"\\end{equation}", "$", string)

    string = re.sub(r"\\begin{equation\*}", "$", string)
    string = re.sub(r"\\end{equation\*}", "$", string)
    string = re.sub(r"\\FLP", "", string)
    # find all \\\\[TEXT] and remove them using regex
    string = re.sub(r"\\\\\[.*?]", "", string)

    # \biggl
    string = re.sub(r"\\biggl", " ", string)
    string = re.sub(r"\\biggr", " ", string)

    string = re.sub(r"\\Biggl", " ", string)
    string = re.sub(r"\\Biggr", " ", string)

    string = re.sub(r"\\tfrac", r"\\frac", string)

    string = re.sub(r"\\notag", "", string)
    string = re.sub(r"\\\\", " ", string)

    # \;
    string = re.sub(r"\\;", " ", string)
    string = re.sub(r"\\,", " ", string)
    string = re.sub(r"\\:", " ", string)
    string = re.sub(r"\\!", " ", string)
    string = re.sub(r"\\quad", " ", string)

    string = re.sub(r"\\([a-zA-Z])op", r"\\hat{\1}", string)
    string = re.sub(r"\\([a-zA-Z])dotop", r"\\hat{\\dot{\1}}", string)

    string = re.sub(r"\\expval{(.*?)}", r"\\braket{\1}", string)
    string = re.sub(r"\\av{(.*?)}", r"\\bar{\1}", string)
    string = re.sub(r"\\abs{(.*?)}", r"|\1|", string)

    string = re.sub(r"\\ketsl{(.*?)}", r"\\ket{\1}", string)
    string = re.sub(r"\\barsl{(.*?)}", r"\\bar{\1}", string)
    string = re.sub(r"\\slOne", "1", string)
    string = re.sub(r"\\slTwo", "2", string)

    # find all \\ddp{SOMETEXT}{TEXT} and replace them with \\frac{\\partial SOMETEXT}{\\partial TEXT}
    string = re.sub(
        r"\\ddp{(.*?)}{(.*?)}", r"\\frac{\\partial \1}{\\partial \2}", string
    )
    string = re.sub(
        r"\\ddpl{(.*?)}{(.*?)}", r"\\frac{\\partial \1}{\\partial \2}", string
    )
    string = re.sub(r"\\ddt{(.*?)}{(.*?)}", r"\\frac{d \1}{d \2}", string)
    string = re.sub(r"\\ddtl{(.*?)}{(.*?)}", r"\\frac{d \1}{d \2}", string)

    # condense all whitespace to a single space
    string = re.sub(r"\s+", " ", string)

    return string


def extract_chapter_name(parsed_html: bs4.BeautifulSoup):
    chapter_name = parsed_html.find("h2", class_="chapter-title")
    chapter_id = chapter_name.find("span").text.strip()

    chapter_name = chapter_name.text.replace(chapter_id, "").strip()
    chapter_name = f"{chapter_id} {chapter_name}"
    chapter_name = lint_string(chapter_name)
    return chapter_name


def extract_section_name(section_element: bs4.BeautifulSoup):
    section_name = section_element.find("h3", class_="section-title")
    section_id = section_name.find("span").text

    section_name = section_name.text.replace(section_id, "").strip()
    section_id = section_id.replace("–", ".").strip()
    section_name = f"{section_id} {section_name}"
    section_name = lint_string(section_name)
    return section_name


def download_script_section(script_id: str, chapter_idx: int):

    # convert the chapter index to a string
    # also add a leading zero if the chapter index is a single digit | 7 -> 07
    if len(str(chapter_idx)) == 1:
        chapter_idx = f"0{chapter_idx}"

    url = BASE_URL.format(script_id=script_id, chapter_idx=chapter_idx)
    html = urllib.request.urlopen(url, context=ctx)
    parsed_html = bs4.BeautifulSoup(html, "html.parser")

    return parsed_html


# setting up the SSL context
# This way we can avoid SSL errors
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# The base URL for the Feynman Lectures
# When you download this you should only use this for your personal use!
# They forbid redistribution of their content
BASE_URL = "https://www.feynmanlectures.caltech.edu/{script_id}_{chapter_idx}.html"
CHAPTERS = {"I": 52, "II": 42, "III": 21}

# We automatically download to the data/scripts folder
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "scripts")

for script_id, num_chapters in CHAPTERS.items():

    script = {}
    for chapter_idx in range(1, num_chapters + 1):
        print(
            f"Processing chapter {chapter_idx}/{num_chapters} of Script {script_id}",
            end="\r",
        )

        parsed_html = download_script_section(script_id, chapter_idx)

        chapter_name = extract_chapter_name(parsed_html)
        script[chapter_name] = {}

        section_elements = parsed_html.find_all("div", class_="section")
        for section_element in section_elements:
            section_name = extract_section_name(section_element)
            script[chapter_name][section_name] = {}

            paragraph_elements = section_element.find_all("div", class_="para")
            for paragraph_idx, paragraph_element in enumerate(paragraph_elements):
                paragraph_text = lint_string(paragraph_element.text)
                script[chapter_name][section_name][paragraph_idx] = paragraph_text

    out_path = os.path.join(OUT_DIR, f"FEYNMAN{script_id}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=4)
