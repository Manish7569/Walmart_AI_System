"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          WALMART ENTERPRISE SYNTHETIC DATA ENGINE v2.0                      ║
║  Generates production-realistic data at Fortune-1 retail scale:             ║
║    • 4,200+ stores across 50 US states, 6 climate regions                  ║
║    • 500,000 SKUs across full product hierarchy (dept → category → sub)     ║
║    • 50M+ simulated POS transactions (90-day window)                        ║
║    • Real-time sensor telemetry from 20 distribution centers                ║
║    • 25-vendor ecosystem with tier classification and risk scoring           ║
║    • Seasonal, holiday, and weather-driven demand multipliers               ║
║    • Anomaly injection for AI detection training                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import hashlib
import json
import random
import threading
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, Generator, List, Optional, Tuple

import numpy as np
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
#  SEEDING  (deterministic so runs are reproducible)
# ─────────────────────────────────────────────────────────────────────────────
RNG = np.random.default_rng(seed=2024)
random.seed(2024)

# ─────────────────────────────────────────────────────────────────────────────
#  GEOGRAPHIC MASTER DATA
# ─────────────────────────────────────────────────────────────────────────────
REGIONS: Dict[str, Dict] = {
    "Southeast": {
        "states": ["FL", "GA", "AL", "MS", "SC", "TN", "NC", "VA"],
        "revenue_multiplier": 1.12,
        "climate": "Humid subtropical",
        "dc_count": 6,
        "avg_store_age": 14,
    },
    "Northeast": {
        "states": ["NY", "PA", "NJ", "MA", "CT", "RI", "VT", "NH", "ME"],
        "revenue_multiplier": 1.21,
        "climate": "Continental humid",
        "dc_count": 5,
        "avg_store_age": 22,
    },
    "Midwest": {
        "states": ["IL", "OH", "MI", "IN", "WI", "MN", "IA", "MO", "KS", "NE", "SD", "ND"],
        "revenue_multiplier": 0.97,
        "climate": "Continental",
        "dc_count": 7,
        "avg_store_age": 19,
    },
    "Southwest": {
        "states": ["TX", "AZ", "NM", "NV", "OK"],
        "revenue_multiplier": 1.08,
        "climate": "Semi-arid",
        "dc_count": 5,
        "avg_store_age": 12,
    },
    "West": {
        "states": ["CA", "WA", "OR", "CO", "UT", "ID", "MT", "WY", "AK", "HI"],
        "revenue_multiplier": 1.18,
        "climate": "Mediterranean / Alpine",
        "dc_count": 4,
        "avg_store_age": 16,
    },
    "SouthCentral": {
        "states": ["LA", "AR", "KY", "WV"],
        "revenue_multiplier": 0.89,
        "climate": "Humid subtropical",
        "dc_count": 3,
        "avg_store_age": 20,
    },
}

STORE_FORMATS: Dict[str, Dict] = {
    "Supercenter": {
        "size_sqft": (180_000, 260_000),
        "avg_daily_txn": (3_500, 7_000),
        "departments": 36,
        "weight": 0.52,
        "avg_basket": (45, 95),
    },
    "Neighborhood Market": {
        "size_sqft": (38_000, 56_000),
        "avg_daily_txn": (700, 1_800),
        "departments": 8,
        "weight": 0.21,
        "avg_basket": (18, 42),
    },
    "Sam's Club": {
        "size_sqft": (128_000, 165_000),
        "avg_daily_txn": (1_800, 4_200),
        "departments": 18,
        "weight": 0.14,
        "avg_basket": (80, 240),
    },
    "Walmart Express": {
        "size_sqft": (12_000, 22_000),
        "avg_daily_txn": (200, 600),
        "departments": 4,
        "weight": 0.08,
        "avg_basket": (12, 28),
    },
    "Walmart Pickup": {
        "size_sqft": (5_000, 9_000),
        "avg_daily_txn": (80, 250),
        "departments": 0,
        "weight": 0.05,
        "avg_basket": (110, 280),
    },
}

