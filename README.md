<img align="right" width="140" src="assets/eternia-trading-co.png" alt="Eternia Trading Co. logo">

### <p style="font-size:32px">Eternia Trading Co.</p>

*Supplying the bold, the baffled, the noble, and the deeply suspicious all across Eternia.*

## Last refreshed

This data was last refreshed on **29 May 2026**.

Data is automatically updated each day. Data covers a rolling three-year window — the current calendar year and the two preceding years — so the oldest year drops off each January as the new year is added.

## About the company

Eternia Trading Co. is one of the most recognisable commercial houses in all Eternia, with trading routes, supplier networks, and customer relationships stretching from the Royal Kingdom to the Dark Hemisphere and well beyond. The company deals in a broad portfolio of high-demand goods including weapons, armour, mystical accessories, transport, consumables, field equipment, and other specialist items required by Eternia's more adventurous populations.

Known for its ambitious regional reach and flair for dramatic merchandising, ETC has built its reputation on being able to put the right product in the right hands at the right moment — whether that means resupplying a palace guard, outfitting a sky patrol, restocking an underground engineering crew, or discreetly fulfilling a rather ominous bulk order from somewhere with too many skull-shaped doors. Its public image is polished, its distribution network is formidable, and its appetite for expansion is, by most accounts, enormous.

## Leadership drama

At the heart of the business are its two formidable sales managers: **He-Man** for the heroic side of the ledger, and **Skeletor** for the more aggressively sinister accounts. Both insist they are carrying the company, both are obsessed with winning the monthly numbers race, and both treat the sales leaderboard as if the fate of Eternia depends on it.

Their rivalry is the engine that keeps the whole enterprise moving. A strong quarter in the Royal Kingdom will be met by a suspiciously intense push in the Dark Hemisphere; a surge in heroic armour sales will somehow be answered by an urgent campaign for cursed blades, shadow beasts, and morally questionable accessories. The result is a company culture powered by competitive energy, theatrical self-belief, and the constant sense that someone is about to storm into a meeting and demand a revised forecast.

## What Eternia Trading Co. actually "does"

In the broadest possible sense, Eternia Trading Co. is in the business of cross-realm commerce. It buys, sells, distributes, promotes, discounts, bundles, and dramatically repositions inventory for customers from every corner of the planet.

Its specialties include:
- Supplying heroic factions with armour, weapons, transport, and defensive gear.
- Supplying evil factions with ominous weaponry, dark magic paraphernalia, traps, and creatures that should probably require additional documentation.
- Keeping neutral customers happily stocked with whatever helps them survive the week.
- Turning regional chaos into something that looks, at least in a dashboard, like a coherent operating model.

## Why this dataset exists

This repository contains a fictional sales and analytics dataset themed around Eternia Trading Co. and designed for BI, dimensional modelling, SQL, analytics engineering, and dashboard storytelling.

It is intended to feel fun rather than corporate: a playful star-schema sales model where serious data work meets a knowingly camp fantasy business premise. In other words, the numbers are useful, the company is ridiculous, and that is entirely the point.

The dataset contains:
- `data/dim_location.csv`
- `data/dim_salesperson.csv`
- `data/dim_customer.csv`
- `data/dim_product.csv`
- `data/fact_sales.csv` *(refreshed daily)*
- `data/fact_salesperson_targets.csv` *(refreshed daily)*

## Schema

### fact_sales
Grain: one row per sales transaction line. Multiple lines can share the same `order_id` (same salesperson, customer, and location) with each line representing a different product.

Columns:
- `sales_id`
- `order_id`
- `order_date`
- `location_key`
- `salesperson_key`
- `customer_key`
- `product_key`
- `quantity`
- `unit_price`
- `discount_amount`
- `net_amount`

### fact_salesperson_targets
Grain: one row per salesperson per calendar month.

