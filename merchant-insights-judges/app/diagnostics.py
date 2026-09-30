"""Rule-based diagnostics that turn the data marts into a merchant action plan.

Each rule looks at one aspect of the business (hours, loyalty, tourism, competition, ...), compares the
merchant - or, for a planned location, the local market - with a benchmark, and returns a Finding with
the evidence, a recommendation and a measure of success. Only rules whose gap is material are returned.
"""
from dataclasses import dataclass, field

import pandas as pd

from lib import money, pct, q

WEEKDAY = range(1, 6)
LUNCH = range(11, 14)      # 11:00-13:59
EVENING = range(17, 22)    # 17:00-21:59


@dataclass
class Finding:
    topic: str
    finding: str
    recommendation: str
    success: str
    score: float                      # 0..1, drives priority
    evidence: pd.DataFrame | None = field(default=None, repr=False)
    # Currency value of closing this gap, from opportunity.size_cells(). None
    # when the finding is real but not sizeable from the marts -- score still
    # orders it. Set by attach_opportunity() in the Action Plan page, not by
    # the rules themselves: sizing needs the cell partition, which is a
    # different mart.
    value: float | None = None

    @property
    def priority(self):
        return "🔴 High" if self.score >= 0.6 else ("🟠 Medium" if self.score >= 0.3 else "🟢 Low")


def clamp(x):
    return max(0.0, min(1.0, float(x)))


# --------------------------------------------------------------------------------------
# Data helpers
# --------------------------------------------------------------------------------------
def hour_grid(df):
    return (df.pivot_table(index="weekday", columns="hour", values="transactions", aggfunc="sum")
              .reindex(index=range(1, 8), columns=range(24)).fillna(0))


def shares(grid):
    wd = grid.loc[list(WEEKDAY)]
    total_wd = wd.values.sum() or 1
    by_hour = grid.sum()
    two_h = (by_hour + by_hour.shift(-1, fill_value=0))
    return {
        "lunch": wd[list(LUNCH)].values.sum() / total_wd,
        "evening": wd[list(EVENING)].values.sum() / total_wd,
        "weekend": grid.loc[[6, 7]].values.sum() / (grid.values.sum() or 1),
        "peak2": two_h.max() / (by_hour.sum() or 1),
        "peak_start": int(two_h.idxmax()),
        "profile": by_hour / (by_hour.sum() or 1),
    }


def market_hours(geo, cat):
    level = "poland" if geo == "POLAND" else "fua"
    return hour_grid(q("SELECT weekday, hour, transactions FROM hours WHERE geo_level = ? AND geo = ? "
                       "AND category_group = ?", (level, geo, cat)))


def foreign_stats(geo, cat):
    level = "poland" if geo == "POLAND" else "fua"
    d = q("""SELECT month, SUM(CASE WHEN dim_value <> 'Domestic' THEN value ELSE 0 END) AS foreign_value,
                    SUM(value) AS value
             FROM channels WHERE geo_level = ? AND geo = ? AND category_group = ? AND dimension = 'Cardholder origin'
             GROUP BY 1 ORDER BY 1""", (level, geo, cat))
    if d.empty:
        return None
    months = sorted(d["month"])
    last6, prev6 = months[-6:], [m - 100 for m in months[-6:]]
    cur = d[d.month.isin(last6)].foreign_value.sum()
    prv = d[d.month.isin(prev6)].foreign_value.sum()
    return {"share": d.foreign_value.sum() / d.value.sum(), "value": d.foreign_value.sum(),
            "growth": (cur / prv - 1) if prv else None, "monthly": d}


def market_growth(geo, cat):
    level = "poland" if geo == "POLAND" else "fua"
    s = q("SELECT month, value FROM supply WHERE geo_level = ? AND geo = ? AND category_group = ? AND month > 0",
          (level, geo, cat))
    months = sorted(s["month"])
    if len(months) < 13:
        return None
    last6, prev6 = months[-6:], [m - 100 for m in months[-6:]]
    prv = s[s.month.isin(prev6)].value.sum()
    return (s[s.month.isin(last6)].value.sum() / prv - 1) if prv else None