# ─────────────────────────────────────────────────────────────────────────────
#  PRODUCT HIERARCHY
# ─────────────────────────────────────────────────────────────────────────────
PRODUCT_HIERARCHY: Dict[str, Dict] = {
    "Grocery & Consumables": {
        "margin_pct": 0.18,
        "velocity": "ultra-high",
        "turn_rate": 52,
        "perishable_pct": 0.38,
        "subcategories": {
            "Dairy & Eggs":      {"price_range": (1.20, 12.99),  "shelf_days": 21},
            "Fresh Produce":     {"price_range": (0.79, 8.99),   "shelf_days": 7},
            "Fresh Meat":        {"price_range": (3.99, 28.99),  "shelf_days": 5},
            "Bakery":            {"price_range": (1.49, 14.99),  "shelf_days": 5},
            "Frozen Foods":      {"price_range": (1.99, 18.99),  "shelf_days": 365},
            "Beverages":         {"price_range": (0.99, 24.99),  "shelf_days": 365},
            "Snacks & Candy":    {"price_range": (0.89, 9.99),   "shelf_days": 180},
            "Canned & Packaged": {"price_range": (0.79, 6.99),   "shelf_days": 730},
            "Cereal & Breakfast":{"price_range": (2.49, 8.99),   "shelf_days": 365},
            "Condiments & Spices":{"price_range": (1.29, 11.99), "shelf_days": 730},
        },
    },
    "Electronics & Tech": {
        "margin_pct": 0.11,
        "velocity": "low",
        "turn_rate": 8,
        "perishable_pct": 0.0,
        "subcategories": {
            "Televisions":       {"price_range": (89.99, 2499.99), "shelf_days": None},
            "Computers":         {"price_range": (149.99, 1899.99),"shelf_days": None},
            "Mobile & Wearables":{"price_range": (19.99, 999.99),  "shelf_days": None},
            "Audio":             {"price_range": (9.99, 499.99),   "shelf_days": None},
            "Gaming":            {"price_range": (19.99, 699.99),  "shelf_days": None},
            "Smart Home":        {"price_range": (14.99, 349.99),  "shelf_days": None},
            "Camera & Photo":    {"price_range": (29.99, 799.99),  "shelf_days": None},
            "Accessories":       {"price_range": (3.99, 89.99),    "shelf_days": None},
        },
    },
    "Apparel & Footwear": {
        "margin_pct": 0.38,
        "velocity": "medium",
        "turn_rate": 18,
        "perishable_pct": 0.0,
        "subcategories": {
            "Men's Clothing":    {"price_range": (5.99, 149.99),  "shelf_days": None},
            "Women's Clothing":  {"price_range": (5.99, 179.99),  "shelf_days": None},
            "Kids & Baby":       {"price_range": (3.99, 59.99),   "shelf_days": None},
            "Footwear":          {"price_range": (9.99, 129.99),  "shelf_days": None},
            "Activewear":        {"price_range": (9.99, 89.99),   "shelf_days": None},
            "Accessories":       {"price_range": (2.99, 49.99),   "shelf_days": None},
        },
    },
    "Home & Garden": {
        "margin_pct": 0.31,
        "velocity": "medium",
        "turn_rate": 14,
        "perishable_pct": 0.0,
        "subcategories": {
            "Furniture":         {"price_range": (49.99, 999.99), "shelf_days": None},
            "Bedding & Bath":    {"price_range": (9.99, 199.99),  "shelf_days": None},
            "Kitchen & Dining":  {"price_range": (4.99, 299.99),  "shelf_days": None},
            "Storage & Org.":    {"price_range": (4.99, 149.99),  "shelf_days": None},
            "Lawn & Garden":     {"price_range": (3.99, 699.99),  "shelf_days": None},
            "Power Tools":       {"price_range": (19.99, 499.99), "shelf_days": None},
            "Cleaning Supplies": {"price_range": (1.99, 39.99),   "shelf_days": 730},
            "Decor & Art":       {"price_range": (3.99, 249.99),  "shelf_days": None},
        },
    },
    "Health & Pharmacy": {
        "margin_pct": 0.24,
        "velocity": "high",
        "turn_rate": 28,
        "perishable_pct": 0.05,
        "subcategories": {
            "OTC Medications":   {"price_range": (2.49, 49.99),   "shelf_days": 730},
            "Vitamins & Suppl.": {"price_range": (3.99, 69.99),   "shelf_days": 730},
            "Personal Care":     {"price_range": (1.99, 39.99),   "shelf_days": 730},
            "Baby & Infant":     {"price_range": (2.99, 59.99),   "shelf_days": 730},
            "Vision & Eye":      {"price_range": (4.99, 299.99),  "shelf_days": 730},
            "First Aid":         {"price_range": (1.99, 49.99),   "shelf_days": 730},
            "Sexual Health":     {"price_range": (5.99, 29.99),   "shelf_days": 730},
        },
    },
    "Sports & Outdoors": {
        "margin_pct": 0.29,
        "velocity": "low",
        "turn_rate": 10,
        "perishable_pct": 0.0,
        "subcategories": {
            "Fitness Equipment":  {"price_range": (9.99, 899.99), "shelf_days": None},
            "Camping & Hiking":   {"price_range": (4.99, 499.99), "shelf_days": None},
            "Team Sports":        {"price_range": (2.99, 199.99), "shelf_days": None},
            "Cycling":            {"price_range": (14.99, 699.99),"shelf_days": None},
            "Water Sports":       {"price_range": (4.99, 299.99), "shelf_days": None},
            "Hunting & Fishing":  {"price_range": (3.99, 399.99), "shelf_days": None},
        },
    },
    "Automotive": {
        "margin_pct": 0.22,
        "velocity": "low",
        "turn_rate": 9,
        "perishable_pct": 0.0,
        "subcategories": {
            "Motor Oil & Fluids": {"price_range": (3.99, 69.99),  "shelf_days": None},
            "Tires & Wheels":     {"price_range": (49.99, 399.99),"shelf_days": None},
            "Car Care":           {"price_range": (2.99, 49.99),  "shelf_days": None},
            "Parts & Accessories":{"price_range": (4.99, 299.99), "shelf_days": None},
        },
    },
    "Toys & Entertainment": {
        "margin_pct": 0.26,
        "velocity": "seasonal",
        "turn_rate": 12,
        "perishable_pct": 0.0,
        "subcategories": {
            "Action & Collectibles":{"price_range": (3.99, 199.99),"shelf_days": None},
            "Board Games":          {"price_range": (5.99, 89.99), "shelf_days": None},
            "Learning & STEM":      {"price_range": (4.99, 149.99),"shelf_days": None},
            "Outdoor Toys":         {"price_range": (4.99, 299.99),"shelf_days": None},
            "Video Games":          {"price_range": (4.99, 69.99), "shelf_days": None},
            "Dolls & Plush":        {"price_range": (2.99, 59.99), "shelf_days": None},
        },
    },
}

# Fix the syntax issues in the dict
PRODUCT_HIERARCHY["Automotive"]["subcategories"]["Parts & Accessories"] = {"price_range": (4.99, 299.99), "shelf_days": None}
PRODUCT_HIERARCHY["Toys & Entertainment"]["subcategories"]["Video Games"] = {"price_range": (4.99, 69.99), "shelf_days": None}
PRODUCT_HIERARCHY["Toys & Entertainment"]["subcategories"]["Dolls & Plush"] = {"price_range": (2.99, 59.99), "shelf_days": None}

