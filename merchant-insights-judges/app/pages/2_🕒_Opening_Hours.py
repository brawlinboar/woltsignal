import pandas as pd
import plotly.express as px
import streamlit as st

from lib import (ALL, WEEKDAYS, area_select, category_select, compliance_note,
                 level_select, page, pct, q)

page("Opening Hours", "🕒",
     "When do customers actually buy in your category and area? Weekday × hour demand in Polish local time, "
     "recommended opening windows, and hours where you may be missing traffic.")

cat = category_select(default="Restaurants & Bars", include_all=True)
level = level_select(["neighborhood", "fua", "lau", "poland"], default="neighborhood")
area = area_select(level, table="hours")
metric = st.sidebar.radio("Measure", ["transactions", "value"], format_func=str.capitalize)
coverage = st.sidebar.slider("Opening window covers … of daily demand", 0.70, 0.99, 0.90, 0.01)

h = q("""SELECT weekday, hour, transactions, value FROM hours
         WHERE geo_level = ? AND geo = ? AND category_group = ?""", (level, area, cat))
base = q("""SELECT weekday, hour, transactions, value FROM hours
            WHERE geo_level = ? AND geo = ? AND category_group = ?""", (level, area, ALL))
if h.empty:
    st.warning("Not enough data for this area and category.")
    st.stop()

grid = (h.pivot_table(index="weekday", columns="hour", values=metric, aggfunc="sum")
          .reindex(index=range(1, 8), columns=range(24)).fillna(0))
share = grid / grid.values.sum()

fig = px.imshow(share.rename(index=WEEKDAYS), aspect="auto", color_continuous_scale="Blues",
                labels={"x": "Hour (local time)", "y": "", "color": "Share"},
                title=f"{cat} demand by weekday and hour – {area}")
fig.update_xaxes(dtick=1)
fig.update_coloraxes(colorbar_tickformat=".1%")
st.plotly_chart(fig, width="stretch")


def window(row, cover):
    """Shortest contiguous hour range covering `cover` of the day's demand."""
    vals = row.values
    total = vals.sum()
    if total == 0:
        return None, None
    best = (0, 23)
    for start in range(24):
        acc = 0
        for end in range(start, 24):
            acc += vals[end]
            if acc >= cover * total:
                if end - start < best[1] - best[0]:
                    best = (start, end)
                break
    return best


rows = []
for wd in range(1, 8):
    s, e = window(grid.loc[wd], coverage)
    day = grid.loc[wd]
    rows.append({
        "Day": WEEKDAYS[wd],
        "Open": f"{s:02d}:00" if s is not None else "–",
        "Close": f"{e + 1:02d}:00" if e is not None else "–",
        "Peak hour": f"{int(day.idxmax()):02d}:00",
        "Share of weekly demand": pct(day.sum() / grid.values.sum()),
    })
rec = pd.DataFrame(rows)

left, right = st.columns([2, 3])
with left:
    st.subheader("Recommended opening window")
    st.caption(f"Shortest daily window that captures {coverage:.0%} of demand.")
    st.dataframe(rec, hide_index=True, width="stretch")
with right:
    # Category profile vs. overall footfall in the area: where does the category under-index?
    b = base.groupby("hour")[metric].sum()
    c = h.groupby("hour")[metric].sum()
    prof = pd.DataFrame({"This category": c / c.sum(), "All spending in area": b / b.sum()}).reindex(range(24)).fillna(0)
    fig = px.line(prof.reset_index().melt(id_vars="hour"), x="hour", y="value", color="variable", markers=True,
                  labels={"hour": "Hour (local time)", "value": "Share of daily demand", "variable": ""},
                  title="Category vs. overall activity in the area")
    fig.update_yaxes(tickformat=".0%")
    fig.update_xaxes(dtick=2)
    st.plotly_chart(fig, width="stretch")

gap = (prof["All spending in area"] - prof["This category"]).sort_values(ascending=False)
untapped = [f"{hr:02d}:00" for hr, v in gap.items() if v > 0.01][:4]
if untapped and cat != ALL:
    st.success(f"**Untapped hours:** people in {area} are out spending around {', '.join(untapped)}, but "
               f"{cat.lower()} captures relatively little then – candidates for extended hours or happy-hour offers.")

weekend = grid.loc[[6, 7]].values.sum() / grid.values.sum()
st.caption(f"Weekend share of demand: **{weekend:.0%}** (Sat + Sun). Times with an unknown timestamp are excluded.")

compliance_note()
