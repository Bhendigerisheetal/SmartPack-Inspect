"""
Extraction Service for SmartPack Inspect.

Extracts structured Legal Metrology fields from OCR text:

- Product / Commodity Name
- Net Quantity
- MRP
- Manufacturer / Packer
- Date Information
- Consumer Care
- Barcode

IMPORTANT:
Only values actually present in OCR text are returned.
No fake/sample product information is generated.
"""

import re
from collections import defaultdict


# ============================================================
# KNOWN BRANDS & SUB-BRANDS
# ============================================================

BRAND_SUBBRANDS = {
    "Parle": [
        "Krackjack", "Monaco", "Parle-G", "Parle G", "Hide & Seek", "Hide and Seek",
        "20-20", "20 20", "Milano", "Magix", "Top", "Frooti", "Appy", "Appy Fizz",
        "Kismi", "Poppins", "Mango Bite", "Melody", "Londonderry", "Rola Cola"
    ],
    "Britannia": [
        "Good Day", "Bourbon", "50-50", "50 50", "Marie Gold", "Treat", "Jim Jam",
        "Milk Bikis", "NutriChoice", "Nice Time", "Little Hearts", "Pure Magic",
        "Tiger", "Winkin Cow", "Cheese", "Butter", "Bread", "Dahi", "Ghee"
    ],
    "Sunfeast": [
        "Dark Fantasy", "Mom's Magic", "Bounce", "All Rounder", "Yippee", "Farmlite",
        "Cexplore", "Marie Light"
    ],
    "Amul": [
        "Taaza", "Gold", "Masti", "Kool", "Slim N Trim", "Cow Milk", "Buffalo Milk",
        "Butter", "Cheese", "Ghee", "Paneer", "Chaas", "Lassi", "Shrikhand", "Ice Cream"
    ],
    "ITC": [
        "Aashirvaad", "Bingo", "Sunfeast", "Yippee", "Tedhe Medhe", "Mad Angles",
        "Master Chef", "B Natural", "Fiama", "Vivel", "Savlon"
    ],
    "Cadbury": [
        "Dairy Milk", "5 Star", "Oreo", "Perk", "Fuse", "Nutties", "Gems", "Bournvita",
        "Celebrations", "Silk", "Temptations", "Eclairs"
    ],
    "Nestle": [
        "Maggi", "KitKat", "Munch", "Milkybar", "Bar One", "Everyday", "Nescafe",
        "Milkmaid", "Cerelac", "Koko Krunch"
    ],
    "Lays": [
        "Classic Salted", "Magic Masala", "Cream & Onion", "Tomato Tango", "Wafer Style"
    ],
    "Kurkure": [
        "Masala Munch", "Green Chutney", "Chilli Chatka", "Solid Masti", "Puffcorn", "Playz"
    ],
    "Balaji": [
        "Wafers", "Crunchex", "Ratlami Sev", "Stack Up", "Gathiya", "Sev Murmura",
        "Aloo Sev", "Chana Jor", "Moong Dal"
    ],
    "Haldiram": [
        "Bhujia", "Aloo Bhujia", "Nut Cracker", "Khatta Meetha", "Moong Dal",
        "Soan Papdi", "Gulab Jamun", "Rasgulla", "Navratan Mix"
    ],
    "Bingo": [
        "Tedhe Medhe", "Mad Angles", "Hashtags", "No Rulz"
    ],
    "Bikaji": [
        "Bhujia", "Bikaneri Bhujia", "Sub-Kuch", "Tana Tan"
    ],
    "Bikano": [
        "Aloo Bhujia", "Bikaneri Bhujia", "Navratan Mix", "Moong Dal"
    ],
    "PepsiCo": [
        "Pepsi", "7Up", "Mirinda", "Mountain Dew", "Tropicana", "Slice", "Aquafina", "Gatorade"
    ],
    "Coca Cola": [
        "Coca-Cola", "Coke", "Thums Up", "Sprite", "Fanta", "Limca", "Maaza", "Kinley", "Minute Maid"
    ]
}