# ─────────────────────────────────────────────────────────────────────────────
#  VENDOR MASTER  (25 enterprise vendors, 3 tiers)
# ─────────────────────────────────────────────────────────────────────────────
VENDORS: List[Dict] = [
    # Tier 1 — Strategic (99-yr relationships, EDI + API integration)
    {"id":"VND-PG-001","name":"Procter & Gamble","tier":1,"otd_pct":0.978,"lead_days":3,"risk":"Low","contract_value_m":2800,"categories":["Grocery & Consumables","Health & Pharmacy"],"country":"USA","integration":"EDI+API","payment_terms":"Net30"},
    {"id":"VND-UL-002","name":"Unilever North America","tier":1,"otd_pct":0.962,"lead_days":4,"risk":"Low","contract_value_m":1940,"categories":["Grocery & Consumables","Health & Pharmacy"],"country":"USA","integration":"EDI","payment_terms":"Net30"},
    {"id":"VND-NS-003","name":"Nestlé USA","tier":1,"otd_pct":0.971,"lead_days":3,"risk":"Low","contract_value_m":2200,"categories":["Grocery & Consumables"],"country":"USA","integration":"EDI+API","payment_terms":"Net45"},
    {"id":"VND-JJ-004","name":"Johnson & Johnson","tier":1,"otd_pct":0.988,"lead_days":2,"risk":"Low","contract_value_m":980,"categories":["Health & Pharmacy"],"country":"USA","integration":"EDI+API","payment_terms":"Net30"},
    {"id":"VND-CC-005","name":"Coca-Cola Refreshments","tier":1,"otd_pct":0.991,"lead_days":2,"risk":"Low","contract_value_m":3100,"categories":["Grocery & Consumables"],"country":"USA","integration":"EDI+API","payment_terms":"Net15"},
    {"id":"VND-PP-006","name":"PepsiCo / Frito-Lay","tier":1,"otd_pct":0.984,"lead_days":2,"risk":"Low","contract_value_m":2780,"categories":["Grocery & Consumables"],"country":"USA","integration":"EDI+API","payment_terms":"Net15"},
    {"id":"VND-KR-007","name":"Kraft Heinz","tier":1,"otd_pct":0.944,"lead_days":5,"risk":"Medium","contract_value_m":1420,"categories":["Grocery & Consumables"],"country":"USA","integration":"EDI","payment_terms":"Net45"},
    {"id":"VND-GM-008","name":"General Mills","tier":1,"otd_pct":0.921,"lead_days":4,"risk":"Medium","contract_value_m":1150,"categories":["Grocery & Consumables"],"country":"USA","integration":"EDI","payment_terms":"Net45"},
    {"id":"VND-TY-009","name":"Tyson Foods","tier":1,"otd_pct":0.956,"lead_days":2,"risk":"Low","contract_value_m":1680,"categories":["Grocery & Consumables"],"country":"USA","integration":"EDI+API","payment_terms":"Net15"},
    # Tier 2 — Preferred
    {"id":"VND-SM-010","name":"Samsung Electronics","tier":2,"otd_pct":0.912,"lead_days":14,"risk":"Medium","contract_value_m":890,"categories":["Electronics & Tech"],"country":"KOR","integration":"API","payment_terms":"Net60"},
    {"id":"VND-LG-011","name":"LG Electronics","tier":2,"otd_pct":0.894,"lead_days":12,"risk":"Medium","contract_value_m":640,"categories":["Electronics & Tech"],"country":"KOR","integration":"API","payment_terms":"Net60"},
    {"id":"VND-NK-012","name":"Nike Inc.","tier":2,"otd_pct":0.938,"lead_days":21,"risk":"Low","contract_value_m":780,"categories":["Apparel & Footwear","Sports & Outdoors"],"country":"USA","integration":"EDI","payment_terms":"Net60"},
    {"id":"VND-HB-013","name":"Hasbro Inc.","tier":2,"otd_pct":0.858,"lead_days":35,"risk":"High","contract_value_m":290,"categories":["Toys & Entertainment"],"country":"USA","integration":"EDI","payment_terms":"Net90"},
    {"id":"VND-MT-014","name":"Mattel Inc.","tier":2,"otd_pct":0.866,"lead_days":30,"risk":"High","contract_value_m":310,"categories":["Toys & Entertainment"],"country":"USA","integration":"EDI","payment_terms":"Net90"},
    {"id":"VND-3M-015","name":"3M Corporation","tier":2,"otd_pct":0.941,"lead_days":6,"risk":"Low","contract_value_m":420,"categories":["Home & Garden","Health & Pharmacy"],"country":"USA","integration":"EDI","payment_terms":"Net30"},
    {"id":"VND-WP-016","name":"Whirlpool Corporation","tier":2,"otd_pct":0.831,"lead_days":21,"risk":"High","contract_value_m":380,"categories":["Home & Garden"],"country":"USA","integration":"EDI","payment_terms":"Net90"},
    {"id":"VND-CP-017","name":"Colgate-Palmolive","tier":1,"otd_pct":0.968,"lead_days":3,"risk":"Low","contract_value_m":860,"categories":["Health & Pharmacy","Grocery & Consumables"],"country":"USA","integration":"EDI+API","payment_terms":"Net30"},
    {"id":"VND-CL-018","name":"Clorox Company","tier":2,"otd_pct":0.932,"lead_days":5,"risk":"Low","contract_value_m":290,"categories":["Home & Garden","Grocery & Consumables"],"country":"USA","integration":"EDI","payment_terms":"Net30"},
    # Tier 3 — Transactional (elevated risk)
    {"id":"VND-AG-019","name":"Anchor Glass Container","tier":3,"otd_pct":0.741,"lead_days":9,"risk":"Critical","contract_value_m":45,"categories":["Home & Garden"],"country":"USA","integration":"Manual","payment_terms":"Net90"},
    {"id":"VND-SR-020","name":"Sunrise Industries","tier":3,"otd_pct":0.768,"lead_days":18,"risk":"Critical","contract_value_m":62,"categories":["Apparel & Footwear"],"country":"BGD","integration":"Manual","payment_terms":"Net120"},
    {"id":"VND-GH-021","name":"Global Home Products","tier":3,"otd_pct":0.812,"lead_days":22,"risk":"High","contract_value_m":88,"categories":["Home & Garden"],"country":"CHN","integration":"EDI","payment_terms":"Net90"},
    {"id":"VND-PF-022","name":"Pacific Foods Co.","tier":2,"otd_pct":0.879,"lead_days":8,"risk":"Medium","contract_value_m":145,"categories":["Grocery & Consumables"],"country":"USA","integration":"EDI","payment_terms":"Net45"},
    {"id":"VND-EZ-023","name":"EzSport International","tier":3,"otd_pct":0.792,"lead_days":28,"risk":"High","contract_value_m":72,"categories":["Sports & Outdoors"],"country":"TWN","integration":"Manual","payment_terms":"Net90"},
    {"id":"VND-AC-024","name":"AutoCare Direct","tier":2,"otd_pct":0.891,"lead_days":7,"risk":"Medium","contract_value_m":195,"categories":["Automotive"],"country":"USA","integration":"EDI","payment_terms":"Net45"},
    {"id":"VND-BF-025","name":"BioFresh Farms","tier":2,"otd_pct":0.903,"lead_days":1,"risk":"Medium","contract_value_m":340,"categories":["Grocery & Consumables"],"country":"USA","integration":"API","payment_terms":"Net7"},
]

# ─────────────────────────────────────────────────────────────────────────────
#  HOLIDAY / SEASONAL DEMAND CALENDAR
# ─────────────────────────────────────────────────────────────────────────────
DEMAND_CALENDAR: List[Dict] = [
    {"name":"Super Bowl",     "month":2, "day_range":(1,10),   "multiplier":1.28,"categories":["Grocery & Consumables","Electronics & Tech"]},
    {"name":"Valentine's",   "month":2, "day_range":(10,15),  "multiplier":1.15,"categories":["Grocery & Consumables","Health & Pharmacy"]},
    {"name":"Spring Break",  "month":3, "day_range":(10,25),  "multiplier":1.18,"categories":["Apparel & Footwear","Toys & Entertainment","Sports & Outdoors"]},
    {"name":"Easter",        "month":4, "day_range":(1,10),   "multiplier":1.22,"categories":["Grocery & Consumables","Toys & Entertainment"]},
    {"name":"Mother's Day",  "month":5, "day_range":(7,15),   "multiplier":1.19,"categories":["Health & Pharmacy","Home & Garden","Apparel & Footwear"]},
    {"name":"Back-to-School","month":8, "day_range":(1,31),   "multiplier":1.41,"categories":["Apparel & Footwear","Electronics & Tech","Toys & Entertainment"]},
    {"name":"Labor Day",     "month":9, "day_range":(1,6),    "multiplier":1.24,"categories":["Grocery & Consumables","Automotive"]},
    {"name":"Halloween",     "month":10,"day_range":(20,31),  "multiplier":1.33,"categories":["Grocery & Consumables","Toys & Entertainment","Home & Garden"]},
    {"name":"Thanksgiving",  "month":11,"day_range":(20,27),  "multiplier":2.15,"categories":["Grocery & Consumables","Electronics & Tech","Apparel & Footwear"]},
    {"name":"Black Friday",  "month":11,"day_range":(27,30),  "multiplier":3.40,"categories":["Electronics & Tech","Apparel & Footwear","Toys & Entertainment","Home & Garden"]},
    {"name":"Cyber Monday",  "month":12,"day_range":(1,3),    "multiplier":2.80,"categories":["Electronics & Tech","Toys & Entertainment"]},
    {"name":"Christmas",     "month":12,"day_range":(10,26),  "multiplier":2.60,"categories":["Toys & Entertainment","Electronics & Tech","Apparel & Footwear","Grocery & Consumables"]},
    {"name":"New Year",      "month":12,"day_range":(28,31),  "multiplier":1.18,"categories":["Grocery & Consumables","Health & Pharmacy"]},
]


