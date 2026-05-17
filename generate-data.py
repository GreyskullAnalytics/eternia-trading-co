import calendar
import pandas as pd
import numpy as np
from datetime import date, timedelta
from pathlib import Path
import random
import time
import csv

run_start = time.time()

print("=" * 80)
print("Starting Eternia Trading Co. dataset refresh")
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
fact_sales_path = data_dir / "fact_sales.csv"
targets_path    = data_dir / "fact_salesperson_targets.csv"
readme_path     = Path("README.md")

print(f"[1/7] Data folder ready: {data_dir.resolve()}")

# ----------------------
# ROLLING DATE WINDOW
# ----------------------

today = date.today()
start_date = date(today.year - 2, 1, 1)  # always Jan 1, two years back
end_date = today - timedelta(days=1)     # yesterday — today's data isn't complete yet

print(f"[2/7] Rolling window: {start_date} -> {end_date}")

# ----------------------
# SEASONAL WEIGHTS + DAILY HELPERS
# ----------------------

hero_weights_template = np.array(
    [1.05, 1.00, 1.02, 1.03, 1.04, 1.00, 0.97, 0.96, 1.00, 1.07, 1.14, 1.22], dtype=float
)
evil_weights_template = np.array(
    [0.95, 0.93, 0.96, 0.98, 1.00, 1.01, 1.03, 1.02, 1.05, 1.10, 1.18, 1.28], dtype=float
)

def combined_weight(month):
    h = hero_weights_template[month - 1]
    e = evil_weights_template[month - 1]
    return float(0.55 + 0.25 * h + 0.20 * e)

_all_monthly_weights = [combined_weight(m) for m in range(1, 13)]
_weight_mean = sum(_all_monthly_weights) / 12.0
_daily_base = 250000 / 365.25

def daily_row_count(d):
    w = combined_weight(d.month) / _weight_mean
    yf = year_factors(d.year)["volume"]
    return max(1, int(round(_daily_base * w * yf)))

def heroic_share(month):
    if month in (1, 2, 3, 4, 5):
        return 0.56
    elif month in (6, 7, 8):
        return 0.49
    return 0.53

# ── SALESPERSON TARGETS CONFIG ───────────────────────────────────────────────
# Annual targets per salesperson, derived from expected transaction volume ×
# average net_amount per transaction × 1.10 stretch, with role-based scaling.
# Evil reps carry higher targets: their product portfolio averages ~$303 unit
# cost vs ~$188 heroic, producing larger net_amount per transaction.
# Orko is substantially lower due to his 10–45% discount behaviour.

ANNUAL_TARGETS = {
    1:  17_496_000,  # He-Man       – Champion   (Heroic manager)
    2:  16_524_000,  # Teela        – Captain
    3:  15_876_000,  # Man-At-Arms  – Engineer
    4:  15_228_000,  # Stratos      – Scout
    5:  12_136_000,  # Orko         – Mage       (heavy discounter, lower net revenue)
    6:  23_112_000,  # Skeletor     – Overlord   (Evil manager)
    7:  22_464_000,  # Evil-Lyn     – Sorceress
    8:  22_032_000,  # Trap Jaw     – Enforcer
    9:  19_872_000,  # Beast Man    – Handler
    10: 21_168_000,  # Tri-Klops   – Technician
    11: 20_736_000,  # Webstor      – Infiltrator
    12: 19_440_000,  # Mantenna     – Observer
    13: 16_200_000,  # Buzz-Off     – Commander
    14: 15_876_000,  # Fisto        – Specialist
}


# Year-level performance factors applied on top of seasonal weights.
# volume: multiplier on daily transaction count.
# price:  multiplier on base unit price realisation.
YEAR_FACTORS = {
    2024: {"volume": 0.85, "price": 0.92},  # disrupted year — Skeletor's schemes hit trade routes hard
    2025: {"volume": 1.00, "price": 1.00},  # recovery baseline
    2026: {"volume": 1.15, "price": 1.08},  # expansion — new territories, stronger pricing power
}
def year_factors(year):
    if year in YEAR_FACTORS:
        return YEAR_FACTORS[year]
    # For years beyond the explicitly defined range, generate reproducible factors
    # seeded on the year so each year always gets the same values across runs.
    rng = random.Random(year * 31_337)
    return {
        "volume": round(rng.uniform(0.82, 1.20), 3),
        "price":  round(rng.uniform(0.90, 1.12), 3),
    }


