# Opportunity sizing — the method

How Merchant Insights turns a share gap into a number, without double-counting
and without an AI call. Every step is arithmetic over pre-aggregated marts, so
the same inputs always give the same output.

Implemented in `app/opportunity.py` (pure pandas, unit-testable) and
`app/opportunity_data.py` (mart access). A standalone replication of the same
method, straight against the raw Parquet, is `tools/adhoc/dedup_opportunity.py`.

A fully worked example with real numbers is in
[`examples/mcd303-worked-example.md`](examples/mcd303-worked-example.md).

---

## 1. Why deduplication is necessary

Size an opportunity per segment — by card type, by channel, by customer origin,
by hour — and the figures **cannot be summed**. One contactless purchase by a
local premium cardholder at 11:00 appears in the channel figure, the origin
figure, the card-type figure and the hourly figure alike. Adding them counts
the same units up to four times.

This is not a rounding problem. On the worked example, the marginal segment
figures implied a far larger opportunity than the deduplicated total.

## 2. The partition

Every transaction is assigned to **exactly one** cell:

    cell = (channel, origin, card_group)

| Dimension | Values |
|---|---|
| `channel` | `mobile`, `contactless`, `other` |
| `origin` | `local` (cardholder's municipality = merchant's), `elsewhere` |
| `card_group` | `classic`, `premium`, `other` |

3 × 2 × 3 = 18 possible cells. Because a transaction belongs to one cell only,
cell figures are additive by construction.

Hour is deliberately **not** a cell dimension — adding 24 hours would give 432
cells and fragment the data past the point where any cell is dense enough to
benchmark. Hourly analysis stays a separate, marginal view on the Opening Hours
page.

## 3. The sizing arithmetic

    cell_share = merchant value in cell / market value in cell
    benchmark  = max(cell_share) over cells with >= 100 transactions
    cell_lift  = max(benchmark - cell_share, 0) * market value in cell
    TOTAL      = SUM(cell_lift) over sized cells            <- additive

Two benchmark choices, both reported:

- **`lift_to_best`** — every cell raised to the best sized cell's share.
  Aspirational, but grounded: the best cell proves that share is attainable
  with this merchant's own offer, in this location.
- **`lift_to_global`** — every cell raised to the merchant's overall share.
  Conservative. A cell already above it contributes zero.

### Cells that are not sized

Cells under **100 transactions** are shown but never sized: their shares swing
on a handful of sales. The app states how many cells and how much value that
excludes. **This is a cap on precision, not hidden upside** — resist the urge
to extrapolate into it.

### The ceiling

    ceiling = market value - merchant value

This is the only *exhaustive* statement available: everything in the market
that is not already the merchant's. It is a bound, not a target — reaching it
means 100% share, which no merchant achieves. The deduplicated lift always
sits inside it.

## 4. Controlled comparisons — why the partition improves the finding

Cells differing in **exactly one** dimension are a controlled comparison: the
other two coordinates are held constant, so the share difference is
attributable to that dimension rather than to a different kind of customer.

`controlled_comparisons()` enumerates every such pair automatically and ranks
them. This is what promotes a correlation to evidence.

From the worked example: the marginal channel gap was 12.7 points and could
have been customer mix. Comparing `mobile/local/classic` (81.9%) against
`contactless/local/classic` (62.1%) holds origin and card type constant — and
the gap *widens* to **19.9 points**, ruling mix out.

## 5. Attaching value to findings

`diagnostics.py` says *what* to fix and scores it 0..1.
`opportunity.attach_opportunity()` says what each fix is *worth*.

A value is attached **only** when a controlled comparison isolates the same
dimension the finding is about. Findings on topics the partition does not
cover — opening hours, loyalty, cross-sell, location — are left **unsized**
rather than given a speculative number.

An unsized finding is not a lesser finding; it is one this mart cannot price.
Findings then sort by value where known, score otherwise, because a mild gap
in a large customer group is worth more than a severe gap in a thin one.

