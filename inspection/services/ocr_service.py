"""
OCR Service for SmartPack Inspect

Responsibilities:
- Receive uploaded product image
- OpenCV preprocessing
- Tesseract OCR when available
- RapidOCR fallback / primary deep-learning OCR
- Multiple image versions for better OCR
- Targeted crops for small package declarations
- OCR confidence calculation
- Return raw extracted text and preprocessed image URL

IMPORTANT:
This service NEVER generates fake/sample product information.
Only text actually detected by OCR is returned.
"""

import os
import shutil

import cv2
import numpy as np

from django.conf import settings


# ============================================================
# RAPIDOCR
# ============================================================

try:
    from rapidocr_onnxruntime import RapidOCR

    RAPID_OCR_ENGINE = RapidOCR()

except Exception as e:
    RAPID_OCR_ENGINE = None
    RAPID_OCR_IMPORT_ERROR = str(e)


# ============================================================
# TESSERACT
# ============================================================

try:
    import pytesseract
    from pytesseract import Output

except Exception:
    pytesseract = None
    Output = None


# Common Tesseract installation locations on Windows
POSSIBLE_TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expandvars(
        r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"
    ),
]


# ============================================================
# FIND TESSERACT
# ============================================================

def find_tesseract_binary():
    """
    Locate Tesseract executable.
    """

    for path in POSSIBLE_TESSERACT_PATHS:

        if os.path.exists(path):
            return path

    which_path = shutil.which("tesseract")

    if which_path:
        return which_path

    return None


# ============================================================
# RESIZE IMAGE
# ============================================================

def resize_for_ocr(image, minimum_width=1800):
    """
    Enlarge small images before OCR.
    """

    if image is None:
        return None

    height, width = image.shape[:2]

    if width >= minimum_width:
        return image

    scale = minimum_width / float(width)

    new_width = int(width * scale)
    new_height = int(height * scale)

    return cv2.resize(
        image,
        (new_width, new_height),
        interpolation=cv2.INTER_CUBIC
    )


# ============================================================
# TARGETED CROP PREPROCESSING
# ============================================================

def preprocess_target_crop(crop, minimum_width=2600):
    """
    Aggressive preprocessing for small package declarations.

    Useful for:
        NET QUANTITY
        NET WT
        MRP
        PRICE
        MFD
        EXP
    """

    if crop is None:
        return []

    # Resize crop first
    crop = resize_for_ocr(
        crop,
        minimum_width=minimum_width
    )

    if crop is None:
        return []

    gray = cv2.cvtColor(
        crop,
        cv2.COLOR_BGR2GRAY
    )

    # --------------------------------------------------------
    # CLAHE
    # --------------------------------------------------------

    clahe = cv2.createCLAHE(
        clipLimit=3.0,
        tileGridSize=(8, 8)
    )

    enhanced = clahe.apply(gray)

    # --------------------------------------------------------
    # Light denoising
    # --------------------------------------------------------

    denoised = cv2.GaussianBlur(
        enhanced,
        (3, 3),
        0
    )

    # --------------------------------------------------------
    # OTSU
    # --------------------------------------------------------

    _, otsu = cv2.threshold(
        denoised,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    # --------------------------------------------------------
    # Adaptive threshold
    # --------------------------------------------------------

    adaptive = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        9
    )

    # --------------------------------------------------------
    # Sharpened grayscale
    # --------------------------------------------------------

    sharpen_kernel = np.array([
        [0, -1, 0],
        [-1, 5, -1],
        [0, -1, 0]
    ])

    sharpened = cv2.filter2D(
        enhanced,
        -1,
        sharpen_kernel
    )

    return [
        crop,
        enhanced,
        sharpened,
        otsu,
        adaptive
    ]


# ============================================================
# OPENCV PREPROCESSING
# ============================================================