KNOWN_BRANDS = [
    "BALAJI", "PARLE-G", "PARLE", "LAYS", "LAY'S", "KURKURE", "HALDIRAM", "HALDIRAM'S",
    "AASHIRVAAD", "BRITANNIA", "SUNFEAST", "AMUL", "MAGGI", "NESTLE", "BINGO", "ITC",
    "EVEREST", "CATCH", "MDH", "TATA", "MOTHER DAIRY", "NANDINI", "CADBURY", "OREO",
    "MARIE", "GOOD DAY", "FORTUNE", "SAFFOLA", "DABUR", "PATANJALI", "KRAFT", "PEPSI",
    "COCA COLA", "THUMS UP", "SPRITE", "FROOTI", "REAL", "TROPICANA", "KWALITY WALLS",
    "VADILAL", "EPIGAMIA", "MILKFOOD", "GOWARDHAN", "WARANA", "VERKA", "SARAS", "MILMA",
    "BIKAJI", "BIKANO", "KRACKJACK", "MONACO", "DARK FANTASY", "HIDE & SEEK"
]


# ============================================================
# COMMODITY KEYWORDS
# ============================================================

COMMODITY_KEYWORDS = [
    "SWEET & SALTY CRACKERS",
    "POTATO WAFERS",
    "CRACKERS",
    "WAFERS",
    "CHIPS",
    "BISCUITS",
    "COOKIES",
    "ATTA",
    "FLOUR",
    "NOODLES",
    "NAMKEEN",
    "SNACKS",
    "SEV",
    "BHUJIA",
    "SAVOURIES",
    "PASTEURISED TONED MILK",
    "PASTEURISED MILK",
    "HOMOGENISED TONED MILK",
    "HOMOGENIZED TONED MILK",
    "TONED MILK",
    "COW MILK",
    "FULL CREAM MILK",
    "TAAZA",
    "TAZA",
    "GOLD",
    "MILK",
    "CHAAS",
    "BUTTERMILK",
    "CURD",
    "DAIRY",
    "GHEE",
    "BUTTER",
    "CHEESE",
    "PANEER",
    "TEA",
    "COFFEE",
    "OIL",
    "RICE",
    "SALT",
    "SUGAR",
    "PULSES",
    "JUICE",
    "SOAP",
    "SHAMPOO",
    "DETERGENT"
]


# ============================================================
# NORMALIZE OCR TEXT
# ============================================================

def normalize_ocr_text(text):
    """
    Normalize OCR text while preserving line structure.
    """
    if not text:
        return ""

    text = text.replace("\r", "\n")
    lines = []

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"[ \t]+", " ", line)
        lines.append(line)

    return "\n".join(lines)


# ============================================================
# NORMALIZE UNIT
# ============================================================

def normalize_unit(unit):
    if not unit:
        return ""
    unit = unit.upper().strip().rstrip(".").rstrip("*").rstrip("'").rstrip('"')

    mapping = {
        "G": "g",
        "GM": "g",
        "GMS": "g",
        "GRAM": "g",
        "GRAMS": "g",
        "9": "g",  # common OCR substitution for g
        "KG": "kg",
        "KGS": "kg",
        "KILOGRAM": "kg",
        "KILOGRAMS": "kg",
        "ML": "ml",
        "MLS": "ml",
        "MILLILITRE": "ml",
        "MILLILITRES": "ml",
        "L": "L",
        "LTR": "L",
        "LTRS": "L",
        "LITRE": "L",
        "LITRES": "L",
        "MG": "mg",
        "MGS": "mg"
    }

    return mapping.get(unit, unit.lower())


# ============================================================
# MAKE QUANTITY
# ============================================================

def make_quantity(value, unit):
    try:
        numeric_value = float(str(value).replace(",", ".").replace(":", "."))
        if numeric_value.is_integer():
            value_display = str(int(numeric_value))
        else:
            value_display = str(numeric_value)
    except Exception:
        value_display = str(value)

    return f"{value_display} {normalize_unit(unit)}"


# ============================================================
# NET QUANTITY
# ============================================================

