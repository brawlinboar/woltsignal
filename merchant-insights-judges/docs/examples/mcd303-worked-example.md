# McDonald's 303 Kraków — store readout

**Store:** `MCDONALDS 303 KRAKOW 01` · postcode `30-644`, Kraków
**Window:** 2025 calendar year (`prch_mnth_id` 202501–202512)
**Source:** `live/datasprint_sample_data.parquet` — full 16.32 GiB sample, 305,525,104 rows
**Prepared:** 2026-09-29

> **Units are a fictional currency** prepared for hackathon purposes (confirmed by
> the DataSprint organisers). Every value figure below is bare units. Do not
> convert to EUR/PLN/USD and do not present as real money. Shares, ranks and
> ratios are unaffected.

> **Revised 2026-09-30 — the second terminal was not a second terminal.** The
> previous revision merged `McDonalds 61600303` into this store, on the grounds
> that it shared the postcode, city and category, and reported share as 77.3%.
> **That was wrong.** A customer-overlap test disproved it: the descriptor
> shares 44.8% of its cards with this store, against 43.6% for
> `PL BK KRAKOW BONARKA` — a Burger King in the same mall. Two tills in one
> restaurant share nearly all their customers; this shares what any co-tenant
> shares. It was the highest overlap in the postcode, which is precisely why the
> merge looked safe, and it is now back in the denominator as a competitor.
>
> The Starbucks correction stands and is independently **confirmed** by the same
> test: six outlets named for other Kraków locations (Rynek, Galeria K,
> Floriańska, Serenada, Galeri 01, Krupnicza) are registered at `30-644` but
> overlap only 7–13%, marking them as trading elsewhere in the city. They stay
> out of the district denominator. `PL SBX KRAKOW BONARKA`, at 29.5%, is
> genuinely on site and stays in.
>
> Effect of splitting the descriptors: store share **77.2% → 69.3%**,
> deduplicated opportunity **18.4k → 26.9k units** (a smaller store has more
> room to grow into), open-hours opportunity **3,798 → 5,358**. **One headline
> insight did not survive** — see §"What the correction changed" below. Every
> figure in this document is on the corrected single-descriptor basis.

---

## The storyline in one line

The store already holds **69.3%** of its food court's fast-food value, so the
whole remaining pool is **119.1k units** and the realistic, deduplicated
opportunity is **26.9k**. The biggest lever is the store's own busiest
segment: **local CLASSIC cardholders paying by mobile** sit at 66.1% share
against 77.1% for the same card type visiting from elsewhere — one cell, 38%
of transactions, **52% of the entire opportunity**. The second lever is the
same local CLASSIC group paying by contactless (62.1%, 29% of the
opportunity). Read together, the pattern is about **local customers, not
payment channels**: locals convert at 64.5% against 74.1% for visitors, a
9.6-point gap. Trading-hour tuning is worth ~5.4k and being closed almost
nothing (~0.3k). Separately, the store's customers spend **715.5k units a year
on Polish food delivery**; McDonald's may already hold part of that pool, so it
can only be quoted as a percentage of it, never as a total.

---

## 1. The store is an anchor, not a participant

| Measure | Value |
|---|---|
| Store transactions, 2025 | 5,153 (`MCDONALDS 303 KRAKOW 01` only) |
| Store value, 2025 | 268,491 units |
| **Share of district fast-food value** | **69.3%** |
| Share of all district restaurant value | 42.9% |
| McDonald's share of fast food, Kraków city-wide | 30.6% |

The all-restaurant figure is **42.9%**, not the 38.3% previously reported. That
earlier number was on a mixed basis: the fast-food denominator excluded the six
off-site Starbucks while the all-restaurant denominator still included them
(73,714 units across both restaurant categories). Both denominators now exclude
them.

The store takes **more than twice the share within its own postcode that the
McDonald's brand takes across Kraków** (69.3% vs 30.6%). It is the dominant
food-service operator on its site, not one option among many. Note that the
*other* McDonald's descriptor in this postcode holds a further 9.3% of
fast-food value in the store's weak hours — the brand's position on the site is
stronger than this store's own share, but that value is not this store's to
win, which is the whole point of splitting them.

**Context for the district:** postcode `30-644` is a single large retail site
(the Bonarka mall address) holding **254 merchants and 87,101 transactions** in
2025, of which 13,126 are restaurant. "District" here means that site, not an
administrative *dzielnica* — Kraków's 18 dzielnice are not in the data.

## 2. Share is flat through the day — a claim the corrections destroyed

Store share of district fast-food value, by Warsaw local hour:

| Hour | 09 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Share % | 66.3 | 65.0 | 68.2 | 68.2 | 65.5 | **74.0** | 72.1 | 67.2 | 65.4 | 70.1 | 73.2 | 71.2 | 73.8 |
| Store txns | 104 | 155 | 276 | 412 | 476 | 552 | 552 | 586 | 542 | 565 | 477 | 406 | 50 |

Share sits in a narrow **65–74% band all day**, with no trend. The strongest
hour is 14:00 (74.0%); the weakest is 10:00 (65.0%).

> **This section previously said the opposite, and it is instructive.** The
> first draft reported share climbing from 38.0% at 09:00 to a 66.9% peak at
> 19:00, and built a story on it: "competing outlets fade in the evening while
> this store holds up, so late trade concentrates into it — inverting
> McDonald's city-wide pattern." That climb was an artefact of the **market
> denominator**, not the merge. The six off-site Starbucks registered to this
> postcode trade in the morning; leaving them in the denominator suppressed the
> store's morning share specifically, manufacturing an upward slope through the
> day. Remove them and the slope disappears.
>
> The transaction counts in the row above are unchanged from the first draft —
> only the denominator moved. A shape this striking, resting entirely on which
> merchants are counted as neighbours, is a warning about how much narrative
> weight a share-by-hour curve can carry.

## 3. The opportunity: 5,358 units across 7 hours

