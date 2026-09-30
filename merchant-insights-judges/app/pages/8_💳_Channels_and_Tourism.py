import plotly.express as px
import streamlit as st

from lib import ALL, area_select, category_select, compliance_note, level_select, page, pct, q, with_month_dates

page("Channels, Payments & Tourism", "💳",
     "How customers pay (contactless, mobile, online, chip…), which card tiers they use, and how much spending "
     "comes from foreign visitors – by month, category and merchant area.")

cat = category_select(default=ALL)
level = level_select(["neighborhood", "poland", "fua"], label="Merchant area", default="neighborhood")
area = area_select(level, table="channels")
dims = q("SELECT DISTINCT dimension FROM channels ORDER BY 1")["dimension"].tolist()
dim = st.sidebar.selectbox("Breakdown", dims, index=dims.index("Channel") if "Channel" in dims else 0)
measure = st.sidebar.radio("Measure", ["value", "transactions"], format_func=str.capitalize)

d = q("""SELECT month, dim_value, transactions, value, cards FROM channels
         WHERE geo_level = ? AND geo = ? AND category_group = ? AND dimension = ?""", (level, area, cat, dim))
if d.empty:
    st.warning("Not enough data.")
    st.stop()
d["share"] = d[measure] / d.groupby("month")[measure].transform("sum")
t = with_month_dates(d)

c1, c2 = st.columns([3, 2])
with c1:
    fig = px.area(t, x="date", y="share", color="dim_value", title=f"{dim} – share of {measure} by month",
                  labels={"share": "", "date": "", "dim_value": ""})
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, width="stretch")
with c2:
    tot = d.groupby("dim_value")[["transactions", "value"]].sum().reset_index()
    tot["avg_ticket"] = tot["value"] / tot["transactions"]
    fig = px.bar(tot.sort_values(measure), x=measure, y="dim_value", orientation="h", text="avg_ticket",
                 title="Total and average ticket", labels={"dim_value": "", measure: measure.capitalize()})
    fig.update_traces(texttemplate="avg %{text:,.0f}", textposition="outside")
    st.plotly_chart(fig, width="stretch")

first, last = t["date"].min(), t["date"].max()
chg = (d[d.month == d.month.max()].set_index("dim_value")["share"]
       - d[d.month == d.month.min()].set_index("dim_value")["share"]).dropna().sort_values()
if not chg.empty:
    st.markdown(f"Biggest change {first:%b %Y} → {last:%b %Y}: **{chg.index[-1]}** "
                f"{chg.iloc[-1] * 100:+.1f} pp, **{chg.index[0]}** {chg.iloc[0] * 100:+.1f} pp.")

st.subheader("🌍 Tourism: where foreign cardholders spend")
tour = q("""SELECT geo, SUM(CASE WHEN dim_value <> 'Domestic' THEN value ELSE 0 END) AS foreign_value,
                   SUM(value) AS value
            FROM channels WHERE geo_level = 'fua' AND category_group = ? AND dimension = 'Cardholder origin'
            GROUP BY 1 HAVING SUM(value) > 0""", (cat,))
tour["foreign_share"] = tour["foreign_value"] / tour["value"]
c3, c4 = st.columns(2)
with c3:
    top = tour.sort_values("foreign_value", ascending=False).head(15)
    fig = px.bar(top, x="foreign_value", y="geo", orientation="h", color="foreign_share",
                 color_continuous_scale="Oranges", title="Top metro areas by foreign-card spend",
                 labels={"foreign_value": "Foreign spend", "geo": "", "foreign_share": "Share"})
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    fig.update_coloraxes(colorbar_tickformat=".0%")
    st.plotly_chart(fig, width="stretch")
with c4:
    season = q("""SELECT month, SUM(CASE WHEN dim_value <> 'Domestic' THEN value ELSE 0 END) / SUM(value) AS share
                  FROM channels WHERE geo_level = ? AND geo = ? AND category_group = ?
                  AND dimension = 'Cardholder origin' GROUP BY 1 ORDER BY 1""", (level, area, cat))
    fig = px.line(with_month_dates(season), x="date", y="share", markers=True,
                  title=f"Foreign share of spend by month – {area}", labels={"share": "", "date": ""})
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, width="stretch")
    if not season.empty:
        peak = season.loc[season["share"].idxmax()]
        st.caption(f"Tourist peak: {int(peak.month) // 100}-{int(peak.month) % 100:02d} "
                   f"({pct(peak.share)} of spend from foreign cards).")

compliance_note()
