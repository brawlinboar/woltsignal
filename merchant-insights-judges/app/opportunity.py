"""Deduplicated opportunity sizing: how much a share gap is actually worth.

`diagnostics.py` says *what* to fix and scores it 0..1. This module says what
each fix is *worth*, in currency units, without double-counting.

The double-counting problem
---------------------------
Size an opportunity per segment -- by card type, by channel, by customer
origin, by hour -- and the figures cannot be summed. One contactless purchase
by a local premium cardholder at 11:00 appears in the channel figure, the
origin figure, the card-type figure and the hourly figure alike. Adding them
counts the same units up to four times.

The fix is a mutually exclusive partition. Every transaction is assigned to
exactly one cell of

    cell = (channel, origin, card_group)

so cell figures are additive by construction. 3 x 2 x 3 = 18 possible cells.

    cell_share = merchant value in cell / market value in cell
    benchmark  = max(cell_share) over cells with >= MIN_CELL_TXNS transactions
    cell_lift  = max(benchmark - cell_share, 0) * market value in cell
    TOTAL      = SUM(cell_lift) over sized cells            <- additive

Cells below MIN_CELL_TXNS are reported but never sized: their shares swing on
a handful of transactions. That is a deliberate cap on precision, not a hidden
opportunity.

The partition also *sharpens* the finding, because cells differing in one
dimension only are a controlled comparison. Worked example (a real Krakow
food-court store): the marginal channel gap was 12.7pt and could have been
customer mix. Comparing mobile/local/classic (81.9%) against
contactless/local/classic (62.1%) holds origin and card type constant and the
gap *widens* to 19.9pt -- ruling out mix.

Measured vs scenario
--------------------
Two kinds of opportunity, never mixed in one total:

* **Measured** -- visible in the transaction data. The merchant's share of a
  market it already competes in. `size_cells()`.
* **Scenario** -- requires an assumption the data cannot supply, because the
  merchant's current capture is unobservable. `scenarios()`. Delivery is the
  clear case: the aggregator is the merchant of record, so a Glovo transaction
  may *already be* this merchant's sale booked through Glovo. There is no
  column that distinguishes it. Such pools are therefore only ever expressed
  as "some % of <pool>", with the rate supplied by the user.

Units are the dataset's own currency. For the DATASPRINT hackathon data that
currency is FICTIONAL -- never convert it or present it as real money.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

# Cells below this transaction count are reported but not sized.
MIN_CELL_TXNS = 100

# Dimension value ordering, for stable display.
CHANNELS = ("mobile", "contactless", "other")
ORIGINS = ("local", "elsewhere")
CARD_GROUPS = ("classic", "premium", "other")

CELL_LABELS = {
    "channel": {"mobile": "Mobile pay", "contactless": "Contactless (card present)",
                "other": "Other channel"},
    "origin": {"local": "Local residents", "elsewhere": "From elsewhere"},
    "card_group": {"classic": "Standard cards", "premium": "Premium cards",
                   "other": "Commercial/other cards"},
}

# Which diagnostics topic a cell dimension maps onto, so a sized cell can be
# attached to the Finding the merchant already sees.
DIMENSION_TOPIC = {"channel": "Channels", "origin": "Tourism", "card_group": "Customer mix"}


def cell_label(row) -> str:
    return " · ".join([
        CELL_LABELS["channel"].get(row.channel, row.channel),
        CELL_LABELS["origin"].get(row.origin, row.origin),
        CELL_LABELS["card_group"].get(row.card_group, row.card_group),
    ])


@dataclass
class Sizing:
    """Result of sizing one merchant's share gap. All values in currency units."""

    market_value: float             # whole addressable market in scope
    merchant_value: float           # what the merchant already holds
    ceiling: float                  # market - merchant; exhaustive, additive
    overall_share: float            # merchant_value / market_value, percent
    best_cell_share: float          # benchmark, percent
    lift_to_best: float             # deduplicated total, additive
    lift_to_global: float           # conservative variant, additive
    cells: pd.DataFrame = field(repr=False)
    unsized_cells: int = 0
    unsized_value: float = 0.0

    @property
    def capture_rate(self) -> float:
        """Share of the ceiling that the deduplicated lift represents."""
        return 0.0 if self.ceiling <= 0 else self.lift_to_best / self.ceiling * 100


