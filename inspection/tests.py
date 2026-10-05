import io
from django.test import TestCase, Client
from django.urls import reverse
from PIL import Image

from inspection.services.extraction_service import (
    extract_net_quantity,
    extract_mrp,
    extract_product_name,
    extract_date_info,
    extract_manufacturer,
    extract_structured_fields,
)
from inspection.services.rule_engine import evaluate_compliance


class InspectionPhase1And2Tests(TestCase):
    def setUp(self):
        self.client = Client()

    def create_dummy_image(self, filename="test_label.png"):
        file = io.BytesIO()
        image = Image.new('RGB', (200, 200), color=(73, 109, 137))
        image.save(file, 'PNG')
        file.name = filename
        file.seek(0)
        return file

    def test_home_page_status_and_content(self):
        response = self.client.get(reverse('inspection:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SMARTPACK INSPECT")
        self.assertContains(response, "IoT and AI-Based Package Verification System")
        self.assertContains(response, "Upload Product Image")
        self.assertContains(response, "Inspection History")

    def test_upload_page_get(self):
        response = self.client.get(reverse('inspection:upload'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Package Verification")
        self.assertContains(response, "VERIFY PRODUCT")

    def test_upload_valid_image(self):
        img = self.create_dummy_image()
        response = self.client.post(reverse('inspection:upload'), {
            'commodity_type': 'biscuits',
            'image': img
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "OVERALL ASSESSMENT")
        self.assertContains(response, "OCR Extracted Raw Text")
        self.assertContains(response, "Structured Field Extraction")
        self.assertContains(response, "Legal Metrology Rule Verification")

    def test_upload_invalid_file_type(self):
        text_file = io.BytesIO(b"fake text content")
        text_file.name = "malicious.txt"
        response = self.client.post(reverse('inspection:upload'), {
            'commodity_type': 'biscuits',
            'image': text_file
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Validation Notice")

    def test_navigation_pages(self):
        for route_name in ['history', 'rules', 'reports', 'system_info']:
            response = self.client.get(reverse(f'inspection:{route_name}'))
            self.assertEqual(response.status_code, 200)


class ExtractionServiceTests(TestCase):
    def test_amul_pack_extraction(self):
        sample_ocr = """
        Amul
        Taaza
        Net Content:
        500ml
        MRP:7
        20.00
        (Inclusive of all taxes)
        FOR BEST RESULTS STORE BELOW 8°C UNTIL USE-BY DATES
        MARKETED BY:
        GUJARAT CO-OPERATIVE MILK MARKETING FEDERATION LTD.
        """
        extracted = extract_structured_fields(sample_ocr, "food_general")
        self.assertEqual(extracted["product_name"], "Amul Taaza")
        self.assertEqual(extracted["net_quantity"], "500 ml")
        self.assertEqual(extracted["net_quantity_val"], 500.0)
        self.assertEqual(extracted["net_quantity_unit"], "ml")
        self.assertEqual(extracted["mrp"], "₹20")
        self.assertEqual(extracted["mrp_val"], 20.0)
        self.assertEqual(extracted["date_info"], "USE-BY DATES")
        self.assertIn("GUJARAT CO-OPERATIVE", extracted["manufacturer"].upper())

        compliance = evaluate_compliance(extracted, "food_general", 90.0)
        check_dict = {c["field"]: c["status"] for c in compliance["checks"]}
        self.assertEqual(check_dict["Net Quantity"], "PASS")
        self.assertEqual(check_dict["Maximum Retail Price (MRP)"], "PASS")
        self.assertEqual(check_dict["Product / Generic Name"], "PASS")
        self.assertEqual(check_dict["Manufacturer / Packer"], "PASS")
        self.assertEqual(check_dict["Date of Manufacture / Packing"], "PASS")

    def test_krackjack_pack_extraction(self):
        sample_ocr = """
        PARLE
        Krackjack
        Sweet & Salty Crackers
        16 INDIVIDUAL PACKS INSIDE
        NET WEIGHT: 705.6 g
        (44.1 g x 16 UNITS)
        MRP ₹ 135.00
        (INCL. OF ALL TAXES)
        PKD: 16/08/2025
        USE BY: 13/04/2027 02:10
        MANUFACTURED BY: PARLE BISCUITS PVT. LTD.
        PHONE NO.: 1800 209 6929
        E-MAIL: CS@PARLE.BIZ
        8901719140433
        """
        extracted = extract_structured_fields(sample_ocr, "food_general")
        self.assertEqual(extracted["product_name"], "Parle Krackjack")
        self.assertEqual(extracted["net_quantity"], "705.6 g")
        self.assertEqual(extracted["net_quantity_val"], 705.6)
        self.assertEqual(extracted["net_quantity_unit"], "g")
        self.assertEqual(extracted["mrp"], "₹135")
        self.assertEqual(extracted["mrp_val"], 135.0)
        self.assertIn("13/04/2027", extracted["date_info"])
        self.assertIn("PARLE", extracted["manufacturer"].upper())
        self.assertEqual(extracted["barcode"], "8901719140433")
        self.assertIn("1800", extracted["consumer_care"])
        self.assertIn("cs@parle", extracted["consumer_care"].lower())

        compliance = evaluate_compliance(extracted, "food_general", 95.0)
        check_dict = {c["field"]: c["status"] for c in compliance["checks"]}
        self.assertEqual(check_dict["Net Quantity"], "PASS")
        self.assertEqual(check_dict["Maximum Retail Price (MRP)"], "PASS")
        self.assertEqual(check_dict["Product / Generic Name"], "PASS")
        self.assertEqual(check_dict["Manufacturer / Packer"], "PASS")
        self.assertEqual(check_dict["Date of Manufacture / Packing"], "PASS")
