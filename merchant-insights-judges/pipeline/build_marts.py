"""
Build aggregated, compliance-checked data marts for the Merchant Insights app.

Reads the raw transaction Parquet file once per chunk of cards and writes small Parquet
tables ("marts") to data/marts/. The app only ever reads these marts - never raw data.

Why chunks of cards: every card (with ALL its transactions) lands in exactly one chunk,
so customer-level logic (segments, loyalty, share of wallet) is exact inside a chunk and
distinct-card counts can simply be summed across chunks.

This script reproduces the marts in data/marts: Kraków neighborhoods, the
area-level compliance rules (30 cards, 3 merchants, no merchant over 75% of
the area and category), and opportunity_overlap.parquet.

If the other marts already exist and only the shared-card table is missing:
    python pipeline/build_overlap.py --file /path/to/data.parquet

The stricter per-group rules are a separate full pass:
    python pipeline/build_marts_final.py --file /path/to/data.parquet

Usage:
    python pipeline/build_marts.py --file /path/to/data.parquet
    python pipeline/build_marts.py --file /path/to/data.parquet --sample 1   # 1% of cards, quick test

Compliance (challenge rules): every published cell must cover >= 30 cards, >= 3 merchants,
and no single merchant may exceed 75% of the cell's value. Merchant concentration is
computed per (geography, category) and attached to every mart as `merchants`,
`top1_share` and `publishable`. The app hides rows where publishable is false.
"""
import argparse
import shutil
import sys
import time
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from categories import category_group_sql  # noqa: E402
from neighborhoods import (  # noqa: E402
    ensure_address_points,
    krakow_postal_codes,
    neighborhood_by_postal,
)

ROOT = Path(__file__).resolve().parents[1]

parser = argparse.ArgumentParser(description="Build data marts for the Merchant Insights app")
parser.add_argument("--file", required=True, help="raw transactions Parquet file")
parser.add_argument("--out", default=str(ROOT / "data" / "marts"), help="output folder for marts")
parser.add_argument("--sample", type=float, default=None, help="percent of cards to use (quick test)")
parser.add_argument("--chunks", type=int, default=20, help="number of card chunks")
parser.add_argument("--memory", default="8GB", help="DuckDB memory limit")
parser.add_argument("--min-cards", type=int, default=30)
parser.add_argument("--min-merchants", type=int, default=3)
parser.add_argument("--max-top1-share", type=float, default=0.75)
parser.add_argument("--dominance", type=float, default=0.5, help="threshold for 'Mainly: <group>' segments")
parser.add_argument("--resume", action="store_true",
                    help="skip chunk processing and only re-run the finalize step on an existing work database")
args = parser.parse_args()

out = Path(args.out)
work = out.parent / "_work"
out.mkdir(parents=True, exist_ok=True)
work.mkdir(parents=True, exist_ok=True)
db_file = work / "work.duckdb"
RESUME = args.resume and db_file.exists()
if not RESUME:
    db_file.unlink(missing_ok=True)

con = duckdb.connect(str(db_file))
con.execute(f"SET memory_limit = '{args.memory}'")
con.execute(f"SET temp_directory = '{work / 'tmp'}'")
con.execute("SET max_temp_directory_size = '60GB'")
con.execute("SET preserve_insertion_order = false")
con.execute("SET enable_progress_bar = false")

T0 = time.time()


def log(msg):
    print(f"[{time.time() - T0:6.0f}s] {msg}", flush=True)


src = f"read_parquet('{args.file}')"
sample_filter = f"AND hash(pymt_crd_acct_num_raw) % 10000 < {int(args.sample * 100)}" if args.sample else ""

# --------------------------------------------------------------------------------------
# 0) Postal code -> LAU (municipality) -> FUA (functional urban area) lookup.
#    Built from the cardholder enrichment columns and applied to merchant postal codes.
# --------------------------------------------------------------------------------------
if not RESUME:
    log("Building postal code lookup")
    con.execute(f"""
    CREATE TABLE postal_lookup AS
    SELECT pstl_cd_enr AS postal, mode(lau_enr) AS lau, mode(fua_enr) AS fua
    FROM {src}
    WHERE pstl_cd_enr IS NOT NULL AND lau_enr IS NOT NULL
    GROUP BY 1
""")
    log("Downloading Kraków neighborhoods from MSIP")
    ensure_address_points()
    lookup = neighborhood_by_postal().rename("neighborhood").reset_index()
    postcodes = pd.DataFrame({"postal": sorted(p for p in krakow_postal_codes() if p)})
    con.register("neighborhood_lookup_df", lookup)
    con.register("krakow_postal_df", postcodes)
    con.execute("CREATE TABLE neighborhood_lookup AS SELECT postal, neighborhood FROM neighborhood_lookup_df")
    con.execute("CREATE TABLE krakow_postal AS SELECT postal FROM krakow_postal_df")

GROUP_SQL = category_group_sql("mrch_catg_cd")

