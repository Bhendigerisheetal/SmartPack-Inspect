from django.db import models


class Inspection(models.Model):
    """
    Stores the result of one SmartPack Inspect inspection.
    """

    inspection_id = models.CharField(
        max_length=30,
        unique=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    # Uploaded product image
    file_name = models.CharField(
        max_length=255
    )

    image = models.CharField(
        max_length=500,
        blank=True
    )

    # Product information
    commodity_type = models.CharField(
        max_length=100,
        blank=True
    )

    product_name = models.CharField(
        max_length=255,
        blank=True
    )

    net_quantity = models.CharField(
        max_length=100,
        blank=True
    )

    mrp = models.CharField(
        max_length=100,
        blank=True
    )

    manufacturer = models.CharField(
        max_length=255,
        blank=True
    )

    # OCR information
    ocr_confidence = models.FloatField(
        default=0.0
    )

    raw_text = models.TextField(
        blank=True
    )

    # Compliance information
    compliance_status = models.CharField(
        max_length=50,
        blank=True
    )

    # Store extracted fields and rule results
    extracted_fields = models.JSONField(
        default=dict,
        blank=True
    )

    rule_assessment = models.JSONField(
        default=dict,
        blank=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.inspection_id} - {self.product_name}"