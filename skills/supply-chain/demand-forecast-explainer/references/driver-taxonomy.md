# Demand Forecast Driver Taxonomy

Use this reference to identify and describe forecast drivers in plain English for retail/grocery leadership.

## Primary Driver Categories

### 1. Seasonality
**What it is:** Predictable demand patterns tied to time of year, holidays, or calendar events.
**How to describe it:** "Demand naturally rises/falls this time of year due to [season/holiday/event]."
**Examples:**
- Back-to-school (Aug-Sep): school supplies, lunchbox items, dairy
- Holiday entertaining (Nov-Dec): baking goods, premium proteins, beverages
- Summer grilling (May-Jul): meats, condiments, charcoal
- New Year health (Jan-Feb): produce, supplements, fitness-related
- Tax refund season (Feb-Mar): discretionary categories, electronics

**Typical magnitude:** 10-40% above/below annual average depending on category

---

### 2. Promotions & Events
**What it is:** Planned commercial activities that artificially stimulate demand.
**How to describe it:** "A confirmed [type] promotion in Week [X] is expected to lift demand by [Y]%."
**Sub-types:**
- TPR (Temporary Price Reduction): typical lift 20-80% depending on depth
- BOGO/Multi-buy: typical lift 40-120%
- End-cap/Display: typical lift 15-40%
- Digital coupon/loyalty: typical lift 10-30%
- Circular feature: typical lift 25-60%
- Competitor promotion (negative impact): typical drag 5-20%

**Key nuance for executives:** Promotional lift is usually followed by a post-promotion dip. The NET effect over the full cycle may be much smaller than the peak week lift.

---

### 3. Price Changes
**What it is:** List price or shelf price changes that affect demand via price elasticity.
**How to describe it:** "A [X]% price [increase/decrease] is expected to [reduce/increase] unit demand by approximately [Y]%."
**Elasticity rules of thumb (grocery):**
- Staples (milk, bread, eggs): elasticity -0.3 to -0.5 (inelastic)
- Branded CPG: elasticity -1.5 to -2.5 (elastic)
- Premium/organic: elasticity -1.0 to -1.8
- Private label: elasticity -0.8 to -1.5

**Key nuance:** Cross-elasticity matters — a price increase on Brand A may lift Brand B and Private Label in the same category.

---

### 4. External Signals — Weather
**What it is:** Weather patterns that shift demand for weather-sensitive categories.
**How to describe it:** "Extended [heat/cold/storms] in key markets is expected to [increase/decrease] demand for [category] by [X]%."
**Weather-sensitive categories:**
- Ice cream, beverages, sunscreen: +5-15% per degree above normal (summer)
- Soups, hot beverages, comfort foods: +5-10% per degree below normal (winter)
- Storm prep (water, batteries, canned goods): +200-500% in 48hrs pre-storm
- Grilling items: highly sensitive to weekend forecasts

---

### 5. External Signals — Economic
**What it is:** Macroeconomic indicators that shift consumer spending patterns.
**How to describe it:** "Consumer confidence is [up/down] [X]% and gas prices are [up/down], which typically shifts demand [toward/away from] [value/premium] products."
**Key indicators:**
- Consumer Confidence Index (CCI): leading indicator for discretionary spend
- Gas prices: inverse correlation with trip frequency and basket size
- Unemployment rate: lagging indicator for trade-down behavior
- SNAP/EBT timing: predictable monthly demand spikes in eligible categories
- Inflation rate: drives private label share gains when rising

---

### 6. Trend Shifts
**What it is:** Sustained directional change in demand not explained by seasonality or events.
**How to describe it:** "We're seeing a sustained [upward/downward] trend of approximately [X]% per [period], likely driven by [distribution gain/loss, consumer preference shift, competitive entry]."
**Common causes:**
- Distribution gains (new stores carrying the item)
- Distribution losses (delisted at a retailer)
- Consumer preference shifts (health trends, sustainability)
- Category maturity / decline
- Competitive new product entry

---

### 7. New Product Introduction (NPI)
**What it is:** Demand for newly launched products with limited historical signal.
**How to describe it:** "This is a new item with [X weeks] of history. The model is relying heavily on [analogous items/category averages] and uncertainty is [higher than normal]."
**Key nuance:** NPI forecasts typically have 2-3x wider confidence bands than established items. Flag this for leadership.

---

### 8. Supply Disruptions (Demand-Side Impact)
**What it is:** Supply constraints that suppressed historical demand, making the baseline unreliable.
**How to describe it:** "Historical demand was depressed by [stockouts/allocation] in [period]. The current forecast assumes full availability and reflects true unconstrained demand."
**Key nuance:** If the model was trained on stockout periods, it may underforecast when supply normalizes. Call this out explicitly.

---

### 9. Cannibalization & Halo Effects
**What it is:** One product's demand affecting another's within the same category.
**How to describe it:** "The launch of [Product B] is expected to cannibalize [X]% of [Product A]'s volume, with a net category impact of [+/-Y]%."

---

### 10. Model / Methodology Change
**What it is:** The forecast changed because the forecasting approach was updated, not because the market changed.
**How to describe it:** "This revision reflects a model update [retraining/new features/algorithm change] rather than a change in market conditions. The new model [better captures X / corrects for Y]."
**Key nuance:** Executives need to know whether a revision reflects NEW INFORMATION or BETTER MATH. These require different responses.

---

## Driver Description Template

When explaining a driver to leadership, use this structure:

> **[Driver Name]:** [One sentence explaining what happened in plain English]
> - **Impact:** ~[X] units ([Y]% of total forecast change)
> - **Confidence:** [High/Medium/Low] — based on [data quality indicator]
> - **What to watch:** [Leading indicator that would confirm or refute this driver]