def size_cells(market: pd.DataFrame, merchant: pd.DataFrame) -> Sizing | None:
    """Deduplicated sizing from two pre-aggregated frames.

    `market` and `merchant` must both carry columns
    (channel, origin, card_group, txns, value). `market` is the denominator
    (all merchants in scope, the merchant included); `merchant` is this
    merchant's own rows.

    Returns None when there is no market to size against.
    """

    if market is None or market.empty:
        return None

    keys = ["channel", "origin", "card_group"]
    m = market.groupby(keys, as_index=False).agg(market_value=("value", "sum"),
                                                 market_txns=("txns", "sum"))
    if merchant is None or merchant.empty:
        own = pd.DataFrame(columns=keys + ["merchant_value", "merchant_txns"])
    else:
        own = merchant.groupby(keys, as_index=False).agg(merchant_value=("value", "sum"),
                                                         merchant_txns=("txns", "sum"))
    c = m.merge(own, on=keys, how="left").fillna({"merchant_value": 0.0, "merchant_txns": 0})

    # A merchant cannot hold more than the market. If it does, the two marts
    # disagree (different filters upstream) and sizing would be nonsense.
    c["merchant_value"] = c[["merchant_value", "market_value"]].min(axis=1)

    c["share"] = c.merchant_value / c.market_value.replace(0, pd.NA) * 100
    c["sized"] = c.market_txns >= MIN_CELL_TXNS

    market_value = float(c.market_value.sum())
    merchant_value = float(c.merchant_value.sum())
    overall = merchant_value / market_value * 100 if market_value else 0.0

    sized = c[c.sized & c.share.notna()]
    if sized.empty:
        # Nothing is dense enough to benchmark against; the ceiling is still
        # a fact, so return it with a zero lift rather than None.
        c["lift_to_best"] = 0.0
        c["lift_to_global"] = 0.0
        return Sizing(market_value, merchant_value, market_value - merchant_value,
                      overall, 0.0, 0.0, 0.0, c.assign(cell=c.apply(cell_label, axis=1)),
                      int((~c.sized).sum()), float(c.loc[~c.sized, "market_value"].sum()))

    best = float(sized.share.max())
    c["lift_to_best"] = ((best - c.share).clip(lower=0) / 100 * c.market_value).where(c.sized, 0.0)
    c["lift_to_global"] = ((overall - c.share).clip(lower=0) / 100 * c.market_value).where(c.sized, 0.0)
    c["cell"] = c.apply(cell_label, axis=1)

    return Sizing(
        market_value=market_value,
        merchant_value=merchant_value,
        ceiling=market_value - merchant_value,
        overall_share=overall,
        best_cell_share=best,
        lift_to_best=float(c.lift_to_best.sum()),
        lift_to_global=float(c.lift_to_global.sum()),
        cells=c.sort_values("lift_to_best", ascending=False),
        unsized_cells=int((~c.sized).sum()),
        unsized_value=float(c.loc[~c.sized, "market_value"].sum()),
    )


