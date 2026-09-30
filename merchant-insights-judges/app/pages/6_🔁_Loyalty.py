import plotly.express as px
import streamlit as st

from lib import ALL, LEVEL_LABELS, area_select, compliance_note, level_select, page, pct, q, with_month_dates

page("Loyalty & Retention", "🔁",
     "How many customers come back month after month in each category and area, and how many are new. "
     "A returning customer bought in the same category and area in the previous month.")

level = level_select(["neighborhood", "poland", "fua"], default="neighborhood")
area = area_select(level, table="retention")

r = q("""SELECT category_group, month, active_customers, returning_customers, new_customers FROM retention
         WHERE geo_level = ? AND geo = ? AND month BETWEEN 202505 AND 202605""", (level, area))
if r.empty:
    st.warning("No retention months from May 2025 through May 2026 for this area.")
    st.stop()
r["retention_rate"] = r["returning_customers"] / r["active_customers"]
r["new_share"] = r["new_customers"] / r["active_customers"]

summary = (r.groupby("category_group")
             .agg(active=("active_customers", "mean"), retention=("retention_rate", "mean"),
                  new=("new_share", "mean"))
             .reset_index().sort_values("retention", ascending=False))

c1, c2 = st.columns(2)
with c1:
    fig = px.bar(summary, x="retention", y="category_group", orientation="h",
                 title="Average month-to-month retention", labels={"retention": "", "category_group": ""})
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=520)
    fig.update_xaxes(tickformat=".0%")
    st.plotly_chart(fig, width="stretch")
with c2:
    fig = px.scatter(summary[summary.category_group != ALL], x="new", y="retention", size="active",
                     text="category_group", title="Acquisition vs. retention (bubble = monthly customers)",
                     labels={"new": "Share of new customers", "retention": "Retention rate"})
    fig.update_traces(textposition="top center", textfont_size=10)
    fig.update_xaxes(tickformat=".0%")
    fig.update_yaxes(tickformat=".0%")
    fig.update_layout(height=520)
    st.plotly_chart(fig, width="stretch")

cats = st.multiselect("Compare categories over time", summary["category_group"].tolist(),
                      default=[c for c in ["Restaurants & Bars", "Fashion & Beauty", "Groceries & Food Stores"]
                               if c in summary["category_group"].tolist()])
t = with_month_dates(r[r["category_group"].isin(cats)]).sort_values(["category_group", "month"])
fig = px.line(t, x="date", y="retention_rate", color="category_group", markers=True,
              labels={"retention_rate": "Retention rate", "date": "", "category_group": ""},
              title=f"Monthly retention – {LEVEL_LABELS[level]} {area if level != 'poland' else ''}")
fig.update_yaxes(tickformat=".0%")
st.plotly_chart(fig, width="stretch")

st.caption("May 2025 through May 2026. January–April 2025 are left out: the data starts in "
           "January 2025, so those early months have almost no one who can count as returning.")
best, worst = summary.iloc[0], summary.iloc[-1]
st.markdown(f"Highest retention: **{best.category_group}** ({pct(best.retention)}); lowest: "
            f"**{worst.category_group}** ({pct(worst.retention)}). Low-retention categories benefit most from "
            "loyalty programmes and win-back campaigns.")

compliance_note()
