import plotly.express as px
import streamlit as st

from lib import ALL, compliance_note, kpi_row, money, page, pct, q, with_month_dates, yoy

page("Merchant Insights", "🛍️",
     "Card-spending intelligence for merchants and city planners: who your customers are, where they shop, "
     "when they buy, where spending leaks out - and where to open next.")

tot = q("SELECT * FROM demand WHERE geo_level = 'poland' AND category_group = ? AND month = 0", (ALL,)).iloc[0]
monthly = q("SELECT month, value, transactions, cards FROM demand "
            "WHERE geo_level = 'poland' AND category_group = ? AND month > 0 ORDER BY month", (ALL,))
growth = yoy(monthly)

kpi_row([
    ("Customers (cards)", money(tot.cards)),
    ("Transactions", money(tot.transactions)),
    ("Spend", money(tot.value)),
    ("Avg transaction", f"{tot.value / tot.transactions:,.0f}"),
    ("Spend growth, last 6m YoY", pct(growth)),
    ("Online share of spend", pct(tot.value_online / tot.value)),
])

left, right = st.columns([3, 2])
with left:
    m = with_month_dates(monthly)
    fig = px.bar(m, x="date", y="value", labels={"value": "Spend", "date": ""}, title="Monthly card spend")
    fig.update_traces(marker_color="#2563eb")
    st.plotly_chart(fig, width="stretch")
with right:
    cats = q("SELECT category_group, value FROM demand WHERE geo_level = 'poland' AND month = 0 "
             "AND category_group <> ? ORDER BY value DESC", (ALL,))
    fig = px.bar(cats, x="value", y="category_group", orientation="h", title="Spend by category",
                 labels={"value": "Spend", "category_group": ""})
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    fig.update_traces(marker_color="#10b981")
    st.plotly_chart(fig, width="stretch")

st.success("**Start here → 🎯 Action Plan:** enter your business name and postal code to get a prioritised list "
           "of problems, recommendations and success measures for your business and neighbourhood.")
st.subheader("What you can do here")
c1, c2, c3 = st.columns(3)
c1.markdown("""
**📍 Where to Open** – rank areas by unmet resident demand, spend leaking to other areas, growth and
merchant density.

**🕒 Opening Hours** – local-time weekday × hour demand curves and recommended opening windows.
""")
c2.markdown("""
**🚪 Customer Leakage** – how much residents spend locally vs. in other areas, online or abroad, and
where exactly it goes.

**🏪 Merchant Benchmark** – a merchant's share of wallet, loyalty, catchment and hours vs. local peers.
""")
c3.markdown("""
**👥 Customer Segments** – who shops: behavioural segments, activity, time of day, channel, card tier.

**🔁 Loyalty**, **🧺 Cross-sell** and **💳 Channels & Tourism** – retention, category affinity,
payment methods and foreign visitors.
""")

st.info("**Data:** synthetic Visa card transactions, Jan 2025 – Jun 2026, Poland. Customer home areas come from "
        "the card-level enrichment (`pstl_cd_enr`, `lau_enr`, `fua_enr`), merchant locations from the merchant "
        "postal code. Transaction times are converted from UTC to Polish local time.")
compliance_note()
