import pandas as pd
import plotly.express as px
import streamlit as st

from lib import (SHOW_MERCHANT_NAMES, WEEKDAYS, business_ctx, compliance_note, kpi_row, mask_merchant, money, num,
                 page, pct, q)

page("Merchant Benchmark", "🏪",
     "A merchant's private view: share of wallet, loyalty, where customers live, when they shop and who they "
     "are – compared with all merchants in the same category and area.")

if not SHOW_MERCHANT_NAMES:
    st.caption("Merchant names are masked in this demo. In production each merchant would see only its own "
               "data after signing in (set `SHOW_MERCHANT_NAMES=1` to show real names locally).")

m = q("""SELECT merchant, geo, category_group, transactions, value, customers, repeat_customers,
                customers_group_value, customers_group_value_same_area, customers_group_value_online
         FROM merchant ORDER BY value DESC""")
m["label"] = m["merchant"].map(mask_merchant) + " · " + m["geo"] + " · " + m["category_group"]
labels = m["label"].tolist()[:3000]
ctx = business_ctx()
if ctx and ctx.get("merchant"):
    hit = m[(m.merchant == ctx["merchant"]) & (m.geo == ctx["mgeo"]) & (m.category_group == ctx["category"])]
    if not hit.empty and hit["label"].iloc[0] not in labels:
        labels = [hit["label"].iloc[0]] + labels
    default_idx = labels.index(hit["label"].iloc[0]) if not hit.empty else 0
else:
    default_idx = 0
choice = st.sidebar.selectbox("Merchant (location · category)", labels, index=default_idx)
r = m[m["label"] == choice].iloc[0]

peers = q("""SELECT value, transactions, cards, merchants FROM supply
             WHERE geo_level = 'fua' AND geo = ? AND category_group = ? AND month = 0""", (r.geo, r.category_group))
peer = peers.iloc[0] if not peers.empty else None

avg_ticket = r.value / r.transactions
freq = r.transactions / r.customers
sow = r.value / r.customers_group_value
kpi_row([
    ("Customers", num(r.customers)),
    ("Sales", money(r.value)),
    ("Avg ticket", f"{avg_ticket:,.0f}",
     f"Peers in area: {peer.value / peer.transactions:,.0f}" if peer is not None else None),
    ("Visits per customer", f"{freq:.1f}",
     f"Peers in area: {peer.transactions / peer.cards:.1f}" if peer is not None else None),
    ("Repeat customers", pct(r.repeat_customers / r.customers)),
    ("Share of wallet", pct(sow), "Your sales ÷ everything your customers spent in this category"),
])

if peer is not None:
    st.markdown(f"**Market in {r.geo} · {r.category_group}:** {num(peer.merchants)} merchants, "
                f"{money(peer.value)} sales, your share **{pct(r.value / peer.value)}**.")

st.subheader("Where your customers' category spend goes")
same_area_comp = max(r.customers_group_value_same_area - r.value, 0)
online = r.customers_group_value_online if r.geo != "Online / unknown" else max(r.customers_group_value_online - r.value, 0)
elsewhere = max(r.customers_group_value - r.value - same_area_comp - online, 0)
leak = pd.DataFrame({"Destination": ["You", "Competitors in your area", "Online", "Other areas"],
                     "value": [r.value, same_area_comp, online, elsewhere]})
c1, c2 = st.columns(2)
with c1:
    fig = px.pie(leak, names="Destination", values="value", hole=0.5,
                 title="Your customers' total spend in the category")
    st.plotly_chart(fig, width="stretch")
    st.caption(f"Leakage: **{money(r.customers_group_value - r.value)}** of your own customers' category spend "
               f"goes to other merchants – {pct(same_area_comp / r.customers_group_value)} to local competitors.")
with c2:
    catch = q("""SELECT home_district, home_fua, customers, value FROM merchant_catchment
                 WHERE merchant = ? ORDER BY customers DESC LIMIT 12""", (r.merchant,))
    if catch.empty:
        st.info("Catchment areas below the 30-customer threshold are hidden.")
    else:
        catch["area"] = catch["home_district"] + " (" + catch["home_fua"].fillna("n/a") + ")"
        fig = px.bar(catch, x="customers", y="area", orientation="h", title="Where your customers live",
                     labels={"customers": "Customers", "area": "Postal district"})
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, width="stretch")

st.subheader("When your customers buy vs. the market")
mh = q("SELECT weekday, hour, transactions FROM merchant_hours WHERE merchant = ?", (r.merchant,))
market = q("""SELECT hour, SUM(transactions) AS transactions FROM hours
              WHERE geo_level = 'fua' AND geo = ? AND category_group = ? GROUP BY 1""", (r.geo, r.category_group))
if not mh.empty:
    prof = pd.DataFrame({"You": mh.groupby("hour")["transactions"].sum()})
    if not market.empty:
        prof["Market in area"] = market.set_index("hour")["transactions"]
    prof = prof.reindex(range(24)).fillna(0).astype(float)
    prof = prof / prof.sum().replace(0, float("nan"))
    c3, c4 = st.columns(2)
    with c3:
        fig = px.line(prof.rename_axis("hour").reset_index().melt(id_vars="hour"), x="hour", y="value",
                      color="variable", markers=True, labels={"hour": "Hour (local)", "value": "Share", "variable": ""},
                      title="Hourly profile")
        fig.update_yaxes(tickformat=".0%")
        st.plotly_chart(fig, width="stretch")
    with c4:
        wd = mh.groupby("weekday")["transactions"].sum().reindex(range(1, 8)).fillna(0)
        fig = px.bar(x=[WEEKDAYS[i] for i in wd.index], y=wd.values / wd.sum(), title="Your weekday mix",
                     labels={"x": "", "y": "Share"})
        fig.update_yaxes(tickformat=".0%")
        st.plotly_chart(fig, width="stretch")
    missed = []
    if "Market in area" in prof:
        gap = (prof["Market in area"] - prof["You"]).sort_values(ascending=False)
        missed = [f"{h:02d}:00" for h, v in gap.items() if v > 0.01][:3]
    if missed:
        st.info(f"The market is relatively busier than you at **{', '.join(missed)}** – check staffing, "
                "opening hours or promotions for these slots.")

st.subheader("Who your customers are")
seg = q("SELECT segment, customers FROM merchant_segments WHERE merchant = ?", (r.merchant,))
mkt = q("""SELECT segment, customers FROM segment_categories
           WHERE geo_level = 'poland' AND category_group = ?""", (r.category_group,))
if not seg.empty:
    comp = seg.assign(share=seg["customers"] / seg["customers"].sum())[["segment", "share"]].merge(
        mkt.assign(market=mkt["customers"] / mkt["customers"].sum())[["segment", "market"]], on="segment", how="outer"
    ).fillna(0)
    comp["index_vs_market"] = (comp["share"] / comp["market"].where(comp["market"] > 0) * 100).round(0)
    fig = px.bar(comp.melt(id_vars="segment", value_vars=["share", "market"]), x="value", y="segment",
                 color="variable", barmode="group", orientation="h",
                 labels={"value": "Share of customers", "segment": "", "variable": ""},
                 title=f"Customer segments: you vs. all {r.category_group} shoppers in Poland")
    fig.update_xaxes(tickformat=".0%")
    fig.update_layout(height=520)
    st.plotly_chart(fig, width="stretch")

compliance_note()
