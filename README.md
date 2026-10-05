# SmartPack Inspect – IoT and AI-Based Package Verification System

Based on **SIH Problem Statement SIH26034**  
*An IoT and AI-assisted decision-support system for packaged-commodity verification under Legal Metrology requirements.*

---

## 📌 Project Overview
SmartPack Inspect is an academic decision-support prototype designed to assist inspectors in verifying packaged commodities against statutory packaging declarations. 

The system verifies printed label declarations (Product Name, Net Quantity, MRP, Manufacturer/Packer, Date) using computer vision and OCR (Mode 1), and bridges this in a later phase with physical load-cell weight measurements collected via an ESP32 IoT platform (Mode 2).

> **Important Regulatory Notice:**  
> This system is an academic decision-support aid and does not issue legal determinations of criminality or official government certification. Compliance statuses are designated as:
> 1. `COMPLIANT`
> 2. `NEEDS REVIEW`
> 3. `POTENTIAL NON-COMPLIANCE` (with specific statutory reasons provided).

---

## 🏗️ Architecture & Phased Roadmap

```
                 SMARTPACK INSPECT

                     PRODUCT
                        |
          +-------------+-------------+
          |                           |
     IMAGE UPLOAD                PHYSICAL PRODUCT
          |                         (LATER)
       OpenCV                         |
          |                       Camera
       OCR                             |
          |                           OCR
          |                           |
          |                       Load Cell
          |                           |
          |                         ESP32
          |                           |
          +-------------+-------------+
                        |
                 Django Backend
                        |
              Information Extraction
                        |
                MongoDB Database
                        |
                 Rule Engine
                        |
             Compliance Assessment
                        |
                  Dashboard
                        |
                    Report
```

---

## 📁 Project Structure

```
SmartPack/
│
├── manage.py                          # Django management script
│
├── smartpack/                         # Django project configuration
│   ├── __init__.py
│   ├── settings.py                    # Settings (App, Static, Media config)
│   ├── urls.py                        # Root URL routing + media serving
│   ├── asgi.py
│   └── wsgi.py
│
├── inspection/                        # Core inspection application
│   ├── migrations/                    # Database migrations
│   ├── templates/inspection/          # Presentation templates
│   │   ├── base.html                  # Master layout with navigation & notices
│   │   ├── home.html                  # Landing dashboard & workflow overview
│   │   ├── upload.html                # Image upload, preview & verification UI
│   │   ├── history.html               # Inspection history & audit repository
│   │   ├── result.html                # Compliance result dashboard
│   │   ├── report.html                # Inspection reports & exports
│   │   └── rules.html                 # Legal Metrology rules repository
│   │
│   ├── static/inspection/             # Static assets
│   │   ├── css/style.css              # Custom dashboard styling
│   │   ├── js/main.js                 # Drag-drop & instant image preview logic
│   │   └── images/                    # Static graphics
│   │
│   ├── services/                      # Modular backend pipeline services
│   │   ├── __init__.py
│   │   ├── ocr_service.py             # OpenCV + Tesseract OCR (Phase 3)
│   │   ├── extraction_service.py      # Regex field extraction (Phase 4)
│   │   ├── rule_engine.py             # Legal Metrology rules evaluator (Phase 7)
│   │   └── report_service.py          # Report generator (Phase 10)
│   │
│   ├── utils/                         # Helper utilities
│   │   └── __init__.py
│   │
│   ├── forms.py                       # Form validation (MIME, file size, extensions)
│   ├── views.py                       # View controllers for Phase 1
│   ├── urls.py                        # App route definitions
│   └── models.py                      # Django ORM models
│
├── media/                             # Uploaded media storage
│   └── products/                      # Uploaded package photos
│
├── requirements.txt                   # Project dependencies
└── README.md                          # Project documentation
```

---

## 🚀 Running the Phase 1 Prototype

### 1. Check Python & Dependencies
Ensure Python 3.10+ is installed:
```bash
python --version
pip install -r requirements.txt
```

### 2. Apply Initial Migrations
```bash
python manage.py migrate
```

### 3. Run Development Server
```bash
python manage.py runserver
```

### 4. Open in Browser
Visit:
- **Dashboard / Home**: `http://127.0.0.1:8000/`
- **New Inspection / Upload UI**: `http://127.0.0.1:8000/upload/`
- **Inspection History**: `http://127.0.0.1:8000/history/`
- **Rules Repository**: `http://127.0.0.1:8000/rules/`
- **System Information**: `http://127.0.0.1:8000/system-info/`
