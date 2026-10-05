import os
import uuid
import json

from django.shortcuts import (
    render,
    get_object_or_404,
    redirect,
)
from django.conf import settings
from django.utils import timezone
from django.http import HttpResponse

from .forms import ProductImageUploadForm
from .models import Inspection

from .services.ocr_service import (
    extract_text_from_image
)

from .services.extraction_service import (
    extract_structured_fields
)

from .services.rule_engine import (
    evaluate_compliance
)

# =========================================================
# AI VISION SERVICE
# =========================================================

try:
    from .services.ai_vision_service import (
        inspect_product_image
    )
except ImportError:
    inspect_product_image = None


# =========================================================
# DASHBOARD
# =========================================================

def home(request):
    """
    Landing dashboard page for SmartPack Inspect.
    """

    return render(
        request,
        'inspection/home.html',
        {
            'page_title':
                'SmartPack Inspect | Home',

            'active_tab':
                'dashboard',
        }
    )


# =========================================================
# PRODUCT IMAGE UPLOAD / INSPECTION
# =========================================================

def upload(request):
    """
    Main SmartPack inspection pipeline.

    Pipeline:

        1. Image validation
        2. Save original image
        3. OpenCV + OCR
        4. AI Vision inspection
        5. AI field validation
        6. Fallback to OCR extraction if AI unavailable
        7. Legal Metrology rule engine
        8. Save inspection to SQLite
        9. Display result
    """

    upload_result = None

    # =====================================================
    # POST REQUEST
    # =====================================================

    if request.method == 'POST':

        form = ProductImageUploadForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            uploaded_file = (
                form.cleaned_data['image']
            )

            commodity_type = (
                form.cleaned_data.get(
                    'commodity_type',
                    'food_general'
                )
            )

            # =================================================
            # 1. SAVE ORIGINAL IMAGE
            # =================================================

            ext = os.path.splitext(
                uploaded_file.name
            )[1].lower()

            safe_filename = (
                f"prod_"
                f"{uuid.uuid4().hex[:10]}"
                f"{ext}"
            )

            relative_path = os.path.join(
                'products',
                safe_filename
            )

            products_directory = os.path.join(
                settings.MEDIA_ROOT,
                'products'
            )

            os.makedirs(
                products_directory,
                exist_ok=True
            )

            full_file_path = os.path.join(
                settings.MEDIA_ROOT,
                relative_path
            )

            with open(
                full_file_path,
                'wb+'
            ) as destination:

                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            # =================================================
            # 2. NORMAL OCR
            #
            # We still run OCR because:
            #
            # - it provides raw text
            # - it provides OCR confidence
            # - it provides OpenCV processed image
            # - it acts as fallback if AI fails
            # =================================================

            try:

                ocr_output = (
                    extract_text_from_image(
                        full_file_path
                    )
                )

            except Exception as e:

                ocr_output = {
                    'status': 'ERROR',
                    'raw_text': '',
                    'confidence': 0.0,
                    'preprocessed_image_url': None,
                    'engine_used': 'OCR ERROR',
                    'message': str(e),
                }

            raw_text = (
                ocr_output.get(
                    'raw_text',
                    ''
                )
            )

            ocr_confidence = (
                ocr_output.get(
                    'confidence',
                    0.0
                )
            )

            # =================================================
            # 3. NORMAL OCR EXTRACTION
            #
            # This is kept as fallback.
            # =================================================

            try:

                ocr_extracted_fields = (
                    extract_structured_fields(
                        raw_text,
                        commodity_type
                    )
                )

            except Exception:

                ocr_extracted_fields = {}

            # =================================================
            # 4. AI VISION INSPECTION
            # =================================================

            ai_result = None

            if inspect_product_image:

                try:

                    ai_result = (
                        inspect_product_image(
                            full_file_path,
                            commodity_type
                        )
                    )

                except Exception as e:

                    print(
                        "\nSMARTPACK AI ERROR:"
                    )

                    print(
                        str(e)
                    )

                    ai_result = {
                        'status':
                            'AI_REQUEST_ERROR',

                        'message':
                            str(e),

                        'ai_available':
                            False,
                    }

            # =================================================
            # 5. CHECK WHETHER AI RESULT IS USABLE
            # =================================================

            ai_available = False

            if isinstance(
                ai_result,
                dict
            ):

                ai_available = (
                    ai_result.get(
                        'ai_available',
                        False
                    )
                    and
                    ai_result.get(
                        'status'
                    ) == 'SUCCESS'
                )

            # =================================================
            # 6. SELECT EXTRACTION SOURCE
            #
            # IMPORTANT:
            #
            # AI becomes the PRIMARY source.
            #
            # OCR becomes FALLBACK.
            # =================================================

            if ai_available:

                print(
                    "\n================================"
                )

                print(
                    "SMARTPACK: AI VISION PRIMARY"
                )

                print(
                    "================================"
                )

                # -------------------------------------------------
                # AI → structured fields
                # -------------------------------------------------

                extracted_fields = {

                    'product_name':
                        ai_result.get(
                            'product_name'
                        ),

                    'net_quantity':
                        ai_result.get(
                            'net_quantity'
                        ),

                    'net_quantity_value':
                        ai_result.get(
                            'net_quantity_value'
                        ),

                    'net_quantity_unit':
                        ai_result.get(
                            'net_quantity_unit'
                        ),

                    'mrp':
                        ai_result.get(
                            'mrp'
                        ),

                    'mrp_value':
                        ai_result.get(
                            'mrp_value'
                        ),

                    'manufacturer':
                        ai_result.get(
                            'manufacturer'
                        ),

                    # Rule engine / template compatibility
                    'date_info':
                        ai_result.get(
                            'date_information'
                        ),

                    'date_information':
                        ai_result.get(
                            'date_information'
                        ),

                    'consumer_care':
                        ai_result.get(
                            'consumer_care'
                        ),

                    # Evidence
                    'product_evidence':
                        ai_result.get(
                            'product_evidence'
                        ),

                    'net_quantity_evidence':
                        ai_result.get(
                            'net_quantity_evidence'
                        ),

                    'mrp_evidence':
                        ai_result.get(
                            'mrp_evidence'
                        ),

                    'manufacturer_evidence':
                        ai_result.get(
                            'manufacturer_evidence'
                        ),

                    'date_evidence':
                        ai_result.get(
                            'date_evidence'
                        ),

                    # AI confidence
                    'net_quantity_confidence':
                        ai_result.get(
                            'net_quantity_confidence',
                            0
                        ),

                    'mrp_confidence':
                        ai_result.get(
                            'mrp_confidence',
                            0
                        ),

                    'overall_confidence':
                        ai_result.get(
                            'overall_confidence',
                            0
                        ),

                    # Source
                    'extraction_source':
                        'AI Vision',

                    'ai_model':
                        ai_result.get(
                            'model'
                        ),

                    'ai_inspection_note':
                        ai_result.get(
                            'inspection_note',
                            ''
                        ),
                }

            else:

                # =================================================
                # AI FAILED → OCR FALLBACK
                # =================================================

                print(
                    "\n================================"
                )

                print(
                    "SMARTPACK: OCR FALLBACK"
                )

                print(
                    "================================"
                )

                extracted_fields = (
                    ocr_extracted_fields
                    or {}
                )

                # Make sure expected fields exist
                extracted_fields.setdefault(
                    'product_name',
                    None
                )

                extracted_fields.setdefault(
                    'net_quantity',
                    None
                )

                extracted_fields.setdefault(
                    'net_quantity_value',
                    None
                )

                extracted_fields.setdefault(
                    'net_quantity_unit',
                    None
                )

                extracted_fields.setdefault(
                    'mrp',
                    None
                )

                extracted_fields.setdefault(
                    'mrp_value',
                    None
                )

                extracted_fields.setdefault(
                    'manufacturer',
                    None
                )

                extracted_fields.setdefault(
                    'date_info',
                    None
                )

                extracted_fields.setdefault(
                    'consumer_care',
                    None
                )

                extracted_fields[
                    'extraction_source'
                ] = 'OCR'

                extracted_fields[
                    'ai_model'
                ] = None

                extracted_fields[
                    'ai_inspection_note'
                ] = (
                    ai_result.get(
                        'message',
                        'AI Vision unavailable.'
                    )
                    if isinstance(
                        ai_result,
                        dict
                    )
                    else
                    'AI Vision service unavailable.'
                )

            # =================================================
            # 7. SAFETY NORMALIZATION
            #
            # AI must never replace missing values with
            # fake defaults.
            # =================================================

            product_name = (
                extracted_fields.get(
                    'product_name'
                )
            )

            net_quantity = (
                extracted_fields.get(
                    'net_quantity'
                )
            )

            mrp = (
                extracted_fields.get(
                    'mrp'
                )
            )

            manufacturer = (
                extracted_fields.get(
                    'manufacturer'
                )
            )

            # Never use "Unknown Product" as an actual
            # extracted value.
            #
            # Use None so the rule engine knows it is
            # missing.
            if not product_name:
                product_name = None

            if not net_quantity:
                net_quantity = None

            if not mrp:
                mrp = None

            if not manufacturer:
                manufacturer = None

            # =================================================
            # 8. LEGAL METROLOGY RULE ENGINE
            # =================================================

            try:

                rule_assessment = (
                    evaluate_compliance(
                        extracted_fields,
                        commodity_type,
                        ocr_confidence
                    )
                )

            except Exception as e:

                print(
                    "\nRULE ENGINE ERROR:"
                )

                print(
                    str(e)
                )

                rule_assessment = {

                    'overall_status':
                        'NEEDS_REVIEW',

                    'compliance_score':
                        0,

                    'pass_count':
                        0,

                    'total_count':
                        0,

                    'checks':
                        [],

                    'issues':
                        [
                            'Rule engine error: '
                            + str(e)
                        ],
                }

            # =================================================
            # 9. COMPLIANCE STATUS
            # =================================================

            compliance_status = (
                rule_assessment.get(
                    'overall_status',
                    'NEEDS_REVIEW'
                )
            )

            # =================================================
            # 10. GENERATE INSPECTION ID
            # =================================================

            inspection_id = (
                f"SP-"
                f"{timezone.now().strftime('%Y%m%d%H%M%S')}-"
                f"{uuid.uuid4().hex[:4].upper()}"
            )

            # =================================================
            # 11. SAVE INSPECTION
            # =================================================

            inspection = Inspection.objects.create(

                inspection_id=
                    inspection_id,

                file_name=
                    uploaded_file.name,

                image=
                    relative_path,

                commodity_type=
                    commodity_type,

                product_name=
                    product_name or '',

                net_quantity=
                    net_quantity or '',

                mrp=
                    mrp or '',

                manufacturer=
                    manufacturer or '',

                ocr_confidence=
                    ocr_confidence,

                raw_text=
                    raw_text,

                compliance_status=
                    compliance_status,

                extracted_fields=
                    extracted_fields,

                rule_assessment=
                    rule_assessment,
            )

            # =================================================
            # 12. PREPARED DISPLAY VALUES
            # =================================================

            commodity_display = dict(
                form.fields[
                    'commodity_type'
                ].choices
            ).get(
                commodity_type,
                commodity_type
            )

            # =================================================
            # 13. CURRENT RESULT
            # =================================================

            upload_result = {

                'success':
                    True,

                'inspection_id':
                    inspection.inspection_id,

                'file_name':
                    uploaded_file.name,

                'saved_as':
                    safe_filename,

                # ---------------------------------------------
                # Original image
                # ---------------------------------------------

                'media_url':
                    (
                        f"{settings.MEDIA_URL}"
                        f"products/"
                        f"{safe_filename}"
                    ),

                # ---------------------------------------------
                # OpenCV image
                # ---------------------------------------------

                'preprocessed_url':
                    ocr_output.get(
                        'preprocessed_image_url'
                    ),

                # ---------------------------------------------
                # File information
                # ---------------------------------------------

                'file_size_kb':
                    round(
                        uploaded_file.size / 1024,
                        1
                    ),

                'commodity_type':
                    commodity_display,

                # ---------------------------------------------
                # OCR
                # ---------------------------------------------

                'ocr_status':
                    ocr_output.get(
                        'status'
                    ),

                'ocr_confidence':
                    ocr_confidence,

                'ocr_message':
                    ocr_output.get(
                        'message'
                    ),

                'engine_used':
                    ocr_output.get(
                        'engine_used',
                        'Unknown'
                    ),

                'tesseract_detected':
                    (
                        'Tesseract'
                        in
                        str(
                            ocr_output.get(
                                'engine_used',
                                ''
                            )
                        )
                    ),

                'raw_text':
                    raw_text,

                # ---------------------------------------------
                # AI
                # ---------------------------------------------

                'ai_available':
                    ai_available,

                'ai_status':
                    (
                        ai_result.get(
                            'status'
                        )
                        if isinstance(
                            ai_result,
                            dict
                        )
                        else
                        'AI_UNAVAILABLE'
                    ),

                'ai_message':
                    (
                        ai_result.get(
                            'message'
                        )
                        if isinstance(
                            ai_result,
                            dict
                        )
                        else
                        ''
                    ),

                'ai_model':
                    (
                        ai_result.get(
                            'model'
                        )
                        if isinstance(
                            ai_result,
                            dict
                        )
                        else
                        None
                    ),

                'ai_overall_confidence':
                    (
                        ai_result.get(
                            'overall_confidence',
                            0
                        )
                        if isinstance(
                            ai_result,
                            dict
                        )
                        else
                        0
                    ),

                'ai_net_quantity_confidence':
                    (
                        ai_result.get(
                            'net_quantity_confidence',
                            0
                        )
                        if isinstance(
                            ai_result,
                            dict
                        )
                        else
                        0
                    ),

                'ai_mrp_confidence':
                    (
                        ai_result.get(
                            'mrp_confidence',
                            0
                        )
                        if isinstance(
                            ai_result,
                            dict
                        )
                        else
                        0
                    ),

                # ---------------------------------------------
                # Extraction source
                # ---------------------------------------------

                'extraction_source':
                    extracted_fields.get(
                        'extraction_source',
                        'OCR'
                    ),

                # ---------------------------------------------
                # Final extracted fields
                # ---------------------------------------------

                'extracted_fields':
                    extracted_fields,

                # ---------------------------------------------
                # Compliance
                # ---------------------------------------------

                'rule_assessment':
                    rule_assessment,
            }

    else:

        form = ProductImageUploadForm()

    # =====================================================
    # RENDER
    # =====================================================

    return render(
        request,
        'inspection/upload.html',
        {
            'page_title':
                'New Inspection | SmartPack Inspect',

            'active_tab':
                'upload',

            'form':
                form,

            'upload_result':
                upload_result,
        }
    )


