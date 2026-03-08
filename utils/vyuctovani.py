"""
Vyúčtování module - Wayne Fleet Management System
CSV parsing and PDF generation for driver invoices
Extracted from uber_bolt_viewer.py
"""

import io
import csv
import unicodedata
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

# Použijeme standardní fonty
DEFAULT_FONT = 'Helvetica'
BOLD_FONT = 'Helvetica-Bold'

def to_ascii(text):
    """Převede text s diakritikou na ASCII (č -> c, ř -> r, atd.)"""
    if isinstance(text, str):
        # Normalizovat a odstranit diakritiku
        nfkd = unicodedata.normalize('NFKD', text)
        return ''.join([c for c in nfkd if not unicodedata.combining(c)])
    return text


def normalize_name(name):
    """Normalizuje jméno pro srovnání - odstraní diakritiku a mezery"""
    # Odstranit diakritiku
    name = unicodedata.normalize('NFD', name)
    name = ''.join(char for char in name if unicodedata.category(char) != 'Mn')
    # Převést na malá písmena a odstranit mezery
    return name.lower().replace(' ', '').strip()


def parse_uber_csv(file_content):
    """
    Parsuje Uber CSV a vrací data po řidičích
    
    OPRAVENÁ LOGIKA:
    - "Tvůj výdělek" = ČISTÁ mzda (po odečtení poplatku)
    - "Servisní poplatek" = Poplatek (provize)
    - HRUBÁ mzda = Tvůj výdělek + abs(Servisní poplatek)
    - Hotovost = abs(Vybraná hotovost)
    
    Returns:
        dict: {normalized_name: {'name': str, 'uber_amount': float (HRUBÁ), 'uber_commission': float, 'uber_hotovost': float}}
    """
    data = {}
    
    # Detekce encodingu
    encodings = ['utf-8', 'utf-8-sig', 'windows-1250', 'iso-8859-2']
    
    for encoding in encodings:
        try:
            content = file_content.decode(encoding)
            break
        except:
            continue
    else:
        content = file_content.decode('utf-8', errors='ignore')
    
    # Parse CSV
    reader = csv.DictReader(io.StringIO(content))
    
    for row in reader:
        first_name = row.get('Křestní jméno řidiče', '').strip()
        last_name = row.get('Příjmení řidiče', '').strip()
        
        if not first_name and not last_name:
            continue
        
        full_name = f"{first_name} {last_name}".strip()
        normalized = normalize_name(full_name)
        
        # ČISTÁ MZDA = "Tvůj výdělek"
        cista_mzda_str = row.get('Zaplatili jsme ti : Tvůj výdělek', '').strip()
        if not cista_mzda_str:
            cista_mzda_str = '0'
        cista_mzda_str = cista_mzda_str.replace(',', '.')
        try:
            cista_mzda = float(cista_mzda_str)
            if cista_mzda < 0:
                cista_mzda = 0
        except:
            cista_mzda = 0
        
        # POPLATEK = abs(Servisní poplatek)
        commission_str = row.get('Zaplatili jsme ti:Tvůj výdělek:Servisní poplatek', '').strip()
        if not commission_str:
            commission_str = '0'
        commission_str = commission_str.replace(',', '.')
        try:
            commission = abs(float(commission_str))
        except:
            commission = 0
        
        # HRUBÁ MZDA = Čistá + Poplatek
        amount = cista_mzda + commission
        
        # HOTOVOST = abs(Vybraná hotovost)
        hotovost_str = row.get('Zaplatili jsme ti : Zůstatek jízdného : Platby : Vybraná hotovost', '').strip()
        if not hotovost_str:
            hotovost_str = '0'
        hotovost_str = hotovost_str.replace(',', '.')
        try:
            hotovost = abs(float(hotovost_str))
        except:
            hotovost = 0
        
        # Pouze pokud má nějaké příjmy nebo provizi
        if amount > 0 or commission > 0:
            if normalized not in data:
                data[normalized] = {
                    'name': full_name,
                    'uber_amount': 0,
                    'uber_commission': 0,
                    'uber_hotovost': 0
                }
            
            data[normalized]['uber_amount'] += amount
            data[normalized]['uber_commission'] += commission
            data[normalized]['uber_hotovost'] += hotovost
    
    return data