def channel_share(geo, cat, dimension, values):
    level = "poland" if geo == "POLAND" else "fua"
    d = q("SELECT dim_value, SUM(value) AS value FROM channels WHERE geo_level = ? AND geo = ? "
          "AND category_group = ? AND dimension = ? GROUP BY 1", (level, geo, cat, dimension))
    return d[d.dim_value.isin(values)].value.sum() / d.value.sum() if not d.empty else None


def best_partners(geo, cat, n=3):
    level = "poland" if geo == "POLAND" else "fua"
    a = q("""SELECT group_b, share_of_a_also_buying_b FROM affinity
             WHERE geo_level = ? AND geo = ? AND group_a = ?""", (level, geo, cat))
    base = q("SELECT group_a AS group_b, MAX(customers_a) AS cb FROM affinity WHERE geo_level = ? AND geo = ? "
             "GROUP BY 1", (level, geo))
    total = q("SELECT customers FROM customers WHERE geo_level = ? AND geo = ? AND segment = 'All segments' "
              "AND dimension = 'All customers'", (level, geo))["customers"].sum()
    if a.empty or not total:
        return pd.DataFrame()
    a = a.merge(base, on="group_b")
    a["lift"] = a["share_of_a_also_buying_b"] / (a["cb"] / total)
    a = a[~a.group_b.isin(["Cash & Financial", "Other Services"]) & (a["lift"] >= 1.05)]
    return a.sort_values("lift", ascending=False).head(n)


def expansion_candidates(fua, cat, n=3):
    d = q("""SELECT geo, value, cards, value_elsewhere_pl FROM demand
             WHERE geo_level = 'lau' AND category_group = ? AND month = 0 AND cards >= 300
               AND geo IN (SELECT DISTINCT lau FROM postal_lookup WHERE fua = ?)""", (cat, fua))
    s = q("SELECT geo, merchants FROM supply WHERE geo_level = 'lau' AND category_group = ? AND month = 0", (cat,))
    if d.empty:
        return pd.DataFrame()
    d = d.merge(s, on="geo", how="left").fillna({"merchants": 0})
    d["outflow_share"] = d.value_elsewhere_pl / d.value
    d["per_1k"] = d.merchants / d.cards * 1000
    d["score"] = d.value_elsewhere_pl.rank(pct=True) + d.outflow_share.rank(pct=True) + d.per_1k.rank(pct=True, ascending=False)
    return d.sort_values("score", ascending=False).head(n)