# =========================================================
# INSPECTION HISTORY
# =========================================================

def history(request):
    """
    Display all inspection records.
    """

    inspections = (
        Inspection.objects
        .all()
        .order_by('-created_at')
    )

    return render(
        request,
        'inspection/history.html',
        {
            'page_title':
                'Inspection History | SmartPack Inspect',

            'active_tab':
                'history',

            'inspections':
                inspections,
        }
    )


# =========================================================
# INDIVIDUAL INSPECTION DETAIL
# =========================================================

def inspection_detail(
    request,
    inspection_id
):
    """
    Display one complete inspection.
    """

    inspection = get_object_or_404(
        Inspection,
        inspection_id=inspection_id
    )

    return render(
        request,
        'inspection/inspection_detail.html',
        {
            'page_title':
                'Inspection Details | SmartPack Inspect',

            'active_tab':
                'history',

            'inspection':
                inspection,

            'media_url':
                settings.MEDIA_URL,
        }
    )


# =========================================================
# DELETE INSPECTION
# =========================================================

def delete_inspection(
    request,
    inspection_id
):
    """
    Delete one inspection record.
    """

    inspection = get_object_or_404(
        Inspection,
        inspection_id=inspection_id
    )

    if request.method == 'POST':

        # -------------------------------------------------
        # Delete physical uploaded image too
        # -------------------------------------------------

        try:

            if inspection.image:

                image_path = (
                    inspection.image.path
                )

                if os.path.exists(
                    image_path
                ):
                    os.remove(
                        image_path
                    )

        except Exception as e:

            print(
                "Image deletion warning:",
                e
            )

        inspection.delete()

        return redirect(
            'inspection:history'
        )

    return redirect(
        'inspection:inspection_detail',
        inspection_id=inspection_id
    )