def controlled_comparisons(s: Sizing) -> pd.DataFrame:
    """Pairs of sized cells differing in exactly one dimension.

    This is what turns a correlation into evidence: if two cells share two
    coordinates and differ on the third, the share difference between them is
    attributable to that third dimension rather than to customer mix. Returned
    sorted by gap, largest first.
    """

    sized = s.cells[s.cells.sized & s.cells.share.notna()]
    keys = ["channel", "origin", "card_group"]
    rows = []
    recs = sized.to_dict("records")
    for i, a in enumerate(recs):
        for b in recs[i + 1:]:
            differing = [k for k in keys if a[k] != b[k]]
            if len(differing) != 1:
                continue
            dim = differing[0]
            hi, lo = (a, b) if a["share"] >= b["share"] else (b, a)
            rows.append({
                "dimension": dim,
                "topic": DIMENSION_TOPIC.get(dim, dim),
                "holding_constant": ", ".join(f"{k}={a[k]}" for k in keys if k != dim),
                "stronger": hi[dim], "stronger_share": hi["share"],
                "weaker": lo[dim], "weaker_share": lo["share"],
                "gap_pts": hi["share"] - lo["share"],
                "weaker_cell_value": lo["market_value"],
                "lift_if_closed": (hi["share"] - lo["share"]) / 100 * lo["market_value"],
            })
    if not rows:
        return pd.DataFrame(columns=["dimension", "gap_pts", "lift_if_closed"])
    return pd.DataFrame(rows).sort_values("gap_pts", ascending=False)


# --------------------------------------------------------------------------------------
# Scenarios -- pools whose current capture is unobservable
# --------------------------------------------------------------------------------------

@dataclass
class Scenario:
    key: str
    label: str
    pool: float                 # the size of the pool, in currency units
    pool_basis: str             # what the pool IS, in one sentence
    why_unmeasurable: str       # why a rate assumption is unavoidable
    default_rate: float         # a starting capture rate, percent
    max_rate: float = 50.0

    def value(self, rate_pct: float) -> float:
        return self.pool * rate_pct / 100


def scenarios(
    delivery_pool: float = 0.0,
    repeat_rate: float | None = None,
    peer_repeat_rate: float | None = None,
    merchant_value: float = 0.0,
    ticket: float | None = None,
    peer_ticket: float | None = None,
    leaked_pool: float = 0.0,
) -> list[Scenario]:
    """Build the scenario set from whatever inputs are available.

    Every scenario is expressed as "some % of a stated pool". None of these
    may be added to the measured `lift_to_best` -- they answer a different
    question and rest on an assumption the data cannot check.
    """

    out: list[Scenario] = []

    if delivery_pool > 0:
        out.append(Scenario(
            key="delivery",
            label="Food delivery",
            pool=delivery_pool,
            pool_basis=("Total spend by this merchant's own customers at Polish delivery "
                        "aggregators (Glovo, Wolt, Pyszne.pl), across all merchants, "
                        "for the whole period."),
            why_unmeasurable=(
                "The aggregator is the merchant of record, so an order placed through "
                "Glovo may ALREADY be this merchant's sale. Nothing in the data "
                "distinguishes it. Whatever the merchant already earns through "
                "aggregators must be netted off this pool from their own reporting. "
                "The pool also spans all restaurant types, not just this category."),
            default_rate=10.0,
        ))

    if repeat_rate is not None and peer_repeat_rate is not None and peer_repeat_rate > repeat_rate:
        # Pool = the merchant's own revenue; the lever is retaining more of it.
        out.append(Scenario(
            key="loyalty",
            label="Loyalty / retention",
            pool=merchant_value,
            pool_basis=(f"This merchant's own revenue. Repeat-customer rate is "
                        f"{repeat_rate:.0%} against {peer_repeat_rate:.0%} for local peers, "
                        f"a {peer_repeat_rate - repeat_rate:.0%} gap."),
            why_unmeasurable=(
                "Closing a retention gap does not translate to revenue at a fixed rate: "
                "the data shows the gap exists but not how much of it is addressable, "
                "nor whether peer retention reflects a better offer or a different "
                "customer base."),
            default_rate=min(round((peer_repeat_rate - repeat_rate) * 100, 1), 20.0),
        ))

    if ticket is not None and peer_ticket is not None and peer_ticket > ticket:
        gap = (peer_ticket / ticket - 1) * 100 if ticket else 0.0
        out.append(Scenario(
            key="basket",
            label="Average ticket",
            pool=merchant_value,
            pool_basis=(f"This merchant's own revenue. Average ticket is {ticket:,.0f} "
                        f"against {peer_ticket:,.0f} for local peers, "
                        f"a {gap:.0f}% shortfall."),
            why_unmeasurable=(
                "A peer-median ticket is not a target: it may reflect a different "
                "product mix, price point or daypart rather than an addressable gap. "
                "Raising price also risks volume, which this pool does not model."),
            default_rate=min(round(gap / 2, 1), 25.0),
        ))

    if leaked_pool > 0:
        out.append(Scenario(
            key="catchment",
            label="New location / catchment",
            pool=leaked_pool,
            pool_basis=("Spend by residents of this area, in this category, that is "
                        "captured by merchants OUTSIDE the area (or online)."),
            why_unmeasurable=(
                "Leaked spend is not addressable by the existing site -- capturing it "
                "implies a new location, and the causality is weak: residents may shop "
                "elsewhere because they work there, not for want of local supply. "
                "Treat as a location-planning prompt, not a revenue forecast."),
            default_rate=5.0,
            max_rate=25.0,
        ))

    return out