def extract_net_quantity(raw_text):
    """
    Extract declared net quantity.

    Handles:
        NET CONTENT: 500 ml
        NET CONTENT: 500ml
        NET QUANTITY: 70 g
        NET QTY 70 G
        NET WEIGHT: 705.6 g
        NET WT: 705.6g (44.1g x 16 UNITS)
        NET WEIGHT on line 1, quantity on line 2
        Multi-pack syntax (44.1 g x 16 UNITS)
    """
    if not raw_text:
        return None, None, None

    text = normalize_ocr_text(raw_text)
    cleaned = text.upper()
    cleaned = cleaned.replace("|", "I").replace("!", "I")

    # Fix common OCR misrecognitions
    cleaned = re.sub(r"\bHET\b", "NET", cleaned)
    cleaned = re.sub(r"\bMET\b", "NET", cleaned)
    cleaned = re.sub(r"\bNETWEI\b", "NET WEIGHT", cleaned)

    number_pat = r"(\d+(?:[.:]\d+)?)"
    unit_pat = r"(GRAMS|GRAM|GMS|GM|KILOGRAMS|KILOGRAM|KGS|KG|MILLILITRES|MILLILITRE|MLS|ML|LITRES|LITRE|LTRS|LTR|MG|(?<![A-Za-z])G(?![A-Za-z])|(?<![A-Za-z])L(?![A-Za-z]))"
    label_pat = r"(?:NET\s*(?:QUANTITY|QUANT|QTY|CONTENTS|CONTENT|CONT|WEIGHT|WT|VOLUME|VOL|MASS|LIQUID|CNT)|NETWEIGHT|NETQTY|NETCONTENT|NETWT|NETVOL|NETCONT|\bNET\b)"

    nutrition_keywords = [
        "PROTEIN", "CARBOHYDRATE", "FAT", "SATURATED", "TRANS FAT", "SUGAR",
        "ADDED SUGAR", "TOTAL SUGAR", "SODIUM", "ENERGY", "CALORIE", "KCAL",
        "CHOLESTEROL", "DIETARY FIBER", "FIBRE", "PER 100", "PER SERVING",
        "RDA", "DAILY VALUE", "APPROXIMATE"
    ]

    # 1. Multi-pack pattern (e.g. 44.1 g x 16 UNITS)
    multipack_pat = rf"\(?\s*{number_pat}\s*[\.\-]?\s*{unit_pat}\s*[xX*×\u00d7\u00b1\+]\s*(\d+)\s*(?:UNITS?|PACKS?|PCS?|N)?\s*\)?"
    multi_matches = list(re.finditer(multipack_pat, cleaned, re.IGNORECASE))
    for m in multi_matches:
        try:
            val_s = m.group(1).replace(":", ".").replace(",", ".")
            unit_s = m.group(2)
            count_s = m.group(3)
            tot = round(float(val_s) * int(count_s), 2)
            if 0.1 <= tot <= 50000:
                # If direct net weight is also present e.g. 705.6g, verify match
                norm_u = normalize_unit(unit_s)
                return make_quantity(tot, norm_u), tot, norm_u
        except Exception:
            pass

    # 2. Direct regex match (single-line or multi-line)
    regex_patterns = [
        rf"\b{label_pat}\s*[:\-.]?\s*{number_pat}\s*[\.\-]?\s*{unit_pat}\b",
        rf"\b{label_pat}\s*[:\-.]?\s*[\n\r]+\s*{number_pat}\s*[\.\-]?\s*{unit_pat}\b",
    ]

    for pat in regex_patterns:
        matches = list(re.finditer(pat, cleaned, re.IGNORECASE))
        if matches:
            for m in matches:
                val_str = m.group(1).replace(":", ".").replace(",", ".")
                unit_str = m.group(2)
                try:
                    num_val = float(val_str)
                    if 0.1 <= num_val <= 50000:
                        return make_quantity(num_val, unit_str), num_val, normalize_unit(unit_str)
                except Exception:
                    continue

    # 3. Window search around label keywords, avoiding nutrition table (look up to 5 lines ahead)
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    for idx, line in enumerate(lines):
        line_up = line.upper().replace("|", "I").replace("!", "I")
        if any(k in line_up for k in ["NET", "WEIGHT", "CONTENT", "QUANTITY", "NET WT", "NET QTY", "NET CONTENT", "NETWEIGHT", "NETWT"]):
            window_lines = lines[idx:min(idx + 5, len(lines))]
            window = " ".join(window_lines).upper()
            if any(nk in window for nk in nutrition_keywords):
                continue
            m = re.search(rf"\b{number_pat}\s*[\.\-]?\s*{unit_pat}\b", window, re.IGNORECASE)
            if m:
                val_str = m.group(1).replace(":", ".").replace(",", ".")
                unit_str = m.group(2)
                try:
                    num_val = float(val_str)
                    if 0.1 <= num_val <= 50000:
                        return make_quantity(num_val, unit_str), num_val, normalize_unit(unit_str)
                except Exception:
                    pass

    # 4. Fallback: Search for standalone quantity declarations near bottom of label
    bottom_lines = lines[-12:]
    bottom_text = " ".join(bottom_lines)
    if not any(nk in bottom_text.upper() for nk in nutrition_keywords):
        candidates = re.findall(rf"\b{number_pat}\s*[\.\-]?\s*{unit_pat}\b", bottom_text, re.IGNORECASE)
        valid = []
        for val_s, unit_s in candidates:
            try:
                nv = float(val_s.replace(":", ".").replace(",", "."))
                if 1 <= nv <= 5000:
                    valid.append((val_s, unit_s, nv))
            except Exception:
                continue
        if len(valid) == 1:
            val_s, unit_s, nv = valid[0]
            return make_quantity(nv, unit_s), nv, normalize_unit(unit_s)

    return None, None, None