def parse_bolt_csv(file_content):
    """
    Parsuje Bolt CSV a vrací data po řidičích
    
    SPRÁVNÁ LOGIKA:
    - Pro vyúčtování: Čisté výdělky - Vybraná hotovost = co přišlo na účet
    - DPH: Provize x 0.21
    - Hotovost: ukládat pro zobrazení v PDF
    - Ignorovat řidiče co mají záporný výsledek (odevzdali víc než vydělali)
    
    Returns:
        dict: {normalized_name: {'name': str, 'bolt_amount': float, 'bolt_commission': float, 'bolt_hotovost': float}}
    """
    data = {}
    
    # Detekce encodingu
    encodings = ['utf-8-sig', 'utf-8', 'windows-1250', 'iso-8859-2']
    
    for encoding in encodings:
        try:
            content = file_content.decode(encoding)
            break
        except:
            continue
    else:
        content = file_content.decode('utf-8', errors='ignore')
    
    # Parse CSV - Bolt má quotes kolem header names
    reader = csv.DictReader(io.StringIO(content))
    
    for row in reader:
        # Bolt CSV může mít quotes kolem názvu sloupce
        driver_name = row.get('Řidič', '') or row.get('"Řidič"', '')
        driver_name = driver_name.strip().strip('"')
        
        if not driver_name:
            continue
        
        normalized = normalize_name(driver_name)
        
        # Načíst Čisté výdělky (co přišlo na účet)
        ciste_vydelky_str = (row.get('Čisté výdělky|Kč', '') or
                            row.get('"Čisté výdělky|Kč"', '') or
                            row.get('Čisté výdělky', '') or 
                            row.get('"Čisté výdělky"', '0'))
        ciste_vydelky_str = ciste_vydelky_str.replace(',', '.').replace('Kč', '').strip()
        if not ciste_vydelky_str:
            ciste_vydelky_str = '0'
        try:
            ciste_vydelky = float(ciste_vydelky_str)
        except:
            ciste_vydelky = 0
        
        # Načíst Vybranou hotovost
        vybrana_hotovost_str = (row.get('Vybraná hotovost|Kč', '0') or 
                               row.get('"Vybraná hotovost|Kč"', '0'))
        vybrana_hotovost_str = vybrana_hotovost_str.replace(',', '.').replace('Kč', '').strip()
        if not vybrana_hotovost_str:
            vybrana_hotovost_str = '0'
        try:
            vybrana_hotovost = abs(float(vybrana_hotovost_str))
        except:
            vybrana_hotovost = 0
        
        # Načíst Provizi (pro DPH)
        commission_str = (row.get('Provize|Kč', '0') or 
                         row.get('"Provize|Kč"', '0'))
        commission_str = commission_str.replace(',', '.').replace('Kč', '').strip()
        if not commission_str:
            commission_str = '0'
        try:
            commission = abs(float(commission_str))
        except:
            commission = 0
        
        # SPRÁVNÝ výpočet: Celková mzda = Čisté výdělky + Provize
        # (Bolt "Čisté výdělky" = už bez provize, takže ji musíme přičíst zpět)
        amount = ciste_vydelky + commission
        
        # Pokud je záporné, nastavit na 0
        if amount < 0:
            amount = 0
        
        # Pouze pokud má nějaké příjmy nebo provizi
        if amount > 0 or commission > 0:
            if normalized not in data:
                data[normalized] = {
                    'name': driver_name,
                    'bolt_amount': 0,
                    'bolt_commission': 0,
                    'bolt_hotovost': 0
                }
            
            data[normalized]['bolt_amount'] += amount
            data[normalized]['bolt_commission'] += commission
            data[normalized]['bolt_hotovost'] += vybrana_hotovost
    
    return data


