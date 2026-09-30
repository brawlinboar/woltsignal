import re

import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit.errors import StreamlitPageNotFoundError

from diagnostics import neighbourhood_rules, plan_for_area, plan_for_merchant, to_table
from lib import categories, compliance_note, kpi_row, money, num, page, pct, q
from opportunity import (attach_opportunity, controlled_comparisons, scenario_table,
                         scenarios, size_cells, unattributed)
from opportunity_data import (delivery_breakdown, delivery_pool, leaked_pool, market_cells,
                              merchant_cells, sibling_descriptors)

page("Action Plan", "🎯",
     "Pick your restaurant. We compare it with the local market and list what to fix, how, "
     "and how to measure the result.")

popular = q("""SELECT merchant, geo, category_group, customers, value, transactions, repeat_customers,
                     customers_group_value, customers_group_value_same_area, customers_group_value_online
              FROM merchant
              WHERE category_group = 'Restaurants & Bars'
                AND geo <> 'Online / unknown'
                AND lower(merchant) NOT LIKE '%automat%'
              ORDER BY transactions DESC
              LIMIT 40""")
popular_labels = [
    f"{r.merchant} · {r.geo} · {num(r.transactions)} transactions" for r in popular.itertuples()
]

# ---- inputs --------------------------------------------------------------------------------
with st.form("who"):
    c1, c2 = st.columns([3, 2.2])
    if popular.empty:
        name = c1.text_input("Business name", placeholder="e.g. Pizzeria Roma")
        picked = None
    else:
        picked = c1.selectbox("Business", range(len(popular_labels)), format_func=popular_labels.__getitem__)
        name = popular.iloc[picked].merchant
    cat_opt = ["Detect from my data"] + categories(include_all=False)
    cat_in = c2.selectbox("Category", cat_opt, help="Needed for a new business or if your name is not found.")
    submitted = st.form_submit_button("Show my action plan", type="primary")

if submitted:
    st.session_state.plan_query = (name.strip(), cat_in, picked)
if "plan_query" not in st.session_state:
    st.info("Pick a restaurant above.")
    st.stop()
saved = st.session_state.plan_query
if len(saved) == 3:
    name, cat_in, picked = saved
else:
    name, cat_in = saved[0], saved[1]
    picked = None

def busiest_postal(merchant, category):
    hit = q("""SELECT postal FROM opportunity_merchant
               WHERE merchant = ? AND category_group = ?
               GROUP BY postal ORDER BY SUM(txns) DESC LIMIT 1""", (merchant, category))
    return hit.postal.iloc[0] if not hit.empty else ""

# ---- find the business -----------------------------------------------------------------------
if picked is not None and not popular.empty and picked < len(popular):
    r = popular.iloc[picked]
    mode, cat, geo = "merchant", r.category_group, r.geo
    postal = busiest_postal(r.merchant, r.category_group)
else:
    cand = None
    if name:
        pattern = "%" + re.sub(r"\s+", "%", name.lower()) + "%"
        cat_filter = "" if cat_in == "Detect from my data" else "AND category_group = ?"
        params = (pattern,) + (() if cat_in == "Detect from my data" else (cat_in,))
        cand = q(f"""SELECT merchant, geo, category_group, customers, value, transactions, repeat_customers,
                            customers_group_value, customers_group_value_same_area, customers_group_value_online
                     FROM merchant WHERE lower(merchant) LIKE ? {cat_filter}
                     ORDER BY transactions DESC LIMIT 50""", params)
    if cand is not None and not cand.empty:
        labels = [f"{row.merchant} · {row.geo} · {row.category_group} · {num(row.transactions)} transactions" for row in cand.itertuples()]
        pick = st.selectbox("We found these matches – pick your business", range(len(labels)), format_func=labels.__getitem__)
        r = cand.iloc[pick]
        mode, cat, geo = "merchant", r.category_group, r.geo
        postal = busiest_postal(r.merchant, r.category_group)
    else:
        if name:
            st.info(f"We couldn't find “{name}” in the card data (new business, or a different name on card "
                    "statements). Showing the plan for a new business in your area.")
        if cat_in == "Detect from my data":
            st.warning("Choose your category in the form to get a plan for a new business.")
            st.stop()
        mode, cat, geo = "area", cat_in, "POLAND"
        postal = ""
        r = None