def last_day_of_month(year, month):
    return date(year, month, calendar.monthrange(year, month)[1])


def sp_monthly_target(sp_key, month):
    """Seasonally-adjusted monthly net_amount target, rounded to nearest 10,000."""
    base     = ANNUAL_TARGETS[sp_key] / 12.0
    seasonal = combined_weight(month) / _weight_mean
    return round(base * seasonal / 10_000) * 10_000


# ----------------------
# DIMENSION DATA (in-memory only — dim_ CSVs are static)
# ----------------------

print("[3/7] Loading dimension lookup structures")

_loc_cols  = ["location_key", "city_name", "region", "alignment", "population_size"]
_sp_cols   = ["salesperson_key", "name", "faction", "sales_manager", "role", "specialty", "home_region"]
_cust_cols = ["customer_key", "customer_name", "race", "alignment", "home_region", "loyalty_tier"]
_prod_cols = ["product_key", "product_name", "category", "alignment", "brand_name", "power_level", "unit_cost"]

all_locations = [dict(zip(_loc_cols, r)) for r in [
    (1,  "Eternos",                "Royal Kingdom",   "Heroic",  "Large"),
    (2,  "Royal Palace District",  "Royal Kingdom",   "Heroic",  "Medium"),
    (3,  "Market of Eternos",      "Royal Kingdom",   "Heroic",  "Medium"),
    (4,  "Snake Mountain",         "Dark Hemisphere", "Evil",    "Medium"),
    (5,  "Dark Fortress",          "Dark Hemisphere", "Evil",    "Medium"),
    (6,  "Shadow Valley",          "Dark Hemisphere", "Evil",    "Small"),
    (7,  "Avion",                  "Sky Realm",       "Heroic",  "Small"),
    (8,  "Cloudspire",             "Sky Realm",       "Heroic",  "Small"),
    (9,  "Stratos Peak",           "Sky Realm",       "Heroic",  "Small"),
    (10, "Subternia",              "Underground",     "Evil",    "Medium"),
    (11, "Mole City",              "Underground",     "Neutral", "Small"),
    (12, "Crystal Caverns",        "Underground",     "Neutral", "Small"),
    (13, "Vine Jungle",            "Wilderness",      "Neutral", "Small"),
    (14, "Whispering Woods",       "Wilderness",      "Neutral", "Small"),
    (15, "Beast Plains",           "Wilderness",      "Neutral", "Medium"),
    (16, "Castle Grayskull",       "Mystic Zone",     "Neutral", "Small"),
    (17, "Mystic Mountains",       "Mystic Zone",     "Neutral", "Small"),
    (18, "Ancient Ruins",          "Mystic Zone",     "Neutral", "Small"),
    (19, "Tundaria Outpost",       "Tundaria",        "Neutral", "Small"),
    (20, "Ice Harbor",             "Tundaria",        "Neutral", "Small"),
    (21, "Frozen Watch",           "Tundaria",        "Neutral", "Small"),
    (22, "Pearl Trench",           "Coastal Depths",  "Neutral", "Medium"),
    (23, "Caligar Reef",           "Coastal Depths",  "Heroic",  "Medium"),
    (24, "Sunken Bazaar",          "Coastal Depths",  "Neutral", "Small"),
]]