Method: benchmark = **69.35%**, the store's value-weighted average share across
its 13 open hours (09:00–21:00, defined as hours with ≥1 store transaction).
For each hour below benchmark, opportunity = (benchmark − actual share) ×
district fast-food value for that hour.

| Hour | District FF value | Store share | Gap (pts) | Opportunity |
|---|---|---|---|---|
| 17:00 | 41,719 | 65.39% | 3.96 | **1,650** |
| 13:00 | 39,335 | 65.49% | 3.86 | 1,519 |
| 16:00 | 44,252 | 67.19% | 2.16 | 957 |
| 10:00 | 10,770 | 64.96% | **4.39** | 473 |
| 12:00 | 31,616 | 68.16% | 1.19 | 375 |
| 11:00 | 19,597 | 68.23% | 1.12 | 220 |
| 09:00 | 5,427 | 66.32% | 3.02 | 164 |
| **Total** | | | | **5,358** |

Equivalent to **2.0%** of the store's 2025 value.

### The ranking inverts when points become value

This is the load-bearing insight, and it survives the correction intact.
**10:00 has the worst share gap (4.4 points) but ranks only 4th in value**,
because the hour is small (10,770 units). **16:00 has a modest 2.2-point gap
yet yields 957 units** because the hour is four times larger. Prioritising off
the share chart sends you after the late morning; prioritising off value sends
you after the **afternoon and early evening, 13:00–17:00, which is 4,126 units
— 77% of the whole opportunity.**

Note how far this moved: the first draft's version of this same paragraph
pointed at "the late-morning ramp, 10:00–11:00, 43% of the whole opportunity."
On the corrected basis those two hours are 693 units, **13%**. The *method* was
right and the *conclusion* was wrong, because the denominator was wrong.

### Sensitivity — the benchmark choice still moves the answer

| Benchmark | Hours below | Opportunity |
|---|---|---|
| Value-weighted average, 69.35% | 7 | **5,358** |
| Unweighted mean of hourly shares, 69.24% | 7 | 5,149 |
| Best single open hour, 74.04% | 12 | 18,157 |

The value-weighted and unweighted variants now agree within 4%, where on the
uncorrected basis they differed by a third — the corrected hourly shares are
flat, so weighting barely matters. The "best single hour" row is the
aggressive upper bound: it holds every hour to 14:00's 74.0% and puts 12 of 13
hours in deficit.

Value-weighted is the store's true average share and is the headline. The
unweighted variant is the conservative read. The third row drops 09:00 and
21:00 on the grounds that an opening ramp and a near-closed hour are not
comparable to a normal trading hour.

## 4. Closed hours: 334 units — logic tested, not the story

Same assumptions applied to the hours the store does **not** trade. "Closed" =
district fast-food activity exists in that hour but the store has 0
transactions. Opportunity = benchmark share (69.35%) × district fast-food value
for that hour.

| Hour | District FF txns | FF value | Opportunity |
|---|---|---|---|
| 02:00 | 1 | 285 | **197** |
| 08:00 | 3 | 173 | 120 |
| 01:00 | 1 | 23 | 16 |
| **Total** | **5** | **481** | **334** |

**0.1%** of store value, and only **6%** of the open-hours opportunity. The 3
closed hours contain just **five fast-food transactions between them**. There
is essentially no market to miss.

> **The breakfast recommendation did not survive the corrections.** The first
> draft found 7 closed hours worth 2,425 units and singled out 08:00 as "the
> only closed hour with a meaningful number" (1,044 units), concluding: "the
> only closed-hour question worth asking is *open one hour earlier*."
>
> That was the off-site Starbucks again. Four of those seven hours — 06:00,
> 07:00, 22:00 and 23:00 — have **no** fast-food activity at this postcode at
> all once outlets trading elsewhere in the city are removed, so they drop out
> of the table entirely. 08:00 survives but collapses from 1,779 units of
> district value to 173. The "breakfast demand the store is missing" was
> coffee shops in Kraków's old town, several kilometres away.
>
> This is the clearest illustration in the readout of why the denominator
> matters more than the arithmetic: the method was applied correctly both
> times and produced a confident, specific, actionable recommendation that was
> entirely an artefact of counting the wrong neighbours.

**Why 00:00 is absent from the table.** Local hour 00:00 has 44 transactions in
postcode `30-644` but **zero** in either restaurant category — they are service
stations (27), car rental, a bakery, a cinema. There is no fast-food value at
midnight to miss, so the hour legitimately drops out. It is *not* an artefact of
the `'000000'` exclusion: that placeholder is GMT 00:00:00, which converts to
local **01:00** (winter) / **02:00** (summer), never local 00:00.

**How much the placeholder exclusion mattered here.** In this postcode it
removed 99% of the rows at local 01:00–02:00:

| Local hour | All rows | Excl. placeholder | Placeholder rows |
|---|---|---|---|
| 00:00 | 44 | 44 | 0 |
| 01:00 | 4,057 | **37** | **4,020** |
| 02:00 | 3,023 | **45** | **2,978** |
| 23:00 | 173 | 173 | 0 |

Unexcluded, 01:00 and 02:00 would rank as the third- and fourth-busiest hours
of the day at a mall food court. That is why those hours contribute only
1 transaction each above — it is all the genuine activity there ever was.

### This inference is weaker than the open-hours one

Worth stating plainly, because the two numbers look comparable but are not:

- **Open hours:** the store's actual share is *observed*, so the gap to its own
  average is a measured shortfall against demonstrated capability.
- **Closed hours:** there is no observed store behaviour at all. The 481
  units of district fast-food value is **not demand the store failed to
  capture** — it is demand that existed while the store was shut, largely at
  outlets on different schedules. Opening would not transfer that value;
  some of it would not exist without the neighbouring outlet's own footfall.

So the closed-hours figure is an **upper bound on a hypothetical**, not a
shortfall. It also assumes the store could hit its trading-hours share in
hours with a completely different demand mix (breakfast, late night).

