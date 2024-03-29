"""Console annotation logger complement.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"


import logging
import os
import re
import time
from collections import namedtuple
from subprocess import call

import config
import thunderdell as td
from biblio import fields as bf
from biblio.keywords import KEY_SHORTCUTS
from change_case import title_case

# function aliases
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug

NOW = time.localtime()


def do_console_annotation(args, biblio):
    """Augment biblio with console annotations"""

    Date = namedtuple("Date", ["year", "month", "day", "circa", "time"])

    def rotate_files(filename, maximum=5):
        """create at most {maximum} rotating files"""

        bare, ext = os.path.splitext(filename)
        for counter in reversed(range(2, maximum + 1)):
            old_filename = f"{bare}{counter-1}{ext}"
            new_filename = f"{bare}{counter}{ext}"
            if os.path.exists(old_filename):
                os.rename(old_filename, new_filename)
        if os.path.exists(filename):
            os.rename(filename, f"{bare}1{ext}")

    def get_tentative_ident(biblio):  # TODO: import from elsewhere? 2021-07-09
        info(biblio)
        return td.get_ident(
            {
                "author": td.parse_names(biblio["author"]),
                "title": biblio["title"],
                # 'date': biblio['date'][0:4],
                "date": Date(
                    year=biblio["date"][0:4],
                    month=None,
                    day=None,
                    circa=None,
                    time=None,
                ),
                "_mm_file": "CONSOLE",
            },
            {},
        )

    def edit_annotation(initial_text, resume_edit=False):
        """Write initial bib info to a tmp file, edit and return"""

        annotation_fn = f"{config.TMP_DIR}b-annotation.txt"
        if not resume_edit:
            rotate_files(annotation_fn)
            if os.path.exists(annotation_fn):
                os.remove(annotation_fn)
            with open(annotation_fn, "w", encoding="utf-8") as annotation_file:
                annotation_file.write(initial_text)
        call([config.EDITOR, annotation_fn])
        return open(annotation_fn, encoding="utf-8").readlines()

    def parse_bib(args, biblio, edited_text):
        """Parse the bib assignments"""

        # biblio['tags'] and whether to yasn publish are overwritten by
        # pre-populated and then edited console annotation
        biblio["tags"] = ""
        do_publish = False
        from_Instapaper = False  # are following lines Instapaper markdown?
        console_annotations = ""
        biblio["comment"] = ""

        print("@%s\n" % (tentative_id))
        EQUAL_PAT = re.compile(r"(\w{1,3})=")
        for line in edited_text:
            info(f"{line=}")
            line = line.replace("\u200b", "")  # Instapaper export artifact
            line = line.strip()
            if line == "":
                continue
            if line.startswith("# ["):
                from_Instapaper = True
                info(f"{from_Instapaper=}")
                continue
            if line == "-p":
                do_publish = True
                warning(f"{do_publish=}")
            elif line.startswith("s."):
                biblio["comment"] = line[2:].strip()
                info(f"{biblio['comment']=}")
            elif "=" in line[0:3]:  # citation only if near start of line
                cites = EQUAL_PAT.split(line)[1:]
                # 2 refs to an iterable are '*' unpacked and rezipped
                cite_pairs = list(zip(*[iter(cites)] * 2, strict=True))
                info(f"{cite_pairs=}")
                for short, value in cite_pairs:
                    info(f"{bf.BIB_SHORTCUTS=}")
                    info(f"{bf.BIB_TYPES=}")
                    info(f"short,value = {short},{value}")
                    # if short == "t":  # 't=phdthesis'
                    # biblio[bf.BIB_SHORTCUTS[value]] = biblio["c_web"]
                    if short == "kw":  # 'kw=complicity
                        biblio["tags"] += " " + value.strip()
                    else:
                        biblio[bf.BIB_SHORTCUTS[short]] = value.strip()
            else:
                if from_Instapaper:
                    if line.startswith(">"):
                        line = line[1:]  # remove redundant quote mark
                    elif line.startswith("-"):
                        pass  # leave comments alone
                    else:
                        line = ", " + line  # prepend paraphrase mark
                console_annotations += "\n\n" + line.strip()

        info("biblio.get('excerpt', '') = '%s'" % (biblio.get("excerpt", "")))
        info(f"console_annotations = '{console_annotations}'")
        biblio["excerpt"] = biblio.get("excerpt", "") + console_annotations

        # See if there is a container/bf.CSL_SHORTCUTS redundant with 'c_web'
        if (
            "c_web" in biblio
            and len([biblio[c] for c in list(bf.CSL_SHORTCUTS.values()) if c in biblio])
            > 1
        ):
            del biblio["c_web"]
        return biblio, do_publish

    # code of do_console_annotation
    info(f"{biblio['author']=}")
    tentative_id = get_tentative_ident(biblio)
    initial_text = [f"d={biblio['date']} au={biblio['author']} ti={biblio['title']}"]
    for key in biblio:
        if key.startswith("c_"):
            initial_text.append(f"{bf.CSL_FIELDS[key]}={title_case(biblio[key])}")
        if key == "tags" and biblio["tags"]:
            tags = " ".join(
                [
                    "kw=" + KEY_SHORTCUTS.get(tag, tag)
                    for tag in biblio["tags"].strip().split(" ")
                ]
            )
            initial_text.append(tags)
    if args.publish:
        warning("appending -p to text")
        initial_text.append("-p")
    if "comment" in biblio and biblio["comment"].strip():
        initial_text.append("s. " + biblio["comment"])
    initial_text = "\n".join(initial_text) + "\n"
    edited_text = edit_annotation(initial_text)
    try:
        biblio, do_publish = parse_bib(args, biblio, edited_text)
    except (TypeError, KeyError) as e:
        print("Error parsing biblio assignments: %s\nTry again." % e)
        time.sleep(2)
        edited_text = edit_annotation("", resume_edit=True)
        biblio, do_publish = parse_bib(args, biblio, edited_text)

    tweaked_id = get_tentative_ident(biblio)
    if tweaked_id != tentative_id:
        print(("logged: %s to" % get_tentative_ident(biblio)), end="\n")
    return biblio, do_publish