def generate_driver_invoice_pdf(driver_name, uber_amount, bolt_amount, vat_amount,
                                  period_start, period_end, license_plate="",
                                  num_days=7, kauce=1250, penalties=0, palivo=0,
                                  uber_hotovost=0, bolt_hotovost=0,
                                  najem_override=None, poplatek_override=None,
                                  vlastni_vuz=False):
    """Generuje PDF vyúčtování pro řidiče"""
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=10*mm, bottomMargin=10*mm)
    story = []
    
    styles = getSampleStyleSheet()
    
    # Vlastní styly
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=15,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#374151'),
        spaceAfter=8,
        spaceBefore=10,
        fontName='Helvetica-Bold'
    )
    
    # Nadpis
    title_text = "TYDENNI VYUCTOVANI RIDICE - FLOTILA"
    story.append(Paragraph(title_text, title_style))
    story.append(Spacer(1, 6*mm))
    
    # Základní údaje
    story.append(Paragraph("Zakladni udaje", heading_style))
    
    basic_data = [
        ['Ridic:', driver_name],
        ['Obdobi (tyden):', f"{period_start} - {period_end}"],
        ['Vozidlo (SPZ):', license_plate if license_plate else '_______________']
    ]
    
    basic_table = Table(basic_data, colWidths=[40*mm, 120*mm])
    basic_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), DEFAULT_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), BOLD_FONT),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#374151')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(basic_table)
    story.append(Spacer(1, 5*mm))
    
    # Platforma - CELKOVÁ MZDA
    story.append(Paragraph(to_ascii("Celkova mzda (Uber + Bolt)"), heading_style))
    
    celkova_mzda = uber_amount + bolt_amount
    celkovy_poplatek = vat_amount / 0.21  # DPH je 21% z poplatku, takže poplatek = DPH / 0.21
    
    platform_data = [
        ['', to_ascii('Castka (Kc)')],
        ['Uber', f"{uber_amount:.2f}"],
        ['Bolt', f"{bolt_amount:.2f}"],
        ['Celkova mzda', f"{celkova_mzda:.2f}"]
    ]
    
    platform_table = Table(platform_data, colWidths=[100*mm, 60*mm])
    platform_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), DEFAULT_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), BOLD_FONT),
        ('FONTNAME', (0, 3), (-1, 3), BOLD_FONT),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5e7eb')),
        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#dbeafe')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(platform_table)
    story.append(Spacer(1, 5*mm))
    
    # POPLATEK (informativní)
    story.append(Paragraph(to_ascii("Poplatek a DPH"), heading_style))
    
    poplatek_data = [
        ['', to_ascii('Castka (Kc)')],
        [to_ascii('Poplatek platforme'), f"{celkovy_poplatek:.2f}"],
        [to_ascii('DPH (odvede flotila)'), f"{vat_amount:.2f}"],
        [to_ascii('Celkem srazky'), f"{celkovy_poplatek + vat_amount:.2f}"]
    ]
    
    poplatek_table = Table(poplatek_data, colWidths=[100*mm, 60*mm])
    poplatek_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), DEFAULT_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), BOLD_FONT),
        ('FONTNAME', (0, 3), (-1, 3), BOLD_FONT),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5e7eb')),
        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#fee2e2')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(poplatek_table)
    story.append(Spacer(1, 5*mm))
    
    # ČISTÁ MZDA
    story.append(Paragraph(to_ascii("Cista mzda"), heading_style))
    
    cista_mzda = celkova_mzda - celkovy_poplatek - vat_amount  # Odečíst i DPH!
    celkova_hotovost = uber_hotovost + bolt_hotovost
    
    cista_data = [
        ['', to_ascii('Castka (Kc)')],
        ['Celkova mzda', f"{celkova_mzda:.2f}"],
        ['Poplatek', f"-{celkovy_poplatek:.2f}"],
        ['DPH (21%)', f"-{vat_amount:.2f}"],
        ['Cista mzda', f"{cista_mzda:.2f}"]
    ]
    
    cista_table = Table(cista_data, colWidths=[100*mm, 60*mm])
    cista_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), DEFAULT_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), BOLD_FONT),
        ('FONTNAME', (0, 4), (-1, 4), BOLD_FONT),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5e7eb')),
        ('BACKGROUND', (0, 4), (-1, 4), colors.HexColor('#dcfce7')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(cista_table)
    story.append(Spacer(1, 5*mm))
    
    # HOTOVOST A VÝPLATA
    story.append(Paragraph(to_ascii("Vyplata"), heading_style))
    
    k_vyplate = cista_mzda - celkova_hotovost
    
    vyplata_data = [
        ['', to_ascii('Castka (Kc)')],
        ['Cista mzda', f"{cista_mzda:.2f}"],
        ['Hotovost (Uber)', f"-{uber_hotovost:.2f}"],
        ['Hotovost (Bolt)', f"-{bolt_hotovost:.2f}"],
        ['K vyplate', f"{k_vyplate:.2f}"]
    ]
    
    vyplata_table = Table(vyplata_data, colWidths=[100*mm, 60*mm])
    vyplata_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), DEFAULT_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), BOLD_FONT),
        ('FONTNAME', (0, 4), (-1, 4), BOLD_FONT),
        ('FONTSIZE', (0, 4), (-1, 4), 12),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5e7eb')),
        ('BACKGROUND', (0, 4), (-1, 4), colors.HexColor('#dbeafe')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(vyplata_table)
    story.append(Spacer(1, 5*mm))
    
    # NÁKLADY VŮČI FLOTILE
    story.append(Paragraph(to_ascii("Naklady vuci flotile"), heading_style))
    
    # Výpočet nákladů
    if najem_override is not None:
        najem = najem_override
        najem_popis = to_ascii('Tydenni pronajem')
    else:
        najem = num_days * 800  # 800 Kc/den
        najem_popis = f'{num_days} dni x 800 Kc'

    if poplatek_override is not None:
        poplatek_flotila = poplatek_override
        poplatek_popis = to_ascii('Tydenni poplatek flotila')
    else:
        poplatek_flotila = num_days * 200  # 200 Kc/den
        poplatek_popis = f'{num_days} dni x 200 Kc'

    naklady_data = [
        [to_ascii('Polozka'), to_ascii('Vypocet'), to_ascii('Castka (Kc)')],
    ]
    if not vlastni_vuz:
        naklady_data.append([to_ascii('Najem vozidla'), najem_popis, f'{najem:.2f}'])
    naklady_data.append([to_ascii('Poplatek flotila'), poplatek_popis, f'{poplatek_flotila:.2f}'])
    
    # Přidat kauci pouze pokud je > 0
    if kauce > 0:
        naklady_data.append([to_ascii('Kauce (tydenni splatka)'), '', f'{kauce:.2f}'])
    
    # Přidat palivo pouze pokud > 0
    if palivo > 0:
        naklady_data.append([to_ascii('Palivo'), '', f'{palivo:.2f}'])
    
    # Přidat pokuty pouze pokud > 0
    if penalties > 0:
        naklady_data.append([to_ascii('Pokuty/skody'), '', f'{penalties:.2f}'])
    
    # Celkem náklady
    celkem_naklady = (0 if vlastni_vuz else najem) + poplatek_flotila + kauce + palivo + penalties
    naklady_data.append([to_ascii('Celkem naklady'), '', f'{celkem_naklady:.2f}'])
    
    naklady_table = Table(naklady_data, colWidths=[60*mm, 50*mm, 50*mm])
    naklady_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), DEFAULT_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, -1), (-1, -1), BOLD_FONT),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5e7eb')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fee2e2')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(naklady_table)
    story.append(Spacer(1, 5*mm))
    
    # FINÁLNÍ VÝSLEDEK
    story.append(Paragraph(to_ascii("Finalni vysledek"), heading_style))
    
    finalni_vysledek = k_vyplate - celkem_naklady
    
    vysledek_data = [
        ['', to_ascii('Castka (Kc)')],
        [to_ascii('K vyplate (po hotovosti)'), f'{k_vyplate:.2f}'],
        [to_ascii('Naklady vuci flotile'), f'-{celkem_naklady:.2f}'],
    ]
    
    # Určit zda řidič dostane nebo dluží
    if finalni_vysledek >= 0:
        vysledek_data.append([to_ascii('VYPLATA RIDICI'), f'{finalni_vysledek:.2f}'])
        bg_color = colors.HexColor('#dcfce7')  # Zelená
    else:
        vysledek_data.append([to_ascii('RIDIC DLUZI FLOTILE'), f'{abs(finalni_vysledek):.2f}'])
        bg_color = colors.HexColor('#fee2e2')  # Červená
    
    vysledek_table = Table(vysledek_data, colWidths=[100*mm, 60*mm])
    vysledek_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), DEFAULT_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, -1), (-1, -1), BOLD_FONT),
        ('FONTSIZE', (0, -1), (-1, -1), 12),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5e7eb')),
        ('BACKGROUND', (0, -1), (-1, -1), bg_color),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(vysledek_table)
    
    # Generovat PDF
    doc.build(story)
    buffer.seek(0)
    return buffer