all_salespeople = [dict(zip(_sp_cols, r)) for r in [
    (1,  "He-Man",    "Heroic", "He-Man",   "Champion",   "Weapons",      "Royal Kingdom"),
    (2,  "Teela",     "Heroic", "He-Man",   "Captain",    "Tactical Gear","Royal Kingdom"),
    (3,  "Man-At-Arms","Heroic","He-Man",   "Engineer",   "Technology",   "Royal Kingdom"),
    (4,  "Stratos",   "Heroic", "He-Man",   "Scout",      "Aerial Gear",  "Sky Realm"),
    (5,  "Orko",      "Heroic", "He-Man",   "Mage",       "Magic",        "Mystic Zone"),
    (6,  "Skeletor",  "Evil",   "Skeletor", "Overlord",   "Dark Magic",   "Dark Hemisphere"),
    (7,  "Evil-Lyn",  "Evil",   "Skeletor", "Sorceress",  "Spells",       "Dark Hemisphere"),
    (8,  "Trap Jaw",  "Evil",   "Skeletor", "Enforcer",   "Weapons",      "Dark Hemisphere"),
    (9,  "Beast Man", "Evil",   "Skeletor", "Handler",    "Creatures",    "Wilderness"),
    (10, "Tri-Klops", "Evil",   "Skeletor", "Technician", "Surveillance", "Dark Hemisphere"),
    (11, "Webstor",   "Evil",   "Skeletor", "Infiltrator","Gadgets",      "Dark Hemisphere"),
    (12, "Mantenna",  "Evil",   "Skeletor", "Observer",   "Recon",        "Dark Hemisphere"),
    (13, "Buzz-Off",  "Heroic", "He-Man",   "Commander",  "Armor",        "Wilderness"),
    (14, "Fisto",     "Heroic", "He-Man",   "Specialist", "Defense",      "Royal Kingdom"),
]]

all_customers = [dict(zip(_cust_cols, r)) for r in [
    (1,  "King Randor",           "Human",    "Heroic",  "Royal Kingdom",   "Gold"),
    (2,  "Royal Guard",           "Human",    "Heroic",  "Royal Kingdom",   "Silver"),
    (3,  "Avion Sky Patrol",      "Avionian", "Heroic",  "Sky Realm",       "Gold"),
    (4,  "Andreenid Hive",        "Andreenid","Neutral", "Wilderness",      "Silver"),
    (5,  "Caligar Council",       "Caligar",  "Heroic",  "Coastal Depths",  "Gold"),
    (6,  "Repton Clan",           "Repton",   "Evil",    "Underground",     "Bronze"),
    (7,  "Trollan Guild",         "Trollan",  "Neutral", "Mystic Zone",     "Silver"),
    (8,  "Dark Warlord",          "Human",    "Evil",    "Dark Hemisphere", "Bronze"),
    (9,  "Beast Collective",      "Beast",    "Neutral", "Wilderness",      "Bronze"),
    (10, "Mole Engineers",        "Molekin",  "Neutral", "Underground",     "Silver"),
    (11, "Mer-Folk Alliance",     "Mer-Folk", "Neutral", "Coastal Depths",  "Silver"),
    (12, "Stone Giant Circle",    "Giant",    "Neutral", "Mystic Zone",     "Bronze"),
    (13, "Northern Rangers",      "Human",    "Heroic",  "Tundaria",        "Silver"),
    (14, "Shadow Syndicate",      "Human",    "Evil",    "Dark Hemisphere", "Bronze"),
    (15, "Skywatch Corps",        "Avionian", "Heroic",  "Sky Realm",       "Gold"),
    (16, "Jungle Cartographers",  "Human",    "Neutral", "Wilderness",      "Silver"),
]]