def preprocess_image_for_ocr(image_path: str):
    """
    Creates multiple OCR-friendly image versions.

    Includes:
        original
        enhanced grayscale
        binary
        OTSU
        lower crop
        lower-left crop
        bottom crop
        left panel
        multiple targeted preprocessing versions
    """

    img = cv2.imread(image_path)

    if img is None:
        raise ValueError(
            f"Could not load image from path: {image_path}"
        )

    # --------------------------------------------------------
    # Resize entire image
    # --------------------------------------------------------

    img = resize_for_ocr(
        img,
        minimum_width=1800
    )

    height, width = img.shape[:2]

    # --------------------------------------------------------
    # Grayscale
    # --------------------------------------------------------

    gray = cv2.cvtColor(
        img,
        cv2.COLOR_BGR2GRAY
    )

    # --------------------------------------------------------
    # Noise reduction
    # --------------------------------------------------------

    denoised = cv2.medianBlur(
        gray,
        3
    )

    # --------------------------------------------------------
    # CLAHE
    # --------------------------------------------------------

    clahe = cv2.createCLAHE(
        clipLimit=2.5,
        tileGridSize=(8, 8)
    )

    enhanced = clahe.apply(
        denoised
    )

    # --------------------------------------------------------
    # Adaptive threshold
    # --------------------------------------------------------

    binary = cv2.adaptiveThreshold(
        enhanced,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11
    )

    # --------------------------------------------------------
    # OTSU
    # --------------------------------------------------------

    _, otsu = cv2.threshold(
        enhanced,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    # ========================================================
    # TARGETED CROPS
    # ========================================================

    # --------------------------------------------------------
    # Lower 45%
    # --------------------------------------------------------

    lower_crop = img[
        int(height * 0.55):height,
        0:width
    ]

    # --------------------------------------------------------
    # Lower-left 75%
    # --------------------------------------------------------

    lower_left_crop = img[
        int(height * 0.50):height,
        0:int(width * 0.75)
    ]

    # --------------------------------------------------------
    # Bottom 32%
    # --------------------------------------------------------

    bottom_crop = img[
        int(height * 0.68):height,
        0:width
    ]

    # --------------------------------------------------------
    # Left-side panel
    # --------------------------------------------------------

    left_panel = img[
        int(height * 0.25):height,
        0:int(width * 0.70)
    ]

    # --------------------------------------------------------
    # MRP / declaration strip
    # Fine-print area on left where MRP & NET QTY appear
    # --------------------------------------------------------

    mrp_strip = img[
        int(height * 0.55):int(height * 0.95),
        0:int(width * 0.55)
    ]

    # Very bottom strip (contains NET QUANTITY declaration)
    bottom_declaration = img[
        int(height * 0.82):height,
        0:width
    ]

    # ========================================================
    # TARGETED PREPROCESSING
    # ========================================================

    lower_versions = preprocess_target_crop(
        lower_crop,
        minimum_width=2600
    )

    lower_left_versions = preprocess_target_crop(
        lower_left_crop,
        minimum_width=2800
    )

    bottom_versions = preprocess_target_crop(
        bottom_crop,
        minimum_width=3000
    )

    left_versions = preprocess_target_crop(
        left_panel,
        minimum_width=2600
    )

    mrp_strip_versions = preprocess_target_crop(
        mrp_strip,
        minimum_width=3200
    )

    bottom_declaration_versions = preprocess_target_crop(
        bottom_declaration,
        minimum_width=3500
    )

    # Keep original resized crops for compatibility
    lower_crop = resize_for_ocr(
        lower_crop,
        minimum_width=2600
    )

    lower_left_crop = resize_for_ocr(
        lower_left_crop,
        minimum_width=2800
    )

    bottom_crop = resize_for_ocr(
        bottom_crop,
        minimum_width=3000
    )

    left_panel = resize_for_ocr(
        left_panel,
        minimum_width=2600
    )

    mrp_strip = resize_for_ocr(
        mrp_strip,
        minimum_width=3200
    )

    bottom_declaration = resize_for_ocr(
        bottom_declaration,
        minimum_width=3500
    )

    # ========================================================
    # SAVE BINARY IMAGE FOR UI
    # ========================================================

    preprocessed_dir = os.path.join(
        settings.MEDIA_ROOT,
        "preprocessed"
    )

    os.makedirs(
        preprocessed_dir,
        exist_ok=True
    )

    base_name = os.path.basename(
        image_path
    )

    preprocessed_filename = (
        f"prep_{base_name}"
    )

    preprocessed_full_path = os.path.join(
        preprocessed_dir,
        preprocessed_filename
    )

    cv2.imwrite(
        preprocessed_full_path,
        binary
    )

    preprocessed_url = (
        f"{settings.MEDIA_URL}"
        f"preprocessed/"
        f"{preprocessed_filename}"
    )

    return {
        "original": img,
        "gray": enhanced,
        "binary": binary,
        "otsu": otsu,

        "lower_crop": lower_crop,
        "lower_left_crop": lower_left_crop,
        "bottom_crop": bottom_crop,
        "left_panel": left_panel,
        "mrp_strip": mrp_strip,
        "bottom_declaration": bottom_declaration,

        "lower_versions": lower_versions,
        "lower_left_versions": lower_left_versions,
        "bottom_versions": bottom_versions,
        "left_versions": left_versions,
        "mrp_strip_versions": mrp_strip_versions,
        "bottom_declaration_versions": bottom_declaration_versions,

        "preprocessed_url": preprocessed_url
    }


# ============================================================
# TESSERACT OCR
# ============================================================

def run_tesseract(image):
    """
    Run Tesseract OCR on one image.

    Returns:
        raw_text
        confidence
    """

    if pytesseract is None:
        return "", 0.0

    if image is None:
        return "", 0.0

    best_text = ""
    best_confidence = 0.0

    configs = [
        r"--oem 3 --psm 6",
        r"--oem 3 --psm 11",
        r"--oem 3 --psm 3",
    ]

    for config in configs:

        try:

            text = pytesseract.image_to_string(
                image,
                config=config
            )

            text = text.strip()

            confidence = 0.0

            if Output is not None:

                data = pytesseract.image_to_data(
                    image,
                    output_type=Output.DICT,
                    config=config
                )

                values = []

                for value in data.get("conf", []):

                    try:

                        conf = float(value)

                        if conf >= 0:
                            values.append(conf)

                    except (
                        ValueError,
                        TypeError
                    ):
                        continue

                if values:

                    confidence = (
                        sum(values) /
                        len(values)
                    )

            if len(text) > len(best_text):

                best_text = text
                best_confidence = confidence

            elif (
                len(text) == len(best_text)
                and confidence > best_confidence
            ):

                best_text = text
                best_confidence = confidence

        except Exception:
            continue

    return (
        best_text,
        round(best_confidence, 1)
    )


# ============================================================
# RAPIDOCR
# ============================================================

def run_rapidocr(image):
    """
    Run RapidOCR on one image.
    """

    if RAPID_OCR_ENGINE is None:
        return "", 0.0

    if image is None:
        return "", 0.0

    try:

        results, _ = RAPID_OCR_ENGINE(
            image
        )

        if not results:
            return "", 0.0

        extracted_lines = []
        confidence_scores = []

        for result in results:

            try:

                box, text, score = result

                text = str(text).strip()

                if not text:
                    continue

                extracted_lines.append(
                    text
                )

                score = float(score)

                if score <= 1.0:
                    score *= 100.0

                confidence_scores.append(
                    score
                )

            except Exception:
                continue

        if not extracted_lines:
            return "", 0.0

        combined_text = "\n".join(
            extracted_lines
        )

        if confidence_scores:

            average_confidence = (
                sum(confidence_scores) /
                len(confidence_scores)
            )

        else:

            average_confidence = 0.0

        return (
            combined_text.strip(),
            round(average_confidence, 1)
        )

    except Exception:
        return "", 0.0


# ============================================================
# NORMALIZE OCR TEXT
# ============================================================

def normalize_ocr_text(text):
    """
    Basic cleanup while preserving actual OCR content.
    """

    if not text:
        return ""

    lines = []

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        line = " ".join(
            line.split()
        )

        lines.append(
            line
        )

    return "\n".join(lines)


# ============================================================
# COMBINE OCR RESULTS
# ============================================================

def combine_ocr_results(results):
    """
    Combine OCR outputs from multiple image versions.

    Duplicate lines are removed.
    """

    unique_lines = []
    seen = set()

    confidences = []

    for text, confidence in results:

        if not text:
            continue

        normalized = normalize_ocr_text(
            text
        )

        if not normalized:
            continue

        for line in normalized.splitlines():

            line_clean = line.strip()

            if not line_clean:
                continue

            key = line_clean.upper()

            if key not in seen:

                seen.add(key)

                unique_lines.append(
                    line_clean
                )

        if confidence > 0:

            confidences.append(
                confidence
            )

    combined_text = "\n".join(
        unique_lines
    )

    if confidences:

        average_confidence = (
            sum(confidences) /
            len(confidences)
        )

    else:

        average_confidence = 0.0

    return (
        combined_text,
        round(average_confidence, 1)
    )


# ============================================================
# MAIN OCR FUNCTION
# ============================================================

def extract_text_from_image(image_path: str):
    """
    Main OCR pipeline.

    Flow:

        Uploaded Image
              ↓
        OpenCV preprocessing
              ↓
        Full image OCR
              ↓
        Targeted crop OCR
              ↓
        Multiple threshold versions
              ↓
        Combine OCR results
              ↓
        Structured extraction
    """

    # ========================================================
    # STEP 1 — PREPROCESS IMAGE
    # ========================================================

    try:

        processed = preprocess_image_for_ocr(
            image_path
        )

    except Exception as e:

        return {
            "status": "ERROR",
            "raw_text": "",
            "confidence": 0.0,
            "preprocessed_image_url": None,
            "engine_used": "None",
            "tesseract_detected": False,
            "message": (
                "OpenCV preprocessing failed: "
                f"{str(e)}"
            )
        }

    original_img = processed["original"]
    gray_img = processed["gray"]
    binary_img = processed["binary"]
    otsu_img = processed["otsu"]

    lower_crop = processed["lower_crop"]
    lower_left_crop = processed["lower_left_crop"]
    bottom_crop = processed["bottom_crop"]
    left_panel = processed["left_panel"]

    lower_versions = processed[
        "lower_versions"
    ]

    lower_left_versions = processed[
        "lower_left_versions"
    ]

    bottom_versions = processed[
        "bottom_versions"
    ]

    left_versions = processed[
        "left_versions"
    ]

    mrp_strip_versions = processed.get(
        "mrp_strip_versions", []
    )

    bottom_declaration_versions = processed.get(
        "bottom_declaration_versions", []
    )

    mrp_strip = processed.get("mrp_strip")
    bottom_declaration = processed.get("bottom_declaration")

    preprocessed_url = (
        processed["preprocessed_url"]
    )

    # ========================================================
    # OCR RESULTS
    # ========================================================

    all_results = []
    engines_used = []

    # ========================================================
    # FIND TESSERACT
    # ========================================================

    tesseract_binary = (
        find_tesseract_binary()
    )

    tesseract_detected = bool(
        tesseract_binary and pytesseract
    )

    # ========================================================
    # TESSERACT
    # ========================================================

    if tesseract_detected:

        try:

            pytesseract.pytesseract.tesseract_cmd = (
                tesseract_binary
            )

            pytesseract.get_tesseract_version()

            tesseract_images = [

                original_img,
                gray_img,
                binary_img,
                otsu_img,

                lower_crop,
                lower_left_crop,
                bottom_crop,
                left_panel,

            ]

            if mrp_strip is not None:
                tesseract_images.append(mrp_strip)
            if bottom_declaration is not None:
                tesseract_images.append(bottom_declaration)

            # Add targeted versions
            tesseract_images.extend(
                lower_versions
            )

            tesseract_images.extend(
                lower_left_versions
            )

            tesseract_images.extend(
                bottom_versions
            )

            tesseract_images.extend(
                left_versions
            )

            tesseract_images.extend(
                mrp_strip_versions
            )

            tesseract_images.extend(
                bottom_declaration_versions
            )

            for image in tesseract_images:

                text, confidence = (
                    run_tesseract(image)
                )

                if text.strip():

                    all_results.append(
                        (
                            text,
                            confidence
                        )
                    )

            if all_results:

                engines_used.append(
                    "Tesseract OCR"
                )

        except Exception:
            pass

    # ========================================================
    # RAPIDOCR
    # ========================================================

    if RAPID_OCR_ENGINE is not None:

        rapid_images = [

            (
                original_img,
                "Original"
            ),

            (
                gray_img,
                "Enhanced"
            ),

            (
                binary_img,
                "Binary"
            ),

            (
                otsu_img,
                "OTSU"
            ),

            (
                lower_crop,
                "Lower Crop"
            ),

            (
                lower_left_crop,
                "Lower Left Crop"
            ),

            (
                bottom_crop,
                "Bottom Crop"
            ),

            (
                left_panel,
                "Left Panel"
            ),
            (
                mrp_strip,
                "MRP Strip"
            ),
            (
                bottom_declaration,
                "Bottom Declaration"
            )
        ]

        # Add every targeted preprocessing version
        for image in lower_versions:

            rapid_images.append(
                (
                    image,
                    "Lower Target"
                )
            )

        for image in lower_left_versions:

            rapid_images.append(
                (
                    image,
                    "Lower Left Target"
                )
            )

        for image in bottom_versions:

            rapid_images.append(
                (
                    image,
                    "Bottom Target"
                )
            )

        for image in left_versions:

            rapid_images.append(
                (
                    image,
                    "Left Target"
                )
            )

        for image in mrp_strip_versions:

            rapid_images.append(
                (
                    image,
                    "MRP Strip Target"
                )
            )

        for image in bottom_declaration_versions:

            rapid_images.append(
                (
                    image,
                    "Bottom Declaration Target"
                )
            )

        # ----------------------------------------------------
        # Run RapidOCR
        # ----------------------------------------------------

        for image, label in rapid_images:

            try:

                text, confidence = (
                    run_rapidocr(image)
                )

                if text.strip():

                    print(
                        f"\n[RapidOCR - {label}]"
                    )

                    print(text)

                    all_results.append(
                        (
                            text,
                            confidence
                        )
                    )

            except Exception:
                continue

        if any(
            text.strip()
            for text, confidence
            in all_results
        ):

            engines_used.append(
                "RapidOCR (ONNX Deep Learning Engine)"
            )

    # ========================================================
    # COMBINE RESULTS
    # ========================================================

    combined_text, combined_confidence = (
        combine_ocr_results(
            all_results
        )
    )

    # ========================================================
    # DEBUG OUTPUT
    # ========================================================

    print(
        "\n"
        "==================================================\n"
        "SMARTPACK OCR RESULT\n"
        "==================================================\n"
        f"{combined_text}\n"
        "==================================================\n"
    )

    # ========================================================
    # SUCCESS
    # ========================================================

    if combined_text.strip():

        engine_used = " + ".join(
            dict.fromkeys(
                engines_used
            )
        )

        if not engine_used:
            engine_used = "OCR"

        return {

            "status": "SUCCESS",

            "raw_text": (
                combined_text.strip()
            ),

            "confidence": (
                combined_confidence
            ),

            "preprocessed_image_url": (
                preprocessed_url
            ),

            "engine_used": (
                engine_used
            ),

            "tesseract_detected": (
                tesseract_detected
            ),

            "message": (
                "Live OCR completed using "
                "multiple OpenCV preprocessing "
                "versions and targeted package "
                "crops."
            )
        }

    # ========================================================
    # EMPTY RESULT
    # ========================================================

    return {

        "status": "EMPTY_RESULT",

        "raw_text": "",

        "confidence": 0.0,

        "preprocessed_image_url": (
            preprocessed_url
        ),

        "engine_used": "None",

        "tesseract_detected": (
            tesseract_detected
        ),

        "message": (
            "No text could be extracted from "
            "the uploaded package image. "
            "Please verify image quality, "
            "lighting, focus, and OCR engine "
            "installation."
        )
    }