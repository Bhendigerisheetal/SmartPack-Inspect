"""
AI Vision Service
==================

SmartPack Inspect

Purpose:
    Use a multimodal AI model to inspect a real packaged-product image.

Main targets:
    - Product Name
    - Net Quantity
    - MRP
    - Manufacturer / Packer
    - MFD / EXP / Best Before
    - Consumer Care

IMPORTANT:
    AI must NOT invent values.

Architecture:

    Original Image
          |
          +----------------------+
          |                      |
          v                      v
    Full Image              Targeted Crops
                               |
                +--------------+--------------+
                |              |              |
                v              v              v
             Quantity         MRP          Other text
                |
                v
          Vision Model
                |
                v
       Validation / Cleaning
                |
                v
          Structured JSON
"""

import os
import json
import base64
import mimetypes
import re
import tempfile

from PIL import Image, ImageEnhance, ImageFilter


# ============================================================
# OPENAI SDK
# ============================================================

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# ============================================================
# MODEL CONFIGURATION
# ============================================================

AI_MODEL = os.getenv(
    "SMARTPACK_AI_MODEL",
    "gpt-5"
)


# ============================================================
# CONSTANTS
# ============================================================

MAX_CONFIDENCE = 100


# ============================================================
# EMPTY RESULT
# ============================================================

def empty_result(
    status="AI_UNAVAILABLE",
    message=""
):
    """
    Return a completely safe empty AI result.
    """

    return {

        "status": status,

        "message": message,

        "ai_available": False,

        "model": AI_MODEL,

        "product_name": None,

        "net_quantity": None,
        "net_quantity_value": None,
        "net_quantity_unit": None,

        "mrp": None,
        "mrp_value": None,

        "manufacturer": None,

        "date_information": None,

        "consumer_care": None,

        "net_quantity_confidence": 0,

        "mrp_confidence": 0,

        "overall_confidence": 0,

        "inspection_note": "",

        # Evidence fields
        "net_quantity_evidence": None,

        "mrp_evidence": None,

        "product_evidence": None,

        "manufacturer_evidence": None,

        "date_evidence": None,
    }


# ============================================================
# IMAGE → BASE64 DATA URL
# ============================================================

def image_to_data_url(image_path):
    """
    Convert an image file to a base64 data URL.
    """

    if not image_path:

        raise ValueError(
            "Image path is empty."
        )

    if not os.path.exists(image_path):

        raise FileNotFoundError(
            f"Image does not exist: {image_path}"
        )

    mime_type, _ = mimetypes.guess_type(
        image_path
    )

    if not mime_type:

        mime_type = "image/jpeg"

    with open(
        image_path,
        "rb"
    ) as image_file:

        encoded = base64.b64encode(
            image_file.read()
        ).decode("utf-8")

    return (
        f"data:{mime_type};base64,{encoded}"
    )


# ============================================================
# CREATE HIGH-RESOLUTION CROPS
# ============================================================