loc = q("SELECT lau, fua FROM postal_lookup WHERE postal = ?", (postal,)) if postal else None
if loc is None or loc.empty:
    lau, fua = None, geo if mode == "merchant" else None
else:
    lau, fua = loc.lau.iloc[0], loc.fua.iloc[0]
if mode == "merchant":
    st.markdown(f"**{r.merchant}** · {geo}" + (f" · {postal}" if postal else ""))
else:
    st.markdown(f"**New business** · {cat}")

# Remember the business so every other page opens pre-filtered on it
st.session_state.business = {
    "label": r.merchant if mode == "merchant" else f"New {cat.lower()} business",
    "merchant": r.merchant if mode == "merchant" else None,
    "mgeo": geo if mode == "merchant" else None,
    "category": cat, "postal": postal, "lau": lau,
    "fua": fua or (geo if geo not in ("POLAND", "Online / unknown") else None),
}

# ---- build findings ---------------------------------------------------------------------------
if mode == "merchant":
    findings, my, med = plan_for_merchant(r)
    kpi_row([
        ("Customers", num(r.customers)),
        ("Sales", money(r.value)),
        ("Average ticket", f"{my['ticket']:,.0f}", f"Local peers: {med.ticket:,.0f}" if med is not None else None),
        ("Visits per customer", f"{my['visits']:.1f}", f"Local peers: {med.visits:.1f}" if med is not None else None),
        ("Repeat customers", pct(my["repeat_rate"]), f"Local peers: {pct(med.repeat_rate)}" if med is not None else None),
        ("Share of wallet", pct(my["sow"]), "Your sales ÷ all your customers' spend in this category"),
    ], per_row=6)
else:
    findings = plan_for_area(geo, cat)
findings = neighbourhood_rules(postal, cat, has_business=(mode == "merchant")) + findings

# ---- size the opportunity -----------------------------------------------------------------
# Deduplicated sizing on a mutually exclusive channel x origin x card_group
# partition, so each finding carries what it is worth and the total can be
# summed without counting the same transaction more than once.
sizing, scen, rates = None, [], {}
if mode == "merchant":
    own = (r.merchant,)
    with st.expander("⚙️ Is this really all of you? (terminals, and who counts as a neighbour)"):
        st.caption(
            "One site often appears under several merchant descriptors — a second terminal, a "
            "concession counter, a renamed acquirer record. Any you leave out get counted as "
            "competitors, which understates your share. Some names in your postal code may also "
            "be a chain's other outlets registered to one head-office address; those are not "
            "your neighbours and inflate the market. Name, postcode, and category cannot settle "
            "which is which. Shared customers can: your own second till shares nearly all of "
            "them, a neighbour in the same building shares more than is typical here, and a "
            "place trading elsewhere in the city shares few. You still confirm the tick boxes.")
        sibs = sibling_descriptors(postal, cat, r.merchant)
        if sibs.empty:
            st.caption("No other merchant names in this postal code and category.")
        else:
            if "overlap_pct" in sibs.columns:
                st.caption(
                    "**Shared customers** is the share of that name's own customers who also "
                    "buy from you. Your own second till shares nearly all of them. A neighbour "
                    "in the same building shares a lot — being top of this list is *not* enough "
                    "on its own. Somewhere trading elsewhere in the city shares very few.")
                st.dataframe(
                    sibs.assign(**{
                        "Name": sibs.merchant,
                        "Shared customers": sibs.overlap_pct.map(
                            lambda v: "—" if pd.isna(v) else f"{v:.0f}%"),
                        "Typical here": sibs.peer_typical_pct.map(lambda v: f"{v:.0f}%"),
                        "Read": sibs.colocation,
                    })[["Name", "Shared customers", "Typical here", "Read"]],
                    hide_index=True, use_container_width=True)
                st.caption(
                    "How this is calculated: shared customers is that name’s own cards who also "
                    "paid you, divided by that name’s cards. Typical here is the median of those "
                    "shares at this postcode. Read flags a name well above that median. "
                    "The other name's own sales are not shown. "
                    "The arithmetic is in `merchant-insights/docs/opportunity-method.md`, "
                    "with the worked example in `docs/examples/mcd303-worked-example.md`."
                )
            also_me = st.multiselect("Also me (same site, different descriptor)",
                                     sibs.merchant.tolist(), key="also_me")
            not_here = st.multiselect("Not actually at this location (exclude from the market)",
                                      [m for m in sibs.merchant if m not in also_me], key="not_here")
            own = (r.merchant, *also_me)
            st.session_state.opp_exclude = tuple(not_here)

    market = market_cells(postal, cat)
    if not market.empty and st.session_state.get("opp_exclude"):
        # Excluded names are removed from the denominator only; the merchant's
        # own rows are unaffected.
        drop = merchant_cells(postal, cat, st.session_state["opp_exclude"])
        if not drop.empty:
            k = ["channel", "origin", "card_group"]
            market = (market.merge(drop.rename(columns={"value": "_dv", "txns": "_dt"}), on=k, how="left")
                            .fillna({"_dv": 0.0, "_dt": 0}))
            market["value"] = (market.value - market._dv).clip(lower=0)
            market["txns"] = (market.txns - market._dt).clip(lower=0)
            market = market.drop(columns=["_dv", "_dt"])

    sizing = size_cells(market, merchant_cells(postal, cat, own))
    findings = attach_opportunity(findings, sizing)

    scen = scenarios(
        delivery_pool=delivery_pool(postal, cat, own),
        repeat_rate=my.get("repeat_rate"),
        peer_repeat_rate=float(med.repeat_rate) if med is not None else None,
        merchant_value=float(r.value),
        ticket=my.get("ticket"),
        peer_ticket=float(med.ticket) if med is not None else None,
        leaked_pool=leaked_pool(postal, cat),
    )