all_products = [dict(zip(_prod_cols, r)) for r in [
    (1,  "Sword of Protection", "Weapons",    "Heroic", "Grayskull Forge",          "High",   300),
    (2,  "Shield of Eternos",   "Defense",    "Heroic", "Eternos Arms",             "Medium", 150),
    (3,  "Battle Armor",        "Armor",      "Heroic", "Eternos Arms",             "High",   250),
    (4,  "Healing Potion",      "Consumables","Heroic", "Lightspire Healing",       "Low",     20),
    (5,  "Sky Sled",            "Vehicle",    "Heroic", "Avion Aerotech",           "Medium", 400),
    (6,  "Guardian Spear",      "Weapons",    "Heroic", "Grayskull Forge",          "Medium", 180),
    (7,  "Defender Cloak",      "Armor",      "Heroic", "Mystic Guard Co.",         "Medium", 140),
    (8,  "Sunstone Charm",      "Accessories","Heroic", "Lightspire Healing",       "Low",     60),
    (9,  "Doom Blade",          "Weapons",    "Evil",   "ShadowForge",              "High",   280),
    (10, "Mind Control Orb",    "Dark Magic", "Evil",   "Darkspell Collective",     "High",   500),
    (11, "Shadow Beast",        "Creatures",  "Evil",   "Snake Mountain Industries","High",   350),
    (12, "Poison Vial",         "Consumables","Evil",   "Havoc Labs",               "Low",     25),
    (13, "Trap Kit",            "Tools",      "Evil",   "DoomTech",                 "Medium", 120),
    (14, "Chaos Staff",         "Weapons",    "Evil",   "Darkspell Collective",     "High",   320),
    (15, "Soul Drain Amulet",   "Dark Magic", "Evil",   "ShadowForge",              "High",   450),
    (16, "Nightmare Blade",     "Weapons",    "Evil",   "ShadowForge",              "High",   380),
]]

heroic_salespeople   = [r for r in all_salespeople if r["faction"] == "Heroic"]
evil_salespeople     = [r for r in all_salespeople if r["faction"] == "Evil"]
heroic_customers     = [r for r in all_customers   if r["alignment"] == "Heroic"]
evil_customers       = [r for r in all_customers   if r["alignment"] == "Evil"]
neutral_customers    = [r for r in all_customers   if r["alignment"] == "Neutral"]
heroic_products      = [r for r in all_products    if r["alignment"] == "Heroic"]
evil_products        = [r for r in all_products    if r["alignment"] == "Evil"]

_heroic_regions = {"Royal Kingdom", "Sky Realm", "Mystic Zone", "Wilderness", "Tundaria", "Coastal Depths"}
_evil_regions   = {"Dark Hemisphere", "Underground", "Mystic Zone", "Wilderness", "Tundaria", "Coastal Depths"}
heroic_location_pool = [r for r in all_locations if r["region"] in _heroic_regions]
evil_location_pool   = [r for r in all_locations if r["region"] in _evil_regions]

region_lookup = {}
for _loc in all_locations:
    region_lookup.setdefault(_loc["region"], []).append(_loc)

print(f"      {len(all_locations)} locations, {len(all_salespeople)} salespeople, "
      f"{len(all_customers)} customers, {len(all_products)} products")

# ----------------------
# EXISTING FILE STATE
# ----------------------

print("[4/7] Checking existing fact_sales")

sales_id_counter = 0
order_id_counter = 100000
generate_from = start_date
existing_rows = 0

if fact_sales_path.exists():
    df_ex = pd.read_csv(fact_sales_path, parse_dates=["order_date"])
    original_count = len(df_ex)

    df_ex["order_date"] = pd.to_datetime(df_ex["order_date"]).dt.date
    df_ex = df_ex[df_ex["order_date"] >= start_date]
    trimmed = original_count - len(df_ex)

    if trimmed > 0:
        df_ex.to_csv(fact_sales_path, index=False)
        print(f"      Trimmed {trimmed:,} rows older than {start_date}")
    else:
        print(f"      No trim needed")

    if len(df_ex) > 0:
        last_date = df_ex["order_date"].max()
        sales_id_counter = int(df_ex["sales_id"].max())
        order_id_counter = int(df_ex["order_id"].max())
        existing_rows = len(df_ex)
        generate_from = last_date + timedelta(days=1)
        print(f"      Last date in file : {last_date}")
        print(f"      Existing rows     : {existing_rows:,}")
        print(f"      Generating from   : {generate_from}")
    else:
        fact_sales_path.unlink()
        print(f"      File empty after trim — regenerating from {start_date}")
