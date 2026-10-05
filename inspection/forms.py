from django import forms
from django.core.exceptions import ValidationError
import os

ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png']
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

class ProductImageUploadForm(forms.Form):
    """
    Form for uploading packaged product images for verification.
    Validates file extension and size safely.
    """
    commodity_type = forms.ChoiceField(
        required=False,
        choices=[
            ('food_general', 'Packaged Food (General)'),
            ('biscuits', 'Biscuits & Cookies'),
            ('flour', 'Flour / Atta / Grains'),
            ('snacks', 'Snacks & Confectionery'),
            ('other', 'Other Packaged Commodity'),
        ],
        initial='food_general',
        widget=forms.Select(attrs={
            'class': 'form-select select-custom',
            'id': 'commodityTypeSelect'
        }),
        label="Commodity Category"
    )

    image = forms.ImageField(
        required=True,
        widget=forms.FileInput(attrs={
            'class': 'file-input-hidden',
            'id': 'productImageInput',
            'accept': 'image/jpeg,image/png,image/jpg'
        }),
        label="Product Image",
        error_messages={
            'required': 'Please select a product label image to proceed.',
            'invalid_image': 'The selected file is not a valid image format (PNG, JPG, JPEG only).'
        }
    )

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if not image:
            raise ValidationError("No image file provided.")

        # Validate file extension
        ext = os.path.splitext(image.name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValidationError(
                f"Unsupported file format '{ext}'. Allowed formats are JPG, JPEG, and PNG."
            )

        # Validate file size
        if image.size > MAX_FILE_SIZE_BYTES:
            raise ValidationError(
                f"File size exceeds {MAX_FILE_SIZE_MB}MB limit ({image.size / (1024 * 1024):.2f}MB detected). Please upload a smaller image."
            )

        return image