# --------------------------------------------------------------------------------------
# Rules shared by both modes (market context)
# --------------------------------------------------------------------------------------
def market_rules(geo, cat):
    out = []
    national = foreign_stats("POLAND", cat)
    local = foreign_stats(geo, cat) if geo != "POLAND" else None
    if local and national and local["share"] >= max(0.08, 1.5 * national["share"]):
        g = f", growing {pct(local['growth'])} year on year" if local["growth"] and local["growth"] > 0 else ""
        out.append(Finding(
            "Tourists",
            f"Foreign cardholders make up {pct(local['share'])} of {cat.lower()} spend in {geo} "
            f"({money(local['value'])}{g}) vs. {pct(national['share'])} nationally.",
            "Add an English menu and price list, improve map and review-site listings in English, accept all "
            "wallets, and test a clearly priced selection of popular local items.",
            "Growth in international-card transactions vs. comparable merchants nearby.",
            clamp(local["share"] / national["share"] / 4),
            local["monthly"].assign(foreign_share=lambda d: d.foreign_value / d.value)[["month", "foreign_share"]],
        ))

    g_local, g_nat = market_growth(geo, cat), market_growth("POLAND", cat)
    if g_local is not None and g_nat is not None and abs(g_local - g_nat) >= 0.05:
        if g_local > g_nat:
            out.append(Finding(
                "Market", f"The {cat.lower()} market in {geo} grew {pct(g_local)} (last 6 months YoY) vs. "
                          f"{pct(g_nat)} nationally – demand is expanding faster than average.",
                "Protect capacity at peak times, consider a second location or delivery radius extension before "
                "competitors fill the gap.",
                "Your sales growth vs. the local market growth rate.", clamp((g_local - g_nat) * 4)))
        else:
            out.append(Finding(
                "Market", f"The {cat.lower()} market in {geo} "
                          + (f"shrank {pct(-g_local)}" if g_local < 0 else f"grew only {pct(g_local)}")
                          + f" (last 6 months YoY) vs. {pct(g_nat)} growth nationally.",
                "Compete on share rather than market growth: loyalty offers, win-back of lapsed customers, and "
                "partnerships with complementary categories.",
                "Share of local category sales and repeat rate.", clamp((g_nat - g_local) * 4)))

    online = channel_share(geo, cat, "Card present", ["Online / not present"])
    online_nat = channel_share("POLAND", cat, "Card present", ["Online / not present"])
    if online is not None and online_nat and online >= max(0.10, 1.2 * online_nat):
        out.append(Finding(
            "Online", f"{pct(online)} of {cat.lower()} spend in {geo} is paid online / card-not-present "
                      f"(national: {pct(online_nat)}).",
            "Make sure you can be ordered online – delivery platform, click & collect or pre-orders – and that "
            "opening hours and menu are up to date online.",
            "Share of orders placed online and their average ticket.", clamp(online * 2)))

    premium = channel_share(geo, cat, "Card tier", ["Premium"])
    premium_nat = channel_share("POLAND", cat, "Card tier", ["Premium"])
    if premium is not None and premium_nat and premium >= 1.2 * premium_nat:
        out.append(Finding(
            "Customers", f"Premium cards generate {pct(premium)} of {cat.lower()} spend in {geo} "
                         f"(national: {pct(premium_nat)}) – an above-average affluent audience.",
            "Test a premium tier (signature items, experiences, reservations) and avoid competing on price alone.",
            "Average ticket and share of premium items in sales.", clamp(premium / premium_nat - 1)))

    partners = best_partners(geo, cat)
    if not partners.empty:
        txt = ", ".join(f"{r.group_b} ({pct(r.share_of_a_also_buying_b, 0)} of customers, lift {r.lift:.1f})"
                        for r in partners.itertuples())
        out.append(Finding(
            "Partnerships", f"{cat} customers in {geo} also shop most in: {txt}.",
            "Set up joint offers or cross-promotions with nearby merchants in these categories (e.g. vouchers, "
            "bundles, shared loyalty points).",
            "Redemptions of partner offers and new customers acquired through partners.",
            clamp((partners.lift.max() - 1) / 2), partners[["group_b", "share_of_a_also_buying_b", "lift"]]))
    return out


# --------------------------------------------------------------------------------------
# Planning mode: category + area, no own data yet
# --------------------------------------------------------------------------------------
def plan_for_area(geo, cat):
    out = []
    mkt, nat = market_hours(geo, cat), market_hours("POLAND", cat)
    if mkt.values.sum() > 0:
        m, n = shares(mkt), shares(nat)
        start = m["peak_start"]
        out.append(Finding(
            "Opening hours", f"Demand for {cat.lower()} in {geo} peaks at {start:02d}:00–{start + 2:02d}:00, "
                             f"which holds {pct(m['peak2'])} of daily transactions; weekends are {pct(m['weekend'])} "
                             f"of the week.",
            "Plan staffing and opening hours around this peak (see the Opening Hours page for the full window per day).",
            "Sales per labour hour in peak vs. off-peak hours.", 0.5,
            m["profile"].rename("share").reset_index().rename(columns={"index": "hour"})))
        if m["lunch"] - n["lunch"] >= 0.03:
            out.append(Finding(
                "Lunch", f"Weekday lunch (11–14) is {pct(m['lunch'])} of weekday demand in {geo} vs. "
                         f"{pct(n['lunch'])} nationally – a strong lunch market.",
                "Design a fast lunch offer (set menu, pre-order) and promote it to nearby offices.",
                "Weekday lunch transactions and ticket.", clamp((m["lunch"] - n["lunch"]) * 10)))
        if m["evening"] - n["evening"] >= 0.03:
            out.append(Finding(
                "Evening", f"Evenings (17–22) are {pct(m['evening'])} of weekday demand in {geo} vs. "
                           f"{pct(n['evening'])} nationally.",
                "Stay open into the evening and test an after-work / dinner offer.",
                "Evening sales vs. extra staffing cost.", clamp((m["evening"] - n["evening"]) * 10)))

    d = q("SELECT value, cards, value_local, value_elsewhere_pl, value_online FROM demand WHERE geo_level = 'fua' "
          "AND geo = ? AND category_group = ? AND month = 0", (geo, cat))
    s = q("SELECT merchants FROM supply WHERE geo_level = 'fua' AND geo = ? AND category_group = ? AND month = 0",
          (geo, cat))
    dn = q("SELECT value, cards FROM demand WHERE geo_level = 'poland' AND category_group = ? AND month = 0", (cat,))
    sn = q("SELECT merchants FROM supply WHERE geo_level = 'poland' AND category_group = ? AND month = 0", (cat,))
    if not d.empty and not s.empty and not dn.empty and not sn.empty:
        dens = s.merchants[0] / d.cards[0] * 1000
        dens_n = sn.merchants[0] / dn.cards[0] * 1000
        out.append(Finding(
            "Competition", f"{geo} has {dens:.1f} {cat.lower()} merchants per 1,000 resident customers vs. "
                           f"{dens_n:.1f} nationally – competition is {'lower' if dens < dens_n else 'higher'} than average.",
            "Low density: room for a broad offer. High density: differentiate (niche concept, location next to "
            "under-served neighbourhoods, longer hours).",
            "Time to break-even and share of local category sales.", clamp(abs(dens / dens_n - 1))))

    cands = expansion_candidates(geo, cat)
    if not cands.empty:
        txt = "; ".join(f"{r.geo} (residents spend {money(r.value)}, {pct(r.outflow_share, 0)} of it elsewhere)"
                        for r in cands.itertuples())
        out.append(Finding(
            "Location", f"Best under-served municipalities in the {geo} metro area for {cat.lower()}: {txt}.",
            "Shortlist sites in these municipalities and validate footfall and rents (see Where to Open for "
            "postal-code detail).",
            "Share of residents' category spend captured after opening.", 0.7,
            cands[["geo", "value", "outflow_share", "merchants"]]))
    return out + market_rules(geo, cat)