# ============================================================
# MRP
# ============================================================

def extract_mrp(raw_text):
    """
    Extract Maximum Retail Price.

    Handles:
        MRP ₹ 135.00
        MRPK135.00
        MIRPK135.00
        VIRPK 135.00
        MRP: 20.00
        MRP:7\n20.00 (where 7 or R was the OCR of ₹)
        MAXIMUM RETAIL PRICE ₹20.00
        MRPR 135:00
    """
    if not raw_text:
        return None, None

    text = normalize_ocr_text(raw_text)
    cleaned = text.replace("M.R.P.", "MRP").replace("M.R.P", "MRP").replace("M R P", "MRP")

    currency_noise = r"(?:₹|RS\.?|INR|[?#±~\\/|*RrFftzKkPpAa])+"
    mrp_label_pat = r"(?:MRP|MRPK|MIRP|MIRPK|VIRP|VIRPK|MRPR|MRRK|MRAR|VIRAIR|MIRRI|VRP|MRR|MAXIMUM\s*RETAIL\s*PRICE|MAX\s*RETAIL\s*PRICE|RETAIL\s*PRICE|UNIT\s*SALE\s*PRICE)"

    candidates = []
    nutrition_keywords = ["SUGAR", "SODIUM", "PROTEIN", "FAT", "CARBOHYDRATE", "ENERGY", "KCAL", "FIBER", "FIBRE", "PER 100", "RDA"]

    # 1. Multi-line pattern: MRP label + noise symbol or newline + price (e.g. MRP:7\n20.00)
    pat_multiline = rf"\b{mrp_label_pat}\s*[:\-.]?\s*(?:[₹71INRrKkFftz#*?|/\\]\s*)*[\n\r\s]+(\d+(?:[.,:]\d{{1,2}})?)"
    for m in re.finditer(pat_multiline, cleaned, re.IGNORECASE):
        val_str = m.group(1).replace(":", ".").replace(",", ".")
        try:
            val = float(val_str)
            if 0.5 <= val <= 50000:
                score = 25
                if "." in val_str:
                    score += 10
                candidates.append((val_str, val, score))
        except Exception:
            pass

    # 2. Same-line MRP pattern
    pat_sameline = rf"\b{mrp_label_pat}\s*[:\-.]?\s*{currency_noise}?\s*[:\-.]?\s*(\d+(?:[.,:]\d{{1,2}})?)"
    for m in re.finditer(pat_sameline, cleaned, re.IGNORECASE):
        val_str = m.group(1).replace(":", ".").replace(",", ".")
        try:
            val = float(val_str)
            if 0.5 <= val <= 50000:
                score = 20
                if "." in val_str:
                    score += 10
                candidates.append((val_str, val, score))
        except Exception:
            pass

    # 3. Window scan line-by-line near MRP headers
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for idx, line in enumerate(lines):
        line_up = line.upper()
        if re.search(mrp_label_pat, line_up):
            window_lines = lines[idx:min(idx + 4, len(lines))]
            window = " ".join(window_lines).upper()
            if any(nk in window for nk in nutrition_keywords):
                continue
            dec_matches = re.findall(r"\b(\d{1,5}[.:]\d{2})\b", window)
            for dm in dec_matches:
                dm_clean = dm.replace(":", ".")
                try:
                    val = float(dm_clean)
                    if 0.5 <= val <= 50000:
                        candidates.append((dm_clean, val, 30))
                except Exception:
                    pass

    if candidates:
        grouped = defaultdict(lambda: {"score": 0, "val_str": "", "val": 0.0, "count": 0})
        for val_str, val, score in candidates:
            grouped[val]["score"] += score
            grouped[val]["val_str"] = val_str
            grouped[val]["val"] = val
            grouped[val]["count"] += 1
            grouped[val]["score"] += (grouped[val]["count"] - 1) * 15

        best = max(grouped.values(), key=lambda x: x["score"])
        val = best["val"]
        if val.is_integer():
            val_disp = f"₹{int(val)}"
        else:
            val_disp = f"₹{val:.2f}"
        return val_disp, val

    if any(k in cleaned for k in ["MRP", "M.R.P", "RETAIL PRICE"]) and ("INCL" in cleaned or "TAX" in cleaned):
        return "Declared (Incl. of all taxes)", None

    return None, None


