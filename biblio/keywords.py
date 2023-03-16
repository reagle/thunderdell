#!/usr/bin/env python3
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2023 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#

"""
Keyword shortcuts for BusySponge.

https://github.com/reagle/thunderdell
"""

# Expansions for common tags/activities

GENERAL_KEY_SHORTCUTS = {
    "aca": "academia",
    "add": "addiction",
    "adv": "advice",
    "edu": "education",
    "eth": "ethics",
    "exi": "exit",
    "for": "fork",
    "gra": "gratitude",
    "his": "history",
    "hum": "humor",
    "ide": "identity",
    "ics": "politics",
    "lea": "leadership",
    "leg": "legal",
    "lit": "literacy",
    "ope": "open",
    "mon": "money",
    "nor": "norms",
    "pat": "patience",
    "pyt": "python",
    "pow": "power",
    "pra": "praxis",
    "pri": "privacy",
    "psy": "psychology",
    "red": "reddit",
    "rel": "relationship",
    "ske": "skepticism",
    "spe": "speech",
    "str": "structure",
    "tea": "teaching",
    "tec": "technology",
    "tro": "troll",
    "zei": "zeitgeist",
}

TV_KEY_SHORTCUTS = {
    # Tech Prediction, Vision, and Utopia
    "dis": "disappointed",
    "nai": "naive",
    "opt": "optimistic",
    "pes": "pessimistic",
    "pre": "prediction",
    "sv": "siliconvalley",
    "uto": "utopia",
}

GF_KEY_SHORTCUTS = {
    # Geek Feminism
    "fem": "feminism",
    "gen": "gender",
    "gf": "gfem",
    "sex": "sexism",
    "mer": "meritocracy",
    "prv": "privilege",
}

LH_KEY_SHORTCUTS = {
    # Lifehack
    "com": "complicity",
    "lh": "lifehack",
    "pro": "productivity",
    "qs": "quantifiedself",
    "sh": "selfhelp",
    "too": "tool",
    "mea": "meaning",
    "min": "minimalism",
    "rati": "rational",
}

RTC_KEY_SHORTCUTS = {
    # Comments
    "ano": "anonymous",
    "ass": "assessment",
    "aut": "automated",
    "cri": "criticism",
    "est": "esteem",
    "fak": "fake",
    "fee": "feedback",
    "inf": "informed",
    "man": "manipulation",
    "mar": "market",
    "mod": "moderation",
    "off": "offensive",
    "qua": "quant",
    "ran": "ranking",
    "rat": "rating",
    "rev": "review",
    "sel": "self",
    "soc": "social",
    "pup": "puppet",
}

WP_KEY_SHORTCUTS = {
    # Wikipedia
    "alt": "alternative",
    "aut": "authority",
    "ana": "analysis",
    "apo": "apologize",
    "att": "attack",
    "bia": "bias",
    "blo": "block",
    "cab": "cabal",
    "col": "collaboration",
    "con": "consensus",
    "cit": "citation",
    "coi": "COI",
    "dep": "deployment",
    "ecc": "eccentric",
    "exp": "expertise",
    "fai": "faith",
    "fru": "frustration",
    "gov": "governance",
    "mot": "motivation",
    "not": "notability",
    "par": "participation",
    "phi": "philosophy",
    "pol": "policy",
    "ver": "verifiability",
    "wp": "wikipedia",
}

LIST_OF_KEYSHORTCUTS = (
    GENERAL_KEY_SHORTCUTS,
    GF_KEY_SHORTCUTS,
    RTC_KEY_SHORTCUTS,
    WP_KEY_SHORTCUTS,
    LH_KEY_SHORTCUTS,
    TV_KEY_SHORTCUTS,
)

KEY_SHORTCUTS = LIST_OF_KEYSHORTCUTS[0].copy()
for short_dict in LIST_OF_KEYSHORTCUTS[1:]:
    KEY_SHORTCUTS.update(short_dict)
