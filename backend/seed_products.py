"""Seed catalog for the demo merchant **Vastra Studio** — Indian ethnic wear.

Two plain data structures the seeder consumes:
  * ``PRODUCTS`` — list of product dicts (keys match ``Product`` columns).
  * ``RELATIONS`` — curated cross-sell links **by product name** (resolved to ids
    at seed time). These drive the contextual, budget-aware upsell.

The eight anchor products below back the primary demo journey
("something for my sister's wedding under ₹4000" -> Banarasi Silk Saree ₹2499,
upsell Pearl Drop Earrings ₹599 -> ₹3098). Do not rename them without also
updating ``RELATIONS`` and the README demo script.

Prices are integer rupees. This is demo seed data.
"""
from __future__ import annotations

from .models import RelationType

# --------------------------------------------------------------------------- #
# Products
# --------------------------------------------------------------------------- #
PRODUCTS = [
    # --- Sarees --------------------------------------------------------------
    {
        "name": "Banarasi Silk Saree",
        "description": "Handwoven pure Banarasi silk saree with intricate gold zari work and a rich pallu — a timeless choice for weddings and grand celebrations.",
        "category": "Sarees", "subcategory": "Silk Saree", "brand": "Vastra Heritage",
        "price": 2499, "stock": 12, "rating": 4.9,
        "tags": ["silk", "zari", "handwoven", "banarasi", "traditional", "premium", "wedding"],
        "occasion": ["wedding", "festive"], "gender": "women",
    },
    {
        "name": "Kanjivaram Silk Saree",
        "description": "South Indian Kanjivaram silk saree with a contrast border and temple motifs, woven for bridal and festive occasions.",
        "category": "Sarees", "subcategory": "Silk Saree", "brand": "Vastra Heritage",
        "price": 3299, "stock": 8, "rating": 4.8,
        "tags": ["silk", "kanjivaram", "temple", "bridal", "premium"],
        "occasion": ["wedding", "festive"], "gender": "women",
    },
    {
        "name": "Chanderi Cotton Saree",
        "description": "Lightweight Chanderi cotton-silk saree with a subtle sheen and delicate buti work — easy elegance for daytime functions.",
        "category": "Sarees", "subcategory": "Cotton Saree", "brand": "Loom & Co.",
        "price": 1799, "stock": 20, "rating": 4.5,
        "tags": ["chanderi", "cotton", "lightweight", "buti"],
        "occasion": ["festive", "office", "casual"], "gender": "women",
    },
    {
        "name": "Georgette Party Saree",
        "description": "Flowy georgette saree with sequin detailing and a pre-stitched pallu for a modern, party-ready drape.",
        "category": "Sarees", "subcategory": "Designer Saree", "brand": "Aria Label",
        "price": 2199, "stock": 15, "rating": 4.4,
        "tags": ["georgette", "sequin", "party", "modern"],
        "occasion": ["party", "wedding"], "gender": "women",
    },
    {
        "name": "Linen Handloom Saree",
        "description": "Breathable pure linen handloom saree with a minimal zari border — understated and office-appropriate.",
        "category": "Sarees", "subcategory": "Handloom Saree", "brand": "Loom & Co.",
        "price": 1499, "stock": 18, "rating": 4.3,
        "tags": ["linen", "handloom", "minimal", "breathable"],
        "occasion": ["office", "casual"], "gender": "women",
    },

    # --- Lehengas & Gowns (categorised under Kurtas' sibling: use "Sarees"? no) -> keep as their own via category Kurtas? Use dedicated
    {
        "name": "Embroidered Bridal Lehenga",
        "description": "Heavily embroidered bridal lehenga with mirror and thread work, blouse and dupatta included — a statement wedding ensemble.",
        "category": "Lehengas", "subcategory": "Bridal Lehenga", "brand": "Vastra Couture",
        "price": 8999, "stock": 5, "rating": 4.9,
        "tags": ["lehenga", "bridal", "embroidered", "mirror", "premium"],
        "occasion": ["wedding"], "gender": "women",
    },
    {
        "name": "Festive Georgette Lehenga",
        "description": "Semi-stitched georgette lehenga with sequin work — festive glamour without the bridal weight.",
        "category": "Lehengas", "subcategory": "Festive Lehenga", "brand": "Aria Label",
        "price": 4499, "stock": 9, "rating": 4.6,
        "tags": ["lehenga", "georgette", "sequin", "festive"],
        "occasion": ["wedding", "festive", "party"], "gender": "women",
    },

    # --- Kurtas & Suits ------------------------------------------------------
    {
        "name": "Anarkali Kurta Suit",
        "description": "Floor-length Anarkali kurta with churidar and dupatta, delicate gota work at the yoke — graceful for festive gatherings.",
        "category": "Kurtas", "subcategory": "Anarkali Suit", "brand": "Rangreza",
        "price": 2299, "stock": 16, "rating": 4.6,
        "tags": ["anarkali", "kurta", "suit", "gota", "festive"],
        "occasion": ["festive", "wedding", "party"], "gender": "women",
    },
    {
        "name": "Cotton Straight Kurti",
        "description": "Everyday cotton straight-cut kurti with block prints — comfortable for work and casual wear.",
        "category": "Kurtas", "subcategory": "Kurti", "brand": "Rangreza",
        "price": 899, "stock": 40, "rating": 4.3,
        "tags": ["cotton", "kurti", "block print", "everyday"],
        "occasion": ["office", "casual"], "gender": "women",
    },
    {
        "name": "Silk Blend Palazzo Suit",
        "description": "Silk-blend kurta with palazzo and organza dupatta — a contemporary festive set with a soft drape.",
        "category": "Kurtas", "subcategory": "Palazzo Suit", "brand": "Rangreza",
        "price": 1999, "stock": 14, "rating": 4.5,
        "tags": ["silk blend", "palazzo", "organza", "festive"],
        "occasion": ["festive", "party", "office"], "gender": "women",
    },
    {
        "name": "Men's Cotton Kurta Set",
        "description": "Classic cotton kurta with matching pyjama and a mandarin collar — versatile for festivals, poojas and daytime functions.",
        "category": "Kurtas", "subcategory": "Men's Kurta", "brand": "Raghav Ethnics",
        "price": 1899, "stock": 22, "rating": 4.6,
        "tags": ["kurta", "cotton", "men", "pyjama", "festive"],
        "occasion": ["festive", "wedding", "casual"], "gender": "men",
    },
    {
        "name": "Men's Silk Kurta",
        "description": "Rich art-silk kurta with subtle self-weave, tailored fit — dressy enough for wedding functions.",
        "category": "Kurtas", "subcategory": "Men's Kurta", "brand": "Raghav Ethnics",
        "price": 2599, "stock": 12, "rating": 4.7,
        "tags": ["kurta", "silk", "men", "wedding"],
        "occasion": ["wedding", "festive"], "gender": "men",
    },
    {
        "name": "Men's Nehru Jacket",
        "description": "Textured Nehru jacket that layers over any kurta for an instant festive upgrade.",
        "category": "Kurtas", "subcategory": "Nehru Jacket", "brand": "Raghav Ethnics",
        "price": 1499, "stock": 18, "rating": 4.5,
        "tags": ["nehru jacket", "layer", "men", "festive"],
        "occasion": ["wedding", "festive"], "gender": "men",
    },

    # --- Dupattas ------------------------------------------------------------
    {
        "name": "Embroidered Silk Dupatta",
        "description": "Pure silk dupatta with hand-embroidered borders and tassels — a finishing layer for suits and lehengas.",
        "category": "Dupattas", "subcategory": "Silk Dupatta", "brand": "Vastra Heritage",
        "price": 799, "stock": 30, "rating": 4.5,
        "tags": ["dupatta", "silk", "embroidered", "tassels"],
        "occasion": ["wedding", "festive", "party"], "gender": "women",
    },
    {
        "name": "Phulkari Cotton Dupatta",
        "description": "Vibrant Phulkari-embroidered cotton dupatta from Punjab — a pop of colour over plain kurtas.",
        "category": "Dupattas", "subcategory": "Cotton Dupatta", "brand": "Loom & Co.",
        "price": 549, "stock": 35, "rating": 4.4,
        "tags": ["dupatta", "phulkari", "cotton", "colourful"],
        "occasion": ["festive", "casual"], "gender": "women",
    },
    {
        "name": "Bandhani Chiffon Dupatta",
        "description": "Tie-dye Bandhani chiffon dupatta with a light, airy fall — a Rajasthani classic.",
        "category": "Dupattas", "subcategory": "Chiffon Dupatta", "brand": "Rang Rasiya",
        "price": 649, "stock": 28, "rating": 4.3,
        "tags": ["dupatta", "bandhani", "chiffon", "tie-dye"],
        "occasion": ["festive", "party", "casual"], "gender": "women",
    },

    # --- Jewellery -----------------------------------------------------------
    {
        "name": "Pearl Drop Earrings",
        "description": "Delicate freshwater-style pearl drop earrings set in gold-tone alloy — light, elegant and pair with almost anything.",
        "category": "Jewellery", "subcategory": "Earrings", "brand": "Zevar",
        "price": 599, "stock": 50, "rating": 4.7,
        "tags": ["earrings", "pearl", "drop", "gold-tone", "elegant"],
        "occasion": ["wedding", "festive", "party", "gifting"], "gender": "women",
    },
    {
        "name": "Kundan Choker Necklace",
        "description": "Traditional Kundan choker with faux-pearl drops and a matching pair of studs — bridal-grade sparkle.",
        "category": "Jewellery", "subcategory": "Necklace", "brand": "Zevar",
        "price": 1399, "stock": 18, "rating": 4.6,
        "tags": ["necklace", "kundan", "choker", "bridal", "set"],
        "occasion": ["wedding", "festive"], "gender": "women",
    },
    {
        "name": "Jhumka Earrings",
        "description": "Oxidised silver-tone jhumkas with ghungroo detailing — a festive staple.",
        "category": "Jewellery", "subcategory": "Earrings", "brand": "Zevar",
        "price": 449, "stock": 45, "rating": 4.5,
        "tags": ["earrings", "jhumka", "oxidised", "festive"],
        "occasion": ["festive", "party", "casual", "gifting"], "gender": "women",
    },
    {
        "name": "Temple Jewellery Set",
        "description": "Antique-gold temple jewellery set with necklace and earrings, inspired by South Indian bridal wear.",
        "category": "Jewellery", "subcategory": "Jewellery Set", "brand": "Zevar",
        "price": 1899, "stock": 10, "rating": 4.7,
        "tags": ["temple", "set", "antique gold", "bridal"],
        "occasion": ["wedding", "festive"], "gender": "women",
    },
    {
        "name": "Polki Maang Tikka",
        "description": "Polki-studded maang tikka that completes a bridal or festive look.",
        "category": "Jewellery", "subcategory": "Maang Tikka", "brand": "Zevar",
        "price": 699, "stock": 22, "rating": 4.4,
        "tags": ["maang tikka", "polki", "bridal", "festive"],
        "occasion": ["wedding", "festive"], "gender": "women",
    },
    {
        "name": "Kada Bangle Pair",
        "description": "Meenakari-work kada bangles in a pair — festive colour on the wrist.",
        "category": "Jewellery", "subcategory": "Bangles", "brand": "Zevar",
        "price": 899, "stock": 26, "rating": 4.3,
        "tags": ["bangles", "kada", "meenakari", "pair"],
        "occasion": ["wedding", "festive", "gifting"], "gender": "women",
    },

    # --- Bags ----------------------------------------------------------------
    {
        "name": "Handcrafted Potli Bag",
        "description": "Silk potli bag with zardozi embroidery and a beaded drawstring — the perfect little companion to ethnic wear.",
        "category": "Bags", "subcategory": "Potli", "brand": "Kalakriti",
        "price": 449, "stock": 38, "rating": 4.5,
        "tags": ["potli", "silk", "zardozi", "beaded", "handcrafted"],
        "occasion": ["wedding", "festive", "party", "gifting"], "gender": "women",
    },
    {
        "name": "Embellished Box Clutch",
        "description": "Structured box clutch with mirror and bead embellishment and a detachable chain — party-perfect.",
        "category": "Bags", "subcategory": "Clutch", "brand": "Kalakriti",
        "price": 1099, "stock": 20, "rating": 4.4,
        "tags": ["clutch", "box", "mirror", "beaded", "party"],
        "occasion": ["party", "wedding", "festive"], "gender": "women",
    },
    {
        "name": "Jute Tote Bag",
        "description": "Everyday jute tote with a block-printed panel — roomy and eco-friendly.",
        "category": "Bags", "subcategory": "Tote", "brand": "Kalakriti",
        "price": 599, "stock": 32, "rating": 4.2,
        "tags": ["tote", "jute", "block print", "everyday", "eco"],
        "occasion": ["casual", "office", "gifting"], "gender": "women",
    },

    # --- Accessories ---------------------------------------------------------
    {
        "name": "Leather Bifold Wallet",
        "description": "Full-grain leather bifold wallet with card slots and a coin pocket — a dependable everyday carry and a safe gift.",
        "category": "Accessories", "subcategory": "Wallet", "brand": "Hide & Craft",
        "price": 999, "stock": 30, "rating": 4.6,
        "tags": ["wallet", "leather", "bifold", "men", "gifting"],
        "occasion": ["gifting", "casual", "office"], "gender": "men",
    },
    {
        "name": "Silk Pocket Square",
        "description": "Printed silk pocket square that dresses up a Nehru jacket or blazer.",
        "category": "Accessories", "subcategory": "Pocket Square", "brand": "Raghav Ethnics",
        "price": 349, "stock": 40, "rating": 4.2,
        "tags": ["pocket square", "silk", "men", "accent"],
        "occasion": ["wedding", "office", "gifting"], "gender": "men",
    },
    {
        "name": "Beaded Potli Clutch",
        "description": "Hand-beaded potli clutch with a metal frame — a jewel-toned accent for evening functions.",
        "category": "Accessories", "subcategory": "Clutch", "brand": "Kalakriti",
        "price": 749, "stock": 24, "rating": 4.3,
        "tags": ["clutch", "beaded", "potli", "evening"],
        "occasion": ["party", "wedding", "festive"], "gender": "women",
    },
    {
        "name": "Embroidered Juttis",
        "description": "Hand-embroidered leather juttis with a cushioned sole — comfortable ethnic footwear.",
        "category": "Footwear", "subcategory": "Juttis", "brand": "Pind Footwear",
        "price": 899, "stock": 28, "rating": 4.4,
        "tags": ["juttis", "embroidered", "leather", "footwear"],
        "occasion": ["wedding", "festive", "casual"], "gender": "women",
    },
    {
        "name": "Men's Mojari Shoes",
        "description": "Classic Rajasthani mojari in tan leather — the finishing touch to a kurta set.",
        "category": "Footwear", "subcategory": "Mojari", "brand": "Pind Footwear",
        "price": 1199, "stock": 18, "rating": 4.5,
        "tags": ["mojari", "leather", "men", "footwear"],
        "occasion": ["wedding", "festive"], "gender": "men",
    },

    # --- Gifts ---------------------------------------------------------------
    {
        "name": "Festive Gift Box",
        "description": "Curated festive hamper with a silk scarf, scented candle and assorted dry fruits in a keepsake box — ready to gift.",
        "category": "Gifts", "subcategory": "Hamper", "brand": "Vastra Studio",
        "price": 1299, "stock": 25, "rating": 4.6,
        "tags": ["gift", "hamper", "festive", "scarf", "candle"],
        "occasion": ["gifting", "festive"], "gender": "unisex",
    },
    {
        "name": "Silk Scarf Gift Set",
        "description": "Two printed silk scarves boxed with a greeting card — a light, elegant present.",
        "category": "Gifts", "subcategory": "Gift Set", "brand": "Vastra Studio",
        "price": 899, "stock": 30, "rating": 4.3,
        "tags": ["gift", "scarf", "silk", "set"],
        "occasion": ["gifting", "festive"], "gender": "unisex",
    },
    {
        "name": "Scented Candle Trio",
        "description": "Three hand-poured soy candles in festive fragrances, gift-boxed.",
        "category": "Gifts", "subcategory": "Home", "brand": "Aroma Ghar",
        "price": 749, "stock": 34, "rating": 4.4,
        "tags": ["gift", "candle", "soy", "home", "festive"],
        "occasion": ["gifting", "festive"], "gender": "unisex",
    },
]