def create_targeted_crops(image_path):
    """
    Create several enlarged crops from the package image.

    These crops are especially useful for:
        - Net Quantity
        - MRP
        - MFD / EXP
        - Manufacturer
    """

    image = Image.open(
        image_path
    ).convert("RGB")

    width, height = image.size

    crop_paths = []

    temp_dir = tempfile.mkdtemp(
        prefix="smartpack_ai_"
    )

    # --------------------------------------------------------
    # FULL IMAGE
    # --------------------------------------------------------

    full_path = os.path.join(
        temp_dir,
        "full.jpg"
    )

    image.save(
        full_path,
        quality=95
    )

    crop_paths.append(
        (
            "FULL PACKAGE IMAGE",
            full_path
        )
    )

    # --------------------------------------------------------
    # BOTTOM REGION
    #
    # Usually contains:
    #   NET QUANTITY
    #   barcode
    #   MRP
    # --------------------------------------------------------

    bottom_top = int(
        height * 0.55
    )

    bottom_crop = image.crop(
        (
            0,
            bottom_top,
            width,
            height
        )
    )

    bottom_crop = bottom_crop.resize(
        (
            bottom_crop.width * 3,
            bottom_crop.height * 3
        ),
        Image.Resampling.LANCZOS
    )

    bottom_crop = ImageEnhance.Contrast(
        bottom_crop
    ).enhance(1.4)

    bottom_crop = ImageEnhance.Sharpness(
        bottom_crop
    ).enhance(1.5)

    bottom_path = os.path.join(
        temp_dir,
        "bottom.jpg"
    )

    bottom_crop.save(
        bottom_path,
        quality=98
    )

    crop_paths.append(
        (
            "BOTTOM / NET QUANTITY / MRP AREA",
            bottom_path
        )
    )

    # --------------------------------------------------------
    # LEFT LOWER REGION
    #
    # Useful for:
    #   Net quantity
    #   MRP
    #   manufacturer
    # --------------------------------------------------------

    left_lower = image.crop(
        (
            0,
            int(height * 0.35),
            int(width * 0.70),
            height
        )
    )

    left_lower = left_lower.resize(
        (
            left_lower.width * 3,
            left_lower.height * 3
        ),
        Image.Resampling.LANCZOS
    )

    left_lower = ImageEnhance.Contrast(
        left_lower
    ).enhance(1.5)

    left_lower = ImageEnhance.Sharpness(
        left_lower
    ).enhance(1.7)

    left_path = os.path.join(
        temp_dir,
        "left_lower.jpg"
    )

    left_lower.save(
        left_path,
        quality=98
    )

    crop_paths.append(
        (
            "LEFT LOWER DECLARATION AREA",
            left_path
        )
    )

    # --------------------------------------------------------
    # CENTER / TEXT AREA
    # --------------------------------------------------------

    center = image.crop(
        (
            int(width * 0.05),
            int(height * 0.20),
            int(width * 0.95),
            int(height * 0.80)
        )
    )

    center = center.resize(
        (
            center.width * 3,
            center.height * 3
        ),
        Image.Resampling.LANCZOS
    )

    center = ImageEnhance.Contrast(
        center
    ).enhance(1.4)

    center = ImageEnhance.Sharpness(
        center
    ).enhance(1.5)

    center_path = os.path.join(
        temp_dir,
        "center.jpg"
    )

    center.save(
        center_path,
        quality=98
    )

    crop_paths.append(
        (
            "CENTER TEXT / MANUFACTURER / DATE AREA",
            center_path
        )
    )

    return crop_paths


# ============================================================
# VISION PROMPT
# ============================================================

