"""
Legal Metrology Rule Engine for SmartPack Inspect.
Evaluates extracted fields against statutory declarations under:
Legal Metrology Act, 2009 & Legal Metrology (Packaged Commodities) Rules, 2011.

Academic Decision-Support Categorization:
- COMPLIANT
- NEEDS REVIEW
- POTENTIAL NON-COMPLIANCE
"""

def evaluate_compliance(extracted_data: dict, commodity_category: str = "food_general", ocr_confidence: float = 85.0) -> dict:
    """
    Evaluates extracted fields against statutory requirements.
    Returns checklist results and overall decision-support status.
    """
    checks = []
    issues = []
    
    # Check 1: Product / Commodity Name (Rule 6(1)(b))
    product_name = extracted_data.get('product_name')
    if product_name and product_name != "Not Detected":
        checks.append({
            'field': 'Product / Generic Name',
            'rule_id': 'LM-R02',
            'requirement': 'Generic or specific commodity identification (Rule 6(1)(b))',
            'extracted_value': product_name,
            'status': 'PASS',
            'reason': 'Generic or branded commodity name clearly identified on label.',
            'statutory_reference': 'Rule 6(1)(b), LM (Packaged Commodities) Rules, 2011'
        })
    else:
        checks.append({
            'field': 'Product / Generic Name',
            'rule_id': 'LM-R02',
            'requirement': 'Generic or specific commodity identification (Rule 6(1)(b))',
            'extracted_value': 'Not Detected',
            'status': 'NEEDS_REVIEW',
            'reason': 'Commodity name could not be confidently isolated from the label text.',
            'statutory_reference': 'Rule 6(1)(b), LM (Packaged Commodities) Rules, 2011'
        })
        issues.append('Product name declaration requires manual verification.')

    # Check 2: Net Quantity (Rule 6(1)(c) & Rule 12)
    net_qty = extracted_data.get('net_quantity')
    net_unit = extracted_data.get('net_quantity_unit')
    standard_units = ['g', 'gm', 'gms', 'gram', 'grams', 'kg', 'kgs', 'kilogram', 'ml', 'l', 'ltr', 'litre']
    
    if net_qty and net_unit in standard_units:
        checks.append({
            'field': 'Net Quantity',
            'rule_id': 'LM-R03',
            'requirement': 'Standard metric unit of weight/volume declaration (Rule 6(1)(c), Rule 12)',
            'extracted_value': net_qty,
            'status': 'PASS',
            'reason': f'Declared in prescribed metric unit ({net_unit}).',
            'statutory_reference': 'Rule 6(1)(c) & Rule 12, LM Rules, 2011'
        })
    elif net_qty and 'Declared' in net_qty:
        checks.append({
            'field': 'Net Quantity',
            'rule_id': 'LM-R03',
            'requirement': 'Standard metric unit of weight/volume declaration (Rule 6(1)(c), Rule 12)',
            'extracted_value': net_qty,
            'status': 'NEEDS_REVIEW',
            'reason': 'Net quantity label section detected, but numeric value requires verification from inkjet coding area.',
            'statutory_reference': 'Rule 6(1)(c) & Rule 12, LM Rules, 2011'
        })
        issues.append('Net quantity value should be verified from coding window.')
    elif net_qty:
        checks.append({
            'field': 'Net Quantity',
            'rule_id': 'LM-R03',
            'requirement': 'Standard metric unit of weight/volume declaration (Rule 6(1)(c), Rule 12)',
            'extracted_value': net_qty,
            'status': 'NEEDS_REVIEW',
            'reason': 'Net quantity detected but unit format requires verification.',
            'statutory_reference': 'Rule 12, LM Rules, 2011'
        })
        issues.append('Net quantity format needs review.')
    else:
        checks.append({
            'field': 'Net Quantity',
            'rule_id': 'LM-R03',
            'requirement': 'Standard metric unit of weight/volume declaration (Rule 6(1)(c), Rule 12)',
            'extracted_value': 'Missing / Unreadable',
            'status': 'POTENTIAL_NON_COMPLIANCE',
            'reason': 'Mandatory net quantity declaration was not identified.',
            'statutory_reference': 'Rule 6(1)(c), LM Rules, 2011'
        })
        issues.append('Mandatory Net Quantity declaration is missing or unreadable.')

    # Check 3: Maximum Retail Price (MRP) (Rule 6(1)(e))
    mrp = extracted_data.get('mrp')
    if mrp and mrp.startswith('₹'):
        checks.append({
            'field': 'Maximum Retail Price (MRP)',
            'rule_id': 'LM-R05',
            'requirement': 'Retail sale price inclusive of all taxes (Rule 6(1)(e))',
            'extracted_value': mrp,
            'status': 'PASS',
            'reason': 'MRP declared with monetary denomination.',
            'statutory_reference': 'Rule 6(1)(e), LM Rules, 2011'
        })
    elif mrp and 'Declared' in mrp:
        checks.append({
            'field': 'Maximum Retail Price (MRP)',
            'rule_id': 'LM-R05',
            'requirement': 'Retail sale price inclusive of all taxes (Rule 6(1)(e))',
            'extracted_value': mrp,
            'status': 'NEEDS_REVIEW',
            'reason': 'MRP statutory statement found on packaging; verify specific amount in stamped coding box.',
            'statutory_reference': 'Rule 6(1)(e), LM Rules, 2011'
        })
        issues.append('MRP amount should be confirmed from coding window.')
    elif mrp:
        checks.append({
            'field': 'Maximum Retail Price (MRP)',
            'rule_id': 'LM-R05',
            'requirement': 'Retail sale price inclusive of all taxes (Rule 6(1)(e))',
            'extracted_value': mrp,
            'status': 'PASS',
            'reason': 'Retail price declaration identified.',
            'statutory_reference': 'Rule 6(1)(e), LM Rules, 2011'
        })
    else:
        checks.append({
            'field': 'Maximum Retail Price (MRP)',
            'rule_id': 'LM-R05',
            'requirement': 'Retail sale price inclusive of all taxes (Rule 6(1)(e))',
            'extracted_value': 'Not Detected',
            'status': 'POTENTIAL_NON_COMPLIANCE',
            'reason': 'Mandatory retail price declaration was not detected.',
            'statutory_reference': 'Rule 6(1)(e), LM Rules, 2011'
        })
        issues.append('Mandatory MRP declaration was not detected.')

    # Check 4: Manufacturer / Packer Details (Rule 6(1)(a))
    mfg = extracted_data.get('manufacturer')
    if mfg:
        checks.append({
            'field': 'Manufacturer / Packer',
            'rule_id': 'LM-R01',
            'requirement': 'Name and complete address of manufacturer/packer (Rule 6(1)(a))',
            'extracted_value': mfg,
            'status': 'PASS',
            'reason': 'Manufacturer or packer identity and address detected.',
            'statutory_reference': 'Rule 6(1)(a), LM Rules, 2011'
        })
    else:
        checks.append({
            'field': 'Manufacturer / Packer',
            'rule_id': 'LM-R01',
            'requirement': 'Name and complete address of manufacturer/packer (Rule 6(1)(a))',
            'extracted_value': 'Not Detected',
            'status': 'NEEDS_REVIEW',
            'reason': 'Manufacturer information could not be confidently parsed.',
            'statutory_reference': 'Rule 6(1)(a), LM Rules, 2011'
        })
        issues.append('Manufacturer information could not be isolated.')

    # Check 5: Date Information (MFD / PKD) (Rule 6(1)(d))
    date_info = extracted_data.get('date_info')
    if date_info and 'present' not in str(date_info).lower():
        checks.append({
            'field': 'Date of Manufacture / Packing',
            'rule_id': 'LM-R04',
            'requirement': 'Month and year of manufacture or packing (Rule 6(1)(d))',
            'extracted_value': date_info,
            'status': 'PASS',
            'reason': 'Manufacturing or packaging date detected.',
            'statutory_reference': 'Rule 6(1)(d), LM Rules, 2011'
        })
    elif date_info:
        checks.append({
            'field': 'Date of Manufacture / Packing',
            'rule_id': 'LM-R04',
            'requirement': 'Month and year of manufacture or packing (Rule 6(1)(d))',
            'extracted_value': date_info,
            'status': 'NEEDS_REVIEW',
            'reason': 'Date declaration label detected; verify date stamped in batch section.',
            'statutory_reference': 'Rule 6(1)(d), LM Rules, 2011'
        })
    else:
        checks.append({
            'field': 'Date of Manufacture / Packing',
            'rule_id': 'LM-R04',
            'requirement': 'Month and year of manufacture or packing (Rule 6(1)(d))',
            'extracted_value': 'Not Detected',
            'status': 'NEEDS_REVIEW',
            'reason': 'Manufacturing / packing date could not be isolated.',
            'statutory_reference': 'Rule 6(1)(d), LM Rules, 2011'
        })
        issues.append('Date of manufacture or packaging requires manual verification.')

    # Check 6: Consumer Care Information (Rule 6(1)(n))
    care_info = extracted_data.get('consumer_care')
    if care_info:
        checks.append({
            'field': 'Consumer Care Details',
            'rule_id': 'LM-R06',
            'requirement': 'Consumer helpline, contact person or email (Rule 6(1)(n))',
            'extracted_value': care_info,
            'status': 'PASS',
            'reason': 'Consumer helpline telephone or email contact information detected.',
            'statutory_reference': 'Rule 6(1)(n), LM Rules, 2011'
        })
    else:
        checks.append({
            'field': 'Consumer Care Details',
            'rule_id': 'LM-R06',
            'requirement': 'Consumer helpline, contact person or email (Rule 6(1)(n))',
            'extracted_value': 'Not Detected',
            'status': 'NEEDS_REVIEW',
            'reason': 'Consumer care details could not be detected from visible panel.',
            'statutory_reference': 'Rule 6(1)(n), LM Rules, 2011'
        })

    # Overall Status Calculation
    statuses = [c['status'] for c in checks]
    if 'POTENTIAL_NON_COMPLIANCE' in statuses:
        overall_status = 'POTENTIAL_NON_COMPLIANCE'
        status_label = 'POTENTIAL NON-COMPLIANCE'
        status_theme = 'danger'
    elif 'NEEDS_REVIEW' in statuses or ocr_confidence < 60.0:
        overall_status = 'NEEDS_REVIEW'
        status_label = 'NEEDS REVIEW'
        status_theme = 'warning'
    else:
        overall_status = 'COMPLIANT'
        status_label = 'COMPLIANT'
        status_theme = 'success'

    pass_count = sum(1 for s in statuses if s == 'PASS')
    total_count = len(statuses)
    compliance_score = round((pass_count / total_count) * 100, 1)

    return {
        'overall_status': overall_status,
        'status_label': status_label,
        'status_theme': status_theme,
        'compliance_score': compliance_score,
        'pass_count': pass_count,
        'total_count': total_count,
        'checks': checks,
        'issues': issues
    }