def scenario_table(scs: list[Scenario], rates: dict[str, float]) -> pd.DataFrame:
    return pd.DataFrame([{
        "Lever": s.label,
        "Pool": s.pool,
        "Assumed capture": f"{rates.get(s.key, s.default_rate):.1f}%",
        "Scenario value": s.value(rates.get(s.key, s.default_rate)),
        "Why an assumption is needed": s.why_unmeasurable,
    } for s in scs])


def summarise(s: Sizing | None, scs: list[Scenario], rates: dict[str, float]) -> dict[str, float]:
    """Headline numbers, keeping measured and scenario strictly separate."""

    measured = s.lift_to_best if s else 0.0
    scenario_total = sum(x.value(rates.get(x.key, x.default_rate)) for x in scs)
    return {
        "measured_dedup": measured,
        "measured_conservative": s.lift_to_global if s else 0.0,
        "ceiling": s.ceiling if s else 0.0,
        "scenario_total": scenario_total,
        # Deliberately NOT a sum of the two: they are different kinds of claim.
        # Reported side by side so the reader can see both without implying
        # one grand total.
    }


# --------------------------------------------------------------------------------------
# Attaching sized value to the rule-based findings
# --------------------------------------------------------------------------------------

def attach_opportunity(findings, s: Sizing | None) -> list:
    """Give each Finding a currency value where the cell partition can size it.

    Deliberately conservative about *which* findings get a number. A value is
    attached only when a controlled comparison isolates the same dimension the
    finding is about -- so the number is the value of closing a gap that was
    measured while holding the other two dimensions constant, not a marginal
    figure that could be customer mix.

    Findings on topics the partition does not cover (opening hours, loyalty,
    cross-sell, location) are left unsized rather than given a speculative
    number. They keep their score ordering. An unsized finding is not a
    lesser finding; it is one this mart cannot price.
    """

    if s is None:
        return findings

    cc = controlled_comparisons(s)
    if cc.empty:
        return findings

    # Best (largest) isolated gap per topic.
    by_topic = (cc.sort_values("lift_if_closed", ascending=False)
                  .drop_duplicates("topic").set_index("topic"))

    for f in findings:
        if f.topic in by_topic.index and f.value is None:
            f.value = float(by_topic.loc[f.topic, "lift_if_closed"])
    return findings


def unattributed(s: Sizing | None, findings) -> float:
    """Deduplicated total minus what was attached to findings.

    Keeps the arithmetic honest: if the cells say 18,431 and only 11,000 was
    attributable to a named finding, the remainder is real but unexplained,
    and saying so is better than inflating a finding to absorb it.
    """

    if s is None:
        return 0.0
    attached = sum(f.value or 0.0 for f in findings)
    return max(s.lift_to_best - attached, 0.0)