if sizing is not None and sizing.market_value > 0:
    kpi_row([
        ("Your share here", pct(sizing.overall_share / 100),
         "Your value ÷ all value in this postal code and category"),
        ("Everything not yours", money(sizing.ceiling),
         "The whole remaining market — a ceiling, not a target. Reaching it means 100% share."),
        ("Measured opportunity", money(sizing.lift_to_best),
         f"Deduplicated: every customer group lifted to your best group's share "
         f"({sizing.best_cell_share:.1f}%). Each transaction counted once, so this total is additive."),
        ("Conservative variant", money(sizing.lift_to_global),
         "Same method, benchmarked against your own overall share instead of your best group."),
    ], per_row=4)
    if sizing.unsized_cells:
        st.caption(
            f"{sizing.unsized_cells} customer groups holding {money(sizing.unsized_value)} are shown but "
            f"not sized — under 100 transactions each, where a share swings on a handful of sales. "
            f"That caps precision; it is not hidden upside.")

if not findings:
    st.success("No material gaps found versus the local market – keep monitoring monthly.")
    st.stop()

table = to_table(findings)
topics = sorted(table["Topic"].unique())
focus = st.multiselect("What is your main concern? (optional filter)", topics)
view = table[table["Topic"].isin(focus)] if focus else table

subject = f"**{r.merchant}**" if mode == "merchant" else f"a new **{cat.lower()}** business"
st.subheader(f"Action plan for {subject} – {len(view)} findings")
st.download_button("⬇️ Download action plan (CSV)", view.drop(columns="_score").to_csv(index=False).encode("utf-8"),
                   file_name=f"action_plan_{postal}.csv", mime="text/csv")