`unattributed()` reports the deduplicated total minus what was attached. If the
cells say 26,934 and only 11,000 is attributable to a named finding, the
remainder is stated as real-but-unexplained rather than folded into a finding
to make the arithmetic look complete.

## 6. Measured vs scenario — never one total

| | Measured | Scenario |
|---|---|---|
| Source | Observed in transactions | Needs an assumption |
| Question | "What share am I not capturing?" | "What is X% of this pool?" |
| Additive | Yes, across cells | No |
| Function | `size_cells()` | `scenarios()` |

Scenario levers have a **measurable pool** but an **unobservable current
capture**, so they are only ever expressed as *"some % of &lt;pool&gt;"*, with
the rate set by the user in the UI.

| Lever | Pool | Why a rate is unavoidable |
|---|---|---|
| **Delivery** | Aggregator spend by this merchant's own customers | The aggregator is the merchant of record — an order through Glovo **may already be this merchant's sale**. No column distinguishes it. Whatever they already earn via aggregators must be netted off from their own reporting. |
| **Loyalty** | The merchant's own revenue | A retention gap vs peers does not convert to revenue at a fixed rate, and peer retention may reflect a different customer base. |
| **Basket** | The merchant's own revenue | A peer-median ticket is not a target: it may reflect different product mix or price point. Raising price risks volume, which the pool does not model. |
| **Catchment** | Resident spend captured outside the area | Implies a new location, and causality is weak — residents may shop elsewhere because they work there. |

The app shows both totals side by side with an explicit warning **not to add
them**. They are different kinds of claim.

### Delivery platform selection

Glovo, Wolt and Pyszne.pl only. **Uber Eats, Deliveroo and Bolt Food are
excluded**: verified against this dataset, all three have *zero*
Polish-merchant transactions (Deliveroo exited Poland in 2021, Uber Eats
followed), so their rows are Polish cardholders ordering delivery abroad.
Including them would have counted unreachable foreign travel spend as
addressable local demand — it would have inflated the pool by roughly a third.

## 7. Two data-quality traps the UI must ask about

Neither is decidable from a merchant's name, postcode or category, so the app
surfaces both and the merchant makes the final call. Both were found the hard
way on the worked example — and one of them was initially got *wrong*.

**One site, several merchant descriptors.** A second terminal, a concession
counter, or a renamed acquirer record appears as a separate merchant. Any left
out is counted as a *competitor*, understating the merchant's share.

The error runs both ways, and the dangerous direction is over-merging. On the
worked example, `McDonalds 61600303` was merged into `MCDONALDS 303 KRAKOW 01`
because the postcode, city and category all matched, taking share to 77.2%.
That was wrong, and it took a customer-overlap test to see it (below). The
defensible figure is **69.3%**. A matching postcode is not evidence of a shared
building; in this dataset it is barely evidence of a shared *city*.

**Merchants registered to a postcode they are not in.** A chain may register
several outlets to one head-office address. On the worked example, six outlets
named for other districts sat in the target postcode and inflated the market
denominator by **16%**. A central registration is indistinguishable from a
genuine neighbour by name alone.

### The test that decides both: shared customers

Names cannot separate these cases; customers can. For any two merchants in a
cell, measure the share of the *candidate's own* customers who also buy from
the merchant in question:

- **Two tills in one restaurant** share nearly every customer — the same people
  are standing in the same building.
- **Two shops in one building** share a lot, because visitors buy at both.
- **An outlet registered here but trading elsewhere** shares very few.

The baseline is a property of the location, not a universal constant: in a busy
mall every neighbour overlaps heavily, on a quiet street none do. So a
candidate must be judged against *the rest of the field*, and only called the
merchant's own site when it stands clear of the best genuine neighbour.

On the worked example, postcode 30-644 is a shopping centre:

| Candidate | Shared customers | What it is |
|---|---|---|
| `McDonalds 61600303` | **44.8%** | assumed a second till — **it is not** |
| `PL BK KRAKOW BONARKA` | 43.6% | a Burger King in the same mall |
| `BONARKA KRAKOW` | 38.0% | same mall |
| `P041 BONARKA` | 31.3% | same mall |
| `PL SBX KRAKOW BONARKA` | 29.5% | same mall |
| six `PL SBX KRAKOW …` others | 7–13% | registered here, trading elsewhere |

The candidate had the **highest overlap of any merchant in the postcode**, which
is exactly why the merge looked safe. But the runner-up was a different
restaurant chain at 43.6%. Being top of the ranking carried no information; the
descriptor was an ordinary co-tenant. Any rule that trusts the top of the list,
or a median, confirms the error — so the app's verdict stays silent unless a
candidate clears the field by a margin, and reports "indistinguishable from a
neighbour" otherwise. See `_flag_colocation` in `app/opportunity_data.py` and
the regression tests in `tests/test_colocation.py`.

The same test independently **confirms** the six exclusions: their 7–13%
overlap marks them as not in this building, which is why removing them from the
denominator was right.

Correcting the registration problem alone moved the worked example's share from
58.7% to **69.3%** and cut its hourly opportunity substantially. These are not
edge cases.

## 8. Other analysis conventions this inherits

- **`tran_id_gmt_tm = '000000'` is a missing-time placeholder, not midnight.**
  Excluded from every hour-based analysis. Left in, it manufactures a false
  01:00–02:00 peak rivalling lunch — in one postcode, 99% of rows at those
  local hours were placeholders.
- **Hours are Europe/Warsaw local, DST-aware** (ICU), converted from GMT. An
  unconverted axis shifts every peak by 1–2 hours and DST smears it.
- **`lau_enr` / `pstl_cd_enr` / `fua_enr` are cardholder location;
  `mrch_*` are merchant location.** They answer different questions. One store
  in the worked example had 1 merchant postcode and 328 distinct `lau_enr`
  values.
- **Currency.** The DATASPRINT dataset's amounts are a **fictional currency**
  prepared for hackathon purposes. Never convert to EUR/PLN/USD or present as
  real money. Shares, ranks and ratios are unaffected.

## 9. Compliance

`opportunity_market` carries the standard publication filter (≥30 cards,
≥3 merchants, no merchant >75% of value).

`opportunity_merchant`, `opportunity_delivery` and `opportunity_overlap` are
**deliberately exempt**,
on the same grounds the repo already exempts the Merchant Benchmark page: they
are the signed-in merchant's private view of **its own** data. The >75% rule
exists to stop a merchant being identifiable to *other* merchants; here the
merchant is looking at itself. Without the exemption the analysis would be
self-defeating — the highest-share cells are exactly the informative ones, and
a dominant merchant would see no opportunity at all.

`opportunity_overlap` additionally requires **both** merchants in a pair to
clear the 100-transaction floor, and suppresses any pair sharing fewer than 30
customers, so a pair is never published down to a handful of identifiable
people. It reports counts of shared customers, never who they are.

Competitor detail shown to a merchant should stay anonymised
(`Fast Food 1`, `Fast Food 2`, …) — see
[`examples/mcd303-competitors-anon.csv`](examples/mcd303-competitors-anon.csv).

## 10. Replicating without the app

```bash
python3 tools/adhoc/dedup_opportunity.py \
    --store "MERCHANT NAME" \
    --postcode 30-644 \
    --categories "FAST FOOD RESTAURANTS" \
    --exclude "OFF SITE MERCHANT 1" "OFF SITE MERCHANT 2" \
    --out out/adhoc/segments
```

`--store` accepts several descriptors, and they are summed into one numerator.
Only pass more than one when shared customers justify it (§7) — a matching
postcode does not. Over-merging inflates the merchant's share and *shrinks* the
opportunity, so it fails quietly in the flattering direction.

Prints the ceiling, both benchmark variants and the deduplicated total, and
writes the full cell grid to `dedup_cells.csv`. Runs against the raw Parquet,
so it needs no marts — useful for validating a mart-derived number.