Columns:
- `date` – last calendar day of the month
- `salesperson_key` – foreign key to dim_salesperson
- `monthly_target` – net revenue target for the month

Targets use a seasonally adjusted formula based on each salesperson's annual quota, with higher-volume months receiving proportionally higher targets. The rolling window always covers the current year and the two preceding calendar years; targets for the remainder of the current year are projected forward. The oldest year rolls off each January.

### dim_location
Columns:
- `location_key`
- `city_name`
- `region`
- `alignment`
- `population_size`

### dim_salesperson
Columns:
- `salesperson_key`
- `name`
- `faction`
- `sales_manager`
- `role`
- `specialty`
- `home_region`

### dim_customer
Columns:
- `customer_key`
- `customer_name`
- `race`
- `alignment`
- `home_region`
- `loyalty_tier`

### dim_product
Columns:
- `product_key`
- `product_name`
- `category`
- `alignment`
- `brand_name`
- `power_level`
- `unit_cost`

## Date logic

- Rolling window start: `2024-01-01` (1 January, 2024)
- Current end date: `2026-05-28`
- Target fact volume: approximately **250,000 rows per calendar year**
- Maximum window: 3 full calendar years; oldest year rolls off each January

## Distribution logic

The fact table is generated with:
- Seasonal monthly weighting repeated across all months in scope
- A mild heroic bias in earlier parts of the year
- Stronger evil presence in later months
- Region-aware location selection
- Mostly alignment-matching product sales, with occasional cross-alignment exceptions
- Higher discount variability for Orko
- Year-level performance factors that vary transaction volume, pricing, and Heroic/Evil faction split year-on-year — 2024 was a disrupted year (lower volume and pricing, Evil faction dominant), 2025 is the recovery baseline, and 2026 reflects an expansion period with stronger volume, pricing power, and a resurgent Heroic faction. Future years beyond the explicitly defined range receive automatically generated factors seeded on the year, ensuring consistent but varied performance across the rolling window

## Refresh summary

- Window start         : `2024-01-01`
- Window end           : `2026-05-28`
- Days covered         : `879`
- Years covered        : `2.41`
- Total fact_sales rows              : `577,233`
- New fact_sales rows this run       : `780`
- Total fact_salesperson_target rows : `504`
- New fact_salesperson_target rows   : `0`

## Power BI Semantic Model

This repository includes a pre-built Power BI semantic model (`power-bi/semantic-model/`) ready to use out of the box.

The model connects directly to the CSV files hosted in this GitHub repository, so refreshing it in Power BI Desktop will always pull the latest data. Since the underlying dataset is updated daily, the model can be kept current with a single refresh — no manual data exports or file replacements required.

## Brand Assets

To help you create professional dashboards and reports, this repository includes complete brand assets for Eternia Trading Co.:

- **Brand Guidelines** (`assets/eternia-trading-co-brand-guidelines.pdf`) – Full brand guide including colour palettes, typography, logo usage, and design principles
- **Logo Suite** (`assets/logos/`) – Multiple logo variations including horizontal, shield-led, and circular crest formats in various file types
- **Power BI Theme** (`power-bi/theme/eternia-trading-co-theme.json`) – Pre-configured theme with brand colours, fonts, and styling for consistent Power BI reports
- **Report Background** (`power-bi/theme/report-background.png`) – Branded background image for Power BI report pages

Feel free to use these assets to create on-brand dashboards, presentations, and analytical reports.

## Support

The Eternia Trading Co. Dataset is provided free of charge. If it saves you time or sparks a project, Greyskull Analytics would really appreciate your support.

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-support-%23FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/greyskullanalytics)

## License

This dataset is free to use for personal and commercial purposes. See the [LICENSE](LICENSE) file for full terms.

## About Greyskull Analytics

Greyskull Analytics builds data solutions that make businesses better. By the Power of Greyskull!

[www.greyskullanalytics.com](https://www.greyskullanalytics.com)
