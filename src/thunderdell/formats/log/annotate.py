"""Console annotation logger complement.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"

import argparse
import logging
import re
import time
from collections import namedtuple
from pathlib import Path
from subprocess import call

from thunderdell import config, map2bib
from thunderdell.biblio import fields as bf
from thunderdell.biblio.keywords import KEY_SHORTCUTS
from thunderdell.change_case import title_case

NOW = time.localtime()


def do_console_annotation(args: argparse.Namespace, biblio):
    """Augment biblio with console annotations."""
    Date = namedtuple("Date", ["year", "month", "day", "circa", "time"])

    def rotate_files(filename: Path, maximum: int = 5):
        """Create at most {maximum} rotating files."""
        bare = filename.with_suffix("")
        ext = filename.suffix
        for counter in reversed(range(2, maximum + 1)):
            old_filename = bare.with_name(f"{bare.name}{counter - 1}{ext}")
            new_filename = bare.with_name(f"{bare.name}{counter}{ext}")
            if old_filename.exists():
                old_filename.rename(new_filename)
        if filename.exists():
            filename.rename(bare.with_name(f"{bare.name}1{ext}"))

    def get_tentative_ident(biblio):  # TODO: import from elsewhere? 2021-07-09
        logging.info(biblio)
        return map2bib.get_identifier(
            {
                "author": map2bib.parse_names(biblio["author"]),
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

    def edit_annotation(initial_text: str, resume_edit: bool = False):
        """Write initial bib info to a tmp file, edit and return."""
        annotation_fn = config.TMP_DIR / "b-annotation.txt"
        if not resume_edit:
            rotate_files(annotation_fn)
            if annotation_fn.exists():
                annotation_fn.unlink()
            annotation_fn.write_text(initial_text, encoding="utf-8")
        call([config.EDITOR, str(annotation_fn)])
        return annotation_fn.read_text(encoding="utf-8").splitlines()

    def parse_bib(args, biblio, edited_text):
        """Parse the bib assignments."""
        # biblio['tags'] and whether to yasn publish are overwritten by
        # pre-populated and then edited console annotation
        biblio["tags"] = ""
        do_publish = False
        from_Instapaper = False  # are following lines Instapaper markdown?
        console_annotations = ""
        biblio["comment"] = ""

        print(f"@{tentative_id}\n")
        EQUAL_PAT = re.compile(r"(\w{1,3})=")
        for line in edited_text:
            logging.info(f"{line=}")
            line = line.replace("\u200b", "")  # Instapaper export artifact
            line = line.strip()
            if line == "":
                continue
            if line.startswith("# ["):
                from_Instapaper = True
                logging.info(f"{from_Instapaper=}")
                continue
            if line == "-p":
                do_publish = True
                logging.warning(f"{do_publish=}")
            elif line.startswith("s."):
                biblio["comment"] = line[2:].strip()
                logging.info(f"{biblio['comment']=}")
            elif "=" in line[0:3]:  # citation only if near start of line
                cites = EQUAL_PAT.split(line)[1:]
                # 2 refs to an iterable are '*' unpacked and rezipped
                cite_pairs = list(zip(*[iter(cites)] * 2, strict=True))
                logging.info(f"{cite_pairs=}")
                for short, value in cite_pairs:
                    logging.info(f"{bf.BIB_SHORTCUTS=}")
                    logging.info(f"{bf.BIB_TYPES=}")
                    logging.info(f"short,value = {short},{value}")
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

        logging.info(
            "biblio.get('excerpt', '') = '{}'".format(biblio.get("excerpt", ""))
        )
        logging.info(f"console_annotations = '{console_annotations}'")
        if console_annotations.strip():  # don't bother with default excerpt
            biblio["excerpt"] = console_annotations

        # See if there is a container/bf.CSL_SHORTCUTS redundant with 'c_web'
        if (
            "c_web" in biblio
            and len([biblio[c] for c in list(bf.CSL_SHORTCUTS.values()) if c in biblio])
            > 1
        ):
            del biblio["c_web"]
        return biblio, do_publish

    # Setup initial id and bibliographic information including keywords
    logging.info(f"{biblio['author']=}")
    tentative_id = get_tentative_ident(biblio)
    initial_text = [f"d={biblio['date']} au={biblio['author']} ti={biblio['title']}"]
    for key in biblio:
        if key.startswith("c_"):
            initial_text.append(f"{bf.CSL_FIELDS[key]}={title_case(biblio[key])}")
        if key == "tags" and biblio["tags"]:
            tags = " ".join(
                [
                    f"kw={KEY_SHORTCUTS.get(tag, tag) or tag}"  # Using or to prevent None
                    for tag in biblio["tags"].strip().split(" ")
                ]
            )
            initial_text.append(tags)
    if args.publish:
        logging.warning("appending -p to text")
        initial_text.append("-p")
    if "comment" in biblio and biblio["comment"].strip():
        initial_text.append("s. " + biblio["comment"])
    initial_text = "\n".join(initial_text) + "\n"
    edited_text = edit_annotation(initial_text)
    try:
        biblio, do_publish = parse_bib(args, biblio, edited_text)
    except (TypeError, KeyError) as e:
        print(f"Error parsing biblio assignments: {e}\nTry again.")
        time.sleep(2)
        edited_text = edit_annotation("", resume_edit=True)
        biblio, do_publish = parse_bib(args, biblio, edited_text)

    tweaked_id = get_tentative_ident(biblio)
    if tweaked_id != tentative_id:
        print((f"logged: {get_tentative_ident(biblio)} to"), end="\n")
    return biblio, do_publish