# --------------------------------------------------------------------------- #
# Relations (by name) — curated cross-sell for the upsell engine.
# priority: lower number = stronger/first suggestion.
# --------------------------------------------------------------------------- #
RELATIONS = [
    # Anchor demo chain: Banarasi Silk Saree -> earrings first (₹599 keeps ₹4000 budget).
    {"product": "Banarasi Silk Saree", "related": "Pearl Drop Earrings", "type": RelationType.ACCESSORY, "priority": 10},
    {"product": "Banarasi Silk Saree", "related": "Handcrafted Potli Bag", "type": RelationType.ACCESSORY, "priority": 20},
    {"product": "Banarasi Silk Saree", "related": "Embroidered Silk Dupatta", "type": RelationType.COMPLEMENT, "priority": 30},
    {"product": "Banarasi Silk Saree", "related": "Kundan Choker Necklace", "type": RelationType.ACCESSORY, "priority": 40},
    {"product": "Banarasi Silk Saree", "related": "Embroidered Juttis", "type": RelationType.ACCESSORY, "priority": 50},

    # Other sarees
    {"product": "Kanjivaram Silk Saree", "related": "Temple Jewellery Set", "type": RelationType.ACCESSORY, "priority": 10},
    {"product": "Kanjivaram Silk Saree", "related": "Pearl Drop Earrings", "type": RelationType.ACCESSORY, "priority": 20},
    {"product": "Kanjivaram Silk Saree", "related": "Handcrafted Potli Bag", "type": RelationType.ACCESSORY, "priority": 30},
    {"product": "Georgette Party Saree", "related": "Embellished Box Clutch", "type": RelationType.ACCESSORY, "priority": 10},
    {"product": "Georgette Party Saree", "related": "Jhumka Earrings", "type": RelationType.ACCESSORY, "priority": 20},
    {"product": "Chanderi Cotton Saree", "related": "Jhumka Earrings", "type": RelationType.ACCESSORY, "priority": 10},
    {"product": "Chanderi Cotton Saree", "related": "Beaded Potli Clutch", "type": RelationType.ACCESSORY, "priority": 20},

    # Lehengas
    {"product": "Embroidered Bridal Lehenga", "related": "Kundan Choker Necklace", "type": RelationType.ACCESSORY, "priority": 10},
    {"product": "Embroidered Bridal Lehenga", "related": "Polki Maang Tikka", "type": RelationType.ACCESSORY, "priority": 20},
    {"product": "Embroidered Bridal Lehenga", "related": "Embellished Box Clutch", "type": RelationType.ACCESSORY, "priority": 30},
    {"product": "Festive Georgette Lehenga", "related": "Jhumka Earrings", "type": RelationType.ACCESSORY, "priority": 10},
    {"product": "Festive Georgette Lehenga", "related": "Kada Bangle Pair", "type": RelationType.ACCESSORY, "priority": 20},

    # Women's suits
    {"product": "Anarkali Kurta Suit", "related": "Jhumka Earrings", "type": RelationType.ACCESSORY, "priority": 10},
    {"product": "Anarkali Kurta Suit", "related": "Embroidered Juttis", "type": RelationType.ACCESSORY, "priority": 20},
    {"product": "Anarkali Kurta Suit", "related": "Beaded Potli Clutch", "type": RelationType.ACCESSORY, "priority": 30},
    {"product": "Silk Blend Palazzo Suit", "related": "Pearl Drop Earrings", "type": RelationType.ACCESSORY, "priority": 10},
    {"product": "Silk Blend Palazzo Suit", "related": "Embroidered Silk Dupatta", "type": RelationType.COMPLEMENT, "priority": 20},
    {"product": "Cotton Straight Kurti", "related": "Phulkari Cotton Dupatta", "type": RelationType.COMPLEMENT, "priority": 10},
    {"product": "Cotton Straight Kurti", "related": "Jute Tote Bag", "type": RelationType.ACCESSORY, "priority": 20},

    # Men's
    {"product": "Men's Cotton Kurta Set", "related": "Men's Nehru Jacket", "type": RelationType.COMPLEMENT, "priority": 10},
    {"product": "Men's Cotton Kurta Set", "related": "Men's Mojari Shoes", "type": RelationType.ACCESSORY, "priority": 20},
    {"product": "Men's Cotton Kurta Set", "related": "Leather Bifold Wallet", "type": RelationType.ACCESSORY, "priority": 30},
    {"product": "Men's Silk Kurta", "related": "Men's Nehru Jacket", "type": RelationType.COMPLEMENT, "priority": 10},
    {"product": "Men's Silk Kurta", "related": "Silk Pocket Square", "type": RelationType.ACCESSORY, "priority": 20},
    {"product": "Men's Silk Kurta", "related": "Men's Mojari Shoes", "type": RelationType.ACCESSORY, "priority": 30},
    {"product": "Men's Nehru Jacket", "related": "Silk Pocket Square", "type": RelationType.ACCESSORY, "priority": 10},

    # Jewellery / gifting cross-sell
    {"product": "Kundan Choker Necklace", "related": "Polki Maang Tikka", "type": RelationType.COMPLEMENT, "priority": 10},
    {"product": "Temple Jewellery Set", "related": "Polki Maang Tikka", "type": RelationType.COMPLEMENT, "priority": 10},
    {"product": "Festive Gift Box", "related": "Scented Candle Trio", "type": RelationType.COMPLEMENT, "priority": 10},
    {"product": "Festive Gift Box", "related": "Silk Scarf Gift Set", "type": RelationType.COMPLEMENT, "priority": 20},
]