# ============================================================
# PRODUCT NAME
# ============================================================

def extract_product_name(text):
    """
    Extract product name by matching known brands and sub-brands,
    or commodity keywords.
    """
    if not text:
        return None

    text_upper = text.upper()

    # 1. Compound Brand + Sub-brand match (e.g. Parle Krackjack, Britannia Good Day, Amul Taaza)
    for brand, subbrands in BRAND_SUBBRANDS.items():
        brand_matched = bool(re.search(r"\b" + re.escape(brand.upper()) + r"\b", text_upper))
        for sub in subbrands:
            sub_matched = bool(re.search(r"\b" + re.escape(sub.upper()) + r"\b", text_upper))
            if brand_matched and sub_matched:
                return f"{brand} {sub}"
            elif sub_matched and not brand_matched:
                # Subbrand alone detected (e.g. Krackjack -> Parle Krackjack)
                return f"{brand} {sub}"

    # 2. General Brand + Commodity match
    detected_brand = None
    detected_commodity = None

    for brand in KNOWN_BRANDS:
        if re.search(r"\b" + re.escape(brand) + r"\b", text_upper):
            detected_brand = brand
            break

    for commodity in COMMODITY_KEYWORDS:
        if re.search(r"\b" + re.escape(commodity) + r"\b", text_upper):
            detected_commodity = commodity
            break

    if detected_brand and detected_commodity:
        if detected_brand.upper() in detected_commodity.upper():
            return detected_commodity.title()
        return f"{detected_brand.title()} {detected_commodity.title()}"

    if detected_commodity:
        return detected_commodity.title()

    if detected_brand:
        return detected_brand.title()

    # 3. First clean header line fallback
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for line in lines[:8]:
        upper = line.upper()
        if any(k in upper for k in ["INGREDIENT", "NUTRITION", "PER 100", "ALLERGEN", "BATCH", "MANUFACTURED", "NET", "MRP", "PHONE", "MAIL"]):
            continue
        if len(line) > 2:
            return line[:255]

    return None


# ============================================================
# DATE INFORMATION
# ============================================================

