import pandas as pd
import plotly.express as px
import streamlit as st

from lib import ALL, area_select, category_select, compliance_note, level_select, money, num, page, q, with_month_dates

page("Market Trends", "📈",
     "Sales of merchants located in an area: growth by category, seasonality, and the detailed merchant "
     "categories (MCC) behind each group.")

level = level_select(["neighborhood", "poland", "fua", "lau"], label="Merchant area", default="neighborhood")
area = area_select(level, table="supply")
cat = category_select(default=ALL)

s = q("""SELECT category_group, month, value, transactions, cards FROM supply
         WHERE geo_level = ? AND geo = ? AND month > 0""", (level, area))
months = sorted(s["month"].unique())
last6, prev6 = months[-6:], [m - 100 for m in months[-6:]]
g = (s.assign(p=s["month"].map(lambda m: "cur" if m in last6 else ("prev" if m in prev6 else None)))
       .dropna(subset=["p"]).pivot_table(index="category_group", columns="p", values="value", aggfunc="sum"))
g["growth"] = g["cur"] / g["prev"] - 1
g = g.reset_index()

c1, c2 = st.columns(2)
with c1:
    gg = g[g.category_group != ALL].sort_values("growth")
    fig = px.bar(gg, x="growth", y="category_group", orientation="h", color="growth",
                 color_continuous_scale="RdYlGn", color_continuous_midpoint=0,
                 title=f"Sales growth, last 6 months vs. year before – {area}",
                 labels={"growth": "", "category_group": ""})
    fig.update_xaxes(tickformat=".0%")
    fig.update_layout(height=520, coloraxis_showscale=False)
    st.plotly_chart(fig, width="stretch")
with c2:
    t = with_month_dates(s[s.category_group == cat])
    fig = px.bar(t, x="date", y="value", title=f"Monthly sales – {cat}", labels={"value": "Sales", "date": ""})
    fig.update_traces(marker_color="#2563eb")
    fig.update_layout(height=520)
    st.plotly_chart(fig, width="stretch")

# Seasonality index: month-of-year average vs. overall monthly average
t = s[s.category_group == cat].copy()
t["moy"] = t["month"] % 100
season = (t.groupby("moy")["value"].mean() / t["value"].mean()).reset_index()
season["month"] = pd.to_datetime(season["moy"], format="%m").dt.strftime("%b")
fig = px.bar(season, x="month", y="value", title="Seasonality index (1.0 = average month)",
             labels={"value": "Index", "month": ""})
fig.add_hline(y=1, line_dash="dot")
st.plotly_chart(fig, width="stretch")

st.subheader("Merchant categories (MCC) behind the numbers")
mlevel = "poland" if level == "poland" else "fua"
if level == "lau":
    st.caption("MCC detail is available for metro areas and all of Poland; showing all of Poland.")
    mlevel, marea = "poland", "POLAND"
else:
    marea = area
mcc = q(f"""SELECT category_group, mcc, merchant_category, transactions, value, cards, merchants FROM mcc
            WHERE geo_level = ? AND geo = ? {"AND category_group = ?" if cat != ALL else ""}
            ORDER BY value DESC LIMIT 40""", (mlevel, marea, cat) if cat != ALL else (mlevel, marea))
mcc["avg_ticket"] = mcc["value"] / mcc["transactions"]
st.dataframe(pd.DataFrame({
    "Group": mcc["category_group"], "MCC": mcc["mcc"], "Merchant category": mcc["merchant_category"],
    "Sales": mcc["value"].map(money), "Transactions": mcc["transactions"].map(num),
    "Customers": mcc["cards"].map(num), "Merchants": mcc["merchants"].map(num),
    "Avg ticket": mcc["avg_ticket"].round(0),
}), hide_index=True, width="stretch")

compliance_note()