**Not actionable here:** hours are set by the mall, not the operator. Retained
as a method test.

---

## Method — how both numbers were derived

Reproducible logic for the two opportunity calculations, so they can be
re-applied to another store.

### Step 1 — build the base

```sql
-- requires: INSTALL icu; LOAD icu;
CREATE VIEW base AS
SELECT mrch_postal_code AS pc, mrch_nm_raw, mrch_catg_nm,
       pymt_crd_acct_num_raw AS card_id, cs_tran_amt,
       EXTRACT(hour FROM (strptime(prch_dt || tran_id_gmt_tm, '%Y-%m-%d%H%M%S')
               AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Warsaw')) AS hr
FROM 'live/datasprint_sample_data.parquet'
WHERE mrch_ctry_nm = 'POLAND'
  AND prch_mnth_id BETWEEN 202501 AND 202512
  AND tran_id_gmt_tm <> '000000'            -- missing-time placeholder
  AND mrch_catg_nm IN ('FAST FOOD RESTAURANTS','EATING PLACES AND RESTAURANTS');
```

Then aggregate to hour × segment for `pc = '30-644'`, and separately for
`mrch_nm_raw = 'MCDONALDS 303 KRAKOW 01'`.

The district denominator must also **exclude the six off-site outlets** —
`PL SBX KRAKOW` Rynek, Galeria K, Floriańska, Krupnicza, Serenada and
Galeri 01 — which are registered to `30-644` but trade elsewhere in Kraków.
Keep `PL SBX KRAKOW BONARKA`, which is on site. Skipping this step is what
produced every wrong figure in the first draft; §2 and §4 show how far wrong.

### Step 2 — define open hours and the benchmark

- **Open hour** = an hour with ≥ 1 store transaction. For this store: 09:00–21:00
  (13 hours). The store has 0 transactions at 08:00 and below.
- **Benchmark** = value-weighted average share across open hours only:

```
benchmark = SUM(store_value over open hours) / SUM(district_ff_value over open hours)
          = 268,491 / 387,157 = 69.35%
```

Value-weighted, not the mean of hourly shares. Here the unweighted mean
(69.24%) lands within 0.11 points, because the corrected hourly shares are
flat — so the choice barely matters for this store and moves the answer by 4%.
That is *not* a general result: on the uncorrected denominator the same two
definitions differed by 1.97 points and moved the answer by a third. Report
both.

### Step 3 — open-hours opportunity (measured shortfall)

For each open hour where `share < benchmark`:

```
gap_pts      = benchmark - actual_share
opportunity  = (gap_pts / 100) * district_ff_value_for_that_hour
```