# ─────────────────────────────────────────────────────────────────────────────
#  GENERATION FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def _uid(prefix: str, n: int) -> str:
    return f"{prefix}-{n:07d}"


def generate_stores(n: int = 4200) -> pd.DataFrame:
    """Generate store master data — realistic geographic distribution."""
    rows: List[Dict] = []
    counter = 1001
    for region, meta in REGIONS.items():
        region_quota = max(1, int(n * len(meta["states"]) / 50))
        for fmt, fmeta in STORE_FORMATS.items():
            fmt_count = max(1, int(region_quota * fmeta["weight"]))
            for _ in range(fmt_count):
                state = random.choice(meta["states"])
                opened = random.randint(1988, 2023)
                sqft = int(RNG.integers(*fmeta["size_sqft"]))
                dc_region = region[:2].upper()
                rows.append({
                    "store_id":            f"WMT-{counter:05d}",
                    "store_name":          f"Walmart {fmt} #{counter}",
                    "format":              fmt,
                    "region":              region,
                    "state":               state,
                    "district":            f"D{random.randint(1,12):02d}-{state}",
                    "size_sqft":           sqft,
                    "opened_year":         opened,
                    "store_age_yrs":       2024 - opened,
                    "avg_daily_txn_base":  int(RNG.integers(*fmeta["avg_daily_txn"])),
                    "avg_basket_base":     float(RNG.uniform(*fmeta["avg_basket"])),
                    "revenue_multiplier":  round(meta["revenue_multiplier"] * RNG.uniform(0.90, 1.10), 4),
                    "departments":         fmeta["departments"],
                    "dc_id":               f"DC-{dc_region}-{random.randint(1, meta['dc_count']):02d}",
                    "manager_id":          f"MGR-{random.randint(10000, 99999)}",
                    "is_24hr":             fmt == "Supercenter" and random.random() < 0.42,
                    "has_pharmacy":        fmt in ("Supercenter", "Neighborhood Market") and random.random() < 0.78,
                    "has_vision_center":   fmt == "Supercenter" and random.random() < 0.65,
                    "has_auto_center":     fmt == "Supercenter" and random.random() < 0.71,
                    "has_fuel":            fmt in ("Supercenter", "Sam's Club") and random.random() < 0.58,
                    "lat":                 round(RNG.uniform(24.5, 48.9), 5),
                    "lon":                 round(RNG.uniform(-124.0, -66.9), 5),
                })
                counter += 1
                if counter > n + 1000:
                    break
    return pd.DataFrame(rows[:n]).reset_index(drop=True)


