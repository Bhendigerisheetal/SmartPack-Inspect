from django.urls import path

from . import views

app_name = 'inspection'

urlpatterns = [

    # Dashboard
    path(
        '',
        views.home,
        name='home'
    ),

    # Upload / Inspection
    path(
        'upload/',
        views.upload,
        name='upload'
    ),

    # Inspection History
    path(
        'history/',
        views.history,
        name='history'
    ),

    # View Individual Inspection
    path(
        'history/<str:inspection_id>/',
        views.inspection_detail,
        name='inspection_detail'
    ),

    # Delete Individual Inspection
    path(
        'history/<str:inspection_id>/delete/',
        views.delete_inspection,
        name='delete_inspection'
    ),

    # Legal Metrology Rules
    path(
        'rules/',
        views.rules,
        name='rules'
    ),

    # Inspection Reports
    path(
        'reports/',
        views.reports,
        name='reports'
    ),

    # Download individual inspection report as PDF
    path(
        'reports/<str:inspection_id>/download/',
        views.download_report,
        name='download_report'
    ),

    # System Information
    path(
        'system-info/',
        views.system_info,
        name='system_info'
    ),
]