DETAIL_PAGE = {
    "Neighbourhood": ("pages/3_🚪_Customer_Leakage.py", "Customer Leakage"),
    "Location": ("pages/1_📍_Where_to_Open.py", "Where to Open"),
    "Expansion": ("pages/1_📍_Where_to_Open.py", "Where to Open"),
    "Opening hours": ("pages/2_🕒_Opening_Hours.py", "Opening Hours"),
    "Lunch": ("pages/2_🕒_Opening_Hours.py", "Opening Hours"),
    "Evening": ("pages/2_🕒_Opening_Hours.py", "Opening Hours"),
    "Weekdays": ("pages/2_🕒_Opening_Hours.py", "Opening Hours"),
    "Weekends": ("pages/2_🕒_Opening_Hours.py", "Opening Hours"),
    "Queues": ("pages/2_🕒_Opening_Hours.py", "Opening Hours"),
    "Loyalty": ("pages/6_🔁_Loyalty.py", "Loyalty"),
    "Basket": ("pages/4_🏪_Merchant_Benchmark.py", "Merchant Benchmark"),
    "Frequency": ("pages/4_🏪_Merchant_Benchmark.py", "Merchant Benchmark"),
    "Catchment": ("pages/4_🏪_Merchant_Benchmark.py", "Merchant Benchmark"),
    "Competition": ("pages/4_🏪_Merchant_Benchmark.py" if mode == "merchant" else "pages/9_📈_Market_Trends.py",
                    "Merchant Benchmark" if mode == "merchant" else "Market Trends"),
    "Market": ("pages/9_📈_Market_Trends.py", "Market Trends"),
    "Tourists": ("pages/8_💳_Channels_and_Tourism.py", "Channels and Tourism"),
    "Online": ("pages/8_💳_Channels_and_Tourism.py", "Channels and Tourism"),
    "Customers": ("pages/5_👥_Customer_Segments.py", "Customer Segments"),
    "Partnerships": ("pages/7_🧺_Cross_Sell.py", "Cross Sell"),
}


def evidence_chart(ev, key):
    if {"hour", "you", "market"} <= set(ev.columns):
        fig = px.line(ev.melt(id_vars="hour"), x="hour", y="value", color="variable", markers=True,
                      labels={"hour": "Hour (local)", "value": "Share of daily transactions", "variable": ""})
        fig.update_yaxes(tickformat=".0%")
    elif {"hour", "share"} <= set(ev.columns):
        fig = px.bar(ev, x="hour", y="share", labels={"hour": "Hour (local)", "share": "Share of daily demand"})
        fig.update_yaxes(tickformat=".0%")
    elif {"month", "foreign_share"} <= set(ev.columns):
        ev = ev.assign(month=ev.month.astype(int).astype(str))
        fig = px.line(ev, x="month", y="foreign_share", markers=True,
                      labels={"foreign_share": "Foreign-card share of spend", "month": ""})
        fig.update_yaxes(tickformat=".0%")
    else:
        st.dataframe(ev, hide_index=True, width="stretch", key=f"tbl_{key}")
        return
    fig.update_layout(height=300, margin=dict(t=10, b=10))
    st.plotly_chart(fig, width="stretch", key=f"fig_{key}")


# Ordered by what each is worth where that is known, score otherwise -- a mild
# gap in a big customer group beats a severe one in a thin group.
shown = [f for f in sorted(findings, key=lambda f: (-(f.value or 0), -f.score))
         if not focus or f.topic in focus]
for i, f in enumerate(shown, 1):
    with st.container(border=True):
        worth = f" &nbsp;·&nbsp; **{money(f.value)}** at stake" if f.value else ""
        st.markdown(f"**{i}. {f.topic}** &nbsp; {f.priority}{worth}")
        c1, c2, c3 = st.columns([1.2, 1.2, 0.8])
        c1.markdown(f"**What the data shows**  \n{f.finding}")
        c2.markdown(f"**Recommendation**  \n{f.recommendation}")
        c3.markdown(f"**Measure of success**  \n{f.success}")
        if f.evidence is not None:
            with st.expander("Show the evidence"):
                evidence_chart(f.evidence, i)
        if f.topic in DETAIL_PAGE:
            path, label = DETAIL_PAGE[f.topic]
            try:
                st.page_link(path, label=f"See details in {label} →", icon="🔎")
            except StreamlitPageNotFoundError:  # page run standalone (e.g. in tests)
                pass