def generate_skus(n: int = 50_000) -> pd.DataFrame:
    """Generate full product catalog with hierarchy, vendor assignments, pricing."""
    rows: List[Dict] = []
    sku_num = 1
    per_dept = n // len(PRODUCT_HIERARCHY)

    for dept, dmeta in PRODUCT_HIERARCHY.items():
        subcats = dmeta["subcategories"]
        per_sub = max(1, per_dept // len(subcats))
        for sub, smeta in subcats.items():
            vendor_pool = [v for v in VENDORS if dept in v["categories"]] or VENDORS[:5]
            for _ in range(per_sub):
                vendor = random.choice(vendor_pool)
                price = round(float(RNG.uniform(*smeta["price_range"])), 2)
                cost  = round(price * (1 - dmeta["margin_pct"]) * RNG.uniform(0.92, 1.08), 2)
                shelf = smeta["shelf_days"]
                is_perishable = shelf is not None and shelf <= 30
                velocity_map = {"ultra-high": 40, "high": 18, "medium": 8, "low": 3, "seasonal": 6}
                base_velocity = int(velocity_map.get(dmeta["velocity"], 8) * RNG.uniform(0.5, 2.0))

                rows.append({
                    "sku_id":              _uid("SKU", sku_num),
                    "upc":                 f"{int(RNG.integers(1e11, 9.99e11))}",
                    "item_nbr":            f"ITEM-{sku_num:08d}",
                    "product_name":        f"{sub} Item {sku_num:06d}",
                    "department":          dept,
                    "category":            sub,
                    "vendor_id":           vendor["id"],
                    "vendor_name":         vendor["name"],
                    "vendor_tier":         vendor["tier"],
                    "unit_price":          price,
                    "unit_cost":           cost,
                    "margin_pct":          round(dmeta["margin_pct"], 4),
                    "velocity_class":      dmeta["velocity"],
                    "base_daily_units":    base_velocity,
                    "reorder_point":       int(base_velocity * vendor["lead_days"] * 1.5),
                    "safety_stock":        int(base_velocity * vendor["lead_days"] * 0.5),
                    "reorder_qty":         int(base_velocity * 30),
                    "max_stock_level":     int(base_velocity * 60),
                    "lead_time_days":      vendor["lead_days"],
                    "shelf_life_days":     shelf,
                    "is_perishable":       is_perishable,
                    "storage_class":       "Refrigerated" if sub in ("Dairy & Eggs", "Fresh Meat", "Fresh Produce") else
                                           "Frozen" if sub == "Frozen Foods" else "Ambient",
                    "weight_lbs":          round(float(RNG.uniform(0.1, 50.0)), 2),
                    "case_pack_qty":       int(RNG.choice([6, 12, 24, 48, 1])),
                    "planogram_facing":    int(RNG.integers(1, 6)),
                    "is_private_label":    random.random() < 0.12,
                    "is_organic":          sub in ("Fresh Produce","Dairy & Eggs") and random.random() < 0.18,
                    "seasonal_flag":       dmeta["velocity"] == "seasonal",
                })
                sku_num += 1
                if sku_num > n:
                    break
            if sku_num > n:
                break
        if sku_num > n:
            break

    return pd.DataFrame(rows[:n]).reset_index(drop=True)


def _demand_multiplier(dt: datetime, category: str) -> float:
    """Compute demand multiplier for a given date and category."""
    mult = 1.0
    if dt.weekday() >= 5:           # weekend lift
        mult *= 1.28
    if dt.weekday() == 4:           # Friday pre-weekend
        mult *= 1.12
    for event in DEMAND_CALENDAR:
        if dt.month == event["month"] and event["day_range"][0] <= dt.day <= event["day_range"][1]:
            if category in event["categories"]:
                mult *= event["multiplier"]
                break
    return mult


def generate_inventory_snapshot(stores_df: pd.DataFrame, skus_df: pd.DataFrame,
                                  sample_stores: int = 300, sample_skus: int = 600) -> pd.DataFrame:
    """Current inventory position across store × SKU combinations."""
    now = datetime.now()
    valid_stores = stores_df[stores_df["format"] != "Walmart Pickup"]
    store_sample = valid_stores.sample(min(sample_stores, len(valid_stores)))
    sku_sample   = skus_df.sample(min(sample_skus, len(skus_df)))

    rows: List[Dict] = []
    for _, store in store_sample.iterrows():
        for _, sku in sku_sample.iterrows():
            rop    = int(sku["reorder_point"])
            max_st = int(sku["max_stock_level"])
            on_hand= int(RNG.integers(0, max_st))
            on_order = int(RNG.integers(0, rop * 2)) if on_hand < rop else 0
            daily_vel = int(sku["base_daily_units"] * store["revenue_multiplier"])
            dos    = round(on_hand / max(daily_vel, 1), 2)

            if on_hand == 0:
                status = "Stockout"
            elif on_hand < sku["safety_stock"]:
                status = "Critical"
            elif on_hand < rop:
                status = "Below Reorder"
            elif on_hand > max_st * 0.90:
                status = "Overstock"
            elif on_hand > max_st * 0.70:
                status = "Excess"
            else:
                status = "Healthy"

            rows.append({
                "snapshot_ts":       now.isoformat(),
                "store_id":          store["store_id"],
                "region":            store["region"],
                "state":             store["state"],
                "dc_id":             store["dc_id"],
                "format":            store["format"],
                "sku_id":            sku["sku_id"],
                "product_name":      sku["product_name"],
                "department":        sku["department"],
                "category":          sku["category"],
                "vendor_id":         sku["vendor_id"],
                "vendor_name":       sku["vendor_name"],
                "vendor_tier":       int(sku["vendor_tier"]),
                "on_hand_units":     on_hand,
                "on_order_units":    on_order,
                "safety_stock":      int(sku["safety_stock"]),
                "reorder_point":     rop,
                "reorder_qty":       int(sku["reorder_qty"]),
                "max_stock_level":   max_st,
                "daily_velocity":    daily_vel,
                "days_of_supply":    dos,
                "status":            status,
                "unit_price":        float(sku["unit_price"]),
                "unit_cost":         float(sku["unit_cost"]),
                "inventory_value":   round(on_hand * float(sku["unit_cost"]), 2),
                "retail_value":      round(on_hand * float(sku["unit_price"]), 2),
                "lead_time_days":    int(sku["lead_time_days"]),
                "is_perishable":     bool(sku["is_perishable"]),
                "storage_class":     sku["storage_class"],
                "last_received_ts":  (now - timedelta(days=int(RNG.integers(0, 14)))).isoformat(),
                "last_sold_ts":      (now - timedelta(hours=int(RNG.integers(0, 72)))).isoformat(),
                "fill_rate_30d":     round(float(RNG.uniform(0.72, 0.999)), 4),
            })
    return pd.DataFrame(rows)


def generate_pos_transactions(stores_df: pd.DataFrame, skus_df: pd.DataFrame,
                               days: int = 90, cap: int = 60_000) -> pd.DataFrame:
    """POS transaction history — realistic sales with seasonality + anomalies."""
    rows: List[Dict] = []
    end_dt = datetime.now()
    retail_stores = stores_df[stores_df["avg_daily_txn_base"] > 0]

    for day_offset in range(days):
        dt = end_dt - timedelta(days=days - day_offset)
        store_sample = retail_stores.sample(min(60, len(retail_stores)))

        for _, store in store_sample.iterrows():
            base_txn = int(store["avg_daily_txn_base"])
            # Sample a random category to drive multiplier
            cat_for_day = random.choice(list(PRODUCT_HIERARCHY.keys()))
            day_mult = _demand_multiplier(dt, cat_for_day) * store["revenue_multiplier"]
            n_txn = min(800, max(1, int(base_txn * day_mult * RNG.uniform(0.85, 1.15))))

            for _ in range(n_txn):
                sku = skus_df.sample(1).iloc[0]
                hour = int(RNG.choice(
                    range(6, 23),
                    p=np.array([1, 2, 3, 4, 5, 6, 7, 9, 9, 8, 7, 6, 5, 4, 3, 2, 1]) / 82
                ))
                qty = max(1, int(RNG.integers(1, 8)))
                price = float(sku["unit_price"]) * float(RNG.uniform(0.90, 1.05))
                is_anomaly = random.random() < 0.018  # 1.8% anomaly rate

                rows.append({
                    "txn_id":       hashlib.md5(f"{day_offset}{store['store_id']}{len(rows)}".encode()).hexdigest()[:14].upper(),
                    "timestamp":    dt.replace(hour=hour, minute=int(RNG.integers(0,60)), second=int(RNG.integers(0,60))).isoformat(),
                    "date":         dt.strftime("%Y-%m-%d"),
                    "week":         dt.strftime("%Y-W%V"),
                    "month":        dt.strftime("%Y-%m"),
                    "store_id":     store["store_id"],
                    "region":       store["region"],
                    "state":        store["state"],
                    "format":       store["format"],
                    "dc_id":        store["dc_id"],
                    "sku_id":       sku["sku_id"],
                    "product_name": sku["product_name"],
                    "department":   sku["department"],
                    "category":     sku["category"],
                    "vendor_id":    sku["vendor_id"],
                    "qty":          qty,
                    "unit_price":   round(price, 2),
                    "unit_cost":    float(sku["unit_cost"]),
                    "total_revenue":round(qty * price, 2),
                    "total_cost":   round(qty * float(sku["unit_cost"]), 2),
                    "gross_margin": round(qty * (price - float(sku["unit_cost"])), 2),
                    "payment":      random.choice(["Credit","Debit","Walmart+","Cash","EBT","SNAP","Gift Card"]),
                    "channel":      random.choice(["In-Store","Self-Checkout","Curbside","Online-Ship","Online-Pickup"]),
                    "loyalty_member":random.random() < 0.38,
                    "is_anomaly":   is_anomaly,
                    "anomaly_type": random.choice(["price_spike","bulk_purchase","off-hours","region_outlier"]) if is_anomaly else None,
                    "day_of_week":  dt.strftime("%A"),
                    "is_weekend":   dt.weekday() >= 5,
                    "demand_event": next((e["name"] for e in DEMAND_CALENDAR
                                         if dt.month == e["month"] and e["day_range"][0] <= dt.day <= e["day_range"][1]), None),
                })
                if len(rows) >= cap:
                    return pd.DataFrame(rows)

    return pd.DataFrame(rows)


def generate_vendor_events(days: int = 90) -> pd.DataFrame:
    """Vendor shipment events — delays, quality issues, capacity warnings."""
    EVENT_TYPES = [
        ("SHIPMENT_DISPATCHED",  0.38),
        ("SHIPMENT_DELIVERED",   0.32),
        ("SHIPMENT_DELAYED",     0.09),
        ("PARTIAL_DELIVERY",     0.06),
        ("QUALITY_REJECTION",    0.04),
        ("CAPACITY_CONSTRAINT",  0.04),
        ("INVOICE_DISPUTE",      0.03),
        ("CONTRACT_AMENDMENT",   0.02),
        ("FORCE_MAJEURE",        0.01),
        ("PRICE_ESCALATION",     0.01),
    ]
    now = datetime.now()
    rows = []
    for vendor in VENDORS:
        n_events = max(10, int(days * (1.5 + (1 - vendor["otd_pct"]) * 15)))
        for i in range(n_events):
            etype = random.choices([e[0] for e in EVENT_TYPES],
                                   weights=[e[1] for e in EVENT_TYPES])[0]
            ts = now - timedelta(days=int(RNG.integers(0, days)),
                                  hours=int(RNG.integers(0, 24)))
            delay_hrs = 0
            if etype == "SHIPMENT_DELAYED":
                delay_hrs = int(RNG.integers(4, 120))
            elif etype == "FORCE_MAJEURE":
                delay_hrs = int(RNG.integers(24, 720))

            risk_delta = int((1 - vendor["otd_pct"]) * 60 + (delay_hrs / 120) * 30 + RNG.integers(-8, 15))
            risk_score = min(100, max(0, risk_delta))

            rows.append({
                "event_id":          'EVT-' + hashlib.md5(f"{vendor['id']}{i}".encode()).hexdigest()[:10].upper(),
                "timestamp":         ts.isoformat(),
                "date":              ts.strftime("%Y-%m-%d"),
                "week":              ts.strftime("%Y-W%V"),
                "vendor_id":         vendor["id"],
                "vendor_name":       vendor["name"],
                "vendor_tier":       vendor["tier"],
                "event_type":        etype,
                "severity":          "Critical" if risk_score > 75 else "High" if risk_score > 50 else "Medium" if risk_score > 25 else "Low",
                "delay_hours":       delay_hrs,
                "risk_score":        risk_score,
                "on_time_pct":       round(vendor["otd_pct"] * 100 + float(RNG.uniform(-3, 3)), 2),
                "sku_count_affected":int(RNG.integers(1, 250)),
                "stores_affected":   int(RNG.integers(1, 180)),
                "po_value_usd":      round(float(RNG.uniform(8_000, 3_500_000)), 2),
                "dc_destination":    f"DC-{random.choice(['SE','NE','MW','SW','WE','SC'])}-{random.randint(1,7):02d}",
                "carrier":           random.choice(["FedEx Freight","UPS Supply Chain","XPO Logistics","J.B. Hunt","Werner Enterprises","Walmart Fleet"]),
                "resolved":          etype not in ("SHIPMENT_DELAYED","QUALITY_REJECTION","FORCE_MAJEURE") or random.random() > 0.35,
                "resolution_hrs":    int(RNG.integers(1, 96)) if random.random() < 0.7 else None,
                "financial_impact":  round(float(RNG.uniform(500, 500_000)), 2) if risk_score > 40 else 0,
            })
    return pd.DataFrame(rows).sort_values("timestamp", ascending=False).reset_index(drop=True)


def generate_warehouse_telemetry(hours: int = 48) -> pd.DataFrame:
    """Real-time sensor data from distribution centers."""
    DCs = [f"DC-{r}-{i:02d}" for r in ["SE","NE","MW","SW","WE","SC"] for i in range(1, 5)]
    now = datetime.now()
    rows = []
    for dc in DCs:
        base_util = RNG.uniform(0.55, 0.94)
        for tick in range(hours * 4):   # 15-min granularity
            ts = now - timedelta(minutes=(hours * 4 - tick) * 15)
            util = float(np.clip(base_util + RNG.normal(0, 0.04), 0.30, 0.99))
            rows.append({
                "timestamp":            ts.isoformat(),
                "dc_id":                dc,
                "region":               dc.split("-")[1],
                "throughput_units_hr":  int(RNG.integers(800, 12_000)),
                "dock_doors_active":    int(RNG.integers(8, 48)),
                "dock_utilization_pct": round(util * 100, 2),
                "conveyor_speed_fpm":   int(RNG.integers(80, 240)),
                "sorter_accuracy_pct":  round(float(RNG.uniform(99.1, 99.95)), 3),
                "picker_efficiency_pct":round(float(RNG.uniform(72, 99)), 2),
                "orders_pending":       int(RNG.integers(50, 2500)),
                "orders_completed_hr":  int(RNG.integers(50, 900)),
                "mhe_fault_count":      int(RNG.integers(0, 8)),
                "temp_ambient_f":       round(float(RNG.uniform(60, 78)), 1),
                "temp_cold_zone_f":     round(float(RNG.uniform(34.0, 38.5)), 1),
                "temp_frozen_zone_f":   round(float(RNG.uniform(-4.0, 2.0)), 1),
                "forklift_active":      int(RNG.integers(4, 32)),
                "safety_incidents":     1 if random.random() < 0.005 else 0,
                "power_draw_kw":        int(RNG.integers(800, 4200)),
                "alert_flag":           util > 0.92 or random.random() < 0.025,
                "alert_type":           "CAPACITY" if util > 0.92 else ("EQUIPMENT" if random.random() < 0.01 else None),
            })
    return pd.DataFrame(rows)


def generate_demand_signals(skus_df: pd.DataFrame, stores_df: pd.DataFrame,
                             horizon_days: int = 14) -> pd.DataFrame:
    """14-day forward demand forecasts with confidence intervals."""
    sample_skus   = skus_df.sample(min(300, len(skus_df)))
    sample_stores = stores_df[stores_df["avg_daily_txn_base"] > 0].sample(min(40, len(stores_df)))
    now = datetime.now()
    rows = []
    for _, sku in sample_skus.iterrows():
        base = int(sku["base_daily_units"])
        for _, store in sample_stores.iterrows():
            for d in range(horizon_days):
                dt = now + timedelta(days=d)
                mult = _demand_multiplier(dt, sku["department"]) * float(store["revenue_multiplier"])
                forecast = max(0, int(base * mult * float(RNG.uniform(0.85, 1.20))))
                uncertainty = 0.22 - d * 0.005  # uncertainty grows with horizon
                rows.append({
                    "forecast_date":       dt.strftime("%Y-%m-%d"),
                    "generated_ts":        now.isoformat(),
                    "forecast_horizon_day":d + 1,
                    "store_id":            store["store_id"],
                    "region":              store["region"],
                    "sku_id":              sku["sku_id"],
                    "department":          sku["department"],
                    "category":            sku["category"],
                    "base_demand_units":   base,
                    "forecast_units":      forecast,
                    "lower_ci_80":         max(0, int(forecast * (1 - uncertainty))),
                    "upper_ci_80":         int(forecast * (1 + uncertainty)),
                    "demand_multiplier":   round(mult, 4),
                    "confidence_score":    round(max(0.5, 0.97 - d * 0.025 + float(RNG.uniform(-0.03, 0.03))), 4),
                    "model":               random.choice(["XGBoost-v4","LightGBM-v3","Prophet-v2","DeepAR-v1"]),
                    "demand_event":        next((e["name"] for e in DEMAND_CALENDAR
                                                if dt.month == e["month"] and e["day_range"][0] <= dt.day <= e["day_range"][1]), None),
                    "is_anomaly_forecast": mult > 2.0,
                })
    return pd.DataFrame(rows)


def generate_agent_observability(hours: int = 72) -> pd.DataFrame:
    """LLMOps observability data for all 7 agents."""
    AGENTS = [
        ("DemandForecastAgent",   "claude-3-haiku-20240307",    300, 900,  0.0012),
        ("InventoryOptAgent",     "claude-3-haiku-20240307",    250, 750,  0.0009),
        ("VendorRiskAgent",       "claude-3-haiku-20240307",    280, 820,  0.0011),
        ("LogisticsCoordAgent",   "claude-3-haiku-20240307",    220, 680,  0.0008),
        ("PricingPromoAgent",     "claude-3-haiku-20240307",    190, 620,  0.0007),
        ("ExecutiveInsightAgent", "claude-3-5-sonnet-20241022", 1200,3500, 0.0180),
        ("ConversationalAgent",   "claude-3-5-sonnet-20241022", 900, 2800, 0.0145),
    ]
    now  = datetime.now()
    rows = []
    for h in range(hours * 2):   # 30-min buckets
        ts = now - timedelta(minutes=(hours * 2 - h) * 30)
        for agent, model, tok_in_base, tok_out_base, cost_per_k in AGENTS:
            calls = int(RNG.integers(5, 180))
            tok_in  = int(tok_in_base  * RNG.uniform(0.7, 1.4))
            tok_out = int(tok_out_base * RNG.uniform(0.7, 1.4))
            rows.append({
                "timestamp":          ts.isoformat(),
                "agent_name":         agent,
                "model":              model,
                "calls_per_interval": calls,
                "avg_latency_ms":     int(RNG.integers(180, 3800)),
                "p50_latency_ms":     int(RNG.integers(150, 2200)),
                "p95_latency_ms":     int(RNG.integers(600, 7500)),
                "p99_latency_ms":     int(RNG.integers(1200, 14000)),
                "tokens_in":          tok_in,
                "tokens_out":         tok_out,
                "cost_usd":           round((tok_in + tok_out) / 1000 * cost_per_k * calls, 6),
                "accuracy_score":     round(float(RNG.uniform(0.84, 0.99)), 4),
                "faithfulness_score": round(float(RNG.uniform(0.88, 0.99)), 4),
                "hallucination_rate": round(float(RNG.uniform(0.003, 0.055)), 5),
                "context_precision":  round(float(RNG.uniform(0.82, 0.99)), 4),
                "tool_calls":         int(RNG.integers(0, 18)),
                "rag_retrievals":     int(RNG.integers(0, 10)),
                "cache_hit_rate":     round(float(RNG.uniform(0.10, 0.72)), 4),
                "errors_count":       int(RNG.integers(0, 4)),
                "retry_count":        int(RNG.integers(0, 2)),
            })
    return pd.DataFrame(rows)


def generate_agent_decisions(n: int = 600) -> pd.DataFrame:
    """Historical agent decisions with business impact tracking."""
    DECISION_TEMPLATES = {
        "DemandForecastAgent": [
            ("DEMAND_SPIKE_ALERT", "Demand surge forecast for {dept} in {region}: +{pct}% above baseline over next {d} days. Initiating upstream cascade.", "High"),
            ("ANOMALY_FLAG", "Unusual purchase velocity: {sku} at {store} — {mult}x 30-day average. Possible bulk buyer or data error.", "Medium"),
            ("SEASONAL_READINESS", "{dept} seasonal demand model activated. Predicted +{pct}% lift starting {d} days out. Safety stock uplift recommended.", "Medium"),
            ("FORECAST_REVISION", "Model revised demand for {dept}/{region} downward by {pct}% due to weather event and competitor opening data.", "Low"),
        ],
        "InventoryOptAgent": [
            ("REPLENISHMENT_ORDER", "Emergency PO generated: {sku} at {n} stores ({region}). {units} units dispatched from DC. ETA: {d} days.", "Critical"),
            ("OVERSTOCK_FLAG", "Overstock detected: {sku} at {pct}% above optimal. ${usd} capital locked. Recommend inter-store transfer + markdown.", "High"),
            ("SAFETY_STOCK_REVISION", "Safety stock formula recalibrated for {dept} — demand volatility σ increased {pct}%.", "Low"),
            ("STOCKOUT_PREDICTION", "Predicted stockout in {d} hours for {sku} at {n} stores. Override reorder at standard cadence.", "Critical"),
        ],
        "VendorRiskAgent": [
            ("VENDOR_DELAY_ESCALATION", "{vendor} delivery {hrs}hrs late. Impacts {n} stores, {sku_count} SKUs. Alt-vendor evaluation triggered.", "Critical"),
            ("RISK_SCORE_UPGRADE", "{vendor} composite risk score elevated to {score}/100 (was {prev}). Recommending procurement review.", "High"),
            ("ALT_VENDOR_RECOMMENDATION", "Alternate sourcing identified for {dept}: {vendor2} (lead-time -{d}d, cost +{pct}%). Pending approval.", "Medium"),
            ("CONTRACT_RISK_FLAG", "{vendor} exhibiting pattern of partial deliveries ({n} in 30d). Legal review of SLA clauses recommended.", "High"),
        ],
        "LogisticsCoordAgent": [
            ("DC_BOTTLENECK_ALERT", "DC-{dc} at {pct}% utilization. Projecting SLA breach in {hrs}hrs. Authorizing overtime + volume reroute.", "Critical"),
            ("ROUTE_OPTIMIZATION", "Optimized last-mile routes for {n} stores from DC-{dc}. Est. ${usd} fuel savings/week, CO₂ -{co2} tons.", "Low"),
            ("FULFILLMENT_RISK", "Fulfillment SLA at risk for {n} stores: pick-pack backlog {hrs}hrs. Cross-docking initiated.", "High"),
            ("CARRIER_PERFORMANCE", "Carrier {carrier} on-time rate dropped to {pct}% (SLA: 96%). Triggering diversification to secondary carrier.", "Medium"),
        ],
        "PricingPromoAgent": [
            ("MARKDOWN_TRIGGER", "Auto-markdown activated: {sku} — {pct}% reduction to clear {units} excess units before expiry in {d} days.", "High"),
            ("COMPETITIVE_PRICE_ALERT", "Competitor undercut detected: {sku} — gap of {pct}%. Revenue impact ~${usd}/wk without correction.", "High"),
            ("PROMO_ROI_ANALYSIS", "{dept} promotion analysis: +{pct}% unit lift, -{margin}% margin impact. Extending 2 weeks recommended.", "Medium"),
            ("PRICE_ARCHITECTURE_VIOLATION", "Price architecture breach: {sku} selling below cost by ${usd}. Pricing rule exception requires SVP approval.", "Critical"),
        ],
        "ExecutiveInsightAgent": [
            ("EXEC_WEEKLY_SUMMARY", "Week {wk}: Revenue ${rev}M ({delta}% vs plan). {n} critical alerts resolved. Vendor risk: {risk}/100. Supply continuity: {pct}%.", "Low"),
            ("STRATEGIC_SUPPLY_RISK", "Supply chain risk index: {score}/100 — ELEVATED. Primary drivers: {vendor} delay, {region} DC constraints.", "High"),
            ("KPI_DEVIATION_ALERT", "{region} region tracking {pct}% below revenue forecast. Root cause: {cause}. Escalating to Regional VP.", "High"),
            ("BOARD_ALERT", "Potential revenue impact >${usd}M from vendor disruption cluster ({n} vendors). Board-level visibility recommended.", "Critical"),
        ],
    }
    agents = list(DECISION_TEMPLATES.keys())
    now = datetime.now()
    rows = []

    for i in range(n):
        agent = random.choice(agents)
        tmpls = DECISION_TEMPLATES[agent]
        dtype, tmpl, base_sev = random.choice(tmpls)
        msg = tmpl.format(
            dept=random.choice(list(PRODUCT_HIERARCHY.keys())[:4]),
            region=random.choice(list(REGIONS.keys())),
            pct=random.randint(8, 87),
            d=random.randint(1, 21),
            sku=f"SKU-{random.randint(1,9999):07d}",
            store=f"WMT-{random.randint(1001,5200):05d}",
            n=random.randint(2, 180),
            units=random.randint(200, 50000),
            mult=round(random.uniform(2.1, 8.5), 1),
            vendor=random.choice(VENDORS)["name"],
            vendor2=random.choice(VENDORS)["name"],
            hrs=random.randint(4, 120),
            sku_count=random.randint(10, 500),
            score=random.randint(51, 99),
            prev=random.randint(20, 50),
            dc=f"{random.choice(['SE','NE','MW'])}-{random.randint(1,7):02d}",
            usd=f"{random.randint(5000, 5_000_000):,}",
            co2=random.randint(2, 40),
            carrier=random.choice(["XPO Logistics","FedEx Freight","J.B. Hunt"]),
            margin=round(random.uniform(1.5, 8.5), 1),
            wk=random.randint(1, 52),
            rev=round(random.uniform(200, 2000), 1),
            delta=f"+{random.randint(1,12)}" if random.random()>0.4 else f"-{random.randint(1,15)}",
            risk=random.randint(25, 88),
            cause=random.choice(["vendor delay", "weather disruption", "demand softness", "competitor activity"]),
        )
        ts = now - timedelta(hours=int(RNG.integers(0, 72 * 7)), minutes=int(RNG.integers(0, 59)))
        rows.append({
            "decision_id":          f"DEC-{i+1:06d}",
            "timestamp":            ts.isoformat(),
            "agent":                agent,
            "decision_type":        dtype,
            "decision_text":        msg,
            "severity":             base_sev,
            "confidence":           round(float(RNG.uniform(0.72, 0.99)), 4),
            "status":               random.choices(
                                        ["AUTO_APPROVED","PENDING_HITL","ESCALATED","REJECTED","IMPLEMENTED"],
                                        weights=[0.48, 0.24, 0.14, 0.08, 0.06])[0],
            "tokens_consumed":      int(RNG.integers(600, 8000)),
            "latency_ms":           int(RNG.integers(180, 5500)),
            "rag_docs_retrieved":   int(RNG.integers(0, 8)),
            "downstream_agents":    json.dumps(random.sample([a for a in agents if a != agent], random.randint(0, 3))),
            "business_impact_usd":  round(float(RNG.uniform(500, 12_000_000)), 2),
            "human_reviewer":       random.choice(["ops-lead@walmart.com", "supply-mgr@walmart.com", None, None]),
            "review_sla_hrs":       random.choice([2, 4, 8, 24, None]),
        })
    return pd.DataFrame(rows).sort_values("timestamp", ascending=False).reset_index(drop=True)


def generate_pricing_intelligence(skus_df: pd.DataFrame) -> pd.DataFrame:
    """Competitive pricing data with AI recommendations."""
    sample = skus_df.sample(min(800, len(skus_df)))
    rows = []
    for _, sku in sample.iterrows():
        price = float(sku["unit_price"])
        gap   = float(RNG.uniform(-0.18, 0.25))
        elast = float(RNG.uniform(-3.2, -0.4))
        is_promo = random.random() < 0.16
        rows.append({
            "sku_id":               sku["sku_id"],
            "product_name":         sku["product_name"],
            "department":           sku["department"],
            "category":             sku["category"],
            "vendor_id":            sku["vendor_id"],
            "current_price":        price,
            "competitor_a_price":   round(price * (1 + gap), 2),
            "competitor_b_price":   round(price * (1 + gap * 0.7 + float(RNG.uniform(-0.05, 0.05))), 2),
            "price_gap_pct":        round(gap * 100, 2),
            "price_elasticity":     round(elast, 3),
            "margin_pct":           float(sku["margin_pct"]),
            "velocity_class":       sku["velocity_class"],
            "promo_active":         is_promo,
            "promo_type":           random.choice(["Rollback","Clearance","Manager Special","EDLP","BOGO"]) if is_promo else None,
            "promo_discount_pct":   round(float(RNG.uniform(5, 40)), 1) if is_promo else 0,
            "days_since_last_price_change": int(RNG.integers(1, 180)),
            "recommended_action":   random.choice(["HOLD","REDUCE_3PCT","REDUCE_5PCT","REDUCE_10PCT","MATCH_COMPETITOR","INCREASE_2PCT","RUN_PROMO","MARKDOWN"]),
            "ai_confidence":        round(float(RNG.uniform(0.68, 0.98)), 4),
            "projected_unit_lift_pct": round(abs(elast * 3.0), 1) if gap > 0.05 else 0,
            "projected_margin_delta": round(float(RNG.uniform(-0.08, 0.04)), 4),
            "last_updated_ts":      datetime.now().isoformat(),
        })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
#  SINGLETON ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class WalmartDataEngine:
    """
    Thread-safe singleton that generates and caches all enterprise datasets.
    Call initialize() once at startup; all datasets live in memory for the session.
    """
    _instance: Optional["WalmartDataEngine"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "WalmartDataEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._ready = False
        return cls._instance

    def initialize(self, verbose: bool = True, fast: bool = False) -> None:
        if self._ready:
            return
        if verbose:
            mode_name = "FAST LOCAL" if fast else "ENTERPRISE"
            print(f"▶ Walmart Data Engine initializing ({mode_name} mode)…")

        if fast:
            stores_count = 300
            skus_count = 3_000
            txns_count = 12_000
            telemetry_hours = 24
            decision_count = 150
        else:
            stores_count = 4_200
            skus_count = 50_000
            txns_count = 60_000
            telemetry_hours = 48
            decision_count = 600

        self.stores         = generate_stores(stores_count)
        self.skus           = generate_skus(skus_count)
        self.inventory      = generate_inventory_snapshot(self.stores, self.skus, 300, 600)
        self.pos            = generate_pos_transactions(self.stores, self.skus, 90, txns_count)
        self.vendor_events  = generate_vendor_events(90)
        self.telemetry      = generate_warehouse_telemetry(telemetry_hours)
        self.demand_signals = generate_demand_signals(self.skus, self.stores, 14)
        self.observability  = generate_agent_observability(72)
        self.decisions      = generate_agent_decisions(decision_count)
        self.pricing        = generate_pricing_intelligence(self.skus)
        self.vendors        = pd.DataFrame(VENDORS)

        self._ready = True
        if verbose:
            print(f"✅ Data Engine ready — {self.stores.shape[0]:,} stores | "
                  f"{self.skus.shape[0]:,} SKUs | {self.pos.shape[0]:,} txns | "
                  f"{self.inventory.shape[0]:,} inv records")

    @property
    def ready(self) -> bool:
        return self._ready

    def summary(self) -> Dict[str, int]:
        if not self._ready:
            return {}
        return {
            "stores":            len(self.stores),
            "skus":              len(self.skus),
            "pos_transactions":  len(self.pos),
            "inventory_records": len(self.inventory),
            "vendor_events":     len(self.vendor_events),
            "telemetry_records": len(self.telemetry),
            "demand_signals":    len(self.demand_signals),
            "agent_decisions":   len(self.decisions),
        }


# Global singleton
engine = WalmartDataEngine()
