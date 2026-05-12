import pandas as pd
import numpy as np
from datetime import date, timedelta
from pathlib import Path
import random
import time
import csv

np.random.seed(42)
random.seed(42)

run_start = time.time()

print("=" * 80)
print("Starting Eternia Trading Co. dataset generation")
print("=" * 80)

# ----------------------
# HELPERS
# ----------------------

def pick_one(seq, fallback_seq=None, label="sequence"):
    if seq:
        return random.choice(seq)
    if fallback_seq:
        return random.choice(fallback_seq)
    raise ValueError(f"Sampling failed: {label} and fallback_seq are both empty.")

def choose_customer(faction, heroic_customers, evil_customers, neutral_customers, all_customers):
    if faction == "Heroic":
        primary = heroic_customers if random.random() < 0.7 else neutral_customers
    else:
        primary = evil_customers if random.random() < 0.7 else neutral_customers
    return pick_one(primary, all_customers, "customer pool")

def choose_location(location_pool, customer_home_region, all_locations, region_lookup):
    region_candidates = region_lookup.get(customer_home_region, [])
    pool_ids = {x["location_key"] for x in location_pool}
    loc_candidates = [x for x in region_candidates if x["location_key"] in pool_ids]

    if loc_candidates:
        return random.choice(loc_candidates)
    if location_pool:
        return random.choice(location_pool)
    if all_locations:
        return random.choice(all_locations)

    raise ValueError("Location selection failed: all location pools are empty.")

def random_date_in_month(start_d, end_d):
    delta = (end_d - start_d).days
    return start_d + timedelta(days=random.randint(0, delta))

def safe_money(value, label="value"):
    try:
        return round(float(value), 2)
    except Exception as e:
        raise ValueError(
            f"Could not convert {label} to rounded float. Value={value}, Type={type(value)}"
        ) from e

# ----------------------
# DATA FOLDER
# ----------------------

data_dir = Path("data")
data_dir.mkdir(parents=True, exist_ok=True)
print(f"[1/9] Data folder ready: {data_dir.resolve()}")

# ----------------------
# DATES / SIZE
# ----------------------

start_date = date(2024, 1, 1)
end_date = date.today()
days_covered = (end_date - start_date).days + 1
years_covered = days_covered / 365.25
target_rows = int(round(years_covered * 250000))

print("[2/9] Date parameters calculated")
print(f"      Start date      : {start_date}")
print(f"      End date        : {end_date}")
print(f"      Days covered    : {days_covered:,}")
print(f"      Years covered   : {years_covered:.2f}")
print(f"      Target fact rows: {target_rows:,}")

months = pd.period_range(start=start_date, end=end_date, freq="M")
month_starts = [p.start_time.date() for p in months]
month_ends = [min(p.end_time.date(), end_date) for p in months]

hero_weights_template = np.array(
    [1.05, 1.00, 1.02, 1.03, 1.04, 1.00, 0.97, 0.96, 1.00, 1.07, 1.14, 1.22],
    dtype=float
)
evil_weights_template = np.array(
    [0.95, 0.93, 0.96, 0.98, 1.00, 1.01, 1.03, 1.02, 1.05, 1.10, 1.18, 1.28],
    dtype=float
)

month_numbers = np.array([p.month for p in months], dtype=int)
hero_weights = np.array([hero_weights_template[m - 1] for m in month_numbers], dtype=float)
evil_weights = np.array([evil_weights_template[m - 1] for m in month_numbers], dtype=float)
base = np.ones(len(months), dtype=float)

month_weights = (0.55 * base + 0.25 * hero_weights + 0.20 * evil_weights)
month_weights = month_weights / month_weights.sum()

month_alloc = np.floor(month_weights * target_rows).astype(int)
remainder = target_rows - month_alloc.sum()

