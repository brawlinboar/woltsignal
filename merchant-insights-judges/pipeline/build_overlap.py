"""Write only opportunity_overlap.parquet. Other marts are left in place.

Reads the same sample (or full) parquet as build_marts.py, in the same card
chunks, and keeps only the shared-card pairs. Eligibility comes from the
opportunity_merchant mart that is already built.
"""

import argparse
import shutil
import sys
import time
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from categories import category_group_sql  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
GROUP_SQL = category_group_sql("mrch_catg_cd")
OPP_MIN_MERCHANT_TXNS = 100
MIN_SHARED_CARDS = 30

parser = argparse.ArgumentParser(description="Build only the opportunity_overlap mart")
parser.add_argument("--file", required=True)
parser.add_argument("--out", default=str(ROOT / "data" / "marts"))
parser.add_argument("--chunks", type=int, default=20)
parser.add_argument("--memory", default="8GB")
args = parser.parse_args()

out = Path(args.out)
work = out.parent / "_work_overlap"
out.mkdir(parents=True, exist_ok=True)
work.mkdir(parents=True, exist_ok=True)
merchant_mart = out / "opportunity_merchant.parquet"
if not merchant_mart.exists():
    raise SystemExit(f"Missing {merchant_mart}. The overlap pass uses it for eligibility.")

src = args.file.replace("'", "''")
t0 = time.time()


def log(msg):
    print(f"[{time.time() - t0:6.0f}s] {msg}", flush=True)


con = duckdb.connect()
con.execute(f"SET memory_limit = '{args.memory}'")
con.execute(f"SET temp_directory = '{work / 'tmp'}'")
con.execute("SET max_temp_directory_size = '60GB'")
con.execute("SET preserve_insertion_order = false")
con.execute("SET enable_progress_bar = false")
con.execute("""
CREATE TABLE p_opp_cards (postal VARCHAR, category_group VARCHAR, merchant VARCHAR, cards BIGINT);
CREATE TABLE p_opp_overlap (
    postal VARCHAR, category_group VARCHAR, merchant_a VARCHAR, merchant_b VARCHAR, shared_cards BIGINT
);
""")

for k in range(args.chunks):
    started = time.time()
    con.execute("DROP TABLE IF EXISTS c")
    con.execute(f"""
        CREATE TEMP TABLE c AS
        SELECT
            hash(pymt_crd_acct_num_raw) AS card_id,
            {GROUP_SQL} AS category_group,
            mrch_nm_raw AS merchant,
            mrch_ctry_nm = 'POLAND' AS merchant_in_pl,
            CASE WHEN regexp_full_match(mrch_postal_code, '[0-9]{{2}}-[0-9]{{3}}')
                      AND mrch_ctry_nm = 'POLAND'
                 THEN mrch_postal_code END AS m_postal,
            tran_id_gmt_tm <> '000000' AS time_known
        FROM read_parquet('{src}')
        WHERE hash(pymt_crd_acct_num_raw) % {args.chunks} = {k}
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE opp_cell_cards AS
        SELECT DISTINCT m_postal AS postal, category_group, merchant, card_id
        FROM c
        WHERE merchant_in_pl AND m_postal IS NOT NULL AND time_known
    """)
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
    log(f"chunk {k + 1}/{args.chunks} done ({time.time() - started:.0f}s)")

dest = out / "opportunity_overlap.parquet"
dest_sql = str(dest).replace("'", "''")
merchant_sql = str(merchant_mart).replace("'", "''")
con.execute(f"""
COPY (
    WITH pairs AS (
        SELECT postal, category_group, merchant_a, merchant_b, SUM(shared_cards) AS shared_cards
        FROM p_opp_overlap GROUP BY ALL),
    cards AS (
        SELECT postal, category_group, merchant, SUM(cards) AS cards
        FROM p_opp_cards GROUP BY ALL),
    elig AS (
        SELECT postal, category_group, merchant FROM read_parquet('{merchant_sql}')
        GROUP BY 1, 2, 3 HAVING SUM(txns) >= {OPP_MIN_MERCHANT_TXNS}),
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
    WHERE s.shared_cards >= {MIN_SHARED_CARDS}
) TO '{dest_sql}' (FORMAT PARQUET, COMPRESSION ZSTD)
""")
rows = con.execute(f"SELECT COUNT(*) FROM '{dest_sql}'").fetchone()[0]
con.close()
shutil.rmtree(work, ignore_errors=True)
log(f"Wrote {dest} ({rows:,} rows)")