Sum over qualifying hours only. Hours **above** benchmark are excluded — not
netted off. Netting would answer a different question ("is the store balanced
across the day?"); the brief was to size the downside only.

Result: 7 of 13 hours qualify → **5,358 units**. The §3 table above is this
calculation, hour by hour.

### Step 4 — closed-hours opportunity (hypothetical upper bound)

For each hour with district fast-food activity but 0 store transactions:

```
opportunity = (benchmark / 100) * district_ff_value_for_that_hour
```

The full benchmark share is applied, since actual share is 0 by definition.

Result: 3 hours → **334 units**.

### Step 5 — sensitivities to report alongside

| Variant | Open hours | Closed hours |
|---|---|---|
| Weighted benchmark 69.35% | **5,358** | **334** |
| Unweighted benchmark 69.24% | 5,149 | 333 |
| Best single open hour, 74.04% | 18,157 | 356 |

### What the logic does *not* do

1. Does not model incremental demand — it reallocates existing district value.
2. Does not test whether the shortfall is *winnable*; a structural cause
   (competitor breakfast offer, coffee-led neighbour, opening ramp) would
   invalidate part of it.
3. Does not adjust for the store's own opening ramp at 09:00. On the corrected
   basis this barely matters — 09:00 contributes 164 units, 3% of the total —
   where on the uncorrected denominator it was the largest share gap in the day
   and needed a dedicated sensitivity row.
4. Assumes the benchmark share is achievable in every hour, including hours
   with a different demand mix.

---

## 5. Where the share could come from — customer segments

Corrected basis: global benchmark **69.35%**, district fast-food value across
open hours **387,157 units**. Each segment gets its **own** value-weighted
benchmark, so segment figures do not sum to the global 5,358.

Two different questions are separated throughout:

- **Hourly opportunity** — shortfall against the segment's *own* average, i.e.
  "this segment underperforms at certain hours."
- **Structural lift** — the gap between this segment's benchmark and the best
  comparable segment's, i.e. "the store is systematically weaker in this
  segment at *every* hour." A segment can show near-zero hourly opportunity
  while being structurally far behind, because its own weak benchmark absorbs
  the weakness.

Structural lift compares each segment with the best-performing segment in its
own family that has a substantial base (≥200 district transactions), so a
20-transaction segment cannot set the bar.

| Segment | District txns | District value | Store share | Structural lift | Hourly opp. |
|---|---|---|---|---|---|
| **Local Kraków** | 3,844 | 191,944 | 64.52% | **18,369** | 5,129 |
| **CLASSIC cards** | 6,413 | 345,458 | 69.79% | **4,698** | 4,590 |
| **INFINITE cards** | 296 | 19,040 | 58.61% | **2,388** | 1,252 |
| **Contactless (card-present)** | 2,039 | 119,414 | 68.46% | **2,305** | 3,150 |
| BUSINESS cards | 65 | 3,793 | 70.52% | 24 | 302 |
| PLATINUM cards | 241 | 13,189 | 71.15% | 0 (best card type) | 494 |
| Mobile pay | 4,978 | 263,065 | 70.39% | 0 (best channel) | 4,341 |
| From elsewhere | 3,248 | 195,213 | 74.09% | 0 (best origin) | 2,790 |
| PREMIER cards | 45 | 3,408 | 82.07% | — (above best) | 316 |
| VISA SIGNATURE | 20 | 1,426 | 79.28% | — (above best) | 144 |

**The ordering of this table is the main casualty of the correction.**
Contactless was previously the runaway structural finding at 15,142 units;
it is now fourth at 2,305. Local Kraków has gone the other way — from 5,029 to
**18,369**, more than three times any other segment. The corrected story is
about *who* the customers are, not *how they pay*.

### Q1 — Is there a card type to target? Yes: INFINITE, not BUSINESS

**BUSINESS is not the answer.** It is only 65 transactions and 3,793 units of
district value in the whole year — too small to move the store, whatever its
share.

**INFINITE is.** The store converts only **58.6%** of INFINITE-card value
against **71.2%** for PLATINUM, the best-performing card type with a
substantial base — a **12.5-point structural gap** on a base of 19,040 units,
worth **2,388 units** if closed. INFINITE is also the second-largest
cardholder population in the dataset nationally (259,467 cards), so this is a
repeatable pattern, not a local quirk.

Reading: **INFINITE specifically under-selects this store, but "premium
cardholders" as a class does not.** The first draft read this as a premium
effect with PLATINUM as the lone exception. On the corrected basis PLATINUM
(71.2%), PREMIER (82.1%) and VISA SIGNATURE (79.3%) all sit *above* CLASSIC
(69.8%) — so premium cards in general over-select the store and INFINITE is
the outlier. Same table, opposite reading. PREMIER and VISA SIGNATURE are 45
and 20 transactions, so treat them as directional.

**CLASSIC is where the volume is.** It is 89% of district fast-food value and
now carries both the second-largest structural lift (4,698) and the largest
hourly opportunity of any card type (4,590) — it fell below PLATINUM once the
merged descriptor's CLASSIC-heavy traffic was removed.

### Q2 — Which venues win in the gap hours? One competitor, not the field

Gap-hour value, anonymised (`competitor_venues_anon.csv`):

| Venue | Txns | Value | % of gap-hour value | Cards |
|---|---|---|---|---|
| McDonald's 303 (the store) | 2,551 | 128,290 | 66.57% | 1,740 |
| **Fast Food 1** | 347 | 20,213 | **10.49%** | 274 |
| **Fast Food 2** — *the other McDonald's descriptor* | 308 | 17,969 | **9.32%** | 162 |
| **Fast Food 3** | 169 | 13,496 | **7.00%** | 137 |
| Fast Food 4 | 60 | 6,029 | 3.13% | 58 |
| Fast Food 5 | 63 | 2,891 | 1.50% | 54 |
| Fast Food 6 | 57 | 1,980 | 1.03% | 43 |
| Fast Food 7 | 15 | 1,700 | 0.88% | 15 |
| Fast Food 8 | 13 | 149 | 0.08% | 11 |

**The competitive set is effectively three venues**, and one of them carries
the McDonald's brand. Fast Food 1, 2 and 3 together hold 26.8% of gap-hour
value against 6.6% for the rest of the field. Fast Food 1 has the highest
transaction count of any competitor (347) and the widest card reach (274) —
broad trial rather than a few heavy users.

> **Fast Food 2 is `McDonalds 61600303`**, the descriptor this readout
> previously counted as part of the store. It is now the store's
> second-largest competitor by value in exactly the hours the store is weakest.
> That is not a contradiction: whether or not the two are the same operator,
> they are separately acquired and separately measured, and 9.3% of gap-hour
> value sitting with another McDonald's descriptor is a finding in its own
> right. **If this table is reused in a merchant-facing deck, annotate that
> row** — a reader who assumes it is a rival chain will draw the wrong
> conclusion about the competitive set.
Every competitor in the gap hours takes a **higher ticket than the store**:
Fast Food 3 averages 79.9 units and Fast Food 1 and 2 both 58.3, against the
store's **50.3**. The store wins on volume and loses on basket size, which is
consistent with the INFINITE-card finding above. (Fast Food 4 and 7 show 100.5
and 113.3 but on 60 and 15 transactions — ignore them.)

### Q3 — Local vs travelling? This is now the story

| Segment | District value | Store share |
|---|---|---|
| Local Kraków | 191,944 | **64.52%** |
| From elsewhere (rest of Poland + international) | 195,213 | **74.09%** |

The food court splits **almost exactly 50/50** between local Kraków cardholders
and visitors, and the store's share differs by **9.6 points** — in the
direction *against* the intuition: it performs markedly **better** with
visitors than with locals. Applied to a 191,944-unit base that is a
**18,369-unit structural lift**, the largest single structural finding in this
readout, and local customers also carry the largest hourly opportunity
(5,129) and the most hours below benchmark (8 of 13).

> **This section previously concluded the opposite, and said so emphatically.**
> On the merged basis the gap was 2.6 points — 76.00% local vs 78.62%
> visitors — and the readout recorded it as "a negative finding worth
> keeping… there is no local-vs-traveller targeting play here", dismissing the
> structural lift as "a by-product of base size, not a behavioural
> difference."
>
> The merged descriptor's customers were disproportionately local, so folding
> them in lifted the local cohort's apparent conversion and flattened the gap
> to noise. Removing them reveals a 9.6-point deficit — 3.6× wider — that was
> invisible before. A finding was not merely mis-sized; it was **ruled out**.

Plausible reading: visitors to a mall food court default to the most
recognisable brand, while locals with more knowledge of the site spread their
spend. That is a hypothesis about behaviour, not something these transactions
establish — but unlike the previous draft's conclusion, there is now a real
gap to explain.

### Q4 — Channel: a modest lever, not the largest

| Channel | District txns | District value | Store share |
|---|---|---|---|
| Mobile pay | 4,978 | 263,065 | **70.39%** |
| Contactless (card-present) | 2,039 | 119,414 | **68.46%** |
| Contactless (non-cp) | 32 | 2,084 | 75.00% |
| E-commerce (`eci`) | 42 | 2,586 | 100.00% |

A **1.9-point** gap between mobile and physical-contactless customers, on
119,414 units of district value — a 2,305-unit structural lift. Mobile carries
the larger hourly opportunity (4,341 vs 3,150), but mostly because it is twice
the base.

> **This was the readout's headline finding, and it does not survive.** The
> merged basis showed mobile at 81.14% against contactless at 68.46% — a
> 12.7-point gap worth a 15,142-unit structural lift, described above as "four
> times larger than the entire hourly opportunity" and read as a
> throughput/ordering-experience signal: app and kiosk ordering converting
> while counter queues deflected customers to faster neighbours. It was a
> tidy, mechanistic, actionable story.
>
> It was an artefact. **`McDonalds 61600303`'s transactions were entirely
> mobile-channel** — the contactless row is *byte-identical* in both bases
> (68.46%, 3,150) while mobile fell from 81.14% to 70.39%. Merging the
> descriptor inflated exactly one side of the comparison and manufactured the
> gap. The deduplicated cells make this starker still: the controlled
> comparison that appeared to prove the mechanism collapses from 19.9 points
> to 4.0 (see below).
>
> The lesson is not that channel is irrelevant — 1.9 points on a large base is
> still worth something. It is that **a controlled comparison is only as
> sound as the numerator's definition.** Holding origin and card type constant
> rules out customer mix; it does nothing about a merchant identity error that
> lands disproportionately in one cell.

Note `eci` is 100% the store, but on only 42 transactions — the district has
almost no online fast-food activity at all.

### Q5 — Acquisition vs share of wallet

The district's 387,157 units decompose **exhaustively**:

| Pool | Cards | Value | % of district |
|---|---|---|---|
| Already the store's | 3,069 | 268,491 | 69.35% |
| **Never used the store** | 956 | **80,487** | **20.79%** |
| **Store customers spending at neighbours** | 309 | **38,180** | **9.86%** |

**Acquisition is ~2× larger than share of wallet.** 956 cards use the food
court's fast food and never once buy from the store; they are worth 80,487
units. The store's own 3,069 customers leak 38,180 units to neighbours — they
remain loyal, but 88% of their food-court fast-food spend goes to the store,
not the 93% previously reported.

So the ceiling is still set more by **non-customers than by under-spending
customers** — but the margin narrowed. Both pools grew when the store's own
slice shrank, and the wallet-leakage pool grew faster (+72% against +23%),
because a good part of what the merged descriptor was crediting to the store
is in fact its own customers spending at a *different* McDonald's descriptor.
That is leakage, and treating it as retained spend hid it entirely.

### Q6 — Delivery: the largest pool in this readout, and the least certain

> **This section has not been recomputed on the corrected basis.** The pool is
> defined as delivery spend by *the store's own customers*, and splitting the
> descriptors changed that customer set from 3,233 cards to 3,069. The figures
> below therefore still include delivery spend by cards that reached the
> merged descriptor only, and the total is overstated by an unknown amount —
> likely around 5%, in proportion to the cards removed, but that assumes the
> removed cards order delivery at the same rate, which is untested. Treat every
> number in this section as provisional pending a rerun.

Polish delivery spend by the store's own customers (3,233 cards on the
superseded merged definition), 2025:

| Platform | Txns | Store customers using | Value |
|---|---|---|---|
| Glovo | 2,690 | 406 | 372,769 |
| Pyszne.pl | 1,511 | 431 | 221,843 |
| Wolt | 1,128 | 147 | 120,931 |
| **Total** | **5,329** | **~800 unique** | **715,544** |

**These customers spend 2.7× more on food delivery than the store earns from
them in the food court** (715,544 vs 268,491 — and the delivery side is
overstated per the note above, so treat the multiple as approximate). Only ~25% of store customers
use delivery at all, so the behaviour is concentrated.

**Heavy caveats — this is not 715k of addressable share:**

1. The aggregator is the merchant of record, so there is **no way to tell
   whether a Glovo order went to McDonald's or a competitor.** Some of this
   spend may already be McDonald's revenue through a different channel.
2. It spans **all restaurant types**, not just fast food.
3. It is **not district value** — delivery goes to the cardholder's home, which
   may be anywhere. It cannot be added to the 118,667-unit district ceiling.
4. Uber Eats, Deliveroo and Bolt Food were **excluded**: all three have zero
   Polish-merchant transactions in this data (Deliveroo exited Poland in 2021,
   Uber Eats followed), so their 248,361 transactions are Polish cardholders
   ordering abroad. Including them would have inflated this pool by ~35% with
   unreachable foreign spend.

### State delivery as a share of the pool, never as a total

Because McDonald's may **already hold part of this pool** and the data cannot
reveal how much, the only honest expression is *"some % of 715,544 units."*
The aggregator is the merchant of record, so a `Glovo` transaction by a store
customer may already be a McDonald's sale booked through Glovo. There is no
column that distinguishes it.

So quote it as a rate against the pool, and let the reader pick the rate:

| If McDonald's captures… | …that is worth |
|---|---|
| 5% of the pool | 35,777 |
| 10% | 71,554 |
| 15% | 107,332 |
| 20% | 143,109 |
| 25% | 178,886 |
| 30% | 214,663 |

**Even the 5% line (35,777) exceeds the entire deduplicated district
opportunity of 26,934** — which is the reason to scope delivery properly
rather than dismiss it. But note this is *gross* pool share: whatever
McDonald's already earns through aggregators has to be netted off, and that
figure is not in this dataset. It must come from McDonald's own aggregator
reporting.

Treat it as evidence that the customer base is delivery-active, and as a
sizing prompt for a proper delivery analysis — **not** as a share target, and
never as a headline number.

---

## Deduplicated opportunity — the non-overlapping view

