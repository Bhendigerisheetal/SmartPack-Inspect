// SmartPack Inspect - Client-Side Interactive Handling

document.addEventListener('DOMContentLoaded', function () {
    const fileInput = document.getElementById('productImageInput');
    const dropzone = document.getElementById('uploadDropzone');
    const previewContainer = document.getElementById('previewContainer');
    const previewImage = document.getElementById('previewImage');
    const uploadPrompt = document.getElementById('uploadPrompt');
    const selectedFileInfo = document.getElementById('selectedFileInfo');
    const fileNameSpan = document.getElementById('selectedFileName');
    const fileSizeSpan = document.getElementById('selectedFileSize');
    const submitBtn = document.getElementById('submitBtn');
    const resetBtn = document.getElementById('resetImageBtn');

    if (!fileInput) return;

    function handleFileSelection(file) {
        if (!file) return;

        // Validation for client-side feedback
        const validTypes = ['image/jpeg', 'image/png', 'image/jpg'];
        if (!validTypes.includes(file.type)) {
            alert('Unsupported file format. Please upload a JPG or PNG image.');
            return;
        }

        const maxBytes = 10 * 1024 * 1024; // 10MB
        if (file.size > maxBytes) {
            alert('File exceeds 10MB limit. Please select a smaller image.');
            return;
        }

        // Show file details
        if (fileNameSpan) fileNameSpan.textContent = file.name;
        if (fileSizeSpan) fileSizeSpan.textContent = `(${(file.size / 1024).toFixed(1)} KB)`;
        if (selectedFileInfo) selectedFileInfo.classList.remove('d-none');
        if (uploadPrompt) uploadPrompt.classList.add('d-none');

        // Render preview
        const reader = new FileReader();
        reader.onload = function (e) {
            if (previewImage) {
                previewImage.src = e.target.result;
            }
            if (previewContainer) {
                previewContainer.style.display = 'block';
            }
        };
        reader.readAsDataURL(file);

        if (submitBtn) {
            submitBtn.disabled = false;
        }
    }

    fileInput.addEventListener('change', function (e) {
        if (this.files && this.files[0]) {
            handleFileSelection(this.files[0]);
        }
    });

    // Drag & Drop
    if (dropzone) {
        ['dragenter', 'dragover'].forEach(eventName => {
            dropzone.addEventListener(eventName, function (e) {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.add('dragover');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropzone.addEventListener(eventName, function (e) {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.remove('dragover');
            }, false);
        });

        dropzone.addEventListener('drop', function (e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files && files.length > 0) {
                fileInput.files = files;
                handleFileSelection(files[0]);
            }
        });
    }

    if (resetBtn) {
        resetBtn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            fileInput.value = '';
            if (previewContainer) previewContainer.style.display = 'none';
            if (selectedFileInfo) selectedFileInfo.classList.add('d-none');
            if (uploadPrompt) uploadPrompt.classList.remove('d-none');
            if (submitBtn) submitBtn.disabled = true;
        });
    }
});