else:
    print(f"      No existing file — generating from {start_date}")

# ----------------------
# GENERATE NEW ROWS
# ----------------------

print("[5/7] Generating new rows")

days_to_generate = []
d = generate_from
while d <= end_date:
    days_to_generate.append(d)
    d += timedelta(days=1)

new_rows = 0

if not days_to_generate:
    print(f"      Already up to date (last date = {end_date})")
else:
    print(f"      Days to generate: {len(days_to_generate):,}  ({days_to_generate[0]} -> {days_to_generate[-1]})")

    file_exists = fact_sales_path.exists()
    with open(fact_sales_path, "a" if file_exists else "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "sales_id", "order_id", "order_date", "location_key",
                "salesperson_key", "customer_key", "product_key",
                "quantity", "unit_price", "discount_amount", "net_amount",
            ])

        for i, day in enumerate(days_to_generate):
            # Seed per-day so each day's rows are reproducible regardless of run timing
            _seed = int(day.strftime("%Y%m%d"))
            random.seed(_seed)
            np.random.seed(_seed)

            hs = heroic_share(day.month)

            # Generate orders; some have multiple lines sharing salesperson/customer/location.
            target_lines = daily_row_count(day)
            lines_today  = 0

            while lines_today < target_lines:
                # 70% single-line, 22% two-line, 8% three-line orders
                n_lines = int(random.choices([1, 2, 3], weights=[70, 22, 8])[0])
                n_lines = min(n_lines, target_lines - lines_today)

                order_id_counter += 1

                # Order-level attributes shared across all lines
                faction = "Heroic" if random.random() < hs else "Evil"

                if faction == "Heroic":
                    sp            = pick_one(heroic_salespeople, all_salespeople, "heroic_salespeople")
                    prod_pool     = heroic_products
                    location_pool = heroic_location_pool
                else:
                    sp            = pick_one(evil_salespeople, all_salespeople, "evil_salespeople")
                    prod_pool     = evil_products
                    location_pool = evil_location_pool

                cust = choose_customer(faction, heroic_customers, evil_customers, neutral_customers, all_customers)
                loc  = choose_location(location_pool, cust["home_region"], all_locations, region_lookup)

                used_product_keys = set()

                for _ in range(n_lines):
                    sales_id_counter += 1

                    # Pick a product not already on this order
                    for _attempt in range(20):
                        if random.random() < 0.12:
                            _candidate = pick_one(all_products, None, "all_products")
                        else:
                            _candidate = pick_one(prod_pool, all_products, "product_pool")
                        if _candidate["product_key"] not in used_product_keys:
                            prod = _candidate
                            break
                    else:
                        _unused = [p for p in all_products if p["product_key"] not in used_product_keys]
                        prod = random.choice(_unused) if _unused else pick_one(prod_pool, all_products, "product_pool")

                    used_product_keys.add(prod["product_key"])

                    qty        = int(random.choices([1, 2, 3, 4, 5, 6], weights=[35, 25, 18, 12, 7, 3])[0])
                    base_price = float(prod["unit_cost"]) * float(random.uniform(1.28, 2.15)) * year_factors(day.year)["price"]

                    if sp["name"] == "Orko":
                        discount = base_price * float(random.uniform(0.10, 0.45))
                    elif prod["alignment"] != sp["faction"]:
                        discount = base_price * float(random.choice([0.05, 0.10, 0.15]))
                    else:
                        discount = base_price * float(random.choices([0, 0.05, 0.10], weights=[62, 25, 13])[0])

                    if day.month in (11, 12) and prod["alignment"] == "Evil":
                        discount *= 0.95
                    if day.month in (1, 2, 3) and prod["alignment"] == "Heroic":
                        discount *= 0.97

                    net = float((base_price - discount) * qty)

                    writer.writerow([
                        sales_id_counter,
                        order_id_counter,
                        day,
                        loc["location_key"],
                        sp["salesperson_key"],
                        cust["customer_key"],
                        prod["product_key"],
                        qty,
                        safe_money(base_price, "base_price"),
                        safe_money(discount, "discount"),
                        safe_money(net, "net"),
                    ])
                    new_rows += 1
                    lines_today += 1

            if (i + 1) % 30 == 0 or i == len(days_to_generate) - 1:
                elapsed = time.time() - run_start
                print(f"      {i+1}/{len(days_to_generate)} days · {new_rows:,} rows · {elapsed:.1f}s")

    print(f"      Done: {new_rows:,} new rows written")