The segment figures in §5 are marginal views of the same transactions and must
not be summed. To get an additive number, every district transaction is placed
in **exactly one cell** of a three-way partition — channel × origin × card
group (16 cells, `segments/dedup_cells.csv`). Each transaction belongs to one
cell only, so cell figures sum correctly.

Benchmark = the best *sized* cell (≥100 transactions): **mobile / elsewhere /
classic at 77.05%**. Lift = (77.05% − cell share) × cell district value.

| Channel | Origin | Card group | Txns | District value | Store share | **Dedup lift** |
|---|---|---|---|---|---|---|
| **mobile** | **local** | **classic** | 2,675 | 127,024 | **66.09%** | **13,928** |
| **contactless** | **local** | **classic** | 942 | 52,129 | **62.05%** | **7,820** |
| mobile | elsewhere | premium | 346 | 20,878 | 65.49% | 2,414 |
| contactless | elsewhere | classic | 952 | 57,478 | 74.23% | 1,624 |
| mobile | local | premium | 143 | 8,208 | 63.07% | 1,148 |
| mobile | elsewhere | classic | 1,782 | 105,075 | 77.05% | 0 (best) |
| *10 cells under 100 txns* | | | 257 | 16,847 | — | not sized |

**Deduplicated total: 26,934 units** (lifting every sized cell to the best
cell's share). Against the global 69.35% benchmark instead of the best cell,
the deduplicated figure is **9,086 units**.

### The controlled comparison now points at origin, not channel

A cell pair differing in exactly one dimension isolates that dimension. On the
corrected basis there are **two independent origin-only pairs, and they agree**:

| Pair (channel and card group held constant) | Store share | Gap |
|---|---|---|
| mobile / **elsewhere** / classic | 77.05% | — |
| mobile / **local** / classic | 66.09% | **10.96 pts** |
| contactless / **elsewhere** / classic | 74.23% | — |
| contactless / **local** / classic | 62.05% | **12.18 pts** |

Locals convert 11–12 points worse than visitors, and the effect holds in both
payment channels. Two separate controlled comparisons reaching the same
magnitude is much stronger evidence than one, and it corroborates §5's
marginal 9.6-point origin gap.

The channel-only pairs, by contrast, now show almost nothing: mobile vs
contactless within local/classic is **4.04 points** (66.09% vs 62.05%), and
within elsewhere/classic **2.82 points** (77.05% vs 74.23%). The first draft
reported the local/classic pair as a 19.9-point gap and called it the
readout's central insight — that figure came from the merged descriptor
inflating `mobile / local / classic` to 81.92%. Compare the two tables: the
contactless rows are unchanged, the mobile rows moved.

**One cell is 52% of the whole opportunity.** `mobile / local / classic` is
2,675 transactions — 38% of district transactions — and 13,928 of the 26,934
deduplicated total. It is the store's largest cell, it is local, and it
underperforms the same-channel same-card visitor cell by 11 points. If there
is a single thing to investigate, it is **why local CLASSIC customers convert
worse than visitors**, in the store's busiest segment.

### Reconciling the two totals

| Statement | Value | Additive? |
|---|---|---|
| District ceiling (all non-store value) | 119,148 | Yes — exhaustive |
| Deduplicated lift to best cell | **26,934** | Yes — disjoint cells |
| Deduplicated lift to global benchmark | 9,086 | Yes — disjoint cells |
| Sum of §5 marginal segment figures | *do not sum* | **No — overlapping** |

The deduplicated 26,934 is the defensible planning number: it counts every
transaction once, and sits inside the 119,148 ceiling. Note the district value
here (387,638) is all-hours; §5's 387,157 is open-hours only — a 0.1%
difference, immaterial to the shares.

Cells under 100 transactions (257 txns, 16,847 units) are deliberately left
unsized — their shares swing on a handful of transactions. They are a cap on
precision, not a hidden opportunity.

**Why the corrected number is bigger.** Splitting the descriptors *reduced* the
store's measured share, which *increased* every figure that depends on
headroom: the ceiling rose from 88,296 to 119,148 and the deduplicated lift
from 18,431 to 26,934. A correction that makes a merchant look smaller makes
its opportunity look larger. The two moved in opposite directions, which is
worth stating plainly to anyone who saw the earlier number — this is not a
more optimistic reading of the same data, it is a less flattering one.

---

## Total opportunity

| Frame | Value | Confidence |
|---|---|---|
| **District ceiling** — all fast-food value not already the store's | **118,667** | High — arithmetic |
| ├ Acquisition: cards that never use the store | 80,487 | High |
| └ Wallet: store customers' spend at neighbours | 38,180 | High |
| **Origin lift** — locals converted at visitor rates | **18,369** | Medium — two controlled comparisons agree |
| **Hourly tuning** — below-average hours to own average | **5,358** | Medium — assumes shortfall is winnable |
| **Premium cards** — INFINITE converted at PLATINUM rates | **2,388** | Medium — small base (296 txns) |
| **Channel lift** — contactless converted at mobile-pay rates | **2,305** | Low — was 15,142 before the identity fix |
| Closed hours | 334 | Low — hypothetical, not actionable (mall hours) |
| *Adjacent:* delivery **pool** (quote as % of it) | *needs recomputation* | See §Q6 note — the published 715,544 used the merged customer set |

**Deduplicated (additive) alternative: 26,934 units** — see the
deduplicated section above, which partitions every transaction into one cell
and therefore *can* be summed. Use that figure when a single planning number
is needed.

**Do not sum the middle rows.** They are overlapping views of the same
transactions: a contactless purchase by a local INFINITE cardholder at 11:00
appears in the channel, origin, card-type *and* hourly figures. The only
additive, exhaustive statement is the district ceiling: **118,667 units, 30.7%
of food-court fast-food value, is the theoretical maximum** — and capturing all
of it would mean 100% share, which no venue achieves.

A defensible planning number: **the origin lift (18,369) is the largest single
identified lever**, and it sits inside the 118,667 ceiling rather than adding
to it. Note that this row and the channel row have swapped places since the
first draft; the channel lift is now the *smallest* of the identified levers,
not the largest.

## What McDonald's can do next

Ranked by value-per-unit-of-effort, not by size alone.

1. **Find out why local customers convert worse than visitors.** Locals sit
   11–12 points below visitors in both payment channels — two independent
   controlled comparisons agreeing — worth **18,369 units structurally**, and
   the single largest cell in the analysis (`mobile / local / classic`, 2,675
   transactions) is **13,928 units, 52% of the deduplicated opportunity**.
   Locals know the site and spread their spend; visitors default to the
   recognisable brand. What the data cannot say is *why*, and that is the
   highest-value question in this readout.
2. **Convert non-customers, not existing ones.** 956 cards use this food court
   and never buy from the store, worth 80,487 units — roughly 2× the wallet
   opportunity. Existing customers are 88% loyal; squeezing them further has
   less headroom. Note that part of the wallet leakage goes to the *other*
   McDonald's descriptor on site, which may not be a loss to the brand.
3. **Target INFINITE cardholders specifically.** INFINITE converts 12.5 points
   below PLATINUM, the best-performing substantial card type. Note this is
   narrower than the first draft's claim: premium cards as a class
   (PLATINUM, PREMIER, VISA SIGNATURE) all *over*-perform here. INFINITE is
   the outlier, and with every gap-hour competitor taking a higher ticket than
   the store, the hypothesis is that **the highest-spending customers choose a
   higher-ticket neighbour.**
4. **Focus daypart work on 13:00–17:00, not the late morning.** Those hours
   carry 77% of the hourly opportunity; 10:00–11:00 carries 13%. This reverses
   the first draft, which pointed at 10:00–11:00 on an uncorrected denominator.
5. **Deprioritise** trading hours (334, mall-controlled) and **channel
   interventions (2,305)**. The channel play was the first draft's number-one
   recommendation, on a 19.9-point gap that the merchant-identity fix reduced
   to 4.0. Anyone who saw that version should be told it was withdrawn, not
   quietly re-ranked.

## How to get started

Each step names the specific check, so it can be handed to an analyst or
operator as-is.

**Week 1 — understand why locals convert worse than visitors.**
- This is the largest lever (18,369) and it reproduces in two independent
  controlled comparisons, so the existence of the gap is not in doubt — the
  cause is. Start with what locals buy *instead*: for local cards active in
  the food court, which neighbours do they use, at what hour and ticket?
- Test whether "local" is really proxying for *frequency*. A local visits the
  mall repeatedly and may rotate venues across visits, while a visitor has one
  occasion and takes the familiar brand. Compare share among locals by visit
  count: if rotation explains it, the lever is repeat-visit merchandising, not
  acquisition.
- Check the 16:00 dip against staffing and order-mix records — it is newly
  visible, worth 957 units, and sits in the site's largest hour by value.

**Week 2 — profile the non-customers.**
- Take the 956 never-used-store cards and compare their card-type, origin and
  hour mix against the store's 3,069 customers. The question is whether they
  are *reachable* (same hours, same profile, just choosing a neighbour) or
  *structurally different* (arriving only when the store is shut, or
  exclusively premium).
- Check what share of them are single-visit versus repeat food-court users —
  repeat non-customers are a far better target than one-off mall visitors.

**Week 3 — size the premium gap properly.**
- Widen the INFINITE analysis beyond this one store to **all Kraków McDonald's**
  locations. 296 district transactions is too thin to act on; if the 12-point
  premium gap reproduces city-wide it becomes a brand-level finding, not a
  store one.
- Profile Fast Food 3's cardholders specifically (the highest-ticket
  competitor in the gap hours at 79.9 units): are they the same INFINITE
  cards, and do they ever also buy from the store?

