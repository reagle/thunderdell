"""
Keyword shortcuts for BusySponge.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"

# General
GENERAL_KEY_SHORTCUTS = {
    "aca": "academia",
    "add": "addiction",
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
    "ora": "oratory",
    "nor": "norms",
    "pat": "patience",
    "pyt": "python",
    "pow": "power",
    "pra": "praxis",
    "pri": "privacy",
    "psy": "psychology",
    "red": "reddit",
    "ske": "skepticism",
    "spe": "speech",
    "str": "structure",
    "tea": "teaching",
    "tec": "technology",
    "tro": "troll",
}


# Advice
ADVICE_KEY_SHORTCUTS = {
    "adv": "advice",
    "aut": "authority",  # normative: who deserves to have power
    "con": "controversy",
    "eff": "efficacy",
    "exp": "expertise",  # descriptive: best process for knowing
    "hea": "health",
    "hoa": "hoax",
    "mot": "motivation",
    "rel": "relationship",
    "zei": "zeitgeist",  # recognition in culture
}


# Tech Prediction, Vision, and Utopia
TV_KEY_SHORTCUTS = {
    "dis": "disappointed",
    "nai": "naive",
    "opt": "optimistic",
    "pes": "pessimistic",
    "pre": "prediction",
    "sv": "siliconvalley",
    "uto": "utopia",
}

# Geek Feminism
GF_KEY_SHORTCUTS = {
    "fem": "feminism",
    "gen": "gender",
    "gf": "gfem",
    "sex": "sexism",
    "mer": "meritocracy",
    "prv": "privilege",
}

# Life-hacking
LH_KEY_SHORTCUTS = {
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

# Comments
RTC_KEY_SHORTCUTS = {
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

# Wikipedia
WP_KEY_SHORTCUTS = {
    "alt": "alternative",
    "ana": "analysis",
    "apo": "apologize",
    "att": "attack",
    "bia": "bias",
    "blo": "block",
    "cab": "cabal",
    "col": "collaboration",
    "cit": "citation",
    "coi": "COI",
    "dep": "deployment",
    "ecc": "eccentric",
    "fai": "faith",
    "fru": "frustration",
    "gov": "governance",
    "not": "notability",
    "par": "participation",
    "phi": "philosophy",
    "pol": "policy",
    "ver": "verifiability",
    "wp": "wikipedia",
}

LIST_OF_KEYSHORTCUTS = (
    GENERAL_KEY_SHORTCUTS,
    ADVICE_KEY_SHORTCUTS,
    GF_KEY_SHORTCUTS,
    RTC_KEY_SHORTCUTS,
    WP_KEY_SHORTCUTS,
    LH_KEY_SHORTCUTS,
    TV_KEY_SHORTCUTS,
)

KEY_SHORTCUTS = LIST_OF_KEYSHORTCUTS[0].copy()
for short_dict in LIST_OF_KEYSHORTCUTS[1:]:
    KEY_SHORTCUTS.update(short_dict)
