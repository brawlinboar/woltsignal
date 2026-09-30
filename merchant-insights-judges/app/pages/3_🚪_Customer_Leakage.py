import pandas as pd
import plotly.express as px
import streamlit as st

from lib import (ALL, area_select, category_select, compliance_note, kpi_row,
                 level_select, money, num, page, pct, q, with_month_dates)

page("Customer Leakage", "🚪",
     "How much of residents' spending stays in their own area – and how much leaks to other towns, online "
     "shops or abroad. Also: which areas pull customers in.")

cat = category_select(default=ALL)
level = level_select(["neighborhood", "lau", "fua"], default="lau", key="leakage_lvl", follow_business=False)
area = area_select(level, table="demand", label="Home area of customers", key="leakage_area")

d = q("""SELECT * FROM demand WHERE geo_level = ? AND geo = ? AND category_group = ? AND month = 0""",
      (level, area, cat))
if d.empty:
    st.warning("Not enough data for this area and category.")
    st.stop()
d = d.iloc[0]
other = d.value - d.value_local - d.value_elsewhere_pl - d.value_online - d.value_abroad

kpi_row([
    ("Resident customers", num(d.cards)),
    ("Resident spend", money(d.value)),
    ("Stays in area", pct(d.value_local / d.value)),
    ("Leaks to other areas", pct(d.value_elsewhere_pl / d.value)),
    ("Leaks online", pct(d.value_online / d.value)),
    ("Leaks abroad", pct(d.value_abroad / d.value)),
])

split = pd.DataFrame({
    "Where the money goes": ["In home area", "Other Polish areas", "Online / card not present", "Abroad (in person)",
                             "Unlocated in-store"],
    "value": [d.value_local, d.value_elsewhere_pl, d.value_online, d.value_abroad, max(other, 0)],
})
left, right = st.columns(2)
with left:
    fig = px.pie(split, names="Where the money goes", values="value", hole=0.5, title=f"Resident spend – {area}")
    st.plotly_chart(fig, width="stretch")
with right:
    cats = q("""SELECT category_group, value, value_local, value_elsewhere_pl, value_online, value_abroad
                FROM demand WHERE geo_level = ? AND geo = ? AND month = 0 AND category_group <> ?""",
             (level, area, ALL))
    cats["Leak share"] = 1 - cats["value_local"] / cats["value"]
    cats["Leaked spend"] = cats["value"] - cats["value_local"]
    fig = px.bar(cats.sort_values("Leaked spend"), x="Leaked spend", y="category_group", orientation="h",
                 color="Leak share", color_continuous_scale="Reds",
                 title="Leaked spend by category", labels={"category_group": ""})
    fig.update_coloraxes(colorbar_tickformat=".0%")
    st.plotly_chart(fig, width="stretch")

st.subheader("Where residents go – and who comes in")
out_f = q("""SELECT dest_geo AS area, value, cards FROM flows
             WHERE geo_level = ? AND home_geo = ? AND category_group = ? AND dest_geo <> home_geo
             ORDER BY value DESC LIMIT 12""", (level, area, cat))
in_f = q("""SELECT home_geo AS area, value, cards FROM flows
            WHERE geo_level = ? AND dest_geo = ? AND category_group = ? AND dest_geo <> home_geo
            ORDER BY value DESC LIMIT 12""", (level, area, cat))
c1, c2 = st.columns(2)
for col, df, title in ((c1, out_f, f"Outflow: residents of {area} spend in…"),
                       (c2, in_f, f"Inflow: customers from … spend in {area}")):
    with col:
        if df.empty:
            st.info("No flows pass the compliance thresholds.")
            continue
        fig = px.bar(df, x="value", y="area", orientation="h", title=title,
                     hover_data={"cards": True}, labels={"value": "Spend", "area": "", "cards": "Customers"})
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, width="stretch")

net_in, net_out = in_f["value"].sum(), out_f["value"].sum()
if net_in or net_out:
    verdict = "a **destination** (pulls in more than it loses)" if net_in > net_out else "a **feeder** (loses more than it pulls in)"
    st.markdown(f"Among the top flows, {area} is {verdict}: inflow {money(net_in)} vs. outflow {money(net_out)}.")

trend = q("""SELECT month, value, value_local, value_online FROM demand
             WHERE geo_level = ? AND geo = ? AND category_group = ? AND month > 0 ORDER BY month""",
          (level, area, cat))
trend["Local share"] = trend["value_local"] / trend["value"]
trend["Online share"] = trend["value_online"] / trend["value"]
t = with_month_dates(trend)[["date", "Local share", "Online share"]].melt(id_vars="date")
fig = px.line(t, x="date", y="value", color="variable", markers=True, title="Is leakage getting worse?",
              labels={"value": "Share of resident spend", "date": "", "variable": ""})
fig.update_yaxes(tickformat=".0%")
st.plotly_chart(fig, width="stretch")

compliance_note()