**Week 4 — scope delivery separately.**
- Do not attempt to attribute aggregator spend by merchant name. Instead
  approach it via the store's card base: how many of the 3,069 customers order
  delivery, at what frequency and ticket, and in which hours. That establishes
  whether delivery is a substitute for a food-court visit or an incremental
  occasion — the question that determines whether it is cannibalisation or growth.

**Both blocking data questions from the previous draft are now answered** —
one of them against the draft's own assumption:
- ~~Confirm `McDonalds 61600303` is this store.~~ **Resolved: it is not.**
  Card overlap put it at 44.8%, indistinguishable from Burger King Bonarka at
  43.6% (a different restaurant in the same mall) and nowhere near the 80%+ a
  shared till would produce. It is excluded from the store throughout. The one
  residual check worth doing is against McDonald's own terminal records — if
  they show a single site after all, the overlap test has found something
  genuinely odd about how that descriptor is used, and this readout would need
  revisiting again.
- ~~Confirm which `30-644` merchants are physically in Bonarka.~~ **Resolved:
  the six exclusions were right.** They were originally removed by name
  inference alone; the same card-overlap test now corroborates it
  independently. The six sit at 7–13% overlap with the store, against 29–44%
  for every merchant genuinely on the site — including `PL SBX KRAKOW BONARKA`
  at 29.5%, which is why that one stays in the denominator. Name inference and
  customer evidence agree on all seven Starbucks records.

---

## What the correction changed

Kept as a record, because the pattern is more useful than this store's numbers.
Two errors were at work: a **merchant-identity** error (merging a co-tenant
into the store) and a **market-denominator** error (counting six off-site
outlets as neighbours). The second was fixed in the first revision; the first
was *introduced* by it.