# --------------------------------------------------------------------------------------
# Merchant mode: own data vs. peers
# --------------------------------------------------------------------------------------
def plan_for_merchant(r):
    out = []
    geo, cat = r.geo, r.category_group
    peers = q("""SELECT repeat_customers / customers AS repeat_rate, value / transactions AS ticket,
                        transactions / customers AS visits, value / customers_group_value AS sow,
                        customers_group_value_online / customers_group_value AS online_leak
                 FROM merchant WHERE geo = ? AND category_group = ? AND merchant <> ?""", (geo, cat, r.merchant))
    have_peers = len(peers) >= 5
    med = peers.median() if have_peers else None

    my = {
        "repeat_rate": r.repeat_customers / r.customers,
        "ticket": r.value / r.transactions,
        "visits": r.transactions / r.customers,
        "sow": r.value / r.customers_group_value,
        "online_leak": r.customers_group_value_online / r.customers_group_value,
    }

    # ---- hours vs. market -------------------------------------------------------------------
    mh = q("SELECT weekday, hour, transactions FROM merchant_hours WHERE merchant = ?", (r.merchant,))
    mkt = market_hours(geo if geo != "Online / unknown" else "POLAND", cat)
    if not mh.empty and mkt.values.sum() > 0:
        me, m = shares(hour_grid(mh)), shares(mkt)
        prof = pd.DataFrame({"hour": range(24), "you": me["profile"].values, "market": m["profile"].values})
        if m["lunch"] - me["lunch"] >= 0.05:
            out.append(Finding(
                "Lunch", f"Weekday lunch (11–14) is {pct(m['lunch'])} of the local market's weekday demand but only "
                         f"{pct(me['lunch'])} of yours – you under-perform at lunch.",
                "Launch a quick lunch set during 11–14 and promote it to nearby offices; consider pre-ordering.",
                "Incremental weekday lunch sales and profit after promotion costs.",
                clamp((m["lunch"] - me["lunch"]) * 6), prof))
        if m["evening"] - me["evening"] >= 0.06:
            out.append(Finding(
                "Evening", f"The local market does {pct(m['evening'])} of weekday business after work (17–22); "
                           f"you do {pct(me['evening'])}.",
                "Extend opening hours on selected days and test a smaller evening menu / after-work offer.",
                "Additional profit compared with staffing and operating costs.",
                clamp((m["evening"] - me["evening"]) * 5), prof))
        if me["weekend"] - m["weekend"] >= 0.08:
            out.append(Finding(
                "Weekdays", f"{pct(me['weekend'])} of your transactions happen at weekends vs. {pct(m['weekend'])} "
                            f"for the local market – weekdays are weak.",
                "Run a weekday-only offer, such as a meal for two, a pickup bundle or a loyalty stamp bonus Mon–Thu.",
                "Weekday growth without a fall in weekend sales.", clamp((me["weekend"] - m["weekend"]) * 5), prof))
        elif m["weekend"] - me["weekend"] >= 0.10:
            out.append(Finding(
                "Weekends", f"Only {pct(me['weekend'])} of your transactions are at weekends vs. "
                            f"{pct(m['weekend'])} for the local market.",
                "Test weekend opening hours or a weekend-specific offer (brunch, family bundle, events).",
                "Weekend sales vs. added operating cost.", clamp((m["weekend"] - me["weekend"]) * 5), prof))
        if me["peak2"] >= 0.30:
            s = me["peak_start"]
            out.append(Finding(
                "Queues", f"{pct(me['peak2'])} of your daily transactions fall in two hours ({s:02d}:00–{s + 2:02d}:00).",
                "Offer pre-orders and scheduled pickup, and add staff or a faster menu for that window.",
                "Orders placed for the peak window, preparation time and repeat orders.",
                clamp((me["peak2"] - 0.25) * 4), prof))

    # ---- loyalty, ticket, share of wallet vs. peers ---------------------------------------------
    if have_peers:
        if my["repeat_rate"] <= 0.8 * med.repeat_rate:
            out.append(Finding(
                "Loyalty", f"{pct(my['repeat_rate'])} of your customers came back at least once vs. "
                           f"{pct(med.repeat_rate)} for a typical {cat.lower()} merchant in {geo}.",
                "Introduce a simple loyalty mechanic (stamp card, second-visit voucher) and collect contacts for "
                "win-back messages.",
                "Repeat-customer rate and visits per customer.", clamp(1 - my["repeat_rate"] / med.repeat_rate), None))
        if my["ticket"] <= 0.85 * med.ticket:
            out.append(Finding(
                "Basket", f"Your average ticket is {my['ticket']:,.0f} vs. {med.ticket:,.0f} for local peers.",
                "Add bundles, add-ons and upsell prompts at checkout; review the price of best-sellers.",
                "Average ticket and attachment rate of add-ons.", clamp(1 - my["ticket"] / med.ticket)))
        elif my["ticket"] >= 1.3 * med.ticket and my["visits"] <= med.visits:
            out.append(Finding(
                "Frequency", f"Your ticket ({my['ticket']:,.0f}) is well above peers ({med.ticket:,.0f}) but customers "
                             f"visit less often ({my['visits']:.1f} vs. {med.visits:.1f} visits).",
                "Create a lower-priced everyday offer to add visits without discounting the core menu.",
                "Visits per customer and total spend per customer.", clamp(my["ticket"] / med.ticket - 1)))
        if my["sow"] <= 0.8 * med.sow:
            comp = max(r.customers_group_value_same_area - r.value, 0)
            out.append(Finding(
                "Competition", f"You capture {pct(my['sow'])} of your own customers' {cat.lower()} spend vs. "
                               f"{pct(med.sow)} for peers; {money(comp)} of their spend goes to competitors in {geo}.",
                "Audit opening hours, online visibility, pricing and ordering availability against the competitors "
                "your customers also use; test the highest-impact change first.",
                "Change in your share of comparable local sales.", clamp(1 - my["sow"] / med.sow)))
        if my["online_leak"] >= max(0.15, 1.3 * med.online_leak):
            out.append(Finding(
                "Online", f"{pct(my['online_leak'])} of your customers' category spend goes online "
                          f"(peers: {pct(med.online_leak)}).",
                "Be orderable online: delivery platform, click & collect, pre-orders.",
                "Online orders and their share of sales.", clamp(my["online_leak"] * 2)))

    # ---- catchment ---------------------------------------------------------------------------------
    catch = q("SELECT home_district, customers FROM merchant_catchment WHERE merchant = ? ORDER BY customers DESC",
              (r.merchant,))
    if not catch.empty:
        top = catch.customers.iloc[0] / r.customers
        if top >= 0.6:
            out.append(Finding(
                "Catchment", f"{pct(top)} of your customers live in one postal district ({catch.home_district.iloc[0]}) "
                             "– you depend on a narrow neighbourhood.",
                "Reach neighbouring districts: local ads, delivery-radius extension, partnerships with merchants "
                "there.",
                "Customers from outside the main district.", clamp(top - 0.4), catch.head(8)))

    # ---- segments vs. market -------------------------------------------------------------------------
    seg = q("SELECT segment, customers FROM merchant_segments WHERE merchant = ?", (r.merchant,))
    mkt_seg = q("SELECT segment, customers FROM segment_categories WHERE geo_level = 'poland' AND category_group = ?",
                (cat,))
    if not seg.empty and not mkt_seg.empty:
        comp = seg.assign(you=seg.customers / seg.customers.sum())[["segment", "you"]].merge(
            mkt_seg.assign(market=mkt_seg.customers / mkt_seg.customers.sum())[["segment", "market"]], on="segment")
        comp = comp[(comp.market >= 0.03) & ~comp.segment.str.startswith("Occasional")]
        comp["gap"] = comp.market - comp.you
        if not comp.empty and comp.gap.max() >= 0.05:
            g = comp.sort_values("gap", ascending=False).iloc[0]
            out.append(Finding(
                "Customers", f"'{g.segment}' customers are {pct(g.market)} of {cat.lower()} shoppers but only "
                             f"{pct(g.you)} of yours.",
                "Target this group with an offer that fits its habits (see Customer Segments for their time of day, "
                "channel and categories).",
                "Share of customers from the target segment.", clamp(g.gap * 4), comp))

    if geo != "Online / unknown":
        out += market_rules(geo, cat)
        cands = expansion_candidates(geo, cat)
        if not cands.empty:
            txt = "; ".join(f"{c.geo} ({pct(c.outflow_share, 0)} of residents' spend goes elsewhere)"
                            for c in cands.itertuples())
            out.append(Finding(
                "Expansion", f"If you consider a second location in the {geo} metro area, the most under-served "
                             f"municipalities for {cat.lower()} are: {txt}.",
                "Validate footfall and rents there; use the Where to Open page for postal-code detail.",
                "Share of residents' category spend captured after opening.", 0.25,
                cands[["geo", "value", "outflow_share", "merchants"]]))
    return out, my, med


