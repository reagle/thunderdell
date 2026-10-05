#!/usr/bin/env python3
#
# This file is part of Thunderdell/BusySponge
# <https://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2023 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>

"""Every declared entry type maps to a valid type in each emitter."""

import pytest

from thunderdell.biblio.fields import BIBLATEX_TYPES, CSL_TYPES
from thunderdell.formats.emit.biblatex import guess_biblatex_type
from thunderdell.formats.emit.yaml_csl import guess_csl_type
from thunderdell.types_thunderdell import EntryDict


@pytest.mark.parametrize("e_t", sorted(BIBLATEX_TYPES | CSL_TYPES))
def test_csl_type(e_t):
    """YAML/JSON CSL output gets a real CSL type."""
    csl_type = guess_csl_type(EntryDict(entry_type=e_t))[0]
    assert csl_type in CSL_TYPES


@pytest.mark.parametrize("e_t", sorted(BIBLATEX_TYPES | CSL_TYPES))
def test_biblatex_type(e_t):
    """Biblatex output gets a type rather than a KeyError."""
    assert guess_biblatex_type(EntryDict(entry_type=e_t))


def test_misc_is_not_legal_case():
    """The old inverted map sent misc to legal_case, which drops the author."""
    assert guess_csl_type(EntryDict(entry_type="misc"))[0] != "legal_case"
    assert guess_csl_type(EntryDict(entry_type="incollection"))[0] == "chapter"