# Tables that receive per-chunk partial aggregates. Additive measures only.
if not RESUME:
    con.execute("""
CREATE TABLE p_supply   (geo_level VARCHAR, geo VARCHAR, category_group VARCHAR, month INTEGER,
                         transactions BIGINT, value DOUBLE, cards BIGINT);
CREATE TABLE p_sconc    (geo_level VARCHAR, geo VARCHAR, category_group VARCHAR, merchant VARCHAR, value DOUBLE);
CREATE TABLE p_demand   (geo_level VARCHAR, geo VARCHAR, category_group VARCHAR, month INTEGER,
                         transactions BIGINT, value DOUBLE, cards BIGINT, value_local DOUBLE,
                         value_elsewhere_pl DOUBLE, value_online DOUBLE, value_abroad DOUBLE);
CREATE TABLE p_dconc    (geo_level VARCHAR, geo VARCHAR, category_group VARCHAR, merchant VARCHAR, value DOUBLE);
CREATE TABLE p_flows    (geo_level VARCHAR, home_geo VARCHAR, dest_geo VARCHAR, category_group VARCHAR,
                         transactions BIGINT, value DOUBLE, cards BIGINT);
CREATE TABLE p_fconc    (geo_level VARCHAR, home_geo VARCHAR, dest_geo VARCHAR, category_group VARCHAR,
                         merchant VARCHAR, value DOUBLE);
CREATE TABLE p_hours    (geo_level VARCHAR, geo VARCHAR, category_group VARCHAR, weekday INTEGER, hour INTEGER,
                         transactions BIGINT, value DOUBLE, cards BIGINT);
CREATE TABLE p_channels (geo_level VARCHAR, geo VARCHAR, category_group VARCHAR, month INTEGER,
                         dimension VARCHAR, dim_value VARCHAR, transactions BIGINT, value DOUBLE, cards BIGINT);
CREATE TABLE p_mcc      (geo_level VARCHAR, geo VARCHAR, category_group VARCHAR, mcc INTEGER, merchant_category VARCHAR,
                         transactions BIGINT, value DOUBLE, cards BIGINT);
CREATE TABLE p_mconc    (geo_level VARCHAR, geo VARCHAR, mcc INTEGER, merchant VARCHAR, value DOUBLE);
CREATE TABLE p_retention(geo_level VARCHAR, geo VARCHAR, category_group VARCHAR, month INTEGER,
                         active_customers BIGINT, returning_customers BIGINT, new_customers BIGINT);
CREATE TABLE p_affinity (geo_level VARCHAR, geo VARCHAR, group_a VARCHAR, group_b VARCHAR,
                         customers_both BIGINT, value_b DOUBLE);
CREATE TABLE p_customers(geo_level VARCHAR, geo VARCHAR, segment VARCHAR, dimension VARCHAR, dim_value VARCHAR,
                         customers BIGINT, transactions BIGINT, value DOUBLE);
CREATE TABLE p_seg_cat  (geo_level VARCHAR, geo VARCHAR, segment VARCHAR, category_group VARCHAR,
                         customers BIGINT, transactions BIGINT, value DOUBLE);
CREATE TABLE p_merchant (merchant VARCHAR, geo VARCHAR, category_group VARCHAR, transactions BIGINT, value DOUBLE,
                         customers BIGINT, repeat_customers BIGINT, customers_group_value DOUBLE,
                         customers_group_value_same_area DOUBLE, customers_group_value_online DOUBLE);
CREATE TABLE p_m_catch  (merchant VARCHAR, home_fua VARCHAR, home_district VARCHAR, customers BIGINT, value DOUBLE);
CREATE TABLE p_m_hours  (merchant VARCHAR, weekday INTEGER, hour INTEGER, transactions BIGINT, value DOUBLE);
CREATE TABLE p_m_seg    (merchant VARCHAR, segment VARCHAR, customers BIGINT, value DOUBLE);
CREATE TABLE p_opp_market  (postal VARCHAR, category_group VARCHAR, channel VARCHAR, origin VARCHAR,
                         card_group VARCHAR, transactions BIGINT, value DOUBLE, cards BIGINT);
CREATE TABLE p_opp_mconc   (postal VARCHAR, category_group VARCHAR, channel VARCHAR, origin VARCHAR,
                         card_group VARCHAR, merchant VARCHAR, value DOUBLE);
CREATE TABLE p_opp_merchant(postal VARCHAR, category_group VARCHAR, merchant VARCHAR, channel VARCHAR,
                         origin VARCHAR, card_group VARCHAR, transactions BIGINT, value DOUBLE, cards BIGINT);
CREATE TABLE p_opp_delivery(postal VARCHAR, category_group VARCHAR, merchant VARCHAR, platform VARCHAR,
                         transactions BIGINT, value DOUBLE, cards BIGINT);
CREATE TABLE p_opp_cards   (postal VARCHAR, category_group VARCHAR, merchant VARCHAR, cards BIGINT);
CREATE TABLE p_opp_overlap (postal VARCHAR, category_group VARCHAR, merchant_a VARCHAR, merchant_b VARCHAR,
                         shared_cards BIGINT);
""")

# Geography expressions. Merchant side uses only card-present, Polish merchants.
M_GEO = {
    "neighborhood": "m_neighborhood",
    "postal": "m_postal",
    "district": "m_district",
    "lau": "m_lau",
    "fua": "m_fua",
    "poland": "'POLAND'",
}
C_GEO = {
    "neighborhood": "c_neighborhood",
    "postal": "c_postal",
    "district": "c_district",
    "lau": "c_lau",
    "fua": "c_fua",
    "poland": "'POLAND'",
}


def with_all_groups(select_keys, measures, table, where, geo_expr, level, extra_keys=""):
    """INSERT rows for every category group AND for 'All categories'."""
    ek = f", {extra_keys}" if extra_keys else ""
    return f"""
        SELECT '{level}', {geo_expr} AS geo, COALESCE(category_group, 'All categories') {ek}, {measures}
        FROM {table} WHERE {where} AND {geo_expr} IS NOT NULL
        GROUP BY GROUPING SETS (({geo_expr}, category_group {ek}), ({geo_expr} {ek}))
    """


