<img align="right" width="140" src="assets/eternia-trading-co.png" alt="Eternia Trading Co. logo">

### <p style="font-size:32px">Eternia Trading Co.</p>

*Supplying the bold, the baffled, the noble, and the deeply suspicious all across Eternia.*

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

The dataset is built on a real [Azure SQL ERP database](https://github.com/GreyskullAnalytics/eternia-trading-co/wiki/Database-BACPAC), updated daily. The files in this repository are published outputs of that system, refreshed automatically.

## What's in this repository

| Path | What it contains |
|---|---|
| `data/` | Pre-modelled star-schema CSVs — ready to use in any BI tool |
| `source-data/sales-targets/` | Annual sales target planning workbooks (Excel), one per manager per year |
| `source-data/database/` | BACPAC download instructions — the full ERP database as a monthly snapshot |
| `power-bi/` | A pre-built Power BI semantic model and report |
| `assets/` | Brand guidelines, logos, and Power BI theme |

## Getting started

### Option 1 — Power BI semantic model

The fastest path. Clone this repository, open `power-bi/semantic-model/Eternia Trading Co Retail Dataset.pbip` in Power BI Desktop, and hit **Refresh**. The model reads directly from the GitHub-hosted CSVs — no manual data wrangling required.

→ **[Power BI Semantic Model](https://github.com/GreyskullAnalytics/eternia-trading-co/wiki/Power-BI-Semantic-Model)** — setup guide and connection details.

### Option 2 — Pre-modelled CSVs

Six CSV files in `data/` form a clean star schema (four dimension tables, two fact tables) ready to load into any database, BI tool, or notebook without further transformation. `fact_sales` grows daily; `fact_salesperson_targets` is updated each December.

→ **[Star Schema CSVs](https://github.com/GreyskullAnalytics/eternia-trading-co/wiki/Star-Schema-CSVs)** — schema detail, column descriptions, and joining keys.

### Option 3 — Source data

For the data engineering challenge. Download `ETERNIA_ERP_DB.bacpac` from the [Releases](https://github.com/GreyskullAnalytics/eternia-trading-co/releases) page and restore it to any SQL Server-compatible engine. The database contains the complete operational history in a normalised OLTP schema — build your own extraction pipeline and validate your output against the `data/` CSVs.

Pair it with the annual sales target planning workbooks in `source-data/sales-targets/` — deliberately messy Excel files built for a cleansing and unpivoting exercise.

→ **[Database BACPAC](https://github.com/GreyskullAnalytics/eternia-trading-co/wiki/Database-BACPAC)** — schema overview and import instructions.  
→ **[Sales Target Workbooks](https://github.com/GreyskullAnalytics/eternia-trading-co/wiki/Sales-Target-Workbooks)** — workbook structure and the data engineering exercise.

## Brand Assets

This repository includes complete brand assets for Eternia Trading Co.:

- **Brand Guidelines** (`assets/eternia-trading-co-brand-guidelines.pdf`) — colour palettes, typography, logo usage, and design principles
- **Logo Suite** (`assets/logos/`) — horizontal, shield-led, and circular crest formats in multiple file types
- **Power BI Theme** (`power-bi/theme/eternia-trading-co-theme.json`) — pre-configured theme with brand colours and fonts
- **Report Background** (`power-bi/theme/report-background.png`) — branded background image for Power BI report pages

## Support

The Eternia Trading Co. Dataset is provided free of charge. If it saves you time or sparks a project, Greyskull Analytics would really appreciate your support.

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-support-%23FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/greyskullanalytics)

## License

This dataset is free to use for personal and commercial purposes. See the [LICENSE](LICENSE) file for full terms.

## About Greyskull Analytics

Greyskull Analytics builds data solutions that make businesses better. By the Power of Greyskull!

[www.greyskullanalytics.com](https://www.greyskullanalytics.com)
