import pandas as pd
import plotly.express as px
import streamlit as st

from lib import (ALL, LEVEL_LABELS, category_select, ctx_area, compliance_note, is_krakow, level_select, money, num,
                 page, pct, q, with_month_dates)

page("Where to Open", "📍",
     "Find areas where residents spend a lot in a category but local merchants capture little of it - "
     "that spend walks out to other areas today and is the opportunity for a new location.")

cat = category_select(default="Restaurants & Bars")
metros = q("""SELECT geo FROM demand WHERE geo_level = 'fua' AND category_group = ? AND month = 0
              ORDER BY value DESC""", (ALL,))["geo"].tolist()
metro_opts = ["All of Poland"] + metros
krakow_metro = next((m for m in metro_opts if is_krakow(m)), None)
if "where_metro" not in st.session_state or st.session_state["where_metro"] not in metro_opts:
    st.session_state["where_metro"] = krakow_metro or (ctx_area("fua") if ctx_area("fua") in metro_opts else metro_opts[0])
metro = st.sidebar.selectbox("Limit to metro area", metro_opts, key="where_metro",
                             help="Rank only postal codes, districts or municipalities inside one metro area (FUA).")
levels = ["postal", "lau", "district"] if metro != "All of Poland" else ["lau", "district", "fua", "postal"]
if is_krakow(metro):
    levels = ["neighborhood"] + levels
level = level_select(levels, default="neighborhood" if is_krakow(metro) else ("postal" if metro != "All of Poland" else "lau"))
default_min = {"neighborhood": 300, "postal": 50, "district": 300, "lau": 300, "fua": 1000}[level]
min_customers = st.sidebar.slider("Min. resident customers in area", 30, 5000, default_min, step=10, key=f"min_{level}")

# Areas belonging to the chosen metro area (via the postal code -> LAU -> FUA lookup)
if metro == "All of Poland" or level == "neighborhood":
    area_filter, area_params = "", ()
else:
    member = {"postal": "postal", "lau": "lau", "district": "substr(postal, 1, 2) || '-xxx'"}[level]
    area_filter = f"AND geo IN (SELECT DISTINCT {member} FROM postal_lookup WHERE fua = ?)"
    area_params = (metro,)

demand = q(f"""SELECT geo, value AS resident_spend, cards AS resident_customers, value_local, value_elsewhere_pl,
                      value_online, value_abroad
               FROM demand WHERE geo_level = ? AND category_group = ? AND month = 0 {area_filter}""",
           (level, cat) + area_params)
supply = q("""SELECT geo, value AS local_sales, merchants AS local_merchants, cards AS local_customers
              FROM supply WHERE geo_level = ? AND category_group = ? AND month = 0""", (level, cat))
monthly = q(f"""SELECT geo, month, value FROM demand
                WHERE geo_level = ? AND category_group = ? AND month > 0 {area_filter}""",
            (level, cat) + area_params)

months = sorted(monthly["month"].unique())
last6, prev6 = months[-6:], [m - 100 for m in months[-6:]]
g = monthly.assign(p=monthly["month"].map(lambda m: "cur" if m in last6 else ("prev" if m in prev6 else None)))
g = g.dropna(subset=["p"]).pivot_table(index="geo", columns="p", values="value", aggfunc="sum")
growth = (g["cur"] / g["prev"] - 1).rename("growth") if {"cur", "prev"} <= set(g.columns) else pd.Series(dtype=float)

df = demand.merge(supply, on="geo", how="left").merge(growth, left_on="geo", right_index=True, how="left")
df = df[df["resident_customers"] >= min_customers].copy()
if df.empty:
    st.warning("No areas match the filters - lower the minimum number of customers.")
    st.stop()

df["local_merchants"] = df["local_merchants"].fillna(0)
df["local_sales"] = df["local_sales"].fillna(0)
df["local_capture"] = df["value_local"] / df["resident_spend"]
df["outflow_share"] = df["value_elsewhere_pl"] / df["resident_spend"]
df["spend_per_resident"] = df["resident_spend"] / df["resident_customers"]
df["merchants_per_1k_residents"] = df["local_merchants"] / df["resident_customers"] * 1000
df["demand_supply_ratio"] = df["resident_spend"] / df["local_sales"].where(df["local_sales"] > 0)

# Opportunity score: equal-weight percentile ranks (0-100)
rank = lambda s, asc=True: s.rank(pct=True, ascending=asc).fillna(0.5)  # noqa: E731
df["opportunity_score"] = 100 * (
    rank(df["value_elsewhere_pl"]) + rank(df["outflow_share"]) + rank(df["growth"])
    + rank(df["merchants_per_1k_residents"], asc=False)
) / 4
df = df.sort_values("opportunity_score", ascending=False)

# Readable labels: postal codes get their municipality name
if level == "postal":
    lau_of = q("SELECT postal, lau FROM postal_lookup").set_index("postal")["lau"]
    df["label"] = df["geo"] + " · " + df["geo"].map(lau_of).fillna("")
