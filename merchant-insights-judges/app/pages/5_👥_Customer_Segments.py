import pandas as pd
import plotly.express as px
import streamlit as st

from lib import compliance_note, ctx_area, level_select, money, num, page, pct, q

page("Customer Segments", "👥",
     "Who the customers are. Each card gets one purchase-behaviour segment from where it spends most "
     "(≥ 50% of spend in one category group = 'Mainly: …', otherwise 'Diversified'), plus behavioural traits.")

level = level_select(["neighborhood", "poland", "fua"], label="Customers living in", default="neighborhood")
if level == "poland":
    area = "POLAND"
else:
    areas = q("""SELECT geo, customers FROM customers WHERE geo_level = ? AND segment = 'All segments'
                 AND dimension = 'All customers' ORDER BY customers DESC""", (level,))["geo"].tolist()
    label = "Neighborhood" if level == "neighborhood" else "Metro area"
    preferred = ctx_area("fua")
    area = st.sidebar.selectbox(label, areas, index=areas.index(preferred) if preferred in areas else 0)
if level == "neighborhood":
    st.caption(
        "Visitor origin counts cards spending at merchants in this neighborhood. "
        "The other breakdowns count cards that live here."
    )

seg = q("""SELECT segment, customers, transactions, value FROM customers
           WHERE geo_level = ? AND geo = ? AND dimension = 'All customers' AND segment <> 'All segments'""",
        (level, area))
seg["share_customers"] = seg["customers"] / seg["customers"].sum()
seg["share_value"] = seg["value"] / seg["value"].sum()
seg["spend_per_customer"] = seg["value"] / seg["customers"]
seg["avg_ticket"] = seg["value"] / seg["transactions"]
seg = seg.sort_values("value", ascending=False)

c1, c2 = st.columns(2)
with c1:
    fig = px.bar(seg, x="share_customers", y="segment", orientation="h", title="Share of customers",
                 labels={"share_customers": "", "segment": ""})
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=520)
    fig.update_xaxes(tickformat=".0%")
    st.plotly_chart(fig, width="stretch")
with c2:
    fig = px.scatter(seg, x="avg_ticket", y="spend_per_customer", size="customers", color="segment",
                     hover_name="segment", title="Ticket size vs. spend per customer (bubble = customers)",
                     labels={"avg_ticket": "Avg transaction", "spend_per_customer": "Spend per customer"})
    fig.update_layout(showlegend=False, height=520)
    st.plotly_chart(fig, width="stretch")

table = pd.DataFrame({
    "Segment": seg["segment"], "Customers": seg["customers"].map(num), "% customers": seg["share_customers"].map(pct),
    "Spend": seg["value"].map(money), "% spend": seg["share_value"].map(pct),
    "Avg transaction": seg["avg_ticket"].round(0), "Spend / customer": seg["spend_per_customer"].round(0),
})
st.dataframe(table, hide_index=True, width="stretch")

st.subheader("Segment profile")
chosen = st.selectbox("Segment", ["All segments"] + seg["segment"].tolist())
prof = q("""SELECT dimension, dim_value, customers, value FROM customers
            WHERE geo_level = ? AND geo = ? AND segment = ? AND dimension <> 'All customers'""",
         (level, area, chosen))
allp = q("""SELECT dimension, dim_value, customers FROM customers
            WHERE geo_level = ? AND geo = ? AND segment = 'All segments' AND dimension <> 'All customers'""",
         (level, area))
prof["share"] = prof["customers"] / prof.groupby("dimension")["customers"].transform("sum")
allp["all"] = allp["customers"] / allp.groupby("dimension")["customers"].transform("sum")
def _first_cap(value):
    text = "" if value is None else str(value)
    return text[:1].upper() + text[1:].lower() if text else text


for frame in (prof, allp):
    mask = frame["dimension"].isin(["Card type", "Visitor origin"])
    frame.loc[mask, "dim_value"] = frame.loc[mask, "dim_value"].map(_first_cap)
prof = prof.merge(allp[["dimension", "dim_value", "all"]], on=["dimension", "dim_value"], how="left")

dims = prof["dimension"].unique().tolist()
cols = st.columns(3)
for i, dim in enumerate(dims):
    d = prof[prof["dimension"] == dim].sort_values("dim_value")
    long = d[["dim_value", "share", "all"]].melt(id_vars="dim_value").replace({"share": chosen, "all": "All customers"})
    fig = px.bar(long, x="dim_value", y="value", color="variable", barmode="group", title=dim,
                 labels={"dim_value": "", "value": "", "variable": ""})
    fig.update_yaxes(tickformat=".0%")
    fig.update_layout(height=320, legend=dict(orientation="h", y=-0.35))
    cols[i % 3].plotly_chart(fig, width="stretch")

st.subheader("What the segment buys")
mix = q("""SELECT category_group, customers, value FROM segment_categories
           WHERE geo_level = ? AND geo = ? AND segment = ?""", (level, area, chosen)) if chosen != "All segments" else \
    q("""SELECT category_group, SUM(customers) AS customers, SUM(value) AS value FROM segment_categories
         WHERE geo_level = ? AND geo = ? GROUP BY 1""", (level, area))
mix["share_of_spend"] = mix["value"] / mix["value"].sum()
fig = px.bar(mix.sort_values("share_of_spend"), x="share_of_spend", y="category_group", orientation="h",
             labels={"share_of_spend": "Share of segment spend", "category_group": ""})
fig.update_xaxes(tickformat=".0%")
st.plotly_chart(fig, width="stretch")

compliance_note()