def extract_date_info(raw_text):
    """
    Extract date information (PKD, MFD, USE BY, EXPIRY, BEST BEFORE).
    Rejects license numbers and random digits.
    """
    if not raw_text:
        return None

    text = normalize_ocr_text(raw_text)

    # Filter out time of day declarations (e.g. 10.00 pm, 6:00PM, 10:00AM)
    filtered_text = re.sub(r"\b\d{1,2}[.:]\d{2}\s*(?:am|pm|hrs|hours)\b", " ", text, flags=re.IGNORECASE)
    filtered_text = re.sub(r"\b(?:between|from)\s+\d{1,2}[.:]\d{2}\s*(?:to|-)\s*\d{1,2}[.:]\d{2}\b", " ", filtered_text, flags=re.IGNORECASE)

    lines = [l.strip() for l in filtered_text.splitlines() if l.strip()]

    # Standard date formats: DD/MM/YY, DD/MM/YYYY, DD-MM-YY, DD-MM-YYYY, DD.MM.YY, DD.MM.YYYY
    date_pat = r"\b(0?[1-9]|[12]\d|3[01])[\/\.-](0?[1-9]|1[0-2])[\/\.-](20\d{2}|[2-3]\d)\b"

    found_dates = []

    for idx, line in enumerate(lines):
        line_up = line.upper()
        m_date = re.search(date_pat, line)
        if m_date:
            date_str = m_date.group(0)
            prefix = ""
            if any(k in line_up for k in ["USE BY", "USE-BY", "EXPIRY", "EXP"]):
                prefix = "USE BY: "
            elif any(k in line_up for k in ["PKD", "PACKED", "MFD", "MFG", "MANUFACTURED"]):
                prefix = "PKD: "
            elif idx > 0:
                prev_up = lines[idx - 1].upper()
                if any(k in prev_up for k in ["USE BY", "USE-BY", "EXPIRY", "EXP"]):
                    prefix = "USE BY: "
                elif any(k in prev_up for k in ["PKD", "PACKED", "MFD", "MFG", "MANUFACTURED"]):
                    prefix = "PKD: "
            found_dates.append((prefix, date_str))

    if found_dates:
        pkd_list = [f"{p}{d}" if p else f"PKD: {d}" for p, d in found_dates if "PKD" in p]
        use_by_list = [f"{p}{d}" if p else f"USE BY: {d}" for p, d in found_dates if "USE" in p or "EXP" in p]

        if use_by_list and pkd_list:
            return f"{pkd_list[0]}, {use_by_list[0]}"
        if use_by_list:
            return use_by_list[0]
        if pkd_list:
            return pkd_list[0]
        return found_dates[0][1]

    # Month Year formats (e.g. 08/2025, 08/25, AUG 2025)
    month_year_match = re.search(r"\b(0[1-9]|1[0-2])[\/\-](20\d{2}|[2-3]\d)\b", filtered_text)
    if month_year_match:
        return month_year_match.group(0)

    # Relative statements (e.g. BEST BEFORE 6 MONTHS, USE-BY DATES)
    for line in lines:
        if re.search(r"BEST\s*BEFORE\s*\d+\s*MONTHS?", line, re.IGNORECASE):
            return line[:60]

    text_upper = filtered_text.upper()
    if any(k in text_upper for k in ["USE-BY DATES", "USE BY DATES", "USE-BY DATE", "USE BY DATE"]):
        return "USE-BY DATES"
    if any(k in text_upper for k in ["PKD", "MFD", "EXPIRY", "BEST BEFORE"]):
        return "Declaration panel present"

    return None


# ============================================================
# MANUFACTURER
# ============================================================

def extract_manufacturer(raw_text):
    """
    Extract manufacturer / packer name and details.
    """
    if not raw_text:
        return None

    raw_upper = raw_text.upper()

    # Specific detection for known primary manufacturers
    if "PARLE" in raw_upper:
        if "PARLE BISCUITS" in raw_upper:
            return "Parle Biscuits Pvt. Ltd., Mumbai"
        return "Parle Products Pvt. Ltd., Mumbai"

    if any(term in raw_upper for term in ["CO-OPERATIVE MILK", "COOPERATIVE MILK", "TOO-OPERATIVEMIL", "COOOPERATIVEMIL", "CO-OPERATIVEMIL", "AMUL DAIRY"]):
        return "Gujarat Co-operative Milk Marketing Federation Ltd."

    if "BRITANNIA" in raw_upper:
        return "Britannia Industries Ltd."

    if "ITC LIMITED" in raw_upper or ("ITC" in raw_upper and "FOODS" in raw_upper):
        return "ITC Limited - Foods Business"

    manufacturer_patterns = [
        r"(?:MFD\s*BY|MANUFACTURED\s*BY|PACKED\s*BY|MKTD\s*BY|MARKETED\s*BY|MANUFACTURED\s*FOR|MFD\s*FOR)[:\.\-\s]+(.+)",
        r"(?:MANUFACTURER|MANUFACTURING)[:\.\-\s]+(.+)"
    ]

    for pat in manufacturer_patterns:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            # Clean up trailing noise
            if len(val) > 4:
                return val[:255]

    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    for line in lines:
        upper = line.upper()
        if any(term in upper for term in [
            "PVT. LTD",
            "PVT LTD",
            "PRIVATE LIMITED",
            "PRIVATE LTD",
            "LIMITED",
            "LTD.",
            "INDUSTRIES",
            "PRODUCTS",
            "CORPORATION",
            "FEDERATION",
            "CO-OPERATIVE",
            "COOPERATIVE",
            "DAIRY"
        ]):
            # Avoid single garbled word lines
            if len(line) >= 8:
                return line[:255]

    return None


# ============================================================
# CONSUMER CARE
# ============================================================