def build_vision_prompt(
    commodity_type="food_general"
):
    """
    Strong prompt designed specifically for SmartPack.
    """

    return f"""
You are the AI vision inspection engine of
SMARTPACK INSPECT.

You are inspecting a REAL photograph of a packaged
consumer product.

Commodity:
{commodity_type}

IMPORTANT:

You have been given:

1. The complete package image.
2. Enlarged targeted crops of the package.

The targeted crops exist because small printed declarations
can be difficult to read in the complete image.

Your job is NOT to describe the image.

Your job is to extract ONLY legally relevant package
declarations that are visibly readable.

============================================================
FIELD 1 — PRODUCT NAME
============================================================

Find the actual product/commodity name.

Do NOT confuse:
- brand name
- flavor
- slogan
- ingredient
- nutrition value

If unclear:
return null.

============================================================
FIELD 2 — NET QUANTITY
============================================================

THIS IS THE HIGHEST PRIORITY FIELD.

Look extremely carefully at:

- bottom of packet
- bottom-left area
- bottom-right area
- words:
  NET QUANTITY
  NET QTY
  NET WEIGHT
  NET WT
  NET.WT
  NET CONTENT

Also inspect declarations such as:

70 g
70g
100 g
200 g
500 g
1 kg
500 ml

If you can visually read:

NET QUANTITY: 70 g

return:

net_quantity = "70 g"
net_quantity_value = 70
net_quantity_unit = "g"

Do NOT confuse it with:
- barcode digits
- nutrition values
- serving size
- batch number
- phone number
- date
- percentage

If a number appears without a clear quantity context,
DO NOT automatically call it net quantity.

============================================================
FIELD 3 — MRP
============================================================

Look carefully for:

MRP
M.R.P.
M R P
Maximum Retail Price
Rs.
₹
INR

MRP is commonly printed near:
- bottom seal
- barcode
- side panel
- declaration panel

Examples:

MRP ₹10
MRP Rs. 10
MRP: Rs 20.00

If clearly readable:

mrp = "₹10"
mrp_value = 10

If NOT clearly readable:

mrp = null
mrp_value = null

NEVER invent MRP.

Do NOT confuse MRP with:
- barcode
- phone number
- batch number
- nutrition number
- manufacturing date
- expiry date

============================================================
FIELD 4 — MANUFACTURER / PACKER
============================================================

Look for:

Manufactured by
Manufactured & Marketed by
Manufactured and Marketed by
Packed by
Marketed by
Mfd. by
Pkd. by

Return only text that is actually readable.

============================================================
FIELD 5 — DATE
============================================================

Look for:

MFD
MFG
PKD
EXP
BEST BEFORE
USE BY

Do NOT convert unrelated text into a date.

If the text is unclear:
return null.

============================================================
FIELD 6 — CONSUMER CARE
============================================================

Look for:

Consumer Care
Customer Care
Helpline
Phone
Email
Contact

Return only if readable.

============================================================
CRITICAL ANTI-HALLUCINATION RULES
============================================================

1. NEVER invent a value.

2. NEVER guess.

3. NEVER use product knowledge to fill a field.

4. NEVER convert random OCR-looking text into a field.

5. If text is unreadable, return null.

6. If two images disagree, prefer the image where the
   declaration is actually readable.

7. For Net Quantity, physical proximity to the words
   "NET QUANTITY", "NET WT", etc. is essential.

8. For MRP, physical proximity to MRP/Rs/₹ is essential.

9. Barcode numbers are NEVER MRP.

10. Phone numbers are NEVER MRP.

11. Nutrition numbers are NEVER MRP.

12. Do not treat words such as:
    "TOMATO", "TOMAFO", "MFDCUSEBY"
    as valid declarations unless they are actually
    readable and contextually associated with that field.

============================================================
CONFIDENCE
============================================================

Use confidence 0-100.

90-100:
Clearly readable.

70-89:
Readable but slightly blurred.

40-69:
Partially readable.

0-39:
Do not return a value.

For Net Quantity and MRP:

If confidence < 60:
return null.

============================================================
EVIDENCE
============================================================

For every important extracted field, return the exact
short visual text that supports the decision.

Example:

net_quantity = "70 g"

net_quantity_evidence =
"NET QUANTITY: 70 g"

Do NOT fabricate evidence.

============================================================
FINAL RULE
============================================================

If the value is not visibly readable in the image,
RETURN NULL.

Do not guess.

Return ONLY structured JSON.
"""


# ============================================================
# JSON SCHEMA
# ============================================================

SMARTPACK_SCHEMA = {

    "type": "object",

    "properties": {

        "product_name": {
            "type": ["string", "null"]
        },

        "net_quantity": {
            "type": ["string", "null"]
        },

        "net_quantity_value": {
            "type": ["number", "null"]
        },

        "net_quantity_unit": {
            "type": ["string", "null"]
        },

        "mrp": {
            "type": ["string", "null"]
        },

        "mrp_value": {
            "type": ["number", "null"]
        },

        "manufacturer": {
            "type": ["string", "null"]
        },

        "date_information": {
            "type": ["string", "null"]
        },

        "consumer_care": {
            "type": ["string", "null"]
        },

        "net_quantity_confidence": {
            "type": "number"
        },

        "mrp_confidence": {
            "type": "number"
        },

        "overall_confidence": {
            "type": "number"
        },

        "net_quantity_evidence": {
            "type": ["string", "null"]
        },

        "mrp_evidence": {
            "type": ["string", "null"]
        },

        "product_evidence": {
            "type": ["string", "null"]
        },

        "manufacturer_evidence": {
            "type": ["string", "null"]
        },

        "date_evidence": {
            "type": ["string", "null"]
        },

        "inspection_note": {
            "type": "string"
        }
    },

    "required": [

        "product_name",

        "net_quantity",
        "net_quantity_value",
        "net_quantity_unit",

        "mrp",
        "mrp_value",

        "manufacturer",

        "date_information",

        "consumer_care",

        "net_quantity_confidence",

        "mrp_confidence",

        "overall_confidence",

        "net_quantity_evidence",

        "mrp_evidence",

        "product_evidence",

        "manufacturer_evidence",

        "date_evidence",

        "inspection_note"
    ],

    "additionalProperties": False
}