if remainder > 0:
    residuals = month_weights * target_rows - np.floor(month_weights * target_rows)
    order = np.argsort(-residuals)
    for i in range(remainder):
        month_alloc[order[i % len(order)]] += 1

print(f"      Months in scope : {len(months)}")
print(f"      Month alloc len : {len(month_alloc)}")
print(f"      Allocation check: {month_alloc.sum():,} rows assigned")

if len(month_alloc) != len(months):
    raise ValueError(
        f"Month allocation mismatch: len(month_alloc)={len(month_alloc)} vs len(months)={len(months)}"
    )

# ----------------------
# LOCATION DIMENSION
# ----------------------

print("[3/9] Building dim_location")

locations = [
    (1, "Eternos", "Royal Kingdom", "Heroic", "Large"),
    (2, "Royal Palace District", "Royal Kingdom", "Heroic", "Medium"),
    (3, "Market of Eternos", "Royal Kingdom", "Heroic", "Medium"),
    (4, "Snake Mountain", "Dark Hemisphere", "Evil", "Medium"),
    (5, "Dark Fortress", "Dark Hemisphere", "Evil", "Medium"),
    (6, "Shadow Valley", "Dark Hemisphere", "Evil", "Small"),
    (7, "Avion", "Sky Realm", "Heroic", "Small"),
    (8, "Cloudspire", "Sky Realm", "Heroic", "Small"),
    (9, "Stratos Peak", "Sky Realm", "Heroic", "Small"),
    (10, "Subternia", "Underground", "Evil", "Medium"),
    (11, "Mole City", "Underground", "Neutral", "Small"),
    (12, "Crystal Caverns", "Underground", "Neutral", "Small"),
    (13, "Vine Jungle", "Wilderness", "Neutral", "Small"),
    (14, "Whispering Woods", "Wilderness", "Neutral", "Small"),
    (15, "Beast Plains", "Wilderness", "Neutral", "Medium"),
    (16, "Castle Grayskull", "Mystic Zone", "Neutral", "Small"),
    (17, "Mystic Mountains", "Mystic Zone", "Neutral", "Small"),
    (18, "Ancient Ruins", "Mystic Zone", "Neutral", "Small"),
    (19, "Tundaria Outpost", "Tundaria", "Neutral", "Small"),
    (20, "Ice Harbor", "Tundaria", "Neutral", "Small"),
    (21, "Frozen Watch", "Tundaria", "Neutral", "Small"),
    (22, "Pearl Trench", "Coastal Depths", "Neutral", "Medium"),
    (23, "Caligar Reef", "Coastal Depths", "Heroic", "Medium"),
    (24, "Sunken Bazaar", "Coastal Depths", "Neutral", "Small"),
]

dim_location = pd.DataFrame(
    locations,
    columns=["location_key", "city_name", "region", "alignment", "population_size"]
)
print(f"      dim_location rows: {len(dim_location):,}")

# ----------------------
# SALESPERSON DIMENSION
# ----------------------

print("[4/9] Building dim_salesperson")

salespeople = [
    (1, "He-Man", "Heroic", None, "Champion", "Weapons", "Royal Kingdom"),
    (2, "Teela", "Heroic", "He-Man", "Captain", "Tactical Gear", "Royal Kingdom"),
    (3, "Man-At-Arms", "Heroic", "He-Man", "Engineer", "Technology", "Royal Kingdom"),
    (4, "Stratos", "Heroic", "He-Man", "Scout", "Aerial Gear", "Sky Realm"),
    (5, "Orko", "Heroic", "He-Man", "Mage", "Magic", "Mystic Zone"),
    (6, "Skeletor", "Evil", None, "Overlord", "Dark Magic", "Dark Hemisphere"),
    (7, "Evil-Lyn", "Evil", "Skeletor", "Sorceress", "Spells", "Dark Hemisphere"),
    (8, "Trap Jaw", "Evil", "Skeletor", "Enforcer", "Weapons", "Dark Hemisphere"),
    (9, "Beast Man", "Evil", "Skeletor", "Handler", "Creatures", "Wilderness"),
    (10, "Tri-Klops", "Evil", "Skeletor", "Technician", "Surveillance", "Dark Hemisphere"),
    (11, "Webstor", "Evil", "Skeletor", "Infiltrator", "Gadgets", "Dark Hemisphere"),
    (12, "Mantenna", "Evil", "Skeletor", "Observer", "Recon", "Dark Hemisphere"),
    (13, "Buzz-Off", "Heroic", "He-Man", "Commander", "Armor", "Wilderness"),
    (14, "Fisto", "Heroic", "He-Man", "Specialist", "Defense", "Royal Kingdom"),
]