# ----------------------
# SALESPERSON TARGETS
# ----------------------

print("[6/7] Updating salesperson targets")

_tgt_window_start = today.year - 2
_tgt_window_end   = today.year

# Load existing records that are within the rolling year window, preserving values.
_tgt_existing      = {}
_tgt_original_count = 0
if targets_path.exists():
    with open(targets_path, encoding="utf-8") as _tf:
        for _row in csv.DictReader(_tf):
            _tgt_original_count += 1
            if int(_row["date"][:4]) >= _tgt_window_start:
                _tgt_existing[(_row["date"], int(_row["salesperson_key"]))] = _row["monthly_target"]

_tgt_trimmed = _tgt_original_count - len(_tgt_existing)

# Append any month-end dates missing from the window (new year roll-in or forward months).
_tgt_added = 0
for _year in range(_tgt_window_start, _tgt_window_end + 1):
    for _month in range(1, 13):
        _d_str = str(last_day_of_month(_year, _month))
        for _sp_key in sorted(ANNUAL_TARGETS):
            _key = (_d_str, _sp_key)
            if _key not in _tgt_existing:
                _tgt_existing[_key] = sp_monthly_target(_sp_key, _month)
                _tgt_added += 1

with open(targets_path, "w", newline="", encoding="utf-8") as _tf:
    _writer = csv.writer(_tf)
    _writer.writerow(["date", "salesperson_key", "monthly_target"])
    for _key in sorted(_tgt_existing):
        _writer.writerow([_key[0], _key[1], _tgt_existing[_key]])

print(f"      Window    : {_tgt_window_start}-{_tgt_window_end}")
print(f"      Total rows: {len(_tgt_existing):,}  (trimmed {_tgt_trimmed:,}, added {_tgt_added:,})")

# ----------------------
# README
# ----------------------

print("[7/7] Updating README.md")

days_covered  = (end_date - start_date).days + 1
years_covered = days_covered / 365.25

readme_md = f"""<img align="right" width="140" src="assets/eternia-trading-co.png" alt="Eternia Trading Co. logo">

### <p style="font-size:32px">Eternia Trading Co.</p>

*Supplying the bold, the baffled, the noble, and the deeply suspicious all across Eternia.*

## Last refreshed

This data was last refreshed on **{today.strftime("%d %B %Y")}**.

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

- Rolling window start: `{start_date}` (1 January, {today.year - 2})
- Current end date: `{end_date}`
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
- Year-level performance factors that vary transaction volume and pricing year-on-year, creating meaningful differences in annual revenue — 2024 was a disrupted year (lower volume and pricing), 2025 is the recovery baseline, and 2026 reflects an expansion period with stronger volume and pricing power. Future years beyond the explicitly defined range receive automatically generated factors seeded on the year, ensuring consistent but varied performance across the rolling window

## Refresh summary

- Window start         : `{start_date}`
- Window end           : `{end_date}`
- Days covered         : `{days_covered:,}`
- Years covered        : `{years_covered:.2f}`
- Total fact_sales rows              : `{existing_rows + new_rows:,}`
- New fact_sales rows this run       : `{new_rows:,}`
- Total fact_salesperson_target rows : `{len(_tgt_existing):,}`
- New fact_salesperson_target rows   : `{_tgt_added:,}`

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
"""

readme_path.write_text(readme_md, encoding="utf-8")
print(f"      Wrote {readme_path}")

elapsed = time.time() - run_start
print("=" * 80)
print("Refresh complete")
print(f"Total elapsed time: {elapsed:.1f}s")
print("=" * 80)