# ============================================================
# VALIDATE QUANTITY
# ============================================================

def validate_quantity(
    quantity,
    value,
    unit,
    confidence
):
    """
    Reject obviously bad AI quantity values.
    """

    if not quantity and not value:
        return None, None, None

    try:

        confidence = float(
            confidence or 0
        )

    except Exception:

        confidence = 0

    if confidence < 60:

        return None, None, None

    # --------------------------------------------------------
    # Try to extract number + unit from the quantity string
    # (AI may return "70 g", "70g", "NET QUANTITY: 70 g", etc.)
    # --------------------------------------------------------

    text = str(quantity or "").strip()

    # Accept all common mass/volume unit variants
    pattern = re.compile(
        r"(\d+(?:\.\d+)?)"
        r"\s*"
        r"(grams|gram|gms|gm|kg|mg|"
        r"millilitres|millilitre|litres|litre|ltr|ml|"
        r"(?<![a-z])g(?![a-z])|(?<![a-z])l(?![a-z]))",
        re.IGNORECASE
    )

    match = pattern.search(text)

    if match:

        number = float(match.group(1))
        detected_unit = match.group(2).lower()

    else:

        # --------------------------------------------------------
        # Fallback: use the separate value + unit AI fields
        # --------------------------------------------------------

        try:
            number = float(value) if value else None
        except Exception:
            number = None

        detected_unit = str(unit or "").strip().lower()

        if number is None or not detected_unit:
            return None, None, None

    # Sanity check
    if number <= 0:

        return None, None, None

    if number > 10000:

        return None, None, None

    # Normalize unit
    unit_map = {
        "grams": "g", "gram": "g", "gms": "g", "gm": "g",
        "kilograms": "kg", "kilogram": "kg", "kgs": "kg",
        "millilitres": "ml", "millilitre": "ml", "mls": "ml",
        "litres": "l", "litre": "l", "ltr": "l",
    }
    detected_unit = unit_map.get(detected_unit, detected_unit)

    # Normalize integer
    if float(number).is_integer():

        number = int(number)

    return (
        f"{number} {detected_unit}",
        number,
        detected_unit
    )



# ============================================================
# VALIDATE MRP
# ============================================================

def validate_mrp(
    mrp,
    value,
    confidence
):
    """
    Reject bad MRP values.

    MRP should be a realistic positive currency amount.
    """

    if not mrp:
        return None, None

    try:

        confidence = float(
            confidence or 0
        )

    except Exception:

        confidence = 0

    if confidence < 60:

        return None, None

    text = str(
        mrp
    ).strip()

    # Find numeric amount
    match = re.search(
        r"(?:₹|rs\.?|inr)?\s*"
        r"(\d+(?:\.\d{1,2})?)",
        text,
        re.IGNORECASE
    )

    if not match:

        return None, None

    amount = float(
        match.group(1)
    )

    if amount <= 0:

        return None, None

    if amount > 100000:

        return None, None

    if amount.is_integer():

        amount_display = str(
            int(amount)
        )

    else:

        amount_display = (
            f"{amount:.2f}"
        )

    # Keep currency symbol if AI supplied one
    if "₹" in text:

        display = (
            f"₹{amount_display}"
        )

    elif re.search(
        r"\brs\b|\brs\.",
        text,
        re.IGNORECASE
    ):

        display = (
            f"Rs. {amount_display}"
        )

    else:

        display = (
            f"₹{amount_display}"
        )

    return (
        display,
        amount
    )


# ============================================================
# CLEAN PRODUCT NAME
# ============================================================

def clean_product_name(
    product_name,
    confidence
):
    """
    Reject obvious OCR garbage.
    """

    if not product_name:

        return None

    try:

        confidence = float(
            confidence or 0
        )

    except Exception:

        confidence = 0

    if confidence < 45:

        return None

    value = str(
        product_name
    ).strip()

    if len(value) < 2:

        return None

    # Reject strings that look like OCR corruption
    garbage_patterns = [

        r"^tomafo$",

        r"^mfdcuseby",

        r"^mfd.*useby.*$",

        r"^[^a-zA-Z]+$",

    ]

    for pattern in garbage_patterns:

        if re.match(
            pattern,
            value,
            re.IGNORECASE
        ):

            return None

    return value