dim_salesperson = pd.DataFrame(
    salespeople,
    columns=["salesperson_key", "name", "faction", "sales_manager", "role", "specialty", "home_region"]
)
print(f"      dim_salesperson rows: {len(dim_salesperson):,}")

# ----------------------
# CUSTOMER DIMENSION
# ----------------------

print("[5/9] Building dim_customer")

customers = [
    (1, "King Randor", "Human", "Heroic", "Royal Kingdom", "Gold"),
    (2, "Royal Guard", "Human", "Heroic", "Royal Kingdom", "Silver"),
    (3, "Avion Sky Patrol", "Avionian", "Heroic", "Sky Realm", "Gold"),
    (4, "Andreenid Hive", "Andreenid", "Neutral", "Wilderness", "Silver"),
    (5, "Caligar Council", "Caligar", "Heroic", "Coastal Depths", "Gold"),
    (6, "Repton Clan", "Repton", "Evil", "Underground", "Bronze"),
    (7, "Trollan Guild", "Trollan", "Neutral", "Mystic Zone", "Silver"),
    (8, "Dark Warlord", "Human", "Evil", "Dark Hemisphere", "Bronze"),
    (9, "Beast Collective", "Beast", "Neutral", "Wilderness", "Bronze"),
    (10, "Mole Engineers", "Molekin", "Neutral", "Underground", "Silver"),
    (11, "Mer-Folk Alliance", "Mer-Folk", "Neutral", "Coastal Depths", "Silver"),
    (12, "Stone Giant Circle", "Giant", "Neutral", "Mystic Zone", "Bronze"),
    (13, "Northern Rangers", "Human", "Heroic", "Tundaria", "Silver"),
    (14, "Shadow Syndicate", "Human", "Evil", "Dark Hemisphere", "Bronze"),
    (15, "Skywatch Corps", "Avionian", "Heroic", "Sky Realm", "Gold"),
    (16, "Jungle Cartographers", "Human", "Neutral", "Wilderness", "Silver"),
]

dim_customer = pd.DataFrame(
    customers,
    columns=["customer_key", "customer_name", "race", "alignment", "home_region", "loyalty_tier"]
)
print(f"      dim_customer rows: {len(dim_customer):,}")

# ----------------------
# PRODUCT DIMENSION
# ----------------------

print("[6/9] Building dim_product")