def process_chunk(k, K):
    # ---- chunk rows ------------------------------------------------------------------
    con.execute("DROP TABLE IF EXISTS c")
    con.execute(f"""
        CREATE TEMP TABLE c AS
        WITH raw AS (
            SELECT *,
                   hash(pymt_crd_acct_num_raw) AS card_id,
                   CASE WHEN tran_id_gmt_tm <> '000000' THEN
                        timezone('Europe/Warsaw', timezone('UTC',
                            CAST(prch_dt AS DATE) + CAST(strptime(tran_id_gmt_tm, '%H%M%S') AS TIME)))
                   END AS ts_local
            FROM {src}
            WHERE hash(pymt_crd_acct_num_raw) % {K} = {k} {sample_filter}
        )
        SELECT
            r.card_id,
            CAST(r.mrch_catg_cd AS INTEGER)                       AS mcc,
            r.mrch_catg_nm                                        AS merchant_category,
            {GROUP_SQL}                                           AS category_group,
            r.mrch_nm_raw                                         AS merchant,
            CAST(r.cs_tran_amt AS DOUBLE)                         AS amt,
            r.prch_mnth_id                                        AS month,
            isodow(CAST(r.prch_dt AS DATE))                       AS weekday,
            hour(r.ts_local)                                      AS hour,
            r.channel_flg                                         AS channel,
            r.transaction_pos_entry_mode                          AS entry_mode,
            r.cp_flag = 1                                         AS card_present,
            r.prod_id_pltfrm_cd_vcis                              AS product,
            r.issr_jurn                                           AS jurisdiction,
            CASE WHEN r.crd_typ_nm IN ('INFINITE','PLATINUM','PREMIER','VISA SIGNATURE CARD') THEN 'Premium'
                 WHEN r.crd_typ_nm IN ('BUSINESS','CORPORATE T&E CARD') OR r.prod_id_pltfrm_cd_vcis IN ('BZ','CO','GV')
                      THEN 'Business'
                 ELSE 'Standard' END                              AS card_tier,
            r.mrch_ctry_nm = 'POLAND'                             AS merchant_in_pl,
            (r.cp_flag = 1 AND r.mrch_ctry_nm = 'POLAND')         AS local_pl,
            CASE WHEN regexp_full_match(r.mrch_postal_code, '[0-9]{{2}}-[0-9]{{3}}') AND r.mrch_ctry_nm = 'POLAND'
                 THEN r.mrch_postal_code END                      AS m_postal,
            r.pstl_cd_enr                                         AS c_postal,
            CASE
                WHEN length(regexp_replace(coalesce(r.pstl_cd_enr, ''), '[^0-9]', '', 'g')) = 5
                THEN substring(regexp_replace(coalesce(r.pstl_cd_enr, ''), '[^0-9]', '', 'g'), 1, 2)
                     || '-' ||
                     substring(regexp_replace(coalesce(r.pstl_cd_enr, ''), '[^0-9]', '', 'g'), 3, 3)
                ELSE NULLIF(trim(r.pstl_cd_enr), '')
            END                                                   AS c_postal_key,
            substr(r.pstl_cd_enr, 1, 2) || '-xxx'                 AS c_district,
            r.lau_enr                                             AS c_lau,
            r.fua_enr                                             AS c_fua,
            r.tran_id_gmt_tm <> '000000'                          AS time_known,
            r.issr_ctry_nm                                        AS issr_ctry_nm,
            r.crd_typ_nm                                          AS crd_typ_nm
        FROM raw r
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE c2 AS
        SELECT c.*,
               CASE WHEN m_postal IS NOT NULL THEN substr(m_postal, 1, 2) || '-xxx' END AS m_district,
               pl.lau AS m_lau, pl.fua AS m_fua,
               mn.neighborhood AS m_neighborhood,
               cn.neighborhood AS c_neighborhood,
               CASE
                   WHEN upper(trim(issr_ctry_nm)) IS NOT NULL AND upper(trim(issr_ctry_nm)) <> 'POLAND'
                       THEN 'TOURIST INTERNATIONAL'
                   WHEN c_postal_key IS NOT NULL AND c_postal_key <> '' AND kp.postal IS NULL
                       THEN 'TOURIST DOMESTIC'
                   WHEN cn.neighborhood IS NOT NULL AND mn.neighborhood IS NOT NULL
                        AND cn.neighborhood = mn.neighborhood
                       THEN 'LOCAL'
                   WHEN cn.neighborhood IS NOT NULL AND mn.neighborhood IS NOT NULL
                        AND cn.neighborhood <> mn.neighborhood
                       THEN 'COMMUTER'
                   ELSE NULL
               END AS visitor_origin
        FROM c
        LEFT JOIN postal_lookup pl ON c.m_postal = pl.postal
        LEFT JOIN neighborhood_lookup mn ON mn.postal = c.m_postal
        LEFT JOIN neighborhood_lookup cn ON cn.postal = c.c_postal_key
        LEFT JOIN krakow_postal kp ON kp.postal = c.c_postal_key
    """)
    con.execute("DROP TABLE c")
    con.execute("ALTER TABLE c2 RENAME TO c")

    # ---- card profiles & segments ------------------------------------------------------
    con.execute("""
        CREATE OR REPLACE TEMP TABLE card_grp AS
        SELECT card_id, category_group, COUNT(*) AS n, SUM(amt) AS v FROM c GROUP BY 1, 2
    """)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE cardp AS
        WITH g AS (
            SELECT card_id, SUM(n) AS n, SUM(v) AS v,
                   arg_max(category_group, v) AS dom_group, MAX(v) / NULLIF(SUM(v), 0) AS dom_share
            FROM card_grp GROUP BY 1
        ), t AS (
            SELECT card_id,
                   MIN(month) AS first_month, MAX(month) AS last_month,
                   mode(c_postal) AS home_postal, mode(c_district) AS home_district,
                   mode(c_lau) AS home_lau, mode(c_fua) AS home_fua,
                   mode(c_neighborhood) AS home_neighborhood,
                   AVG(CASE WHEN NOT card_present THEN 1 ELSE 0 END) AS online_share,
                   AVG(CASE WHEN weekday >= 6 THEN 1 ELSE 0 END) AS weekend_share,
                   MAX(CASE WHEN NOT merchant_in_pl AND card_present THEN 1 ELSE 0 END) = 1 AS travels_abroad,
                   mode(card_tier) AS card_tier,
                   mode(crd_typ_nm) AS card_type,
                   SUM(CASE WHEN hour BETWEEN 6 AND 10 THEN 1 ELSE 0 END)  AS h_morning,
                   SUM(CASE WHEN hour BETWEEN 11 AND 16 THEN 1 ELSE 0 END) AS h_day,
                   SUM(CASE WHEN hour BETWEEN 17 AND 21 THEN 1 ELSE 0 END) AS h_evening,
                   SUM(CASE WHEN hour >= 22 OR hour <= 5 THEN 1 ELSE 0 END) AS h_night
            FROM c GROUP BY 1
        )
        SELECT g.card_id, g.n, g.v, t.*  EXCLUDE (card_id),
            CASE WHEN g.n < 3 THEN 'Occasional (<3 transactions)'
                 WHEN g.dom_share >= {args.dominance} THEN 'Mainly: ' || g.dom_group
                 ELSE 'Diversified (no dominant category)' END AS segment,
            CASE WHEN g.n / ((t.last_month // 100 - t.first_month // 100) * 12
                             + t.last_month % 100 - t.first_month % 100 + 1.0) < 4 THEN '1 Low (<4 tx/month)'
                 WHEN g.n / ((t.last_month // 100 - t.first_month // 100) * 12
                             + t.last_month % 100 - t.first_month % 100 + 1.0) < 15 THEN '2 Medium (4-15 tx/month)'
                 ELSE '3 High (15+ tx/month)' END AS activity,
            CASE WHEN h_morning + h_day + h_evening + h_night = 0 THEN 'Unknown'
                 WHEN h_morning >= greatest(h_day, h_evening, h_night) THEN 'Morning (6-11)'
                 WHEN h_day >= greatest(h_evening, h_night) THEN 'Daytime (11-17)'
                 WHEN h_evening >= h_night THEN 'Evening (17-22)'
                 ELSE 'Night (22-6)' END AS daypart,
            CASE WHEN online_share >= 0.3 THEN 'Online-heavy (30%+)' ELSE 'Mostly in-store' END AS channel_pref,
            CASE WHEN weekend_share >= 0.4 THEN 'Weekend shopper (40%+)' ELSE 'Weekday shopper' END AS weekend_pref,
            CASE WHEN g.n > (SELECT volume_median FROM card_medians)
                 THEN 'Above median volume' ELSE 'At or below median volume' END AS volume_band,
            CASE WHEN g.v / NULLIF(g.n, 0) > (SELECT value_median FROM card_medians)
                 THEN 'Above median value' ELSE 'At or below median value' END AS value_band
        FROM g JOIN t USING (card_id)
    """)

    # ---- supply (spend at merchants located in an area) --------------------------------
    for lvl, ge in M_GEO.items():
        con.execute("INSERT INTO p_supply " + with_all_groups(
            "", "COUNT(*), SUM(amt), COUNT(DISTINCT card_id)", "c", "local_pl", ge, lvl, "month"))
        con.execute("INSERT INTO p_supply " + with_all_groups(   # month = 0 -> whole period
            "", "COUNT(*), SUM(amt), COUNT(DISTINCT card_id)", "(SELECT *, 0 AS all_months FROM c)",
            "local_pl", ge, lvl, "all_months"))
        con.execute(f"""
            INSERT INTO p_sconc
            SELECT '{lvl}', {ge}, COALESCE(category_group, 'All categories'), merchant, SUM(amt)
            FROM c WHERE local_pl AND {ge} IS NOT NULL
            GROUP BY GROUPING SETS (({ge}, category_group, merchant), ({ge}, merchant))
        """)

    # ---- demand (spend of residents of an area, wherever they spend) -------------------
    for lvl, ge in C_GEO.items():
        mge = M_GEO[lvl]
        local_cond = "local_pl" if lvl == "poland" else f"local_pl AND {mge} = {ge}"
        con.execute("INSERT INTO p_demand " + with_all_groups(
            "", f"""COUNT(*), SUM(amt), COUNT(DISTINCT card_id),
                   SUM(CASE WHEN {local_cond} THEN amt ELSE 0 END),
                   SUM(CASE WHEN local_pl AND NOT ({local_cond}) THEN amt ELSE 0 END),
                   SUM(CASE WHEN NOT card_present THEN amt ELSE 0 END),
                   SUM(CASE WHEN card_present AND NOT merchant_in_pl THEN amt ELSE 0 END)""",
            "c", "TRUE", ge, lvl, "month"))
        con.execute("INSERT INTO p_demand " + with_all_groups(   # month = 0 -> whole period
            "", f"""COUNT(*), SUM(amt), COUNT(DISTINCT card_id),
                   SUM(CASE WHEN {local_cond} THEN amt ELSE 0 END),
                   SUM(CASE WHEN local_pl AND NOT ({local_cond}) THEN amt ELSE 0 END),
                   SUM(CASE WHEN NOT card_present THEN amt ELSE 0 END),
                   SUM(CASE WHEN card_present AND NOT merchant_in_pl THEN amt ELSE 0 END)""",
            "(SELECT *, 0 AS all_months FROM c)", "TRUE", ge, lvl, "all_months"))
        con.execute(f"""
            INSERT INTO p_dconc
            SELECT '{lvl}', {ge}, COALESCE(category_group, 'All categories'), merchant, SUM(amt)
            FROM c WHERE {ge} IS NOT NULL
            GROUP BY GROUPING SETS (({ge}, category_group, merchant), ({ge}, merchant))
        """)

    # ---- flows: where residents of area A spend (area B) ---------------------------------
    for lvl in ("neighborhood", "lau", "fua"):
        con.execute(f"""
            INSERT INTO p_flows
            SELECT '{lvl}', c_{lvl}, m_{lvl}, COALESCE(category_group, 'All categories'),
                   COUNT(*), SUM(amt), COUNT(DISTINCT card_id)
            FROM c WHERE local_pl AND c_{lvl} IS NOT NULL AND m_{lvl} IS NOT NULL
            GROUP BY GROUPING SETS ((c_{lvl}, m_{lvl}, category_group), (c_{lvl}, m_{lvl}))
        """)
        con.execute(f"""
            INSERT INTO p_fconc
            SELECT '{lvl}', c_{lvl}, m_{lvl}, COALESCE(category_group, 'All categories'), merchant, SUM(amt)
            FROM c WHERE local_pl AND c_{lvl} IS NOT NULL AND m_{lvl} IS NOT NULL
            GROUP BY GROUPING SETS ((c_{lvl}, m_{lvl}, category_group, merchant), (c_{lvl}, m_{lvl}, merchant))
        """)

    # ---- hours (local time, merchant location) ---------------------------------------------
    for lvl in ("neighborhood", "lau", "fua", "poland"):
        ge = M_GEO[lvl]
        con.execute("INSERT INTO p_hours " + with_all_groups(
            "", "COUNT(*), SUM(amt), COUNT(DISTINCT card_id)", "c", "local_pl AND hour IS NOT NULL",
            ge, lvl, "weekday, hour"))

    # ---- channels, payment methods, card types, tourists -------------------------------------
    for lvl in ("neighborhood", "fua", "poland"):
        ge = M_GEO[lvl]
        where = {"neighborhood": "m_neighborhood IS NOT NULL", "fua": "m_fua IS NOT NULL", "poland": "TRUE"}[lvl]
        for dim, expr in {
            "Channel": "channel",
            "Entry mode": "entry_mode",
            "Card present": "CASE WHEN card_present THEN 'In-store' ELSE 'Online / not present' END",
            "Card product": "CASE product WHEN 'CN' THEN 'Consumer' WHEN 'BZ' THEN 'Business' "
                            "WHEN 'CO' THEN 'Commercial' WHEN 'GV' THEN 'Government' ELSE product END",
            "Card tier": "card_tier",
            "Cardholder origin": "CASE jurisdiction WHEN 'Domestic' THEN 'Domestic' "
                                 "WHEN 'Intra' THEN 'Foreign (EU/Europe)' ELSE 'Foreign (outside Europe)' END",
        }.items():
            con.execute(f"""
                INSERT INTO p_channels
                SELECT '{lvl}', {ge}, COALESCE(category_group, 'All categories'), month, '{dim}', {expr},
                       COUNT(*), SUM(amt), COUNT(DISTINCT card_id)
                FROM c WHERE {where}
                GROUP BY GROUPING SETS (({ge}, category_group, month, {expr}), ({ge}, month, {expr}))
            """)

    # ---- MCC detail --------------------------------------------------------------------------
    for lvl in ("neighborhood", "fua", "poland"):
        ge = M_GEO[lvl]
        con.execute(f"""
            INSERT INTO p_mcc
            SELECT '{lvl}', {ge}, category_group, mcc, any_value(merchant_category),
                   COUNT(*), SUM(amt), COUNT(DISTINCT card_id)
            FROM c WHERE local_pl AND {ge} IS NOT NULL GROUP BY 2, 3, 4
        """)
        con.execute(f"""
            INSERT INTO p_mconc SELECT '{lvl}', {ge}, mcc, merchant, SUM(amt)
            FROM c WHERE local_pl AND {ge} IS NOT NULL GROUP BY 2, 3, 4
        """)

    # ---- retention: returning vs new customers per month --------------------------------------
    for lvl in ("neighborhood", "fua", "poland"):
        ge = M_GEO[lvl]
        con.execute(f"""
            INSERT INTO p_retention
            WITH a AS (
                SELECT DISTINCT {ge} AS geo, category_group, card_id, month
                FROM c WHERE local_pl AND {ge} IS NOT NULL
                UNION ALL
                SELECT DISTINCT {ge}, 'All categories', card_id, month
                FROM c WHERE local_pl AND {ge} IS NOT NULL
            ), l AS (
                SELECT *,
                    lag(month) OVER (PARTITION BY geo, category_group, card_id ORDER BY month) AS prev_month,
                    row_number() OVER (PARTITION BY geo, category_group, card_id ORDER BY month) AS rn
                FROM a
            )
            SELECT '{lvl}', geo, category_group, month, COUNT(*),
                   SUM(CASE WHEN prev_month IS NOT NULL AND
                            (month - prev_month = 1 OR (month % 100 = 1 AND prev_month % 100 = 12
                                                      AND month // 100 - prev_month // 100 = 1))
                            THEN 1 ELSE 0 END),
                   SUM(CASE WHEN rn = 1 THEN 1 ELSE 0 END)
            FROM l GROUP BY 1, 2, 3, 4
        """)

    # ---- cross-shopping affinity between category groups ------------------------------------------
    con.execute("""
        INSERT INTO p_affinity
        SELECT lvl, geo, g1.category_group, g2.category_group, COUNT(*), SUM(g2.v)
        FROM card_grp g1
        JOIN card_grp g2 ON g1.card_id = g2.card_id
        JOIN (SELECT card_id, 'fua' AS lvl, home_fua AS geo FROM cardp WHERE home_fua IS NOT NULL
              UNION ALL SELECT card_id, 'poland', 'POLAND' FROM cardp
              UNION ALL SELECT card_id, 'neighborhood', home_neighborhood FROM cardp
                        WHERE home_neighborhood IS NOT NULL) p ON p.card_id = g1.card_id
        GROUP BY 1, 2, 3, 4
    """)

    # ---- customer cube (one row per combination of customer attributes) -----------------------------
    # Customer profiles: distribution of behavioural attributes per home area and segment
    for dim, expr in {
        "All customers": "'All'",
        "Activity": "activity",
        "Preferred time of day": "daypart",
        "Channel preference": "channel_pref",
        "Weekend vs weekday": "weekend_pref",
        "Travels abroad": "CASE WHEN travels_abroad THEN 'Shops abroad' ELSE 'Only in Poland' END",
        "Card tier": "card_tier",
        "Card type": "card_type",
        "Volume": "volume_band",
        "Value": "value_band",
    }.items():
        con.execute(f"""
            INSERT INTO p_customers
            SELECT lvl, geo, COALESCE(segment, 'All segments'), '{dim}', {expr}, COUNT(*), SUM(n), SUM(v)
            FROM (SELECT *, 'fua' AS lvl, home_fua AS geo FROM cardp WHERE home_fua IS NOT NULL
                  UNION ALL SELECT *, 'poland', 'POLAND' FROM cardp
                  UNION ALL SELECT *, 'neighborhood', home_neighborhood FROM cardp
                            WHERE home_neighborhood IS NOT NULL)
            GROUP BY GROUPING SETS ((lvl, geo, segment, {expr}), (lvl, geo, {expr}))
        """)
    con.execute("""
        INSERT INTO p_customers
        SELECT 'neighborhood', c.m_neighborhood, COALESCE(p.segment, 'All segments'),
               'Visitor origin', c.visitor_origin,
               COUNT(DISTINCT c.card_id), COUNT(*), SUM(c.amt)
        FROM c
        JOIN cardp p USING (card_id)
        WHERE c.m_neighborhood IS NOT NULL AND c.visitor_origin IS NOT NULL
        GROUP BY GROUPING SETS (
            (c.m_neighborhood, p.segment, c.visitor_origin),
            (c.m_neighborhood, c.visitor_origin)
        )
    """)
    con.execute("""
        INSERT INTO p_seg_cat
        SELECT lvl, geo, p.segment, g.category_group, COUNT(*), SUM(g.n), SUM(g.v)
        FROM card_grp g
        JOIN (SELECT card_id, segment, 'fua' AS lvl, home_fua AS geo FROM cardp WHERE home_fua IS NOT NULL
              UNION ALL SELECT card_id, segment, 'poland', 'POLAND' FROM cardp
              UNION ALL SELECT card_id, segment, 'neighborhood', home_neighborhood FROM cardp
                        WHERE home_neighborhood IS NOT NULL) p USING (card_id)
        GROUP BY 1, 2, 3, 4
    """)

    # ---- merchant view: share of wallet & leakage ---------------------------------------------------
    con.execute("""
        CREATE OR REPLACE TEMP TABLE cm AS
        SELECT card_id, merchant, COALESCE(m_fua, 'Online / unknown') AS geo, category_group,
               COUNT(*) AS n, SUM(amt) AS v
        FROM c GROUP BY 1, 2, 3, 4
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE cg AS
        SELECT card_id, category_group, COALESCE(m_fua, 'Online / unknown') AS geo,
               SUM(amt) AS v, SUM(CASE WHEN NOT card_present THEN amt ELSE 0 END) AS v_online
        FROM c GROUP BY 1, 2, 3
    """)
    con.execute("""
        INSERT INTO p_merchant
        WITH tot AS (SELECT card_id, category_group, SUM(v) AS v, SUM(v_online) AS v_online FROM cg GROUP BY 1, 2)
        SELECT cm.merchant, cm.geo, cm.category_group, SUM(cm.n), SUM(cm.v), COUNT(*),
               SUM(CASE WHEN cm.n >= 2 THEN 1 ELSE 0 END),
               SUM(tot.v), SUM(cg.v), SUM(tot.v_online)
        FROM cm
        JOIN tot USING (card_id, category_group)
        JOIN cg  USING (card_id, category_group, geo)
        GROUP BY 1, 2, 3
    """)
    con.execute("""
        INSERT INTO p_m_catch
        SELECT cm.merchant, p.home_fua, p.home_district, COUNT(DISTINCT cm.card_id), SUM(cm.v)
        FROM cm JOIN cardp p USING (card_id) GROUP BY 1, 2, 3
    """)
    con.execute("""
        INSERT INTO p_m_hours
        SELECT merchant, weekday, hour, COUNT(*), SUM(amt) FROM c WHERE hour IS NOT NULL GROUP BY 1, 2, 3
    """)
    con.execute("""
        INSERT INTO p_m_seg
        SELECT m.merchant, p.segment, COUNT(*), SUM(m.v)
        FROM (SELECT card_id, merchant, SUM(v) AS v FROM cm GROUP BY 1, 2) m JOIN cardp p USING (card_id)
        GROUP BY 1, 2
    """)

    # ---- opportunity engine: market (denominator), merchant (numerator), delivery pool ------
    # Cell dimensions shared by opportunity_market and opportunity_merchant. `origin` compares
    # the cardholder's home municipality (c_lau) to the MERCHANT's municipality (m_lau, already
    # derived from the postal_lookup join above) - not a new lookup, per the README's existing
    # postal -> LAU mapping.
    OPP_CHANNEL = ("CASE WHEN channel = 'mobile' THEN 'mobile' "
                   "WHEN channel = 'cp_contactless' THEN 'contactless' ELSE 'other' END")
    OPP_ORIGIN = "CASE WHEN issr_ctry_nm = 'POLAND' AND c_lau = m_lau THEN 'local' ELSE 'elsewhere' END"
    OPP_CARD_GROUP = ("CASE WHEN crd_typ_nm = 'CLASSIC' THEN 'classic' "
                       "WHEN crd_typ_nm IN ('INFINITE','PLATINUM','PREMIER','VISA SIGNATURE CARD') THEN 'premium' "
                       "ELSE 'other' END")
    OPP_WHERE = "merchant_in_pl AND m_postal IS NOT NULL AND time_known"

    con.execute(f"""
        INSERT INTO p_opp_market
        SELECT m_postal, category_group, {OPP_CHANNEL}, {OPP_ORIGIN}, {OPP_CARD_GROUP},
               COUNT(*), SUM(amt), COUNT(DISTINCT card_id)
        FROM c WHERE {OPP_WHERE}
        GROUP BY 1, 2, 3, 4, 5
    """)
    con.execute(f"""
        INSERT INTO p_opp_mconc
        SELECT m_postal, category_group, {OPP_CHANNEL}, {OPP_ORIGIN}, {OPP_CARD_GROUP}, merchant, SUM(amt)
        FROM c WHERE {OPP_WHERE}
        GROUP BY 1, 2, 3, 4, 5, 6
    """)
    con.execute(f"""
        INSERT INTO p_opp_merchant
        SELECT m_postal, category_group, merchant, {OPP_CHANNEL}, {OPP_ORIGIN}, {OPP_CARD_GROUP},
               COUNT(*), SUM(amt), COUNT(DISTINCT card_id)
        FROM c WHERE {OPP_WHERE}
        GROUP BY 1, 2, 3, 4, 5, 6
    """)

    # Delivery pool: for the cards seen at each (postal, category_group, merchant) cell, their
    # TOTAL spend (anywhere, not just at that cell) at Polish food-delivery aggregators. Every
    # transaction for a card lives in this same chunk (cards are chunked whole), so this stays a
    # single-chunk computation - no cross-chunk join needed.
    # Uber Eats, Deliveroo and Bolt Food are deliberately excluded: verified against this dataset,
    # all three have ZERO Polish-merchant transactions here (Deliveroo exited Poland in 2021, Uber
    # Eats followed) - their rows are Polish cardholders ordering abroad, not addressable local
    # delivery demand, and including them would overstate the opportunity.
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE opp_cell_cards AS
        SELECT DISTINCT m_postal AS postal, category_group, merchant, card_id
        FROM c WHERE {OPP_WHERE}
    """)
    # Co-location evidence. A merchant's own second terminal and an unrelated neighbour look
    # IDENTICAL in the data by name, postcode and category - but not by customers. Two tills in
    # one restaurant share nearly all their cards; two shops in one mall share only the cards of
    # people who visit both. So the app flags candidate siblings by card overlap instead of
    # asking the merchant to guess from a bare list.
    #
    # Both aggregates are additive across chunks because cards are chunked WHOLE: every
    # transaction for a card is in this same chunk, so a card is counted in exactly one chunk's
    # partial and the sums compose. No cross-chunk join is needed.
    #
    # The pair self-join is bounded by cards, not by merchants: its cost is the number of
    # (merchant, merchant) pairs each CARD participates in, and a card visits only a handful of
    # merchants in one postcode. A postcode with 2,400 merchants does not produce 2,400^2 rows.
    con.execute("""
        INSERT INTO p_opp_cards
        SELECT postal, category_group, merchant, COUNT(*)
        FROM opp_cell_cards GROUP BY 1, 2, 3
    """)
    con.execute("""
        INSERT INTO p_opp_overlap
        SELECT a.postal, a.category_group, a.merchant, b.merchant, COUNT(*)
        FROM opp_cell_cards a
        JOIN opp_cell_cards b
          ON a.postal = b.postal AND a.category_group = b.category_group
         AND a.card_id = b.card_id
         AND a.merchant < b.merchant
        GROUP BY 1, 2, 3, 4
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE opp_card_delivery AS
        SELECT card_id,
               CASE WHEN LOWER(merchant) LIKE '%glovo%' THEN 'Glovo'
                    WHEN LOWER(merchant) LIKE '%wolt%' THEN 'Wolt'
                    WHEN LOWER(merchant) LIKE '%pyszne%' THEN 'Pyszne.pl' END AS platform,
               COUNT(*) AS n, SUM(amt) AS v
        FROM c
        WHERE merchant_in_pl AND (LOWER(merchant) LIKE '%glovo%' OR LOWER(merchant) LIKE '%wolt%'
                                   OR LOWER(merchant) LIKE '%pyszne%')
        GROUP BY 1, 2
    """)
    con.execute("""
        INSERT INTO p_opp_delivery
        SELECT cc.postal, cc.category_group, cc.merchant, cd.platform,
               SUM(cd.n), SUM(cd.v), COUNT(DISTINCT cc.card_id)
        FROM opp_cell_cards cc JOIN opp_card_delivery cd USING (card_id)
        GROUP BY 1, 2, 3, 4
    """)


# --------------------------------------------------------------------------------------
# Run chunks
# --------------------------------------------------------------------------------------
K = 1 if args.sample else args.chunks
if not RESUME:
    log("Card volume and value, one row per card")
    con.execute("CREATE TABLE card_stats (txns BIGINT, value DOUBLE)")
    for k in range(K):
        con.execute(f"""
            INSERT INTO card_stats
            SELECT count(*), sum(CAST(cs_tran_amt AS DOUBLE))
            FROM {src}
            WHERE hash(pymt_crd_acct_num_raw) % {K} = {k} {sample_filter}
            GROUP BY pymt_crd_acct_num_raw
        """)
        log(f"  card stats chunk {k + 1}/{K}")
    con.execute("""
        CREATE TABLE card_medians AS
        SELECT median(txns) AS volume_median,
               median(value / txns) AS value_median
        FROM card_stats
        WHERE txns > 0
    """)
for k in ([] if RESUME else range(K)):
    t = time.time()
    process_chunk(k, K)
    log(f"chunk {k + 1}/{K} done ({time.time() - t:.0f}s)")

# --------------------------------------------------------------------------------------
# Finalize: sum partials, attach compliance, write Parquet
# --------------------------------------------------------------------------------------
log("Finalizing marts")
MC, MM, MT = args.min_cards, args.min_merchants, args.max_top1_share


def build_conc(target, table, keys, partition):
    """Merchant count and top-1 share per cell, computed one partition at a time to bound memory."""
    con.execute(f"DROP TABLE IF EXISTS {target}")
    parts = con.execute(f"SELECT DISTINCT {', '.join(partition)} FROM {table}").fetchall()
    where = " AND ".join(f"({c}) = ?" for c in partition)
    for i, vals in enumerate(parts):
        sql = f"""
            SELECT {keys}, COUNT(*) AS merchants, MAX(value) / NULLIF(SUM(value), 0) AS top1_share
            FROM (SELECT {keys}, merchant, SUM(value) AS value FROM {table} WHERE {where} GROUP BY ALL)
            GROUP BY ALL
        """
        con.execute(f"CREATE TABLE {target} AS {sql}" if i == 0 else f"INSERT INTO {target} {sql}", list(vals))
    log(f"  {target}: {len(parts)} partitions")


def publishable(cards_col="cards"):
    return f"({cards_col} >= {MC} AND merchants >= {MM} AND top1_share <= {MT})"


build_conc("sconc", "p_sconc", "geo_level, geo, category_group", ["geo_level", "category_group"])
build_conc("dconc", "p_dconc", "geo_level, geo, category_group", ["geo_level", "category_group"])
build_conc("fconc", "p_fconc", "geo_level, home_geo, dest_geo, category_group", ["geo_level", "category_group"])
build_conc("mconc", "p_mconc", "geo_level, geo, mcc", ["geo_level", "mcc % 10"])
# Concentration is computed at the FULL published cell grain, not at (postal,
# category_group). The market mart publishes one row per channel x origin x
# card_group, and those dimensions re-slice the merchant mix: a thin cell can be
# ~100% one merchant while the postal code overall is diverse. Testing top1_share
# at the coarser grain would publish that cell and expose a single merchant's
# value -- exactly what the >75% rule prevents. (Unlike `month` on the other
# marts, which does not change who the merchants are.)
build_conc("opp_conc", "p_opp_mconc", "postal, category_group, channel, origin, card_group",
           ["substr(postal, 1, 2)"])

# Minimum lifetime transactions a merchant needs, within a (postal, category_group) cell, before
# it is included in opportunity_merchant / opportunity_delivery. Without this the per-merchant
# breakdown explodes to one row per tiny/one-off merchant.
OPP_MIN_MERCHANT_TXNS = 100

MARTS = {
    "supply": f"""
        SELECT s.*, x.merchants, x.top1_share, {publishable()} AS publishable
        FROM (SELECT geo_level, geo, category_group, month, SUM(transactions) AS transactions,
                     SUM(value) AS value, SUM(cards) AS cards FROM p_supply GROUP BY ALL) s
        JOIN sconc x USING (geo_level, geo, category_group)""",
    # month = 0 rows hold totals for the whole period (exact distinct cards)
    "demand": f"""
        SELECT d.*, x.merchants, x.top1_share, {publishable()} AS publishable
        FROM (SELECT geo_level, geo, category_group, month, SUM(transactions) AS transactions,
                     SUM(value) AS value, SUM(cards) AS cards, SUM(value_local) AS value_local,
                     SUM(value_elsewhere_pl) AS value_elsewhere_pl, SUM(value_online) AS value_online,
                     SUM(value_abroad) AS value_abroad
              FROM p_demand GROUP BY ALL) d
        JOIN dconc x USING (geo_level, geo, category_group)""",
    "flows": f"""
        SELECT f.*, x.merchants, x.top1_share, {publishable()} AS publishable
        FROM (SELECT geo_level, home_geo, dest_geo, category_group, SUM(transactions) AS transactions,
                     SUM(value) AS value, SUM(cards) AS cards FROM p_flows GROUP BY ALL) f
        JOIN fconc x USING (geo_level, home_geo, dest_geo, category_group)""",
    "hours": f"""
        SELECT h.*, x.merchants, x.top1_share, {publishable()} AS publishable
        FROM (SELECT geo_level, geo, category_group, weekday, hour, SUM(transactions) AS transactions,
                     SUM(value) AS value, SUM(cards) AS cards FROM p_hours GROUP BY ALL) h
        JOIN sconc x USING (geo_level, geo, category_group)""",
    "channels": f"""
        SELECT ch.*, x.merchants, x.top1_share, {publishable()} AS publishable
        FROM (SELECT geo_level, geo, category_group, month, dimension, dim_value,
                     SUM(transactions) AS transactions, SUM(value) AS value, SUM(cards) AS cards
              FROM p_channels GROUP BY ALL) ch
        LEFT JOIN (SELECT * FROM sconc WHERE geo_level IN ('neighborhood', 'fua', 'poland')) x
             USING (geo_level, geo, category_group)""",
    "mcc": f"""
        SELECT m.*, x.merchants, x.top1_share, {publishable()} AS publishable
        FROM (SELECT geo_level, geo, category_group, mcc, any_value(merchant_category) AS merchant_category,
                     SUM(transactions) AS transactions, SUM(value) AS value, SUM(cards) AS cards
              FROM p_mcc GROUP BY geo_level, geo, category_group, mcc) m
        JOIN mconc x USING (geo_level, geo, mcc)""",
    "retention": f"""
        SELECT r.*, x.merchants, x.top1_share, {publishable('active_customers')} AS publishable
        FROM (SELECT geo_level, geo, category_group, month, SUM(active_customers) AS active_customers,
                     SUM(returning_customers) AS returning_customers, SUM(new_customers) AS new_customers
              FROM p_retention GROUP BY ALL) r
        JOIN sconc x USING (geo_level, geo, category_group)""",
    "affinity": f"""
        SELECT a.*, t.customers_a, a.customers_both / t.customers_a AS share_of_a_also_buying_b,
               a.customers_both >= {MC} AS publishable
        FROM (SELECT geo_level, geo, group_a, group_b, SUM(customers_both) AS customers_both,
                     SUM(value_b) AS value_b FROM p_affinity WHERE group_a <> group_b GROUP BY ALL) a
        JOIN (SELECT geo_level, geo, group_a, SUM(customers_both) AS customers_a
              FROM p_affinity WHERE group_a = group_b GROUP BY ALL) t USING (geo_level, geo, group_a)""",
    "customers": f"""
        SELECT c.*, (c.customers >= {MC} AND (c.geo_level <> 'neighborhood'
                    OR (x.merchants >= {MM} AND x.top1_share <= {MT}))) AS publishable
        FROM (SELECT geo_level, geo, segment, dimension, dim_value, SUM(customers) AS customers,
                     SUM(transactions) AS transactions, SUM(value) AS value FROM p_customers GROUP BY ALL) c
        LEFT JOIN sconc x
          ON c.geo_level = 'neighborhood' AND x.geo_level = c.geo_level AND x.geo = c.geo
         AND x.category_group = 'All categories'""",
    "segment_categories": f"""
        SELECT s.*, (s.customers >= {MC} AND (s.geo_level <> 'neighborhood'
                    OR (x.merchants >= {MM} AND x.top1_share <= {MT}))) AS publishable
        FROM (SELECT geo_level, geo, segment, category_group, SUM(customers) AS customers,
                     SUM(transactions) AS transactions, SUM(value) AS value FROM p_seg_cat GROUP BY ALL) s
        LEFT JOIN sconc x
          ON s.geo_level = 'neighborhood' AND x.geo_level = s.geo_level AND x.geo = s.geo
         AND x.category_group = 'All categories'""",
    # Merchant-level tables describe ONE merchant and are meant for that merchant's private view.
    "merchant": f"""
        SELECT * FROM (
            SELECT merchant, geo, category_group, SUM(transactions) AS transactions, SUM(value) AS value,
                   SUM(customers) AS customers, SUM(repeat_customers) AS repeat_customers,
                   SUM(customers_group_value) AS customers_group_value,
                   SUM(customers_group_value_same_area) AS customers_group_value_same_area,
                   SUM(customers_group_value_online) AS customers_group_value_online
            FROM p_merchant GROUP BY ALL) WHERE customers >= {MC}""",
    "merchant_catchment": f"""
        SELECT * FROM (SELECT merchant, home_fua, home_district, SUM(customers) AS customers, SUM(value) AS value
                       FROM p_m_catch GROUP BY ALL) WHERE customers >= {MC}""",
    "merchant_hours": f"""
        SELECT merchant, weekday, hour, SUM(transactions) AS transactions, SUM(value) AS value
        FROM p_m_hours
        WHERE merchant IN (SELECT merchant FROM p_merchant GROUP BY merchant, geo, category_group
                           HAVING SUM(customers) >= {MC})
        GROUP BY ALL""",
    "merchant_segments": f"""
        SELECT * FROM (SELECT merchant, segment, SUM(customers) AS customers, SUM(value) AS value
                       FROM p_m_seg GROUP BY ALL) WHERE customers >= {MC}""",
    "postal_lookup": "SELECT * FROM postal_lookup",
    # ---- Opportunity engine -------------------------------------------------------------
    # opportunity_market is the denominator (whole market per cell) and IS compliance-filtered,
    # like every other market-level mart above.
    "opportunity_market": f"""
        SELECT mk.postal, mk.category_group, mk.channel, mk.origin, mk.card_group,
               mk.txns, mk.cards, mk.value, x.merchants, x.top1_share, {publishable()} AS publishable
        FROM (SELECT postal, category_group, channel, origin, card_group,
                     SUM(transactions) AS txns, SUM(value) AS value, SUM(cards) AS cards
              FROM p_opp_market GROUP BY ALL) mk
        JOIN opp_conc x USING (postal, category_group, channel, origin, card_group)""",
    # opportunity_merchant is a signed-in merchant's private view of ITS OWN cell and is
    # deliberately EXEMPT from publishable() - same exemption already granted to the
    # "merchant" / "merchant_*" marts above. The >75%-single-merchant rule exists to stop a
    # merchant being identifiable to OTHER merchants from a market-level cell; that concern does
    # not apply when the merchant is looking at itself. Still gated by OPP_MIN_MERCHANT_TXNS so a
    # merchant with only a handful of transactions in a cell isn't exposed either.
    "opportunity_merchant": f"""
        SELECT om.postal, om.category_group, om.merchant, om.channel, om.origin, om.card_group,
               om.txns, om.cards, om.value
        FROM (SELECT postal, category_group, merchant, channel, origin, card_group,
                     SUM(transactions) AS txns, SUM(value) AS value, SUM(cards) AS cards
              FROM p_opp_merchant GROUP BY ALL) om
        JOIN (SELECT postal, category_group, merchant FROM p_opp_merchant
              GROUP BY 1, 2, 3 HAVING SUM(transactions) >= {OPP_MIN_MERCHANT_TXNS}) elig
             USING (postal, category_group, merchant)""",
    # opportunity_delivery: same private-view exemption and same OPP_MIN_MERCHANT_TXNS guard as
    # opportunity_merchant, for the same reason (it is keyed on the same merchant cell).
    "opportunity_delivery": f"""
        SELECT od.postal, od.category_group, od.merchant, od.platform, od.txns, od.cards, od.value
        FROM (SELECT postal, category_group, merchant, platform,
                     SUM(transactions) AS txns, SUM(value) AS value, SUM(cards) AS cards
              FROM p_opp_delivery GROUP BY ALL) od
        JOIN (SELECT postal, category_group, merchant FROM p_opp_merchant
              GROUP BY 1, 2, 3 HAVING SUM(transactions) >= {OPP_MIN_MERCHANT_TXNS}) elig
             USING (postal, category_group, merchant)""",
    # opportunity_overlap: how many cards each pair of merchants in a cell SHARE. This is the
    # evidence that separates "my own second terminal" from "a neighbour in the same mall" -
    # the two are indistinguishable by name, postcode and category, but not by customers.
    #
    # Emitted symmetrically (one row per ordered pair) so the app can filter on the signed-in
    # merchant directly. Judge a candidate against the OTHER pairs in the same postcode, not
    # against a fixed cut-off: on the Krakow example the true co-tenants all sat at 29-44% while
    # genuinely off-site outlets sat at 7-13%, so the honest signal is "an outlier above this
    # postcode's own median", which the app computes.
    #
    # Same private-view exemption as opportunity_merchant / opportunity_delivery: it is keyed on
    # the merchant cell and shown to that merchant about itself. Both sides of every pair must
    # clear OPP_MIN_MERCHANT_TXNS, and a pair is suppressed below MC shared cards so a pair is
    # never published down to a handful of identifiable customers.
    "opportunity_overlap": f"""
        WITH pairs AS (
            SELECT postal, category_group, merchant_a, merchant_b, SUM(shared_cards) AS shared_cards
            FROM p_opp_overlap GROUP BY ALL),
        cards AS (
            SELECT postal, category_group, merchant, SUM(cards) AS cards
            FROM p_opp_cards GROUP BY ALL),
        elig AS (
            SELECT postal, category_group, merchant FROM p_opp_merchant
            GROUP BY 1, 2, 3 HAVING SUM(transactions) >= {OPP_MIN_MERCHANT_TXNS}),
        sym AS (
            SELECT postal, category_group, merchant_a AS merchant, merchant_b AS other, shared_cards
            FROM pairs
            UNION ALL
            SELECT postal, category_group, merchant_b AS merchant, merchant_a AS other, shared_cards
            FROM pairs)
        SELECT s.postal, s.category_group, s.merchant, s.other, s.shared_cards,
               cm.cards AS merchant_cards, co.cards AS other_cards
        FROM sym s
        JOIN elig e1 ON e1.postal = s.postal AND e1.category_group = s.category_group
                    AND e1.merchant = s.merchant
        JOIN elig e2 ON e2.postal = s.postal AND e2.category_group = s.category_group
                    AND e2.merchant = s.other
        JOIN cards cm ON cm.postal = s.postal AND cm.category_group = s.category_group
                     AND cm.merchant = s.merchant
        JOIN cards co ON co.postal = s.postal AND co.category_group = s.category_group
                     AND co.merchant = s.other
        WHERE s.shared_cards >= {MC}""",
}

for name, sql in MARTS.items():
    path = out / f"{name}.parquet"
    if "AS publishable" in sql:  # only compliant cells ever leave the pipeline
        sql = f"SELECT * EXCLUDE (publishable) FROM ({sql}) WHERE publishable"
    con.execute(f"COPY ({sql}) TO '{path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    rows = con.execute(f"SELECT COUNT(*) FROM '{path}'").fetchone()[0]
    log(f"  {name:20s} {rows:>10,} rows")

con.close()
shutil.rmtree(work, ignore_errors=True)
log(f"Done. Marts written to {out}")