# ============================================================
# NORMALIZE AI RESULT
# ============================================================

def normalize_ai_result(
    ai_data
):
    """
    Clean and validate the model response.
    """

    if not isinstance(
        ai_data,
        dict
    ):

        raise ValueError(
            "AI returned invalid JSON object."
        )

    # --------------------------------------------------------
    # Confidence
    # --------------------------------------------------------

    try:

        nq_conf = float(
            ai_data.get(
                "net_quantity_confidence",
                0
            )
        )

    except Exception:

        nq_conf = 0

    try:

        mrp_conf = float(
            ai_data.get(
                "mrp_confidence",
                0
            )
        )

    except Exception:

        mrp_conf = 0

    try:

        overall_conf = float(
            ai_data.get(
                "overall_confidence",
                0
            )
        )

    except Exception:

        overall_conf = 0

    # Clamp
    nq_conf = max(
        0,
        min(
            MAX_CONFIDENCE,
            nq_conf
        )
    )

    mrp_conf = max(
        0,
        min(
            MAX_CONFIDENCE,
            mrp_conf
        )
    )

    overall_conf = max(
        0,
        min(
            MAX_CONFIDENCE,
            overall_conf
        )
    )

    # --------------------------------------------------------
    # PRODUCT
    # --------------------------------------------------------

    product_name = clean_product_name(
        ai_data.get(
            "product_name"
        ),
        overall_conf
    )

    # --------------------------------------------------------
    # QUANTITY
    # --------------------------------------------------------

    quantity, quantity_value, quantity_unit = (
        validate_quantity(

            ai_data.get(
                "net_quantity"
            ),

            ai_data.get(
                "net_quantity_value"
            ),

            ai_data.get(
                "net_quantity_unit"
            ),

            nq_conf
        )
    )

    # --------------------------------------------------------
    # MRP
    # --------------------------------------------------------

    mrp, mrp_value = validate_mrp(

        ai_data.get(
            "mrp"
        ),

        ai_data.get(
            "mrp_value"
        ),

        mrp_conf
    )

    # --------------------------------------------------------
    # Other fields
    # --------------------------------------------------------

    manufacturer = (
        ai_data.get(
            "manufacturer"
        )
    )

    date_information = (
        ai_data.get(
            "date_information"
        )
    )

    consumer_care = (
        ai_data.get(
            "consumer_care"
        )
    )

    # --------------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------------

    return {

        "status": "SUCCESS",

        "message":
            "AI Vision inspection completed.",

        "ai_available": True,

        "model": AI_MODEL,

        "product_name":
            product_name,

        "net_quantity":
            quantity,

        "net_quantity_value":
            quantity_value,

        "net_quantity_unit":
            quantity_unit,

        "mrp":
            mrp,

        "mrp_value":
            mrp_value,

        "manufacturer":
            manufacturer,

        "date_information":
            date_information,

        "consumer_care":
            consumer_care,

        "net_quantity_confidence":
            nq_conf,

        "mrp_confidence":
            mrp_conf,

        "overall_confidence":
            overall_conf,

        "net_quantity_evidence":
            ai_data.get(
                "net_quantity_evidence"
            ),

        "mrp_evidence":
            ai_data.get(
                "mrp_evidence"
            ),

        "product_evidence":
            ai_data.get(
                "product_evidence"
            ),

        "manufacturer_evidence":
            ai_data.get(
                "manufacturer_evidence"
            ),

        "date_evidence":
            ai_data.get(
                "date_evidence"
            ),

        "inspection_note":
            ai_data.get(
                "inspection_note",
                ""
            )
    }


# ============================================================
# MAIN AI VISION FUNCTION
# ============================================================