products = [
    (1, "Sword of Protection", "Weapons", "Heroic", "Grayskull Forge", "High", 300),
    (2, "Shield of Eternos", "Defense", "Heroic", "Eternos Arms", "Medium", 150),
    (3, "Battle Armor", "Armor", "Heroic", "Eternos Arms", "High", 250),
    (4, "Healing Potion", "Consumables", "Heroic", "Lightspire Healing", "Low", 20),
    (5, "Sky Sled", "Vehicle", "Heroic", "Avion Aerotech", "Medium", 400),
    (6, "Guardian Spear", "Weapons", "Heroic", "Grayskull Forge", "Medium", 180),
    (7, "Defender Cloak", "Armor", "Heroic", "Mystic Guard Co.", "Medium", 140),
    (8, "Sunstone Charm", "Accessories", "Heroic", "Lightspire Healing", "Low", 60),
    (9, "Doom Blade", "Weapons", "Evil", "ShadowForge", "High", 280),
    (10, "Mind Control Orb", "Dark Magic", "Evil", "Darkspell Collective", "High", 500),
    (11, "Shadow Beast", "Creatures", "Evil", "Snake Mountain Industries", "High", 350),
    (12, "Poison Vial", "Consumables", "Evil", "Havoc Labs", "Low", 25),
    (13, "Trap Kit", "Tools", "Evil", "DoomTech", "Medium", 120),
    (14, "Chaos Staff", "Weapons", "Evil", "Darkspell Collective", "High", 320),
    (15, "Soul Drain Amulet", "Dark Magic", "Evil", "ShadowForge", "High", 450),
    (16, "Nightmare Blade", "Weapons", "Evil", "ShadowForge", "High", 380),
]

dim_product = pd.DataFrame(
    products,
    columns=["product_key", "product_name", "category", "alignment", "brand_name", "power_level", "unit_cost"]
)
print(f"      dim_product rows: {len(dim_product):,}")

# ----------------------
# VALIDATION + FAST LOOKUPS
# ----------------------

print("[7/9] Building fast lookup structures")

if dim_location.empty or dim_salesperson.empty or dim_customer.empty or dim_product.empty:
    raise ValueError("One or more dimensions are empty. Cannot continue.")

all_locations = dim_location.to_dict("records")
all_salespeople = dim_salesperson.to_dict("records")
all_customers = dim_customer.to_dict("records")
all_products = dim_product.to_dict("records")

heroic_salespeople = [r for r in all_salespeople if r["faction"] == "Heroic"]
evil_salespeople = [r for r in all_salespeople if r["faction"] == "Evil"]

heroic_customers = [r for r in all_customers if r["alignment"] == "Heroic"]
evil_customers = [r for r in all_customers if r["alignment"] == "Evil"]
neutral_customers = [r for r in all_customers if r["alignment"] == "Neutral"]

heroic_products = [r for r in all_products if r["alignment"] == "Heroic"]
evil_products = [r for r in all_products if r["alignment"] == "Evil"]

region_lookup = {}
for loc in all_locations:
    region_lookup.setdefault(loc["region"], []).append(loc)

heroic_regions = {"Royal Kingdom", "Sky Realm", "Mystic Zone", "Wilderness", "Tundaria", "Coastal Depths"}
evil_regions = {"Dark Hemisphere", "Underground", "Mystic Zone", "Wilderness", "Tundaria", "Coastal Depths"}

heroic_location_pool = [r for r in all_locations if r["region"] in heroic_regions]
evil_location_pool = [r for r in all_locations if r["region"] in evil_regions]

print(f"      Heroic salespeople : {len(heroic_salespeople):,}")
print(f"      Evil salespeople   : {len(evil_salespeople):,}")
print(f"      Heroic customers   : {len(heroic_customers):,}")
print(f"      Evil customers     : {len(evil_customers):,}")
print(f"      Neutral customers  : {len(neutral_customers):,}")
print(f"      Heroic products    : {len(heroic_products):,}")
print(f"      Evil products      : {len(evil_products):,}")

# ----------------------
# EXPORT DIMENSIONS
# ----------------------

dim_location_path = data_dir / "dim_location.csv"
dim_salesperson_path = data_dir / "dim_salesperson.csv"
dim_customer_path = data_dir / "dim_customer.csv"
dim_product_path = data_dir / "dim_product.csv"
fact_sales_path = data_dir / "fact_sales.csv"
readme_path = Path("README.md")

print("[8/9] Writing dimension files")

dim_location.to_csv(dim_location_path, index=False)
print(f"      Wrote {dim_location_path}")

dim_salesperson.to_csv(dim_salesperson_path, index=False)
print(f"      Wrote {dim_salesperson_path}")

