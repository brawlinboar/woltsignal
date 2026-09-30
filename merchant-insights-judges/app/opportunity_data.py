"""Mart access for the opportunity engine.

Isolated from `opportunity.py` on purpose: the engine is pure pandas and can
be unit-tested with hand-built frames, while everything that knows about
parquet marts and Streamlit caching lives here.

Reads four marts built by `pipeline/build_marts.py`:

* `opportunity_market`   (postal, category_group, channel, origin, card_group)
* `opportunity_merchant` (+ merchant) -- the merchant's own rows
* `opportunity_delivery` (postal, category_group, merchant, platform)
* `opportunity_overlap`  (postal, category_group, merchant, other) -- shared
  customers between two merchants in the same cell, the evidence for whether a
  similar-looking descriptor is the merchant's own till or just a neighbour

All of them degrade when the marts are absent, so the app still runs against an
older `data/marts` build -- the Action Plan simply shows no opportunity column
rather than erroring, and the descriptor picker falls back to an unranked list.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from lib import q

CELL_COLS = ["channel", "origin", "card_group", "txns", "value"]


@st.cache_data(show_spinner=False)
def _has(mart: str) -> bool:
    try:
        q(f"SELECT 1 FROM {mart} LIMIT 1")
        return True
    except Exception:
        # The mart is not in this build of data/marts. Treated as "no sizing
        # available" rather than an error: the rest of the page is unaffected.
        return False


def _empty_cells() -> pd.DataFrame:
    return pd.DataFrame(columns=CELL_COLS)


@st.cache_data(show_spinner=False)
def market_cells(postal: str, category: str) -> pd.DataFrame:
    """Denominator: every merchant in this postal code and category."""

    if not postal or not category or not _has("opportunity_market"):
        return _empty_cells()
    return q("""SELECT channel, origin, card_group, SUM(txns) AS txns, SUM(value) AS value
                FROM opportunity_market
                WHERE postal = ? AND category_group = ?
                GROUP BY 1, 2, 3""", (postal, category))


@st.cache_data(show_spinner=False)
def merchant_cells(postal: str, category: str, merchants: tuple[str, ...]) -> pd.DataFrame:
    """Numerator: this merchant's own rows.

    `merchants` is a tuple because one physical site can appear under several
    merchant descriptors -- a second terminal, a concession counter, a renamed
    acquirer record. Passing them all in is what stops a store's own second
    descriptor being counted as a competitor, which understates its share.

    The error runs both ways, and the wrong direction is the easy one. Omitting
    a genuine second descriptor understates share; merging in a NEIGHBOUR
    overstates it. On the Krakow worked example a plausible-looking second
    McDonald's descriptor was merged on the strength of a matching postcode and
    city, and put share at 77.2% when the defensible figure was 69.3%. Customer
    overlap later showed it was an ordinary mall neighbour. Prefer the evidence
    in `sibling_descriptors` over a name that looks right.
    """

    if not merchants or not postal or not category or not _has("opportunity_merchant"):
        return _empty_cells()
    holes = ", ".join("?" for _ in merchants)
    return q(f"""SELECT channel, origin, card_group, SUM(txns) AS txns, SUM(value) AS value
                 FROM opportunity_merchant
                 WHERE postal = ? AND category_group = ? AND merchant IN ({holes})
                 GROUP BY 1, 2, 3""", (postal, category, *merchants))


@st.cache_data(show_spinner=False)
def sibling_descriptors(postal: str, category: str, merchant: str) -> pd.DataFrame:
    """Other merchant names in the same postal code and category.

    Candidates for "this is also me" (second terminal) and for "this is not
    actually on site" (a chain's outlets registered to one head-office
    postcode). Neither is decidable from name, postcode or category -- a
    chain's central registration looks identical to a genuine neighbour -- so
    the merchant always makes the final call. On the Krakow example, six
    outlets named for other districts sat in one postcode and inflated the
    denominator by 16%.

    What the data CAN supply is evidence. When `opportunity_overlap` is in the
    build, each candidate carries `overlap_pct` (the share of its own customers
    who are also this merchant's), a `colocation` verdict and the
    `peer_typical_pct` baseline for the postcode -- see `_flag_colocation`.
    Without that mart the frame degrades to the bare (merchant, txns, value)
    list and the merchant is back to guessing from names.
    """

    if not postal or not category or not _has("opportunity_merchant"):
        return pd.DataFrame(columns=["merchant", "txns", "value"])
    sibs = q("""SELECT merchant, SUM(txns) AS txns, SUM(value) AS value
                FROM opportunity_merchant
                WHERE postal = ? AND category_group = ? AND merchant <> ?
                GROUP BY 1 ORDER BY value DESC""", (postal, category, merchant))
    if sibs.empty or not _has("opportunity_overlap"):
        return sibs
    return _flag_colocation(sibs, postal, category, merchant)


# How far above the rest of the field a candidate's customer overlap must sit
# before it is worth flagging as "probably your own till". Calibrated on the
# Krakow worked example, where the runner-up was a genuinely different
# restaurant in the same mall: see _flag_colocation.
COLOCATION_OUTLIER_RATIO = 1.5


def _flag_colocation(sibs: pd.DataFrame, postal: str, category: str, merchant: str) -> pd.DataFrame:
    """Add customer-overlap evidence and a co-location verdict to each candidate.

    `overlap_pct` is the share of the CANDIDATE's own customers who are also
    this merchant's customers. Two tills in one restaurant share nearly every
    customer; two shops in one mall share only the people who visit both; an
    outlet registered here but trading elsewhere in the city shares very few.

    The verdict deliberately compares a candidate against *the rest of the
    field* rather than a fixed cut-off, because the co-tenant baseline is a
    property of the location: in a busy mall every neighbour overlaps heavily,
    in a quiet street none do. A candidate is only called out as the merchant's
    own site when it stands clear of the best genuine neighbour by
    COLOCATION_OUTLIER_RATIO.

    That test is what the worked example needed. `McDonalds 61600303` had the
    highest overlap of any candidate (44.8%) and was assumed to be a second
    till -- but the next highest, a Burger King in the same mall, sat at 43.6%.
    Being top of the field meant nothing; it was an ordinary neighbour, and
    merging it overstated the store's share by 8 points. A median-based or
    rank-based rule would have confirmed the error. This one reports
    "indistinguishable".
    """

    ov = q("""SELECT other AS merchant, shared_cards, other_cards
              FROM opportunity_overlap
              WHERE postal = ? AND category_group = ? AND merchant = ?""",
           (postal, category, merchant))
    if ov.empty:
        return sibs

    s = sibs.merge(ov, on="merchant", how="left")
    s["overlap_pct"] = (s.shared_cards / s.other_cards.replace(0, pd.NA) * 100)

    known = s.overlap_pct.dropna()
    # The field a candidate is judged against is every OTHER candidate, so the
    # top one is compared with the runner-up rather than with itself.
    ranked = known.sort_values(ascending=False)
    runner_up = float(ranked.iloc[1]) if len(ranked) > 1 else 0.0
    typical = float(known.median()) if not known.empty else 0.0

    def verdict(pct: float) -> str:
        if pd.isna(pct):
            return "no shared-customer data"
        if pct >= max(runner_up, 1e-9) * COLOCATION_OUTLIER_RATIO and pct > typical:
            return "probably also you — stands clear of the field"
        if pct < typical / 2:
            return "probably not at this location"
        return "indistinguishable from a neighbour — your call"

    s["colocation"] = s.overlap_pct.map(verdict)
    s["peer_typical_pct"] = typical
    return s.sort_values("overlap_pct", ascending=False, na_position="last")


@st.cache_data(show_spinner=False)
def delivery_pool(postal: str, category: str, merchants: tuple[str, ...]) -> float:
    """Total Polish aggregator spend by this merchant's own customers.

    Glovo / Wolt / Pyszne.pl only. Uber Eats, Deliveroo and Bolt Food are
    excluded upstream in the pipeline: all three have zero Polish-merchant
    transactions in this dataset, so their rows are Polish cardholders
    ordering abroad -- foreign travel spend, not addressable local demand.
    """

    if not merchants or not _has("opportunity_delivery"):
        return 0.0
    holes = ", ".join("?" for _ in merchants)
    d = q(f"""SELECT SUM(value) AS pool FROM opportunity_delivery
              WHERE postal = ? AND category_group = ? AND merchant IN ({holes})""",
          (postal, category, *merchants))
    return float(d.pool.iloc[0] or 0.0) if not d.empty else 0.0


@st.cache_data(show_spinner=False)
def delivery_breakdown(postal: str, category: str, merchants: tuple[str, ...]) -> pd.DataFrame:
    if not merchants or not _has("opportunity_delivery"):
        return pd.DataFrame(columns=["platform", "txns", "cards", "value"])
    holes = ", ".join("?" for _ in merchants)
    return q(f"""SELECT platform, SUM(txns) AS txns, SUM(cards) AS cards, SUM(value) AS value
                 FROM opportunity_delivery
                 WHERE postal = ? AND category_group = ? AND merchant IN ({holes})
                 GROUP BY 1 ORDER BY value DESC""", (postal, category, *merchants))


@st.cache_data(show_spinner=False)
def leaked_pool(postal: str, category: str) -> float:
    """Resident spend in this category captured outside the area or online.

    Reuses the existing `demand` mart rather than adding one: it already
    carries value_elsewhere_pl and value_online per (geo_level, geo,
    category_group).
    """

    if not postal or not category:
        return 0.0
    try:
        d = q("""SELECT value_elsewhere_pl, value_online FROM demand
                 WHERE geo_level = 'postal' AND geo = ? AND category_group = ? AND month = 0""",
              (postal, category))
    except Exception:
        return 0.0
    if d.empty:
        return 0.0
    row = d.iloc[0]
    return float((row.value_elsewhere_pl or 0) + (row.value_online or 0))
