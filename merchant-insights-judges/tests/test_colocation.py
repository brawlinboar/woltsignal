"""Regression tests for the co-location verdict in `app/opportunity_data.py`.

These exist because of a specific, expensive mistake. The worked example merged
`McDonalds 61600303` into `MCDONALDS 303 KRAKOW 01` as one physical site on the
strength of a matching postcode, city and category, and reported the store's
share as 77.2%. Customer overlap later showed the descriptor was an ordinary
neighbour in the same shopping centre, and the defensible share was 69.3% -- an
8-point error in the headline figure of the whole readout.

The trap is that the descriptor had the HIGHEST customer overlap of any
candidate in the postcode (44.8%). Any rule that trusts the top of the ranking,
or compares against a median, confirms the wrong answer. The runner-up was a
Burger King in the same mall at 43.6%: indistinguishable. So the verdict must
compare a candidate against the rest of the field and stay silent when it does
not stand clear of it.

Not collected by the repo's default pytest run (`testpaths = ["tests"]` covers
the signalkit suite only). Run explicitly:

    python3 -m pytest merchant-insights/tests/test_colocation.py
"""

from __future__ import annotations

import sys
import types

import pandas as pd
import pytest


def _stub_streamlit() -> None:
    """Install a minimal Streamlit stand-in.

    `_flag_colocation` is pure pandas, but its module imports Streamlit for the
    caching decorators. Stubbing them keeps this test runnable without the
    Streamlit runtime, which is not a dependency of the logic under test.
    """

    if "streamlit" in sys.modules and hasattr(sys.modules["streamlit"], "cache_data"):
        return

    def passthrough(*args, **kwargs):
        if args and callable(args[0]):
            return args[0]
        return lambda fn: fn

    st = types.ModuleType("streamlit")
    st.cache_data = passthrough
    st.cache_resource = passthrough
    errors = types.ModuleType("streamlit.errors")
    errors.StreamlitPageNotFoundError = type("StreamlitPageNotFoundError", (Exception,), {})
    st.errors = errors
    sys.modules["streamlit"] = st
    sys.modules["streamlit.errors"] = errors


@pytest.fixture
def od():
    """The module under test, with Streamlit stubbed and `q` left injectable."""

    _stub_streamlit()
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "app"))
    import opportunity_data

    return opportunity_data


# Measured overlap in postal code 30-644 against `MCDONALDS 303 KRAKOW 01`:
# (descriptor, cards shared with the store, the descriptor's own card count).
# 30-644 is the Bonarka shopping centre, so the mall co-tenants sit high and the
# Starbucks outlets that are merely REGISTERED here sit low.
BONARKA = [
    ("McDonalds 61600303", 168, 375),        # 44.8% - the merge this test guards against
    ("PL BK KRAKOW BONARKA", 58, 133),       # 43.6% - a different restaurant, same mall
    ("BONARKA KRAKOW", 30, 79),              # 38.0%
    ("PL PH KRAKOW BONARKA", 12, 38),        # 31.6%
    ("P041 BONARKA", 98, 313),               # 31.3%
    ("PL SBX KRAKOW BONARKA", 76, 258),      # 29.5% - genuinely in this mall
    ("LODZIARNIE FIRMOWE", 114, 483),        # 23.6%
    ("PL SBX KRAKOW KRUPNICZA", 16, 122),    # 13.1% - off-site
    ("PL SBX KRAKOW SERENADA", 15, 158),     #  9.5% - off-site
    ("PL SBX Krakow Galeri 01", 15, 162),    #  9.3% - off-site
    ("PL SBX KRAKOW RYNEK", 28, 303),        #  9.2% - off-site
    ("PL SBX KRAKOW FLORIANSK", 16, 187),    #  8.6% - off-site
    ("PL SBX KRAKOW GALERIA K", 20, 285),    #  7.0% - off-site
]


def _run(od, rows):
    overlap = pd.DataFrame(rows, columns=["merchant", "shared_cards", "other_cards"])
    od.q = lambda sql, params=None: overlap.copy()
    siblings = pd.DataFrame({"merchant": overlap.merchant, "txns": 0, "value": 0.0})
    return od._flag_colocation(siblings, "30-644", "FAST FOOD RESTAURANTS",
                               "MCDONALDS 303 KRAKOW 01")


def test_top_of_the_field_is_not_treated_as_the_merchants_own_site(od):
    """The exact error that produced the 8-point overstatement.

    Highest overlap in the postcode, but only 1.2x the runner-up. Being top of
    the ranking is not evidence of anything.
    """

    out = _run(od, BONARKA)
    verdict = out.set_index("merchant").colocation["McDonalds 61600303"]
    assert "indistinguishable" in verdict


def test_a_genuine_second_till_is_still_flagged(od):
    """Guards the opposite failure: a rule so cautious it never helps anyone.

    Two tills in one restaurant share nearly every customer, which puts the
    candidate far clear of the best neighbour.
    """

    rows = [(m, 340, 375) if m == "McDonalds 61600303" else (m, s, c) for m, s, c in BONARKA]
    out = _run(od, rows)
    verdict = out.set_index("merchant").colocation["McDonalds 61600303"]
    assert "probably also you" in verdict


def test_off_site_registrations_are_called_out(od):
    """The six Starbucks registered here but trading elsewhere in Kraków.

    Their low overlap is independent confirmation that excluding them from the
    market denominator was correct. Five of the six fall below the "not at this
    location" line; KRUPNICZA at 13.1% sits just above it and reads as a
    neighbour, so the boundary is deliberately soft and the merchant decides.
    """

    out = _run(od, BONARKA).set_index("merchant")
    off_site = ["PL SBX KRAKOW SERENADA", "PL SBX Krakow Galeri 01", "PL SBX KRAKOW RYNEK",
                "PL SBX KRAKOW FLORIANSK", "PL SBX KRAKOW GALERIA K"]
    for name in off_site:
        assert "probably not at this location" in out.colocation[name], name


def test_overlap_is_measured_against_the_candidates_own_customers(od):
    """`overlap_pct` must be the candidate's share, not the merchant's.

    The store has thousands of customers and a candidate may have a few
    hundred; dividing by the wrong side makes every candidate look unrelated.
    """

    out = _run(od, BONARKA).set_index("merchant")
    assert out.overlap_pct["McDonalds 61600303"] == pytest.approx(168 / 375 * 100, abs=0.1)


def test_absent_overlap_mart_leaves_the_list_untouched(od):
    """With no overlap evidence the picker must degrade, not break.

    Older `data/marts` builds have no `opportunity_overlap`; the merchant then
    gets the plain list rather than an error.
    """

    od.q = lambda sql, params=None: pd.DataFrame(columns=["merchant", "shared_cards", "other_cards"])
    siblings = pd.DataFrame({"merchant": ["A", "B"], "txns": [1, 2], "value": [1.0, 2.0]})
    out = od._flag_colocation(siblings, "30-644", "FAST FOOD RESTAURANTS", "X")
    assert "colocation" not in out.columns
    assert list(out.merchant) == ["A", "B"]


def test_single_candidate_has_no_field_to_stand_clear_of(od):
    """One candidate and no runner-up.

    With nothing to compare against, a high overlap is the only signal there
    is, and it should still be usable rather than crashing on an empty field.
    """

    out = _run(od, [("Only One", 300, 320)])
    assert len(out) == 1
    assert isinstance(out.colocation.iloc[0], str)