| First draft said | Corrected | What broke |
|---|---|---|
| Share climbs 38% → 67% through the day, inverting the brand pattern | Flat 65–74%, no trend | Denominator: off-site coffee shops suppressed morning share |
| Breakfast is the one closed-hour play worth making (08:00, 1,044 units) | 08:00 is worth 120 units; 4 of 7 closed hours have no market at all | Denominator: the "missing breakfast demand" was cafés across town |
| Channel is the biggest lever — 19.9 pts, 58% of the opportunity | 4.0 pts, the smallest identified lever | Identity: the merged descriptor was ~all mobile, inflating one cell |
| No local-vs-visitor play; 2.6 pts, "no signal" | 9.6 pts marginal, 11–12 pts in two controlled comparisons — the largest lever | Identity: the merged descriptor's customers were disproportionately local |
| Premium cardholders under-select the store | Only INFINITE does; PLATINUM, PREMIER and VISA SIGNATURE all over-perform | Identity: CLASSIC fell below PLATINUM once the merge was removed |
| Prioritise 10:00–11:00 — 43% of the opportunity | 13%; prioritise 13:00–17:00 at 77% | Denominator |
| Store share 77.3%, opportunity 18,431 | 69.3%, opportunity 26,934 | Identity |

Three things are worth taking from this:

1. **Every wrong finding was specific, plausible and actionable.** None looked
   like an error. The channel finding even survived a controlled comparison,
   which is the technique meant to catch confounding — but controlling for
   customer mix does nothing about a numerator that is wrong.
2. **The direction of the identity error was flattering.** Over-merging raises
   a merchant's apparent share and *shrinks* its apparent opportunity. A
   merchant reviewing its own readout has no incentive to challenge it, and
   the correction makes the number go up.
3. **Both errors lived in "which merchants count", not in the method.** The
   arithmetic was correct throughout. That is why §7 of the method doc is the
   longest section, and why the app now shows customer-overlap evidence
   instead of a bare list of names.

---

## Caveats — carry these with the number

1. **This is share reallocation, not incremental demand.** The arithmetic
   assumes the store captures its average share of *existing* district
   fast-food value, i.e. takes it from food-court neighbours. It does not model
   growing the hour, and it assumes the shortfall is winnable. A structural
   cause — a competitor's breakfast offer, a coffee-led neighbour, the store's
   own opening ramp — would invalidate part of it.
2. **09:00 is the store's first trading hour**, so some of its 3.0-point gap
   is an opening ramp rather than lost competition. On the corrected basis it
   contributes only 164 units, so this no longer needs its own sensitivity.
3. **21:00 is a near-closed hour** (50 store transactions, 59 district). Its
   figures are arithmetic, not signal.
4. **49,080 rows city-wide carry `tran_id_gmt_tm = '000000'`**, a missing-time
   placeholder, and are excluded throughout. Left in, they produce a false
   01:00–02:00 peak rivalling lunch. Totals here are therefore ~6.5% below
   true totals, but hourly *shape* and *shares* are sound.
5. **Hours are Warsaw local, DST-aware**, converted from GMT via ICU. Raw
   `tran_id_gmt_tm` is GMT; an unconverted axis shifts every peak by 1–2 hours.
6. **`prch_dt` basis is unresolved** — it is combined with a GMT time to build
   the timestamp. If `prch_dt` is a local posting date, rows near midnight get
   a date off by one. This perturbs only 23:00–01:00, the smallest hours, so it
   does not move any conclusion here, but those hours are not certified.
7. **Postcode ≠ administrative district.** `30-644` is one retail site. A
   dzielnica-level view needs an external postcode→district lookup.
8. **The market denominator drives more of this readout than the arithmetic
   does.** Two of the first draft's headline findings — an upward share curve
   through the day, and a breakfast opportunity at 08:00 — were produced
   entirely by counting six off-site outlets as neighbours, and a third (the
   channel lever) by merging a co-tenant into the store. Each was specific,
   plausible and actionable. Before trusting any figure here, check §7 of
   `../opportunity-method.md` and confirm who is in the denominator.

---

## Open questions for the storyline

- **Why do locals convert worse than visitors?** The largest finding in the
  readout, and the data shows the gap but not the cause. This is the question
  to take to the operator.
- **Why the 16:00 dip?** Newly visible once the descriptors were split: 67.2%
  against a 69.4% benchmark in the site's largest hour by value, worth 957
  units. Worth checking for an operational cause — staffing changeover, order
  mix — now that it is isolated to the single descriptor.
- **Is 69.4% the right ambition?** The benchmark is the store's own average. A
  stronger frame is its best sustained hours, or the best sized cell (77.05%),
  which is what the deduplicated view already uses.
- **How does this store compare to other Kraków McDonald's?** Only this store
  and the brand-wide city figure have been computed. Per-store shares across
  the city would establish whether 69.3% is exceptional or typical of mall
  sites — and would also test whether `McDonalds 61600303` behaves like a
  separate outlet, which is the open question underneath the identity fix.
- **Is the delivery pool still right?** §Q6 was not recomputed after the
  customer set changed from 3,233 to 3,069 cards. Rerun before reuse.
- **McDonald's matching is name-based** (`ILIKE '%mcdonald%' OR '%mc donald%'`)
  as there is no chain identifier. This store was matched exactly by name, so
  store-level figures are unaffected; the city-wide 30.6% may miss odd spellings.

## Reproducing this

Source CSVs (2025, merchant-side geography, `'000000'` excluded, Warsaw local hour):

| File | Contents |
|---|---|
| `out/adhoc/pc30644_restaurants_by_hour_2025.csv` | District, by hour × restaurant category |
| `out/adhoc/pc30644_mcd303_by_hour_2025.csv` | This store, by hour |
| `out/adhoc/krakowMERCH_restaurants_by_hour_2025.csv` | Kraków city-wide, by hour × category |
| `out/adhoc/krakowMERCH_mcdonalds_by_hour_2025.csv` | Kraków McDonald's brand-wide, by hour |

**Geography warning:** use merchant-side columns (`mrch_city_nm_raw`,
`mrch_postal_code`) for "where the store is". `lau_enr` / `pstl_cd_enr` /
`fua_enr` are **cardholder** location — this store has 1 merchant postcode but
328 distinct `lau_enr` values. Filtering on `lau_enr = 'KRAKOW'` answers "where
Kraków residents spent", a different question.