# ---- scenarios: pools whose current capture cannot be observed ----------------------------
if scen:
    st.divider()
    st.subheader("Scenarios — opportunity that needs an assumption")
    st.markdown(
        "These levers have a **measurable pool** but an **unmeasurable current capture**, so they "
        "cannot be added to the measured opportunity above. Set a capture rate and see what it "
        "would be worth. Every rate is yours to justify — the data does not supply it.")

    cols = st.columns(min(len(scen), 4))
    for col, s in zip(cols, scen):
        rates[s.key] = col.slider(s.label, 0.0, s.max_rate, s.default_rate, step=0.5,
                                  format="%.1f%%", key=f"rate_{s.key}",
                                  help=f"Pool: {money(s.pool)}. {s.pool_basis}")

    tbl = scenario_table(scen, rates)
    st.dataframe(
        tbl.assign(Pool=tbl.Pool.map(money), **{"Scenario value": tbl["Scenario value"].map(money)}),
        hide_index=True, width="stretch",
        column_config={"Why an assumption is needed": st.column_config.TextColumn(width="large")})

    measured = sizing.lift_to_best if sizing else 0.0
    scen_total = float(sum(s.value(rates[s.key]) for s in scen))
    c1, c2 = st.columns(2)
    c1.metric("Measured opportunity", money(measured),
              help="Deduplicated, additive, observed in the transaction data.")
    c2.metric("Scenario opportunity", money(scen_total),
              help="At the rates set above. Rests on assumptions the data cannot check.")
    st.warning(
        "**Do not add these two together.** The measured figure is a share the data shows you are "
        "not capturing. The scenario figure is a share of a pool where your current position is "
        "unknown — for delivery you may already hold part of it, because the aggregator is the "
        "merchant of record and an order placed through it may already be your sale.")

    dl = delivery_breakdown(postal, cat, own) if mode == "merchant" else None
    if dl is not None and not dl.empty:
        with st.expander("Delivery pool — what it is made of"):
            st.dataframe(dl.assign(value=dl.value.map(money)), hide_index=True, width="stretch")
            st.caption(
                "Glovo, Wolt and Pyszne.pl only. Uber Eats, Deliveroo and Bolt Food are excluded: "
                "all three have no Polish-merchant transactions in this data, so those rows are "
                "cardholders ordering delivery abroad — foreign travel spend, not local demand.")

# ---- the cell grid behind the measured number ---------------------------------------------
if sizing is not None and not sizing.cells.empty:
    with st.expander("How the measured opportunity is calculated (no double counting)"):
        st.markdown(
            "Every transaction is put in **exactly one** customer group — payment channel × "
            "local or visiting × card tier. That is what makes the total addable: a contactless "
            "purchase by a local premium cardholder belongs to one group only. Sizing each "
            "dimension separately instead would count that sale three times.\n\n"
            f"Each group is then lifted to your strongest group's share "
            f"(**{sizing.best_cell_share:.1f}%**), and the lifts are summed.")
        g = sizing.cells.copy()
        st.dataframe(
            g.assign(share=g.share.map(lambda v: "–" if pd.isna(v) else f"{v:.1f}%"),
                     market_value=g.market_value.map(money),
                     merchant_value=g.merchant_value.map(money),
                     lift_to_best=g.lift_to_best.map(money))[
                ["cell", "market_txns", "market_value", "merchant_value", "share",
                 "lift_to_best", "sized"]]
            .rename(columns={"cell": "Customer group", "market_txns": "Transactions",
                             "market_value": "Market", "merchant_value": "Yours",
                             "share": "Your share", "lift_to_best": "Opportunity",
                             "sized": "Sized"}),
            hide_index=True, width="stretch")

        cc = controlled_comparisons(sizing)
        if not cc.empty:
            st.markdown(
                "**Like-for-like comparisons.** Each row differs in one dimension only, with the "
                "other two held constant — so the gap is attributable to that dimension rather "
                "than to a different kind of customer.")
            st.dataframe(
                cc.assign(gap=cc.gap_pts.map(lambda v: f"{v:.1f} pts"),
                          worth=cc.lift_if_closed.map(money))[
                    ["dimension", "holding_constant", "stronger", "weaker", "gap", "worth"]]
                .rename(columns={"dimension": "Differs by", "holding_constant": "Holding constant",
                                 "stronger": "Stronger", "weaker": "Weaker", "gap": "Gap",
                                 "worth": "Worth closing"}),
                hide_index=True, width="stretch")

        rest = unattributed(sizing, findings)
        if rest > 0:
            st.caption(
                f"{money(rest)} of the measured opportunity is not attributed to any finding above. "
                f"It is real but unexplained by these rules — better stated than folded into a "
                f"finding to make the arithmetic look complete.")

st.caption("Findings are generated by transparent rules comparing you with merchants in the same category and "
           "metro area (medians of ≥ 5 peers) or with national benchmarks. Hours are Polish local time. "
           "In production, a merchant would sign in and see only their own business.")
compliance_note()