def to_table(findings):
    """Findings as a table, ordered by what they are worth where that is known.

    Sorting by value rather than score is the point of the opportunity engine:
    the worst-scoring gap is often in a thin segment, while a mild gap in a
    large one is worth several times more. Unsized findings keep their score
    ordering and sort after sized ones.
    """

    t = pd.DataFrame([{"Priority": f.priority, "Topic": f.topic, "What the data shows": f.finding,
                       "Recommendation": f.recommendation, "Measure of success": f.success,
                       "_score": f.score, "_value": f.value} for f in findings])
    return t.sort_values(["_value", "_score"], ascending=False, na_position="last")


# --------------------------------------------------------------------------------------
# Neighbourhood (postal code / postal district) context
# --------------------------------------------------------------------------------------
def neighbourhood_rules(postal, cat, has_business):
    out = []
    district = postal[:2] + "-xxx"
    for level, geo in (("postal", postal), ("district", district)):
        d = q("SELECT value, cards, value_local, value_elsewhere_pl, value_online FROM demand "
              "WHERE geo_level = ? AND geo = ? AND category_group = ? AND month = 0", (level, geo, cat))
        if d.empty:
            continue
        d = d.iloc[0]
        s = q("SELECT merchants FROM supply WHERE geo_level = ? AND geo = ? AND category_group = ? AND month = 0",
              (level, geo, cat))
        merchants = int(s.merchants.iloc[0]) if not s.empty else 0
        local = d.value_local / d.value
        where = "your postal code" if level == "postal" else f"postal district {district}"
        rec = ("Market directly to residents around you: local social ads, leaflets, a neighbour discount or a "
               "local delivery radius." if has_business else
               "Residents already spend in this category but mostly elsewhere – a local offer can capture part of it.")
        out.append(Finding(
            "Neighbourhood",
            f"{int(d.cards):,} residents of {where} spend {money(d.value)} on {cat.lower()}; only {pct(local)} of it "
            f"stays at the {merchants} merchant(s) located there, {pct(d.value_elsewhere_pl / d.value)} goes to other "
            f"areas and {pct(d.value_online / d.value)} online.",
            rec, "Share of local residents among your customers and their spend with you.",
            clamp((1 - local) * 0.8)))
        break  # the finest level with enough data is enough
    return out