dim_customer.to_csv(dim_customer_path, index=False)
print(f"      Wrote {dim_customer_path}")

dim_product.to_csv(dim_product_path, index=False)
print(f"      Wrote {dim_product_path}")

# ----------------------
# FACT TABLE
# ----------------------

print("[9/9] Generating and writing fact_sales with csv.writer")
print("      This version avoids pandas sampling inside the row loop for better speed.")

if fact_sales_path.exists():
    fact_sales_path.unlink()
    print(f"      Removed existing {fact_sales_path.name}")

rows_generated = 0
order_id_counter = 100000
sales_id_counter = 1
total_months = len(months)

with open(fact_sales_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "sales_id", "order_id", "order_date", "location_key",
        "salesperson_key", "customer_key", "product_key",
        "quantity", "unit_price", "discount_amount", "net_amount"
    ])

    for i, rows_in_month in enumerate(month_alloc):
        m_start = month_starts[i]
        m_end = month_ends[i]
        month_num = months[i].month
        month_label = months[i].strftime("%Y-%m")
        month_start_time = time.time()

        print(f"      -> Month {i+1}/{total_months}: {month_label}, target rows = {rows_in_month:,}")

        if rows_in_month <= 0:
            print(f"         Skipped {month_label} (0 rows)")
            continue

        heroic_share = 0.56 if month_num in [1, 2, 3, 4, 5] else 0.49 if month_num in [6, 7, 8] else 0.53

        for row_num in range(rows_in_month):
            order_id_counter += 1
            faction = "Heroic" if random.random() < heroic_share else "Evil"

            if faction == "Heroic":
                sp = pick_one(heroic_salespeople, all_salespeople, "heroic_salespeople")
                prod_pool = heroic_products
                location_pool = heroic_location_pool
            else:
                sp = pick_one(evil_salespeople, all_salespeople, "evil_salespeople")
                prod_pool = evil_products
                location_pool = evil_location_pool

            if random.random() < 0.12:
                prod = pick_one(all_products, None, "all_products")
            else:
                prod = pick_one(prod_pool, all_products, "product_pool")

            cust = choose_customer(
                faction,
                heroic_customers,
                evil_customers,
                neutral_customers,
                all_customers
            )

            loc = choose_location(location_pool, cust["home_region"], all_locations, region_lookup)

            qty = int(random.choices([1, 2, 3, 4, 5, 6], weights=[35, 25, 18, 12, 7, 3])[0])
            base_price = float(prod["unit_cost"]) * float(random.uniform(1.28, 2.15))

            if sp["name"] == "Orko":
                discount = base_price * float(random.uniform(0.10, 0.45))
            elif prod["alignment"] != sp["faction"]:
                discount = base_price * float(random.choice([0.05, 0.10, 0.15]))
            else:
                discount = base_price * float(random.choices([0, 0.05, 0.10], weights=[62, 25, 13])[0])

            if month_num in [11, 12] and prod["alignment"] == "Evil":
                discount *= 0.95
            if month_num in [1, 2, 3] and prod["alignment"] == "Heroic":
                discount *= 0.97

            discount = float(discount)
            net = float((base_price - discount) * qty)

            try:
                unit_price_out = safe_money(base_price, "base_price")
                discount_out = safe_money(discount, "discount")
                net_out = safe_money(net, "net")
            except Exception as e:
                print("DEBUG FAILURE")
                print("base_price:", base_price, type(base_price))
                print("discount:", discount, type(discount))
                print("net:", net, type(net))
                print("prod:", prod)
                print("sp:", sp)
                print("cust:", cust)
                raise e

            writer.writerow([
                sales_id_counter,
                order_id_counter,
                random_date_in_month(m_start, m_end),
                loc["location_key"],
                sp["salesperson_key"],
                cust["customer_key"],
                prod["product_key"],
                qty,
                unit_price_out,
                discount_out,
                net_out
            ])

            sales_id_counter += 1
            rows_generated += 1

            if (row_num + 1) % 50000 == 0:
                print(f"         ...{row_num + 1:,} rows written for {month_label}")

        month_elapsed = time.time() - month_start_time
        total_elapsed = time.time() - run_start
        print(
            f"         Completed {month_label}: cumulative rows = {rows_generated:,}, "
            f"month time = {month_elapsed:.1f}s, total time = {total_elapsed:.1f}s"
        )