# =========================================================
# LEGAL METROLOGY RULES
# =========================================================

def rules(request):

    return render(
        request,
        'inspection/rules.html',
        {
            'page_title':
                'Legal Metrology Rules | SmartPack Inspect',

            'active_tab':
                'rules',
        }
    )


# =========================================================
# REPORTS PAGE
# =========================================================

def reports(request):
    """
    Display all inspection records.
    """

    inspections = (
        Inspection.objects
        .all()
        .order_by('-created_at')
    )

    return render(
        request,
        'inspection/report.html',
        {
            'page_title':
                'Inspection Reports | SmartPack Inspect',

            'active_tab':
                'reports',

            'inspections':
                inspections,
        }
    )


# =========================================================
# DOWNLOAD PDF REPORT
# =========================================================

def download_report(
    request,
    inspection_id
):
    """
    Generate a PDF report for one inspection.

    ReportLab is imported inside the function so that
    the complete Django application does not crash at
    startup if ReportLab is missing.
    """

    inspection = get_object_or_404(
        Inspection,
        inspection_id=inspection_id
    )

    # =====================================================
    # REPORTLAB CHECK
    # =====================================================

    try:

        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4

    except ImportError:

        return HttpResponse(
            (
                "ReportLab is not installed. "
                "Run: python -m pip install reportlab"
            ),
            status=500,
            content_type='text/plain'
        )

    # =====================================================
    # RESPONSE
    # =====================================================

    response = HttpResponse(
        content_type='application/pdf'
    )

    response[
        'Content-Disposition'
    ] = (
        'attachment; '
        f'filename="SmartPack_Report_'
        f'{inspection.inspection_id}.pdf"'
    )

    pdf = canvas.Canvas(
        response,
        pagesize=A4
    )

    width, height = A4

    y = height - 50

    # =====================================================
    # TITLE
    # =====================================================

    pdf.setFont(
        'Helvetica-Bold',
        18
    )

    pdf.drawString(
        50,
        y,
        'SMARTPACK INSPECT'
    )

    y -= 25

    pdf.setFont(
        'Helvetica-Bold',
        13
    )

    pdf.drawString(
        50,
        y,
        'Packaging Compliance Inspection Report'
    )

    y -= 40

    # =====================================================
    # INSPECTION INFORMATION
    # =====================================================

    pdf.setFont(
        'Helvetica-Bold',
        11
    )

    pdf.drawString(
        50,
        y,
        'Inspection Information'
    )

    y -= 22

    pdf.setFont(
        'Helvetica',
        10
    )

    pdf.drawString(
        50,
        y,
        f'Inspection ID: '
        f'{inspection.inspection_id}'
    )

    y -= 18

    pdf.drawString(
        50,
        y,
        (
            f'Date: '
            f'{inspection.created_at.strftime(
                "%Y-%m-%d %H:%M"
            )}'
        )
    )

    y -= 18

    pdf.drawString(
        50,
        y,
        f'Category: '
        f'{inspection.commodity_type}'
    )

    y -= 35

    # =====================================================
    # PRODUCT INFORMATION
    # =====================================================

    pdf.setFont(
        'Helvetica-Bold',
        11
    )

    pdf.drawString(
        50,
        y,
        'Extracted Product Information'
    )

    y -= 22

    pdf.setFont(
        'Helvetica',
        10
    )

    extracted = (
        inspection.extracted_fields
        or {}
    )

    product_name = (
        extracted.get(
            'product_name'
        )
        or inspection.product_name
        or 'Not detected'
    )

    quantity = (
        extracted.get(
            'net_quantity'
        )
        or inspection.net_quantity
        or 'Not detected'
    )

    mrp = (
        extracted.get(
            'mrp'
        )
        or inspection.mrp
        or 'Not detected'
    )

    manufacturer = (
        extracted.get(
            'manufacturer'
        )
        or inspection.manufacturer
        or 'Not detected'
    )

    date_info = (
        extracted.get(
            'date_info'
        )
        or extracted.get(
            'date_information'
        )
        or 'Not detected'
    )

    consumer_care = (
        extracted.get(
            'consumer_care'
        )
        or 'Not detected'
    )

    pdf.drawString(
        50,
        y,
        f'Product Name: {product_name}'
    )

    y -= 18

    pdf.drawString(
        50,
        y,
        f'Net Quantity: {quantity}'
    )

    y -= 18

    pdf.drawString(
        50,
        y,
        f'MRP: {mrp}'
    )

    y -= 18

    pdf.drawString(
        50,
        y,
        f'Manufacturer: {manufacturer}'
    )

    y -= 18

    pdf.drawString(
        50,
        y,
        f'Date Information: {date_info}'
    )

    y -= 18

    pdf.drawString(
        50,
        y,
        f'Consumer Care: {consumer_care}'
    )

    y -= 35

    # =====================================================
    # AI INFORMATION
    # =====================================================

    pdf.setFont(
        'Helvetica-Bold',
        11
    )

    pdf.drawString(
        50,
        y,
        'AI / OCR Information'
    )

    y -= 22

    pdf.setFont(
        'Helvetica',
        10
    )

    extraction_source = (
        extracted.get(
            'extraction_source',
            'OCR'
        )
    )

    ai_model = (
        extracted.get(
            'ai_model'
        )
        or 'Not used'
    )

    pdf.drawString(
        50,
        y,
        f'Extraction Source: '
        f'{extraction_source}'
    )

    y -= 18

    pdf.drawString(
        50,
        y,
        f'AI Model: {ai_model}'
    )

    y -= 18

    pdf.drawString(
        50,
        y,
        (
            f'OCR Confidence: '
            f'{float(
                inspection.ocr_confidence or 0
            ):.1f}%'
        )
    )

    y -= 35

    # =====================================================
    # COMPLIANCE
    # =====================================================

    pdf.setFont(
        'Helvetica-Bold',
        11
    )

    pdf.drawString(
        50,
        y,
        'Compliance Assessment'
    )

    y -= 22

    pdf.setFont(
        'Helvetica',
        10
    )

    status = (
        inspection.compliance_status
        or 'NOT ASSESSED'
    )

    pdf.drawString(
        50,
        y,
        f'Status: {status}'
    )

    y -= 18

    assessment = (
        inspection.rule_assessment
        or {}
    )

    score = (
        assessment.get(
            'compliance_score',
            0
        )
    )

    pdf.drawString(
        50,
        y,
        f'Compliance Score: '
        f'{score}%'
    )

    y -= 35

    # =====================================================
    # RULE CHECKS
    # =====================================================

    checks = (
        assessment.get(
            'checks',
            []
        )
    )

    if checks:

        pdf.setFont(
            'Helvetica-Bold',
            11
        )

        pdf.drawString(
            50,
            y,
            'Rule Verification'
        )

        y -= 20

        pdf.setFont(
            'Helvetica',
            8
        )

        for check in checks:

            field = str(
                check.get(
                    'field',
                    ''
                )
            )

            status = str(
                check.get(
                    'status',
                    ''
                )
            )

            reason = str(
                check.get(
                    'reason',
                    ''
                )
            )

            line = (
                f'{field}: '
                f'{status} - '
                f'{reason}'
            )

            # Prevent huge lines
            line = line[:120]

            if y < 60:

                pdf.showPage()

                y = height - 50

                pdf.setFont(
                    'Helvetica',
                    8
                )

            pdf.drawString(
                50,
                y,
                line
            )

            y -= 14

    # =====================================================
    # OCR RAW TEXT
    # =====================================================

    if y < 100:

        pdf.showPage()

        y = height - 50

    y -= 15

    pdf.setFont(
        'Helvetica-Bold',
        11
    )

    pdf.drawString(
        50,
        y,
        'OCR Extracted Raw Text'
    )

    y -= 20

    pdf.setFont(
        'Helvetica',
        8
    )

    raw_text = (
        inspection.raw_text
        or 'No OCR text available.'
    )

    raw_text = raw_text.replace(
        '\x00',
        ''
    )

    for line in raw_text.splitlines():

        line = line.strip()

        if not line:
            continue

        # Wrap long lines
        while len(line) > 105:

            part = line[:105]

            if y < 50:

                pdf.showPage()

                y = height - 50

                pdf.setFont(
                    'Helvetica',
                    8
                )

            pdf.drawString(
                50,
                y,
                part
            )

            y -= 12

            line = line[105:]

        if line:

            if y < 50:

                pdf.showPage()

                y = height - 50

                pdf.setFont(
                    'Helvetica',
                    8
                )

            pdf.drawString(
                50,
                y,
                line
            )

            y -= 12

    # =====================================================
    # FOOTER
    # =====================================================

    if y < 50:

        pdf.showPage()

        y = height - 50

    pdf.setFont(
        'Helvetica-Oblique',
        8
    )

    pdf.drawString(
        50,
        30,
        (
            'SmartPack Inspect - '
            'Academic Prototype / '
            'Decision Support System'
        )
    )

    pdf.drawString(
        50,
        18,
        (
            'AI results are subject to image quality '
            'and must be manually verified.'
        )
    )

    # =====================================================
    # SAVE PDF
    # =====================================================

    pdf.save()

    return response


# =========================================================
# SYSTEM INFORMATION
# =========================================================

def system_info(request):

    return render(
        request,
        'inspection/system_info.html',
        {
            'page_title':
                'System Information | SmartPack Inspect',

            'active_tab':
                'system_info',
        }
    )