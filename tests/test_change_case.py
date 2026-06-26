#!/usr/bin/env python3
#
# This file is part of Thunderdell/BusySponge
# <https://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2023 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>

"""Run tests against golden YAML results; useful for detecting inadvertent changes."""

from thunderdell.change_case import change_case, change_case_markdown

CASES = """
1My Defamation 2.0 Experience: A Story of Wikipedia and a Boy
1My defamation 2.0 experience: A story of Wikipedia and a boy
2My defamation 2.0 experience: a story of Wikipedia and a boy
2My defamation 2.0 experience: A story of Wikipedia and a boy
Broadband makes women and Aaron happy
Broadband makes women and Aaron happy
Broadband Makes Women and Aaron Happy
Broadband makes women and Aaron happy
Tax Example Explains the Value of Hosted Software to Business
Tax example explains the value of hosted software to business
PS3 shipments pass 35 million units worldwide
PS3 shipments pass 35 million units worldwide
New Theorem Proved by Poincaré
New theorem proved by Poincaré
Wikipedia goes 3D
Wikipedia goes 3D
Wikipedia trumps Britannica
Wikipedia trumps Britannica
Wikirage: What's hot now on Wikipedia
Wikirage: What's hot now on Wikipedia
Glycogen: A Trojan Horse for Neurons
Glycogen: A Trojan horse for neurons
Characterization of the SKN7 Ortholog of Aspergillus Fumigatus
Characterization of the SKN7 Ortholog of Aspergillus Fumigatus
Wikipedia:Attribution
Wikipedia:Attribution
Why Do People Write for Wikipedia? Incentives to Contribute
Why do people write for Wikipedia? Incentives to contribute
<span class="pplri7t-x-x-120">Wikipedia:WikiLove</span>
<span class="pplri7t-x-x-120">Wikipedia:WikiLove</span>
The Altruism Question: Toward a Social-Psychological Answer
The altruism question: Toward a social-psychological answer
Human Services:  Cambridge War Memorial Recreation Center
Human services: Cambridge war memorial recreation center
Career Advice:     Stop Admitting Ph.D. Students - Inside Higher Ed
Career advice: Stop admitting Ph.D. Students - inside higher Ed
THIS SENTENCE ABOUT AOL IN AMERICA IS ALL CAPS
This sentence about AOL in America is all caps
Lessons I learned on the road as a Digital Nomad
Lessons I learned on the road as a digital nomad
r/AmItheButtface
r/AmItheButtface
""".strip().split("\n")


def test_change_case():
    """Tests chage_case variations."""
    for test, expect in zip(CASES[::2], CASES[1::2], strict=True):
        result = change_case(test)
        assert result == expect


# (case_direction, input, expected) triples exercising markup preservation.
MARKDOWN_CASES = [
    # links: visible text cased, URL frozen
    ("title", "[cooperation needs attention](http://X)",
     "[Cooperation Needs Attention](http://X)"),
    ("sentence", "[Cooperation Needs Attention](http://X)",
     "[Cooperation needs attention](http://X)"),
    # citations are opaque
    ("sentence", "Are you tech savvy? [@Sidibe2015mat]",
     "Are you tech savvy? [@Sidibe2015mat]"),
    # pandoc attribute block on a heading; ATX marker preserved
    ("title", "## cooperation needs attention {.img_left}",
     "## Cooperation Needs Attention {.img_left}"),
    ("sentence", "## Cooperation Needs Attention {.img_left}",
     "## Cooperation needs attention {.img_left}"),
    # emphasis delimiters frozen, content cased; BORING word stays lowercase
    ("title", "the *best* idea in here", "The *Best* Idea in Here"),
    # inline code is opaque
    ("title", "using `code` here", "Using `code` Here"),
]


def test_change_case_markdown():
    """Tests markdown-aware case conversion leaves markup intact."""
    for direction, test, expect in MARKDOWN_CASES:
        assert change_case_markdown(test, direction) == expect


if __name__ == "__main__":
    test_change_case()
    test_change_case_markdown()