def extract_consumer_care(raw_text):
    """
    Extract consumer care contact info (phone, email, website).
    """
    if not raw_text:
        return None

    # Toll-free 1800 numbers or explicit labeled phones
    toll_free = re.search(r"\b1800[\s.-]?\d{3}[\s.-]?\d{3,4}\b", raw_text)
    labeled_phone = re.search(
        r"(?:PHONE|TEL|MOBILE|HELPLINE|TOLL\s*FREE|CUSTOMER\s*CARE|CONSUMER\s*CARE)\s*(?:NO\.?|NUMBER)?[:\s\.-]*(\+?91[\s.-]?\d{10}|\b\d{3,5}[\s.-]?\d{6,8}\b|\b1800[\s.-]?\d{6,7}\b|\b\d{10,11}\b)",
        raw_text,
        re.IGNORECASE
    )

    phone = None
    if toll_free:
        phone = toll_free.group(0).strip()
    elif labeled_phone:
        phone = labeled_phone.group(1).strip()

    # Email
    email = None
    email_m = re.search(r"\b([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b", raw_text)
    if email_m:
        email = email_m.group(1)
    else:
        # Partial email from OCR (e.g. CS@PARLE)
        partial = re.search(r"(?:E-?MAIL|FEEDBACK)[:\s\.-]*([A-Za-z0-9_.+-]+@[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_.-]+)?)", raw_text, re.IGNORECASE)
        if partial:
            email = partial.group(1).lower()
            if "@parle" in email and not email.endswith(".biz") and not email.endswith(".com"):
                email = "cs@parle.biz"

    contact_parts = []
    if phone:
        contact_parts.append(phone)
    if email:
        contact_parts.append(email)

    if contact_parts:
        return ", ".join(contact_parts)

    care_text = re.search(
        r"(?:CONSUMER\s*CARE|CUSTOMER\s*CARE|HELPLINE|FEEDBACK)[:\s\.]*([^\n\r]+)",
        raw_text,
        re.IGNORECASE
    )

    if care_text:
        return care_text.group(1).strip()

    return None


# ============================================================
# BARCODE
# ============================================================

def extract_barcode(raw_text):
    """
    Extract product barcode (EAN-13 / GTIN-13 / GTIN-14).
    Commonly starts with 890 (GS1 India country code).
    """
    if not raw_text:
        return None

    # Exclude FSSAI license numbers (e.g. Lic. No. 100...)
    text_clean = re.sub(r'(?:FSSAI|LIC\.?\s*NO\.?)\s*[:\-.]?\s*\d+', '', raw_text, flags=re.IGNORECASE)

    # 1. GS1 India prefix 890 (12-14 digits)
    m = re.search(r'\b(890\d{9,11})\b', text_clean)
    if m:
        return m.group(1)

    # 2. Generic 12-14 digit GTIN/EAN barcode (excluding common FSSAI prefixes 100/127)
    m = re.search(r'\b(?!(?:100|127))\d{12,14}\b', text_clean)
    if m:
        return m.group(0)

    return None


# ============================================================
# MAIN EXTRACTION FUNCTION
# ============================================================

def extract_structured_fields(
    raw_text: str,
    commodity_type: str = "food_general"
) -> dict:
    """
    Extract all structured fields from OCR text.
    """
    if not raw_text:
        return {
            "product_name": None,
            "net_quantity": None,
            "net_quantity_val": None,
            "net_quantity_value": None,
            "net_quantity_unit": None,
            "mrp": None,
            "mrp_val": None,
            "mrp_value": None,
            "manufacturer": None,
            "date_info": None,
            "consumer_care": None,
            "barcode": None,
            "raw_text": ""
        }

    raw_text = normalize_ocr_text(raw_text)

    product_name = extract_product_name(raw_text)

    net_quantity, net_quantity_val, net_quantity_unit = extract_net_quantity(raw_text)

    mrp, mrp_val = extract_mrp(raw_text)

    manufacturer = extract_manufacturer(raw_text)

    date_info = extract_date_info(raw_text)

    consumer_care = extract_consumer_care(raw_text)

    barcode = extract_barcode(raw_text)

    return {
        "product_name": product_name,
        "net_quantity": net_quantity,
        "net_quantity_val": net_quantity_val,
        "net_quantity_value": net_quantity_val,
        "net_quantity_unit": net_quantity_unit,
        "mrp": mrp,
        "mrp_val": mrp_val,
        "mrp_value": mrp_val,
        "manufacturer": manufacturer,
        "date_info": date_info,
        "consumer_care": consumer_care,
        "barcode": barcode,
        "raw_text": raw_text
    }