# ----------------------
# README
# ----------------------

readme_md = f"""<img align="right" width="140" src="assets/eternia-trading-co.png" alt="Eternia Trading Co. logo">

# Eternia Trading Co.

*Supplying the bold, the baffled, the noble, and the deeply suspicious all across Eternia.*

## About the company

Eternia Trading Co. is one of the most recognisable commercial houses in all Eternia, with trading routes, supplier networks, and customer relationships stretching from the Royal Kingdom to the Dark Hemisphere and well beyond. The company deals in a broad portfolio of high-demand goods including weapons, armour, mystical accessories, transport, consumables, field equipment, and other specialist items required by Eternia’s more adventurous populations.

Known for its ambitious regional reach and flair for dramatic merchandising, ETC has built its reputation on being able to put the right product in the right hands at the right moment — whether that means resupplying a palace guard, outfitting a sky patrol, restocking an underground engineering crew, or discreetly fulfilling a rather ominous bulk order from somewhere with too many skull-shaped doors. Its public image is polished, its distribution network is formidable, and its appetite for expansion is, by most accounts, enormous.

## Leadership drama

At the heart of the business are its two formidable sales managers: **He-Man** for the heroic side of the ledger, and **Skeletor** for the more aggressively sinister accounts. Both insist they are carrying the company, both are obsessed with winning the monthly numbers race, and both treat the sales leaderboard as if the fate of Eternia depends on it.

Their rivalry is the engine that keeps the whole enterprise moving. A strong quarter in the Royal Kingdom will be met by a suspiciously intense push in the Dark Hemisphere; a surge in heroic armour sales will somehow be answered by an urgent campaign for cursed blades, shadow beasts, and morally questionable accessories. The result is a company culture powered by competitive energy, theatrical self-belief, and the constant sense that someone is about to storm into a meeting and demand a revised forecast.

## What Eternia Trading Co. actually “does”

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
- `data/fact_sales.csv`

## Schema

### fact_sales
Grain: one row per sales transaction line.

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

- Fixed start date: `2024-01-01`
- Dynamic end date: the day the script is run
- Target fact volume: approximately **250,000 rows per calendar year covered**

## Distribution logic

The fact table is generated with:
- Seasonal monthly weighting repeated across all months in scope
- A mild heroic bias in earlier parts of the year
- Stronger evil presence in later months
- Region-aware location selection
- Mostly alignment-matching product sales, with occasional cross-alignment exceptions
- Higher discount variability for Orko

## Performance notes

This version uses lightweight Python structures and `csv.writer` for faster fact generation and output.

## Reliability notes

This version explicitly converts money values to native Python floats before rounding and writing, and validates that month allocation matches the full month range.

## Generation summary

- Start date: `{start_date}`
- End date: `{end_date}`
- Days covered: `{days_covered:,}`
- Years covered: `{years_covered:.2f}`
- Months in scope: `{len(months):,}`
- Target fact rows: `{target_rows:,}`
- Actual fact rows written: `{rows_generated:,}`
"""

readme_path.write_text(readme_md, encoding="utf-8")
print(f"      Wrote {readme_path}")

elapsed = time.time() - run_start
print("=" * 80)
print("Dataset generation finished successfully")
print(f"Total elapsed time: {elapsed:.1f} seconds")
print(f"Data folder: {data_dir.resolve()}")
print(f"README: {readme_path.resolve()}")
print("=" * 80)