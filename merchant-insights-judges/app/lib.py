"""Shared helpers for the Merchant Insights app: data access, filters, formatting, compliance."""
import hashlib
import os
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
MARTS_DIR = Path(os.environ.get("MARTS_DIR", ROOT / "data" / "marts"))
MART_SETS = {
    "Usual": ROOT / "data" / "marts",
    "Final": ROOT / "data" / "marts_final",
}
SHOW_MERCHANT_NAMES = os.environ.get("SHOW_MERCHANT_NAMES", "0") == "1"

LEVEL_LABELS = {
    "neighborhood": "Neighborhood",
    "fua": "Metro area (FUA)",
    "lau": "Municipality (LAU)",
    "district": "Postal district (XX-xxx)",
    "postal": "Postal code",
    "poland": "All of Poland",
}


def is_krakow(name) -> bool:
    """True when a metro or municipality name is Kraków."""
    if not name:
        return False
    folded = str(name).upper().translate(str.maketrans({"Ó": "O", "Ł": "L"}))
    return "KRAKOW" in folded
WEEKDAYS = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}
ALL = "All categories"

PALETTE = ["#2563eb", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6", "#06b6d4", "#ec4899", "#84cc16",
           "#f97316", "#64748b", "#14b8a6", "#a855f7", "#eab308", "#0ea5e9"]


# --------------------------------------------------------------------------------------
# Data access
# --------------------------------------------------------------------------------------
def mart_dir() -> Path:
    """Folder selected in the sidebar. Falls back to the usual marts."""
    choice = st.session_state.get("mart_set", "Usual")
    path = MART_SETS.get(choice, MARTS_DIR)
    if path.exists() and any(path.glob("*.parquet")):
        return path
    return MARTS_DIR


def _ready(path: Path) -> bool:
    return path.exists() and any(path.glob("*.parquet"))


def select_mart():
    """Judges' app: Kraków metro marts. National marts are a separate long build."""
    options = [name for name, path in MART_SETS.items() if _ready(path)]
    if not options:
        return
    choice = os.environ.get("INSIGHTS_DATASET")
    if choice not in options:
        choice = "Final" if "Final" in options else options[0]
    st.session_state["mart_set"] = choice


@st.cache_resource
def _con(mart_path: str):
    path = Path(mart_path)
    if not _ready(path):
        return None
    con = duckdb.connect()
    for f in path.glob("*.parquet"):
        con.execute(f"CREATE VIEW {f.stem} AS SELECT * FROM read_parquet('{f.as_posix()}')")
    return con


@st.cache_data(show_spinner=False)
def q(sql: str, params: tuple = ()) -> pd.DataFrame:
    return _con(str(mart_dir())).execute(sql, list(params)).df()


def require_data():
    path = mart_dir()
    if _con(str(path)) is None:
        st.error(f"No data marts found in `{path}`. Build them first:\n\n"
                 "`python pipeline/build_marts.py --file /path/to/data.parquet`")
        st.stop()


# --------------------------------------------------------------------------------------
# Page scaffolding
# --------------------------------------------------------------------------------------
def business_ctx():
    """Business selected on the Action Plan page; other pages use it as their default filters."""
    return st.session_state.get("business")


def ctx_area(level):
    ctx = business_ctx()
    if not ctx:
        return None
    return {"fua": ctx.get("fua"), "lau": ctx.get("lau"), "postal": ctx.get("postal"),
            "district": (ctx.get("postal") or "")[:2] + "-xxx", "poland": "POLAND"}.get(level)


def page(title: str, icon: str, intro: str):
    full = title if title == "Merchant Insights" else f"{title} · Merchant Insights"
    st.set_page_config(page_title=full, page_icon=icon, layout="wide")
    select_mart()
    require_data()
    st.title(f"{icon} {title}")
    if st.session_state.get("mart_set") == "Final":
        st.warning(
            "Prototype for an individual merchant. Please allow about 5 minutes for this demo to be ready. "
            "The full national build takes too long to run here, so this view uses Kraków metro merchants only. "
            "It is not the whole country. Groups still follow the 30-card, 3-merchant, and 75% rules."
        )
    st.caption(intro)
    ctx = business_ctx()
    if ctx and title != "Action Plan":
        with st.sidebar:
            st.info(f"📌 **{ctx['label']}**  \n{ctx['category']} · {ctx['postal']} · {ctx.get('fua') or 'Poland'}  \n"
                    "Filters below start from this business.")
            if st.button("Clear business", key="clear_business"):
                del st.session_state["business"]
                st.rerun()