else:
    df["label"] = df["geo"]

where = f" in the {metro} metro area" if metro != "All of Poland" else ""
st.markdown(f"**{cat}** · {LEVEL_LABELS[level]}{where} · {len(df):,} areas with ≥ {min_customers} resident customers")
with st.expander("How the opportunity score works"):
    st.markdown("""
Equal-weight average of four percentile ranks (0–100):
1. **Spend leaving the area** – in-store spend of residents at merchants in *other* Polish areas (absolute value).
2. **Outflow share** – that spend as a share of all resident spend in the category.
3. **Growth** – resident spend in the last 6 months vs. the same months a year earlier.
4. **Low competition** – fewer local merchants per 1,000 resident customers scores higher.

Residents are assigned to an area by the card's usual location; merchants by their postal code.
""")

top = df.head(15)
show = pd.DataFrame({
    "Area": top["label"],
    "Score": top["opportunity_score"].round(0).astype(int),
    "Resident customers": top["resident_customers"].map(num),
    "Resident spend": top["resident_spend"].map(money),
    "Spent in other areas": top["value_elsewhere_pl"].map(money),
    "Outflow share": top["outflow_share"].map(pct),
    "Captured locally": top["local_capture"].map(pct),
    "Local merchants": top["local_merchants"].map(num),
    "Merchants / 1k residents": top["merchants_per_1k_residents"].round(1),
    "Growth YoY (6m)": top["growth"].map(pct),
})
st.subheader("Top areas to open a new location")
st.dataframe(show, hide_index=True, width="stretch")
st.caption("0 local merchants means no merchant in that category is located there, or too few to publish under "
           "the compliance rules. Growth is blank where the area had no comparable spend a year earlier.")

fig = px.scatter(
    df.head(300), x="resident_spend", y="outflow_share", size="value_elsewhere_pl", color="opportunity_score",
    hover_name="label", color_continuous_scale="Viridis", log_x=True,
    labels={"resident_spend": "Resident spend in category (log)", "outflow_share": "Share spent in other areas",
            "opportunity_score": "Score", "value_elsewhere_pl": "Spend leaving"},
    title="Demand vs. outflow (bubble = spend leaving the area)")
fig.update_yaxes(tickformat=".0%")
st.plotly_chart(fig, width="stretch")

# ---- drill-down -----------------------------------------------------------------------
st.subheader("Area drill-down")
labels = dict(zip(df["geo"], df["label"]))
area = st.selectbox("Area", df["geo"].tolist(), index=0, format_func=labels.get)
row = df[df["geo"] == area].iloc[0]
local = row.local_capture
elsewhere = row.outflow_share
online = row.value_online / row.resident_spend
abroad = row.value_abroad / row.resident_spend
shown = [round(x * 100, 1) for x in (local, elsewhere, online, abroad)]
other = (100 - sum(shown)) / 100
c = st.columns(6)
c[0].metric("Resident spend", money(row.resident_spend))
c[1].metric("Captured locally", pct(local))
c[2].metric("Other Polish areas", pct(elsewhere))
c[3].metric("Online", pct(online))
c[4].metric("Abroad", pct(abroad))
c[5].metric("Other", pct(other))
st.caption("Other is in-store spend in Poland at a merchant with no municipality, so it is neither local nor another Polish area. The shares add to 100%.")

left, right = st.columns(2)
with left:
    if level in ("lau", "fua"):
        dest = q("""SELECT dest_geo AS destination, value, cards FROM flows
                    WHERE geo_level = ? AND home_geo = ? AND category_group = ? AND dest_geo <> home_geo
                    ORDER BY value DESC LIMIT 10""", (level, area, cat))
        if dest.empty:
            st.info("No destination areas pass the compliance thresholds.")
        else:
            fig = px.bar(dest, x="value", y="destination", orientation="h",
                         title=f"Where residents of {area} spend instead", labels={"value": "Spend", "destination": ""})
            fig.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, width="stretch")
    else:
        st.info("Destination flows are available at municipality (LAU) and metro area (FUA) level.")
with right:
    trend = q("""SELECT d.month, d.value AS resident_spend, s.value AS local_sales
                 FROM demand d LEFT JOIN supply s
                   ON s.geo_level = d.geo_level AND s.geo = d.geo AND s.category_group = d.category_group
                  AND s.month = d.month
                 WHERE d.geo_level = ? AND d.geo = ? AND d.category_group = ? AND d.month > 0
                 ORDER BY d.month""", (level, area, cat))
    t = with_month_dates(trend).melt(id_vars=["date"], value_vars=["resident_spend", "local_sales"])
    fig = px.line(t, x="date", y="value", color="variable", markers=True,
                  title="Resident spend vs. sales of local merchants",
                  labels={"value": "Spend", "date": "", "variable": ""})
    st.plotly_chart(fig, width="stretch")

compliance_note()
