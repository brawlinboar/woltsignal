# Merchant Insights

A prototype for one merchant. It turns anonymised Visa DATASPRINT card transactions into a dashboard: where to open, when to be open, where resident spend leaks, how a business compares with its area, who the customers are, whether they return, and which categories sit next to each other.

**GitHub description**

> Prototype merchant dashboard on anonymised Visa DATASPRINT data. The judges' demo is the Kraków metro only, not the whole country. Published groups follow the 30-card, 3-merchant, and 75% rules. Amounts are in the dataset's fictional currency.

## Read this first

- **Prototype.** This is a demo for an individual merchant, not a production Visa product and not a signed-in merchant portal.
- **Kraków metro only in the judges' demo.** Merchants outside the Kraków metro (FUA `KRAKOW`) are left out because a full national build takes too long to run in front of judges. It is not the whole of Poland. The national build is a separate script, `national.py`, and takes about an hour and a half on the sample file.
- **Allow about 5 minutes** if you are building the Kraków marts yourself. Opening the app when those marts are already in `data/marts_final` does not rebuild them.
- **Residents are cards, not people.** Every "resident customers" or "population" figure is a count of distinct cards with a home area on the card, not a census population.
- **Amounts are fictional.** The dataset's currency is not the złoty. Do not read the figures as real turnover.
- **The data is synthetic and anonymised.** Patterns can still be generator artifacts. Treat findings as directional.
- **The app never reads raw transactions.** It queries pre-aggregated parquet tables only. Card numbers are not stored in those tables.
- **Other merchants are anonymised in the published groups.** A group is kept only when it covers at least 30 cards, at least 3 merchants, and no single merchant is more than 75% of the group's value. Cells that fail are dropped in the pipeline and never reach the screen.
- **Action Plan and Merchant Benchmark are the client's own view.** The business you pick is shown as itself. Comparisons with other merchants still go through the rules above.
- **A merchant name is a 25-character string.** One chain can appear as several outlet names. A count of names is a count of those strings, not of legal entities.
- **Neighborhoods exist for Kraków only.** A postcode is assigned to a district when that district has a strict majority of addresses in the Kraków address file. Ties stay unmapped. Other cities use municipality and metro area.
- **Customer Leakage opens on municipality (LAU).** Neighborhood and metro stay in that dropdown. Other pages keep their own geography default.
- **Loyalty runs from May 2025 through May 2026.** January–April 2025 are left out because the file starts in January 2025 and those early cohorts look artificially low.
- **Where to Open "Other"** is in-store Polish spend at a merchant with no municipality, so it is neither local nor another Polish area. The five shares on that drill-down are shown so they add to 100%.

## What each page answers

| Question | Page |
|---|---|
| I run a restaurant. What should I fix? | Action Plan. Pick a restaurant from the busiest names. Online and automat names are not in that list. There is no postal-code field. |
| Where should I open? | Where to Open. Areas where resident cards spend a lot in a category and local merchants capture little of it. |
| When should I be open? | Opening Hours. Weekday and hour in Europe/Warsaw. Rows with unknown time are left out of the hourly view only. |
| Where does resident spend go? | Customer Leakage. Starts on municipality. |
| How do I compare with the area? | Merchant Benchmark. |
| Who is spending? | Customer Segments. |
| Do they come back? | Loyalty. May 2025–May 2026. A return is the same category and the same area in the previous month. |
| Who should I sit next to? | Cross-sell. |
| How do people pay, and who is visiting? | Channels and Tourism. |
| What is growing? | Market Trends. |

## Setup

Python 3.12. No Poetry. Dependencies are pinned in `requirements.txt`. The virtual environment is created on your machine and is not part of the repository.

```bash
./install.command
.venv/bin/python final.py
```

`final.py` opens the Kraków demo at <http://127.0.0.1:8502>. It does not rebuild the marts.

On Windows, from this folder:

```bat
py -3.12 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python final.py
```

### Build the Kraków marts (about 5 minutes)

Only if `data/marts_final` is missing:

```bash
.venv/bin/python pipeline/build_marts_final.py --file /path/to/data.parquet --out data/marts_final
```

### National build (not the judges' demo)

```bash
.venv/bin/python national.py --file /path/to/data.parquet
```

That writes `data/marts` and is the long run. The app opened by `final.py` does not load it.

## What is aggregated

Each transaction has a merchant place (`mrch_postal_code`) and a card home (`pstl_cd_enr`, with municipality and metro from the enrichment columns). Comparing those two is what leakage, flows, and Where to Open use.

Geography in the marts: neighborhood (Kraków only), postal code, postal district (`XX-xxx`), municipality (LAU), metro area (FUA), and Poland.

About 400 merchant category codes are grouped in `pipeline/categories.py`. A card is "Mainly" one group when at least half of its spend is there, "Diversified" otherwise, and "Occasional" with fewer than 3 transactions.

## What this is not

A map, a forecast, a census, a rent or footfall model, or a live merchant login. Merchant names in a private benchmark can be masked; set `SHOW_MERCHANT_NAMES=1` in the environment to show them locally.