def compliance_note():
    st.caption("🔒 Only aggregated groups are shown: every cell covers ≥ 30 cards and ≥ 3 merchants, and no "
               "single merchant exceeds 75% of its value. Smaller cells are removed in the data pipeline. "
               "Amounts are in the dataset's fictional currency.")


# --------------------------------------------------------------------------------------
# Filters
# --------------------------------------------------------------------------------------
def categories(include_all=True):
    cats = q("SELECT DISTINCT category_group FROM supply WHERE category_group <> ? ORDER BY 1", (ALL,))
    lst = cats["category_group"].tolist()
    return ([ALL] + lst) if include_all else lst


def category_select(label="Category", key="cat", include_all=True, sidebar=True, default=None):
    opts = categories(include_all)
    ctx = business_ctx()
    if ctx and ctx.get("category") in opts:
        default = ctx["category"]
    idx = opts.index(default) if default in opts else 0
    container = st.sidebar if sidebar else st
    return container.selectbox(label, opts, index=idx, key=key)


def level_select(levels, label="Geography level", key="lvl", sidebar=True, default=None, follow_business=True):
    container = st.sidebar if sidebar else st
    if follow_business and business_ctx() and business_ctx().get("fua") and "fua" in levels:
        default = "fua"
    idx = levels.index(default) if default in levels else 0
    return container.selectbox(label, levels, index=idx, format_func=lambda x: LEVEL_LABELS.get(x, x), key=key)


def area_select(level, table="supply", label="Area", key="area", sidebar=True, default=None):
    """Areas sorted by total value so the largest ones come first."""
    if level == "poland":
        return "POLAND"
    geo_col = "home_geo" if table == "flows" else "geo"
    extra = "AND month = 0" if table in ("supply", "demand") else ""
    measure = "active_customers" if table == "retention" else "value"
    areas = q(f"""SELECT {geo_col} AS geo, SUM({measure}) AS v FROM {table}
                  WHERE geo_level = ? AND category_group = ? {extra}
                  GROUP BY 1 ORDER BY 2 DESC""", (level, ALL))["geo"].tolist()
    if not areas:
        st.warning("No areas available for this level.")
        st.stop()
    container = st.sidebar if sidebar else st
    if ctx_area(level) in areas:
        default = ctx_area(level)
    idx = areas.index(default) if default in areas else 0
    return container.selectbox(label, areas, index=idx, key=key)


# --------------------------------------------------------------------------------------
# Formatting
# --------------------------------------------------------------------------------------
def money(x, digits=0):
    if x is None or pd.isna(x):
        return "–"
    for div, suf in ((1e9, "B"), (1e6, "M"), (1e3, "k")):
        if abs(x) >= div:
            return f"{x / div:,.{max(digits, 1)}f}{suf}"
    return f"{x:,.{digits}f}"


def num(x):
    return "–" if x is None or pd.isna(x) else f"{x:,.0f}"


def pct(x, digits=1):
    return "–" if x is None or pd.isna(x) else f"{x * 100:.{digits}f}%"


def month_label(m):
    m = int(m)
    return f"{m // 100}-{m % 100:02d}"


def with_month_dates(df, col="month"):
    df = df.copy()
    df["date"] = pd.to_datetime(df[col].astype(int).astype(str) + "01", format="%Y%m%d")
    return df


def yoy(df, value_col="value", month_col="month"):
    """Growth of the last 6 months vs the same 6 months a year earlier."""
    months = sorted(m for m in df[month_col].unique() if m)
    last = months[-6:]
    prev = [m - 100 for m in last]
    cur = df[df[month_col].isin(last)][value_col].sum()
    prv = df[df[month_col].isin(prev)][value_col].sum()
    return (cur / prv - 1) if prv else None


def mask_merchant(name: str) -> str:
    if SHOW_MERCHANT_NAMES:
        return name
    return "Merchant " + hashlib.sha1(name.encode()).hexdigest()[:6].upper()


def kpi_row(items, per_row=3):
    for i in range(0, len(items), per_row):
        cols = st.columns(per_row)
        for c, (label, value, *help_) in zip(cols, items[i:i + per_row]):
            c.metric(label, value, help=help_[0] if help_ else None)