def inspect_product_image(
    image_path,
    commodity_type="food_general"
):
    """
    Main SmartPack AI Vision function.
    """

    # ========================================================
    # SDK CHECK
    # ========================================================

    if OpenAI is None:

        return empty_result(

            "AI_SDK_NOT_INSTALLED",

            "OpenAI Python SDK is not installed."
        )

    # ========================================================
    # API KEY
    # ========================================================

    api_key = os.getenv(
        "OPENAI_API_KEY"
    )

    if not api_key:

        return empty_result(

            "AI_API_KEY_MISSING",

            "OPENAI_API_KEY environment variable is missing."
        )

    # ========================================================
    # IMAGE CHECK
    # ========================================================

    if not image_path:

        return empty_result(

            "IMAGE_PATH_MISSING",

            "Image path was not supplied."
        )

    if not os.path.exists(
        image_path
    ):

        return empty_result(

            "IMAGE_NOT_FOUND",

            f"Image does not exist: {image_path}"
        )

    # ========================================================
    # CREATE CLIENT
    # ========================================================

    try:

        client = OpenAI(
            api_key=api_key
        )

    except Exception as e:

        return empty_result(

            "AI_CLIENT_ERROR",

            str(e)
        )

    # ========================================================
    # CREATE CROPS
    # ========================================================

    try:

        crops = create_targeted_crops(
            image_path
        )

    except Exception as e:

        return empty_result(

            "CROP_CREATION_ERROR",

            str(e)
        )

    # ========================================================
    # BUILD INPUT CONTENT
    # ========================================================

    content = [

        {
            "type": "input_text",

            "text": build_vision_prompt(
                commodity_type
            )
        }

    ]

    # --------------------------------------------------------
    # Add all images
    # --------------------------------------------------------

    for label, path in crops:

        try:

            data_url = image_to_data_url(
                path
            )

            content.append(

                {
                    "type": "input_text",

                    "text":
                        f"\nIMAGE LABEL: {label}\n"
                        "Inspect this image carefully."
                }

            )

            content.append(

                {
                    "type": "input_image",

                    "image_url": data_url,

                    "detail": "high"
                }

            )

        except Exception as e:

            print(
                "AI image preparation error:",
                e
            )

    # ========================================================
    # CALL VISION MODEL
    # ========================================================

    try:

        response = client.responses.create(

            model=AI_MODEL,

            input=[

                {
                    "role": "user",

                    "content": content
                }

            ],

            text={

                "format": {

                    "type": "json_schema",

                    "name":
                        "smartpack_inspection",

                    "description":
                        "Structured packaged product "
                        "inspection.",

                    "schema":
                        SMARTPACK_SCHEMA,

                    "strict":
                        True
                }
            }
        )

    except Exception as e:

        print(
            "\nSMARTPACK AI REQUEST ERROR:"
        )

        print(
            str(e)
        )

        return empty_result(

            "AI_REQUEST_ERROR",

            str(e)
        )

    # ========================================================
    # READ RESPONSE
    # ========================================================

    try:

        output_text = (
            response.output_text
        )

        if not output_text:

            raise ValueError(
                "AI returned empty output."
            )

        print(
            "\n================ AI RAW OUTPUT ================"
        )

        print(
            output_text
        )

        print(
            "================================================\n"
        )

        ai_data = json.loads(
            output_text
        )

    except Exception as e:

        return empty_result(

            "AI_PARSE_ERROR",

            str(e)
        )

    # ========================================================
    # VALIDATE
    # ========================================================

    try:

        result = normalize_ai_result(
            ai_data
        )

    except Exception as e:

        return empty_result(

            "AI_VALIDATION_ERROR",

            str(e)
        )

    # ========================================================
    # DEBUG
    # ========================================================

    print(
        "\n================ AI FINAL RESULT ================"
    )

    print(
        "PRODUCT:",
        result.get(
            "product_name"
        )
    )

    print(
        "NET QUANTITY:",
        result.get(
            "net_quantity"
        )
    )

    print(
        "NET QUANTITY CONFIDENCE:",
        result.get(
            "net_quantity_confidence"
        )
    )

    print(
        "MRP:",
        result.get(
            "mrp"
        )
    )

    print(
        "MRP CONFIDENCE:",
        result.get(
            "mrp_confidence"
        )
    )

    print(
        "DATE:",
        result.get(
            "date_information"
        )
    )

    print(
        "MANUFACTURER:",
        result.get(
            "manufacturer"
        )
    )

    print(
        "================================================\n"
    )

    return result