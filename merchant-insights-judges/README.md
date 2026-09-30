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

Python 3.11 or newer. No Poetry. Dependencies are pinned in `requirements.txt`. The virtual environment is created on your machine and is not part of the repository.

Do these in order: install, build the Kraków tables, then open the app. `final.py` does not build anything.

### 1. Install

Mac: double-click `install.command`. Terminal installs the packages and prints `pinned-ok`. It does not open the app.

Windows: do not double-click `install.command`. Open Command Prompt in this folder and run:

```bat
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

If `py` is not recognized, install Python 3.11 or newer from python.org and tick **Add python.exe to PATH**, then run the same lines again. Use `python` instead of `py -3` if that is the command that prints a version of 3.11 or higher.

### 2. Build the Kraków marts (about 5 minutes)

Do this before `final.py`. Skip it only when `data/marts_final` is already in this folder. Use the sample file, `datasprint_sample_data.parquet`. On Windows, close the app first if it is open: it keeps those files open, and Windows will not let the build replace them.

Mac:

```bash
.venv/bin/python pipeline/build_marts_final.py --file /Users/YourName/Downloads/datasprint_sample_data.parquet --out data/marts_final
```

Windows, in PowerShell, from this folder:

```powershell
.\.venv\Scripts\python.exe pipeline\build_marts_final.py --file "C:/Users/YourName/Downloads/datasprint_sample_data.parquet" --out data\marts_final
```

Replace `YourName` with the account folder on that computer.

### 3. Open the app

Mac:

```bash
.venv/bin/python final.py
```

Windows, in PowerShell:

```powershell
.\.venv\Scripts\python.exe final.py
```

The demo is at <http://127.0.0.1:8502>.

### National build (not the judges' demo)

This writes `data/marts` and takes about an hour and a half on the sample file. The app opened by `final.py` does not load it.

Mac:

```bash
.venv/bin/python national.py --file /Users/YourName/Downloads/datasprint_sample_data.parquet
```

Windows:

```powershell
.\.venv\Scripts\python.exe national.py --file "C:/Users/YourName/Downloads/datasprint_sample_data.parquet"
```

## What is aggregated

Each transaction has a merchant place (`mrch_postal_code`) and a card home (`pstl_cd_enr`, with municipality and metro from the enrichment columns). Comparing those two is what leakage, flows, and Where to Open use.

Geography in the marts: neighborhood (Kraków only), postal code, postal district (`XX-xxx`), municipality (LAU), metro area (FUA), and Poland.

About 400 merchant category codes are grouped in `pipeline/categories.py`. A card is "Mainly" one group when at least half of its spend is there, "Diversified" otherwise, and "Occasional" with fewer than 3 transactions.

## What this is not

A map, a forecast, a census, a rent or footfall model, or a live merchant login. Merchant names in a private benchmark can be masked; set `SHOW_MERCHANT_NAMES=1` in the environment to show them locally.
