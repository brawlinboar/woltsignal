import plotly.express as px
import streamlit as st

from lib import category_select, ctx_area, compliance_note, level_select, money, page, pct, q

page("Cross-sell Partners", "🧺",
     "Which other categories your customers also buy in – and how much more likely they are to do so than an "
     "average customer (lift). Use it to pick partners for joint promotions, co-location or loyalty coalitions.")

cat = category_select(label="Your category", include_all=False, default="Restaurants & Bars")
level = level_select(["neighborhood", "poland", "fua"], label="Customers living in", default="neighborhood")
if level == "poland":
    area = "POLAND"
else:
    areas = q("SELECT geo, MAX(customers_a) AS c FROM affinity WHERE geo_level = ? GROUP BY 1 ORDER BY 2 DESC", (level,))
    opts = areas["geo"].tolist()
    label = "Neighborhood" if level == "neighborhood" else "Metro area"
    preferred = ctx_area("fua")
    area = st.sidebar.selectbox(label, opts, index=opts.index(preferred) if preferred in opts else 0)

a = q("""SELECT group_b, customers_a, customers_both, share_of_a_also_buying_b, value_b FROM affinity
         WHERE geo_level = ? AND geo = ? AND group_a = ?""", (level, area, cat))
base = q("""SELECT group_a AS group_b, MAX(customers_a) AS customers_b FROM affinity
            WHERE geo_level = ? AND geo = ? GROUP BY 1""", (level, area))
total = q("""SELECT customers FROM customers WHERE geo_level = ? AND geo = ? AND segment = 'All segments'
             AND dimension = 'All customers'""", (level, area))["customers"].sum()
if a.empty or not total:
    st.warning("Not enough data.")
    st.stop()

a = a.merge(base, on="group_b")
a["base_rate"] = a["customers_b"] / total
a["lift"] = a["share_of_a_also_buying_b"] / a["base_rate"]
a["spend_per_shared_customer"] = a["value_b"] / a["customers_both"]
a = a.sort_values("lift", ascending=False)

c1, c2 = st.columns(2)
with c1:
    fig = px.bar(a, x="share_of_a_also_buying_b", y="group_b", orientation="h",
                 title=f"Share of {cat} customers who also buy in…",
                 labels={"share_of_a_also_buying_b": "", "group_b": ""})
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    fig.update_xaxes(tickformat=".0%")
    st.plotly_chart(fig, width="stretch")
with c2:
    fig = px.bar(a, x="lift", y="group_b", orientation="h", color="lift", color_continuous_scale="RdYlGn",
                 color_continuous_midpoint=1, title="Lift vs. average customer (1.0 = no affinity)",
                 labels={"lift": "Lift", "group_b": ""})
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, width="stretch")

top = a.head(3)
st.success("**Best partner categories:** " + "; ".join(
    f"{r.group_b} (lift {r.lift:.2f}, {pct(r.share_of_a_also_buying_b)} overlap, "
    f"{money(r.spend_per_shared_customer)} per shared customer)" for r in top.itertuples()))

st.subheader("Affinity matrix")
mat = q("""SELECT group_a, group_b, share_of_a_also_buying_b FROM affinity WHERE geo_level = ? AND geo = ?""",
        (level, area)).pivot(index="group_a", columns="group_b", values="share_of_a_also_buying_b")
fig = px.imshow(mat, color_continuous_scale="Blues", aspect="auto",
                labels={"x": "…also buy in", "y": "Customers of", "color": "Share"})
fig.update_coloraxes(colorbar_tickformat=".0%")
fig.update_layout(height=620)
st.plotly_chart(fig, width="stretch")

compliance_note()
