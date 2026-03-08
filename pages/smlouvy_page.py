"""
Smlouvy Page - Wayne Fleet Management System
Generování smluv: Pronájem vozidla, Dohoda o zprostředkování Bolt/Uber
"""

import io
import os
import streamlit as st
from datetime import date
from utils.cached_queries import cached_drivers as get_all_drivers, cached_cars as get_all_cars

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def _setup_fonts():
    """Registruje Arial (podporuje češtinu), fallback na Helvetica."""
    # Priorita: 1) assets/fonts/ (cloud + lokálně), 2) Windows systém, 3) Helvetica
    _base = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'fonts')
    _candidates = [
        (os.path.join(_base, 'arial.ttf'), os.path.join(_base, 'arialbd.ttf')),
        ('C:/Windows/Fonts/arial.ttf', 'C:/Windows/Fonts/arialbd.ttf'),
    ]
    for regular, bold in _candidates:
        try:
            pdfmetrics.registerFont(TTFont('CF', regular))
            pdfmetrics.registerFont(TTFont('CF-Bold', bold))
            return 'CF', 'CF-Bold'
        except Exception:
            continue
    return 'Helvetica', 'Helvetica-Bold'


FONT, FONT_BOLD = _setup_fonts()
W = A4[0] - 40 * mm  # použitelná šířka stránky


def _s():
    """Vrátí slovník stylů pro smlouvy."""
    return {
        'title': ParagraphStyle('title', fontName=FONT_BOLD, fontSize=13,
                                alignment=TA_CENTER, spaceAfter=4, leading=18),
        'subtitle': ParagraphStyle('subtitle', fontName=FONT, fontSize=10,
                                   alignment=TA_CENTER, spaceAfter=8, leading=14),
        'section': ParagraphStyle('section', fontName=FONT_BOLD, fontSize=11,
                                  alignment=TA_CENTER, spaceAfter=5, spaceBefore=8, leading=16),
        'h1': ParagraphStyle('h1', fontName=FONT_BOLD, fontSize=18,
                             spaceAfter=6, spaceBefore=4, leading=24),
        'h2': ParagraphStyle('h2', fontName=FONT_BOLD, fontSize=13,
                             spaceAfter=5, spaceBefore=8, leading=18),
        'label': ParagraphStyle('label', fontName=FONT_BOLD, fontSize=10,
                                spaceAfter=2, leading=14),
        'body': ParagraphStyle('body', fontName=FONT, fontSize=10,
                               spaceAfter=5, leading=14, alignment=TA_JUSTIFY),
        'field': ParagraphStyle('field', fontName=FONT, fontSize=10,
                                spaceAfter=4, leading=14),
    }


def _fld(label, value, s):
    """Vykreslí pole s hodnotou nebo čárou."""
    val = value if value else '_' * 40
    return Paragraph(f"<b>{label}:</b> {val}", s['field'])


def _sig_table(left_top, left_bottom, right_top, right_bottom=''):
    """Vytvoří podpisovou tabulku."""
    tbl = Table(
        [['_' * 32, '_' * 32],
         [left_top, right_top],
         [left_bottom, right_bottom]],
        colWidths=[W / 2, W / 2]
    )
    tbl.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    return tbl


# ─────────────────────────────────────────────────────────────────────────────
# PDF: Smlouva o pronájmu vozidla
# ─────────────────────────────────────────────────────────────────────────────

def generate_smlouva_pronajem_pdf(data: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    s = _s()
    story = []

    # Nadpis
    story.append(Paragraph("Smlouva o pronájmu vozidla", s['title']))
    story.append(Paragraph("Uzavřená mezi", s['subtitle']))
    story.append(Spacer(1, 3*mm))

    # Pronajímatel
    story.append(Paragraph("Pronajímatel:", s['label']))
    for line in [
        "Obchodní firma: <b>Wayne Fleet s.r.o.</b>",
        "Sídlo: Příčná 1892/4, 110 00, Praha 1 - Nové Město",
        "IČO: 24083127",
        "Zastoupená: Pavel Kropáč",
    ]:
        story.append(Paragraph(line, s['field']))
    story.append(Spacer(1, 3*mm))

    # Nájemce
    story.append(Paragraph("Nájemce:", s['label']))
    story.append(_fld("Jméno, příjmení / název firmy", data.get('jmeno'), s))
    story.append(_fld("Adresa trvalého bydliště / sídlo společnosti", data.get('adresa'), s))
    story.append(_fld("RČ / IČO", data.get('rc_ico'), s))
    story.append(_fld("Číslo OP, nebo pasu", data.get('op_pas'), s))
    story.append(_fld("Telefon", data.get('telefon'), s))
    story.append(_fld("Email", data.get('email'), s))
    story.append(Spacer(1, 3*mm))

    # §1 Předmět smlouvy
    story.append(Paragraph("1. Předmět smlouvy", s['section']))
    story.append(Paragraph("Osobní motorové vozidlo:", s['field']))
    znacka = data.get('znacka', '') or '_' * 20
    model_auto = data.get('model', '') or '_' * 30
    spz = data.get('spz', '') or '_' * 20
    vin = data.get('vin', '') or '_' * 30
    tbl = Table(
        [[f"Tovární značka: {znacka}", f"Model: {model_auto}"],
         [f"Registrační značka: {spz}", f"VIN: {vin}"]],
        colWidths=[W / 2, W / 2]
    )
    tbl.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 3*mm))

    # §2 Nabytí práva
    story.append(Paragraph("2. Nabytí práva k užívání automobilu", s['section']))
    story.append(Paragraph(
        "Nájemcem automobilu se osoba stává okamžikem nabytí účinnosti této smlouvy a uhrazení celé "
        "nájemní ceny za automobil. Automobil je určen pro užívání pouze na území České republiky. "
        "Řidič je vždy povinen nahlásit den předem cestu do zahraničí, pokud tak neučiní, bude sankciován.",
        s['body']))
    story.append(Paragraph(
        "Pronajímatel a nájemce se dohodli na ceně <b>800,- Kč (slovy: osm set korun českých)</b> "
        "za jeden den (12hodinová směna).", s['body']))
    od = data.get('obdobi_od', '_' * 15)
    do = data.get('obdobi_do', '_' * 15)
    story.append(Paragraph(f"na období od: {od}  do: {do}", s['field']))
    story.append(Paragraph(
        "Vratná kauce: <b>10 000,- Kč</b> — hrazena ve <b>8 týdenních splátkách po 1 250,- Kč.</b>",
        s['body']))
    story.append(Paragraph(
        "Vratná kauce je splatná po uplynutí lhůty 60 dnů od ukončení smlouvy o pronájmu, "
        "aby z této kauce mohly být hrazeny případné pokuty.", s['body']))
    story.append(Paragraph(
        "Platba bude uskutečněna v hotovosti 1x týdně, či vkladem na účet.", s['body']))
    cu = data.get('cislo_uctu', '') or '_' * 50
    story.append(Paragraph(f"Č.Ú.: {cu}", s['field']))
    story.append(Spacer(1, 3*mm))

    # §3 Předání automobilu
    story.append(Paragraph("3. Předání automobilu a přechod nebezpečí škody na automobilu", s['section']))
    story.append(Paragraph(
        "Pronajímatel předá automobil nájemci po zaplacení celé dohodnuté ceny v den a čas uvedeném "
        "v předávacím protokolu, jenž je nedílnou součástí této smlouvy. Od okamžiku převzetí automobilu "
        "nese nájemce plnou odpovědnost za dodržování veškerých právních předpisů týkající se provozu "
        "vozidel na pozemních komunikacích. Případné pokuty, které vzniknou v době trvání nájmu vozidla "
        "hradí nájemce. Pokud bude pokuta doručena pronajímateli, kvůli nezastižení řidiče na místě, "
        "vyzve pronajímatel nájemce k uhrazení této částky. Pokud nájemce neprokáže uhrazení pokuty, "
        "pronajímatel předá totožnost nájemce, jakožto řidiče správnímu orgánu.", s['body']))
    story.append(Paragraph(
        "Nájemce se zavazuje řídit toto vozidlo přiměřeně s ohledem na jeho technický stav a stáří, "
        "zejména rozjíždět se a brzdit plynule, nikoli agresivně a na maximální výkon.", s['body']))
    story.append(Paragraph(
        "Pronajímatel prohlašuje, že vozidlo má platnou technickou prohlídku a pojištění odpovědnosti "
        "z provozu vozidla.", s['body']))
    story.append(Spacer(1, 3*mm))

    # §4 Palivo
    story.append(Paragraph("4. Palivo", s['section']))
    palivo = data.get('palivo', '') or '_' * 22
    csk_pal = data.get('cena_skody_palivo', '') or '_' * 15
    story.append(Paragraph(
        f"Palivem vozidla je {palivo}. Nájemce je povinen tankovat toto palivo.", s['body']))
    story.append(Paragraph(
        "Pokud nájemce natankuje jiné palivo a takto zahájí jízdu, je vysoce pravděpodobné, že tím způsobí "
        "totální škodu vozidla. V případě, kdy nájemce zavinil totální škodu vozidla, je povinen "
        "pronajímateli zaplatit cenu vozidla ve výši", s['body']))
    story.append(Paragraph(f"{csk_pal} Kč", s['field']))
    story.append(Paragraph(
        "Nájemce předá vozidlo zpět pronajímateli se stejným množstvím paliva, se kterým jej převzal. "
        "Při nižším stavu paliva nájemce uhradí rozdíl podle aktuálního ceníku čerpací stanice.", s['body']))
    story.append(Paragraph(
        "Nájemce je povinen doplnit všechny kapaliny tj: pohonné hmoty – nafta, cng, benzin, adblue, "
        "voda do ostřikovačů. Pokud všechny tyto kapaliny nebudou doplněny, bude pronajímateli zaúčtována "
        "celková cena těchto kapalin a následně pokuta 1 000,- Kč za nedodržení stanov této smlouvy.", s['body']))
    story.append(Spacer(1, 3*mm))

    # §5 Vybavení vozidla
    story.append(Paragraph("5. Vybavení vozidla", s['section']))
    story.append(Paragraph(
        "Automobil je plně vybaven jako vozidlo taxislužby. Nájemce přebírá odpovědnost za veškerá "
        "zařízení a součásti vozu, které jsou nedílnou součástí pronájmu vozidla. Nájemce je povinen "
        "pronajímateli bezodkladně nahlásit poškození vozidla, stejně jako jeho vybavení. Případná "
        "poškození vozidla i jeho vybavení hradí nájemce pronajímateli, pokud nebudou kryta havarijním "
        "pojištěním vozidla. Případně nájemce hradí rozdíl mezi skutečnou hodnotou poškozené součásti "
        "a pojistným plněním za tuto škodu.", s['body']))
    story.append(Paragraph(
        "Je výslovně zakázáno odebírat nebo vyměňovat součásti automobilu bez předchozího svolení "
        "pronajímatele. Stejně tak je zakázáno instalovat nová zařízení, např. tuning, lepit na vozidlo "
        "samolepky a podobně, pokud to pronajímatel nepovolí.", s['body']))
    story.append(Paragraph(
        "Základní údržbu provádí na vlastní náklady nájemce. Drobnými opravami se rozumí zejména: "
        "Výměna prasklých žárovek, výměna kola za rezervní, doplnění kapaliny do ostřikovačů, "
        "mytí čištění vozidla a podobně.", s['body']))
    story.append(Paragraph(
        "Standardní, pravidelná údržba vozidla je zahrnuta v ceně za pronájem a provádí ji pronajímatel. "
        "Jedná se zejména o: výměnu rozvodů, oleje, filtrů, brzdových destiček a podobně. Pokud v průběhu "
        "pronájmu nastane situace, kdy bude třeba takovou údržbu provést, informuje nájemce pronajímatele "
        "a ten určí další postup.", s['body']))
    story.append(Paragraph("Pravidelná kontrola vozu probíhá jednou za měsíc.", s['body']))
    story.append(Spacer(1, 3*mm))

    # §6 Doklady
    story.append(Paragraph("6. Doklady", s['section']))
    story.append(Paragraph(
        "Nájemce poskytuje souhlas pronajímateli s pořízením kopie občanského průkazu a řidičského "
        "průkazu pro účely evidence.", s['body']))
    story.append(Spacer(1, 3*mm))

    # §7 Odpovědnost za škodu
    story.append(Paragraph("7. Odpovědnost za škodu", s['section']))
    csk_poj = data.get('cena_skody_pojistovna', '') or '_' * 15
    story.append(Paragraph(
        "Pokud vzniklou škody, které budou předmětem pojistného plnění, je nájemce povinen splnit "
        "takovou spoluúčast jakou bude pojišťovna účtovat pronajímateli.", s['body']))
    story.append(Paragraph(
        f"Pokud na vozidle vznikne totální škoda, kterou neuhradí pojišťovna, uhradí nájemce "
        f"částku <b>{csk_poj} Kč</b>.", s['body']))
    story.append(Spacer(1, 3*mm))

    # §8 Sankce
    story.append(Paragraph("8. Sankce", s['section']))
    story.append(Paragraph(
        "Pokud nájemce nepředá vozidlo zpět pronajímateli do termínu určeném ve smlouvě, může "
        "pronajímatel naúčtovat nájemní smluvní pokutu ve výši 1 000,- Kč (jeden tisíc korun českých) "
        "za každý započatý den prodlení s vrácením vozidla a nájemce je povinen ji uhradit.", s['body']))
    story.append(Paragraph(
        "Nájemce je povinen informovat pronajímatele 1 měsíc předem před ukončením pronájmu.", s['body']))
    story.append(Paragraph(
        "Pokud nájemce nedodrží měsíční lhůtu, bude mu dopočítána celková suma nájmu pokrývající "
        "výpovědní lhůtu 1 měsíc.", s['body']))
    story.append(Paragraph(
        "Při nedodržení 1 měsíční výpovědní lhůty, automaticky propadá kauce.", s['body']))
    story.append(Paragraph(
        "Nájemce je povinné uhradit kauci ve výši <b>10 000,- Kč.</b>", s['body']))
    story.append(Paragraph(
        "Nájemce se zavazuje vrátit vozidlo osobně, toto vozidlo projde následně kompletní prohlídkou. "
        "Pokud nájemce nevrátí vozidlo osobně, nebude mu vystaven předávací protokol.", s['body']))
    story.append(Paragraph(
        "V tomto předávacím protokolu bude jasně uvedeno zdali vozidlo potřebuje další opravy za které "
        "je bezprostředně odpovědný nájemce, či jsou to běžné vady opotřebení.", s['body']))
    story.append(Paragraph(
        "Pokud bude vozidlo při vrácení znečištěné, bude nájemci účtována smluvní pokuta:", s['body']))
    story.append(Paragraph("6 500,- Kč za hloubkové čištění.", s['field']))
    story.append(Paragraph("2 000,- Kč za mytí karoserie a kol.", s['field']))
    story.append(Spacer(1, 3*mm))

    # §9 Závěrečná ustanovení
    story.append(Paragraph("9. Závěrečná ustanovení", s['section']))
    story.append(Paragraph(
        "Jakékoliv změny nebo dodatky této smlouvy, vyžadují písemnou formu, nebo elektronickou "
        "komunikaci emailem uvedeným v této smlouvě.", s['body']))
    story.append(Paragraph(
        "Smlouva má 3 strany, je vyhotovena ve dvou exemplářích, z nichž každá smluvní strana "
        "obdrží po jednom.", s['body']))
    story.append(Paragraph(
        "Smluvní strany prohlašují, že si smlouvu přečetly a prohlašují, že smlouva je projevem jejich "
        "pravé a svobodné vůle, že všem ujednáním porozuměly, případně se k jejich porozumění dotázal "
        "druhé smluvní strany a ta poskytla dostatečné vysvětlení, a na důkaz toho připojují své podpisy.",
        s['body']))
    story.append(Spacer(1, 8*mm))

    # Podpis
    datum_str = data.get('datum_podpisu', date.today().strftime('%d.%m.%Y'))
    story.append(Paragraph(f"V Praze dne {datum_str}  čas _______________", s['field']))
    story.append(Spacer(1, 12*mm))
    story.append(_sig_table("Za pronajímatele", "Wayne Fleet s.r.o.", "Nájemce", ""))

    doc.build(story)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# PDF: Smlouva o pronájmu vozidla – týdenní tarif
# ─────────────────────────────────────────────────────────────────────────────

def generate_smlouva_pronajem_tydeni_pdf(data: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    s = _s()
    story = []

    story.append(Paragraph("Smlouva o pronájmu vozidla", s['title']))
    story.append(Paragraph("Uzavřená mezi", s['subtitle']))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph("Pronajímatel:", s['label']))
    for line in [
        "Obchodní firma: <b>Wayne Fleet s.r.o.</b>",
        "Sídlo: Příčná 1892/4, 110 00, Praha 1 - Nové Město",
        "IČO: 24083127",
        "Zastoupená: Pavel Kropáč",
    ]:
        story.append(Paragraph(line, s['field']))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph("Nájemce:", s['label']))
    story.append(_fld("Jméno, příjmení / název firmy", data.get('jmeno'), s))
    story.append(_fld("Adresa trvalého bydliště / sídlo společnosti", data.get('adresa'), s))
    story.append(_fld("RČ / IČO", data.get('rc_ico'), s))
    story.append(_fld("Číslo OP, nebo pasu", data.get('op_pas'), s))
    story.append(_fld("Telefon", data.get('telefon'), s))
    story.append(_fld("Email", data.get('email'), s))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph("1. Předmět smlouvy", s['section']))
    story.append(Paragraph("Osobní motorové vozidlo:", s['field']))
    znacka = data.get('znacka', '') or '_' * 20
    model_auto = data.get('model', '') or '_' * 30
    spz = data.get('spz', '') or '_' * 20
    vin = data.get('vin', '') or '_' * 30
    tbl = Table(
        [[f"Tovární značka: {znacka}", f"Model: {model_auto}"],
         [f"Registrační značka: {spz}", f"VIN: {vin}"]],
        colWidths=[W / 2, W / 2]
    )
    tbl.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph("2. Nabytí práva k užívání automobilu", s['section']))
    story.append(Paragraph(
        "Nájemcem automobilu se osoba stává okamžikem nabytí účinnosti této smlouvy a uhrazení celé "
        "nájemní ceny za automobil. Automobil je určen pro užívání pouze na území České republiky. "
        "Řidič je vždy povinen nahlásit den předem cestu do zahraničí, pokud tak neučiní, bude sankciován.",
        s['body']))

    cena_tyden = data.get('cena_tyden', '')
    cena_tyden_slovy = data.get('cena_tyden_slovy', '')
    story.append(Paragraph(
        f"Pronajímatel a nájemce se dohodli na ceně <b>{cena_tyden} Kč (slovy: {cena_tyden_slovy})</b> "
        f"za jeden týden.", s['body']))

    od = data.get('obdobi_od', '_' * 15)
    do = data.get('obdobi_do', '_' * 15)
    story.append(Paragraph(f"na období od: {od}  do: {do}", s['field']))
    story.append(Paragraph(
        "Vratná kauce: <b>10 000,- Kč</b> — hrazena ve <b>8 týdenních splátkách po 1 250,- Kč.</b>",
        s['body']))
    story.append(Paragraph(
        "Vratná kauce je splatná po uplynutí lhůty 60 dnů od ukončení smlouvy o pronájmu, "
        "aby z této kauce mohly být hrazeny případné pokuty.", s['body']))
    story.append(Paragraph(
        "Platba bude uskutečněna v hotovosti 1x týdně, či vkladem na účet.", s['body']))
    cu = data.get('cislo_uctu', '') or '_' * 50
    story.append(Paragraph(f"Č.Ú.: {cu}", s['field']))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph("3. Předání automobilu a přechod nebezpečí škody na automobilu", s['section']))
    story.append(Paragraph(
        "Pronajímatel předá automobil nájemci po zaplacení celé dohodnuté ceny v den a čas uvedeném "
        "v předávacím protokolu, jenž je nedílnou součástí této smlouvy. Od okamžiku převzetí automobilu "
        "nese nájemce plnou odpovědnost za dodržování veškerých právních předpisů týkající se provozu "
        "vozidel na pozemních komunikacích. Případné pokuty, které vzniknou v době trvání nájmu vozidla "
        "hradí nájemce. Pokud bude pokuta doručena pronajímateli, kvůli nezastižení řidiče na místě, "
        "vyzve pronajímatel nájemce k uhrazení této částky. Pokud nájemce neprokáže uhrazení pokuty, "
        "pronajímatel předá totožnost nájemce, jakožto řidiče správnímu orgánu.", s['body']))
    story.append(Paragraph(
        "Nájemce se zavazuje řídit toto vozidlo přiměřeně s ohledem na jeho technický stav a stáří, "
        "zejména rozjíždět se a brzdit plynule, nikoli agresivně a na maximální výkon.", s['body']))
    story.append(Paragraph(
        "Pronajímatel prohlašuje, že vozidlo má platnou technickou prohlídku a pojištění odpovědnosti "
        "z provozu vozidla.", s['body']))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph("4. Palivo", s['section']))
    palivo = data.get('palivo', '') or '_' * 22
    csk_pal = data.get('cena_skody_palivo', '') or '_' * 15
    story.append(Paragraph(f"Palivem vozidla je {palivo}. Nájemce je povinen tankovat toto palivo.", s['body']))
    story.append(Paragraph(
        "Pokud nájemce natankuje jiné palivo a takto zahájí jízdu, je vysoce pravděpodobné, že tím způsobí "
        "totální škodu vozidla. V případě, kdy nájemce zavinil totální škodu vozidla, je povinen "
        "pronajímateli zaplatit cenu vozidla ve výši", s['body']))
    story.append(Paragraph(f"{csk_pal} Kč", s['field']))
    story.append(Paragraph(
        "Nájemce předá vozidlo zpět pronajímateli se stejným množstvím paliva, se kterým jej převzal. "
        "Při nižším stavu paliva nájemce uhradí rozdíl podle aktuálního ceníku čerpací stanice.", s['body']))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph("5. Vybavení vozidla", s['section']))
    story.append(Paragraph(
        "Automobil je plně vybaven jako vozidlo taxislužby. Nájemce přebírá odpovědnost za veškerá "
        "zařízení a součásti vozu, které jsou nedílnou součástí pronájmu vozidla. Nájemce je povinen "
        "pronajímateli bezodkladně nahlásit poškození vozidla, stejně jako jeho vybavení.", s['body']))
    story.append(Paragraph(
        "Standardní, pravidelná údržba vozidla je zahrnuta v ceně za pronájem a provádí ji pronajímatel. "
        "Pravidelná kontrola vozu probíhá jednou za měsíc.", s['body']))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph("6. Doklady", s['section']))
    story.append(Paragraph(
        "Nájemce poskytuje souhlas pronajímateli s pořízením kopie občanského průkazu a řidičského "
        "průkazu pro účely evidence.", s['body']))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph("7. Odpovědnost za škodu", s['section']))
    csk_poj = data.get('cena_skody_pojistovna', '') or '_' * 15
    story.append(Paragraph(
        "Pokud vzniklou škody, které budou předmětem pojistného plnění, je nájemce povinen splnit "
        "takovou spoluúčast jakou bude pojišťovna účtovat pronajímateli.", s['body']))
    story.append(Paragraph(
        f"Pokud na vozidle vznikne totální škoda, kterou neuhradí pojišťovna, uhradí nájemce "
        f"částku <b>{csk_poj} Kč</b>.", s['body']))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph("8. Sankce", s['section']))
    story.append(Paragraph(
        "Pokud nájemce nepředá vozidlo zpět pronajímateli do termínu určeném ve smlouvě, může "
        "pronajímatel naúčtovat nájemní smluvní pokutu ve výši 1 000,- Kč za každý započatý den "
        "prodlení s vrácením vozidla a nájemce je povinen ji uhradit.", s['body']))
    story.append(Paragraph(
        "Nájemce je povinen informovat pronajímatele 1 měsíc předem před ukončením pronájmu.", s['body']))
    story.append(Paragraph(
        "Při nedodržení 1 měsíční výpovědní lhůty, automaticky propadá kauce.", s['body']))
    story.append(Paragraph(
        "Nájemce je povinné uhradit kauci ve výši <b>10 000,- Kč.</b>", s['body']))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph("9. Závěrečná ustanovení", s['section']))
    story.append(Paragraph(
        "Jakékoliv změny nebo dodatky této smlouvy, vyžadují písemnou formu, nebo elektronickou "
        "komunikaci emailem uvedeným v této smlouvě.", s['body']))
    story.append(Paragraph(
        "Smlouva má 3 strany, je vyhotovena ve dvou exemplářích, z nichž každá smluvní strana "
        "obdrží po jednom.", s['body']))
    story.append(Paragraph(
        "Smluvní strany prohlašují, že si smlouvu přečetly a prohlašují, že smlouva je projevem jejich "
        "pravé a svobodné vůle, že všem ujednáním porozuměly, a na důkaz toho připojují své podpisy.",
        s['body']))
    story.append(Spacer(1, 8*mm))

    datum_str = data.get('datum_podpisu', date.today().strftime('%d.%m.%Y'))
    story.append(Paragraph(f"V Praze dne {datum_str}  čas _______________", s['field']))
    story.append(Spacer(1, 12*mm))
    story.append(_sig_table("Za pronajímatele", "Wayne Fleet s.r.o.", "Nájemce", ""))

    doc.build(story)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# PDF: Dohoda o zprostředkování Bolt/Uber
# ─────────────────────────────────────────────────────────────────────────────

def generate_dohoda_bolt_pdf(data: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    s = _s()
    story = []

    # Nadpis
    story.append(Paragraph(
        "DOHODA O ZPROSTŘEDKOVÁNÍ<br/>INTERNETOVÝCH APLIKACÍ UBER A BOLT", s['h1']))
    story.append(Spacer(1, 5*mm))

    # Smluvní strany
    story.append(Paragraph("Smluvní strany", s['h2']))
    story.append(Paragraph("Dodavatel:", s['label']))
    for line in [
        "Wayne Fleet s.r.o.",
        "Sídlo: Příčná 1892/4, 110 00 Praha 1 – Nové Město",
        "IČO: 24083127",
        "Zapsaná v obchodním rejstříku vedeném u příslušného soudu",
        "Zastoupena: Pavel Kropáč, jednatel",
        '(dále jen „Dodavatel")',
    ]:
        story.append(Paragraph(line, s['field']))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph("a", s['field']))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph("Odběratel (řidič):", s['label']))
    story.append(_fld("Jméno a příjmení", data.get('jmeno'), s))
    story.append(_fld("Datum narození", data.get('datum_narozeni'), s))
    story.append(_fld("Adresa bydliště", data.get('adresa'), s))
    story.append(Paragraph('(dále jen „Řidič")', s['field']))
    story.append(Spacer(1, 5*mm))

    # Článek I
    story.append(Paragraph("Článek I – Předmět dohody", s['h2']))
    story.append(Paragraph(
        "1. Dodavatel zajišťuje Řidiči zprostředkování přístupu a provozu prostřednictvím digitálních "
        "platforem Uber a Bolt v rámci flotilového partnerství.", s['body']))
    story.append(Paragraph(
        "2. Řidič bude vykonávat osobní silniční dopravu vozidly určenými pro přepravu nejvýše 9 osob "
        "včetně řidiče v souladu s platnými právními předpisy České republiky.", s['body']))
    story.append(Spacer(1, 4*mm))

    # Článek II
    story.append(Paragraph("Článek II – Odměna a platební podmínky", s['h2']))
    story.append(Paragraph(
        "1. Řidič se zavazuje hradit Dodavateli poplatek za zprostředkování ve výši <b>200 Kč za každý "
        "odjetý den</b>, přičemž odjetým dnem se rozumí aktivní výkon činnosti v rozsahu maximálně "
        "12 hodin během jednoho kalendářního dne.", s['body']))
    story.append(Paragraph(
        "2. Poplatek bude odečten z týdenního vyúčtování Řidiče, případně fakturován samostatně "
        "dle dohody stran.", s['body']))
    story.append(Paragraph(
        "3. V případě, že Řidič v daný den neodjede žádnou jízdu, poplatek se neúčtuje.", s['body']))
    story.append(Spacer(1, 4*mm))

    # Článek III
    story.append(Paragraph("Článek III – Daňové a zákonné povinnosti", s['h2']))
    story.append(Paragraph(
        "1. Dodavatel je plátcem daně z přidané hodnoty (DPH) a veškerá plnění poskytovaná "
        "Dodavatelem Řidiči v rámci této dohody jsou fakturována v souladu s platnými předpisy "
        "o DPH. Za správné uplatnění DPH na straně Dodavatele odpovídá výhradně Dodavatel.", s['body']))
    story.append(Paragraph(
        "2. Řidič bere na vědomí, že příjmy plynoucí mu z činnosti vykonávané na základě této "
        "dohody podléhají zdanění dle příslušných ustanovení zákona č. 586/1992 Sb., o daních "
        "z příjmů, ve znění pozdějších předpisů. Řidič je výhradně odpovědný za splnění "
        "veškerých svých daňových a odvodových povinností vůči orgánům finanční správy "
        "a správy sociálního zabezpečení.", s['body']))
    story.append(Paragraph(
        "3. Dodavatel není povinen za Řidiče odvádět zálohy na daň z příjmů ani příspěvky "
        "na sociální zabezpečení a zdravotní pojištění, pokud mezi stranami není sjednán "
        "pracovněprávní vztah.", s['body']))
    story.append(Paragraph(
        "4. Řidič je povinen disponovat veškerými zákonem vyžadovanými oprávněními "
        "k výkonu smluvní přepravy osob a udržovat je platná po celou dobu trvání této dohody.", s['body']))
    story.append(Spacer(1, 4*mm))

    # Článek IV
    story.append(Paragraph("Článek IV – Doba trvání", s['h2']))
    story.append(Paragraph("1. Tato dohoda se uzavírá na dobu neurčitou.", s['body']))
    story.append(Paragraph(
        "2. Každá ze smluvních stran může dohodu vypovědět bez udání důvodu s výpovědní lhůtou 7 dní.",
        s['body']))
    story.append(Spacer(1, 4*mm))

    # Článek V
    story.append(Paragraph("Článek V – Závěrečná ustanovení", s['h2']))
    story.append(Paragraph(
        "1. Tato dohoda nabývá účinnosti dnem podpisu oběma stranami.", s['body']))
    story.append(Paragraph(
        "2. Dohoda je vyhotovena ve dvou stejnopisech, z nichž každá strana obdrží jedno vyhotovení.",
        s['body']))
    story.append(Spacer(1, 10*mm))

    # Podpis
    datum_str = data.get('datum_podpisu', date.today().strftime('%d.%m.%Y'))
    story.append(Paragraph(f"V Praze dne: {datum_str}", s['field']))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("Za Dodavatele:", s['field']))
    story.append(Spacer(1, 12*mm))
    story.append(_sig_table(
        "Pavel Kropáč",
        "jednatel Wayne Fleet s.r.o.",
        "Řidič:",
        data.get('jmeno', '')
    ))

    doc.build(story)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# PDF: Dohoda o zprostředkování Bolt/Uber – týdenní tarif (1 000 Kč/týden)
# ─────────────────────────────────────────────────────────────────────────────

def generate_dohoda_bolt_tydeni_pdf(data: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    s = _s()
    story = []

    story.append(Paragraph(
        "DOHODA O ZPROSTŘEDKOVÁNÍ<br/>INTERNETOVÝCH APLIKACÍ UBER A BOLT", s['h1']))
    story.append(Spacer(1, 5*mm))

    story.append(Paragraph("Smluvní strany", s['h2']))
    story.append(Paragraph("Dodavatel:", s['label']))
    for line in [
        "Wayne Fleet s.r.o.",
        "Sídlo: Příčná 1892/4, 110 00 Praha 1 – Nové Město",
        "IČO: 24083127",
        "Zapsaná v obchodním rejstříku vedeném u příslušného soudu",
        "Zastoupena: Pavel Kropáč, jednatel",
        '(dále jen „Dodavatel")',
    ]:
        story.append(Paragraph(line, s['field']))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph("a", s['field']))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph("Odběratel (řidič):", s['label']))
    story.append(_fld("Jméno a příjmení", data.get('jmeno'), s))
    story.append(_fld("Datum narození", data.get('datum_narozeni'), s))
    story.append(_fld("Adresa bydliště", data.get('adresa'), s))
    story.append(Paragraph('(dále jen „Řidič")', s['field']))
    story.append(Spacer(1, 5*mm))

    story.append(Paragraph("Článek I – Předmět dohody", s['h2']))
    story.append(Paragraph(
        "1. Dodavatel zajišťuje Řidiči zprostředkování přístupu a provozu prostřednictvím digitálních "
        "platforem Uber a Bolt v rámci flotilového partnerství.", s['body']))
    story.append(Paragraph(
        "2. Řidič bude vykonávat osobní silniční dopravu vozidly určenými pro přepravu nejvýše 9 osob "
        "včetně řidiče v souladu s platnými právními předpisy České republiky.", s['body']))
    story.append(Paragraph(
        "3. Řidič používá vlastní vozidlo nebo vozidlo pronajaté na týdenní bázi.", s['body']))
    story.append(Spacer(1, 4*mm))

    story.append(Paragraph("Článek II – Odměna a platební podmínky", s['h2']))
    story.append(Paragraph(
        "1. Řidič se zavazuje hradit Dodavateli poplatek za zprostředkování ve výši <b>1 000 Kč za každý "
        "odjetý týden</b>, přičemž odjetým týdnem se rozumí kalendářní týden, ve kterém Řidič aktivně "
        "vykonával činnost prostřednictvím platforem Uber nebo Bolt.", s['body']))
    story.append(Paragraph(
        "2. Poplatek bude odečten z týdenního vyúčtování Řidiče, případně fakturován samostatně "
        "dle dohody stran.", s['body']))
    story.append(Paragraph(
        "3. V případě, že Řidič v daném týdnu neodjede žádnou jízdu, poplatek se neúčtuje.", s['body']))
    story.append(Spacer(1, 4*mm))

    story.append(Paragraph("Článek III – Daňové a zákonné povinnosti", s['h2']))
    story.append(Paragraph(
        "1. Dodavatel je plátcem daně z přidané hodnoty (DPH) a veškerá plnění poskytovaná "
        "Dodavatelem Řidiči v rámci této dohody jsou fakturována v souladu s platnými předpisy "
        "o DPH. Za správné uplatnění DPH na straně Dodavatele odpovídá výhradně Dodavatel.", s['body']))
    story.append(Paragraph(
        "2. Řidič bere na vědomí, že příjmy plynoucí mu z činnosti vykonávané na základě této "
        "dohody podléhají zdanění dle příslušných ustanovení zákona č. 586/1992 Sb., o daních "
        "z příjmů, ve znění pozdějších předpisů. Řidič je výhradně odpovědný za splnění "
        "veškerých svých daňových a odvodových povinností vůči orgánům finanční správy "
        "a správy sociálního zabezpečení.", s['body']))
    story.append(Paragraph(
        "3. Dodavatel není povinen za Řidiče odvádět zálohy na daň z příjmů ani příspěvky "
        "na sociální zabezpečení a zdravotní pojištění, pokud mezi stranami není sjednán "
        "pracovněprávní vztah.", s['body']))
    story.append(Paragraph(
        "4. Řidič je povinen disponovat veškerými zákonem vyžadovanými oprávněními "
        "k výkonu smluvní přepravy osob a udržovat je platná po celou dobu trvání této dohody.", s['body']))
    story.append(Spacer(1, 4*mm))

    story.append(Paragraph("Článek IV – Doba trvání", s['h2']))
    story.append(Paragraph("1. Tato dohoda se uzavírá na dobu neurčitou.", s['body']))
    story.append(Paragraph(
        "2. Každá ze smluvních stran může dohodu vypovědět bez udání důvodu s výpovědní lhůtou 7 dní.",
        s['body']))
    story.append(Spacer(1, 4*mm))

    story.append(Paragraph("Článek V – Závěrečná ustanovení", s['h2']))
    story.append(Paragraph(
        "1. Tato dohoda nabývá účinnosti dnem podpisu oběma stranami.", s['body']))
    story.append(Paragraph(
        "2. Dohoda je vyhotovena ve dvou stejnopisech, z nichž každá strana obdrží jedno vyhotovení.",
        s['body']))
    story.append(Spacer(1, 10*mm))

    datum_str = data.get('datum_podpisu', date.today().strftime('%d.%m.%Y'))
    story.append(Paragraph(f"V Praze dne: {datum_str}", s['field']))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("Za Dodavatele:", s['field']))
    story.append(Spacer(1, 12*mm))
    story.append(_sig_table(
        "Pavel Kropáč",
        "jednatel Wayne Fleet s.r.o.",
        "Řidič:",
        data.get('jmeno', '')
    ))

    doc.build(story)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# PDF: Předávací protokol vozu
# ─────────────────────────────────────────────────────────────────────────────

def generate_predavaci_protokol_pdf(data: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    s = _s()
    story = []

    typ = data.get('typ_protokolu', 'předání')  # 'předání' nebo 'vrácení'
    nadpis = "PŘEDÁVACÍ PROTOKOL VOZIDLA" if typ == 'předání' else "PROTOKOL O VRÁCENÍ VOZIDLA"

    story.append(Paragraph(nadpis, s['title']))
    story.append(Spacer(1, 5*mm))

    # Smluvní strany
    story.append(Paragraph("Smluvní strany", s['section']))
    tbl_strany = Table(
        [
            [Paragraph("<b>Pronajímatel:</b>", s['field']),
             Paragraph("<b>Nájemce:</b>", s['field'])],
            [Paragraph("Wayne Fleet s.r.o.", s['field']),
             Paragraph(data.get('jmeno') or '_' * 30, s['field'])],
            [Paragraph("Příčná 1892/4, 110 00 Praha 1", s['field']),
             Paragraph(data.get('adresa') or '_' * 30, s['field'])],
            [Paragraph("IČO: 24083127", s['field']),
             Paragraph(f"RČ / IČO: {data.get('rc_ico') or '_' * 20}", s['field'])],
            [Paragraph("Zastoupená: Pavel Kropáč", s['field']),
             Paragraph(f"OP: {data.get('op_pas') or '_' * 20}", s['field'])],
        ],
        colWidths=[W / 2, W / 2]
    )
    tbl_strany.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(tbl_strany)
    story.append(Spacer(1, 5*mm))

    # Údaje o vozidle
    story.append(Paragraph("Identifikace vozidla", s['section']))
    znacka = data.get('znacka', '') or '_' * 15
    model_auto = data.get('model', '') or '_' * 20
    spz = data.get('spz', '') or '_' * 15
    vin = data.get('vin', '') or '_' * 25
    km = data.get('km', '') or '_' * 10
    palivo_stav = data.get('palivo_stav', '') or '_' * 10

    tbl_vozidlo = Table(
        [
            [f"Tovární značka: {znacka}", f"Model: {model_auto}"],
            [f"Registrační značka: {spz}", f"VIN: {vin}"],
            [f"Stav km: {km}", f"Stav paliva: {palivo_stav}"],
        ],
        colWidths=[W / 2, W / 2]
    )
    tbl_vozidlo.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('BOX', (0, 0), (-1, -1), 0.5, (0.7, 0.7, 0.7)),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, (0.8, 0.8, 0.8)),
    ]))
    story.append(tbl_vozidlo)
    story.append(Spacer(1, 3*mm))

    datum_str = data.get('datum_predani', date.today().strftime('%d.%m.%Y'))
    cas_str = data.get('cas_predani', '') or '_____'
    story.append(Paragraph(f"Datum {typ}: <b>{datum_str}</b> &nbsp;&nbsp; Čas: <b>{cas_str}</b>", s['field']))
    story.append(Spacer(1, 5*mm))

    # Stav vozidla – tabulka kontrolního seznamu
    story.append(Paragraph("Stav vozidla při předání", s['section']))

    def _check_row(polozka, stav, poznamka=''):
        return [polozka, stav or '_' * 12, poznamka or '_' * 20]

    check_data = [
        [Paragraph('<b>Položka</b>', s['label']),
         Paragraph('<b>Stav</b>', s['label']),
         Paragraph('<b>Poznámka</b>', s['label'])],
        _check_row("Karoserie – škrábance / promáčkliny",
                   data.get('stav_karoserie'), data.get('pozn_karoserie')),
        _check_row("Skla – praskliny / poškození",
                   data.get('stav_sklo'), data.get('pozn_sklo')),
        _check_row("Interiér – čistota a poškození",
                   data.get('stav_interior'), data.get('pozn_interior')),
        _check_row("Pneumatiky – dezén a tlak",
                   data.get('stav_pneu'), data.get('pozn_pneu')),
        _check_row("Doklady (TP, pojistka)",
                   data.get('stav_doklady'), data.get('pozn_doklady')),
        _check_row("Klíče (počet)",
                   data.get('stav_klice'), data.get('pozn_klice')),
        _check_row("Nabíječka / příslušenství",
                   data.get('stav_prislusenstvi'), data.get('pozn_prislusenstvi')),
    ]
    col_widths = [W * 0.42, W * 0.22, W * 0.36]
    tbl_check = Table(check_data, colWidths=col_widths)
    tbl_check.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
        ('BACKGROUND', (0, 0), (-1, 0), (0.92, 0.92, 0.92)),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('BOX', (0, 0), (-1, -1), 0.5, (0.5, 0.5, 0.5)),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, (0.7, 0.7, 0.7)),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [(1, 1, 1), (0.97, 0.97, 0.97)]),
    ]))
    story.append(tbl_check)
    story.append(Spacer(1, 5*mm))

    # Poznámky
    story.append(Paragraph("Poznámky / zjištěné závady:", s['label']))
    poznamky = data.get('poznamky') or ''
    story.append(Paragraph(poznamky if poznamky else '_' * 80, s['field']))
    story.append(Paragraph('_' * 80, s['field']))
    story.append(Spacer(1, 8*mm))

    # Prohlášení
    story.append(Paragraph(
        "Obě smluvní strany potvrzují, že vozidlo bylo předáno/převzato ve stavu popsaném v tomto protokolu "
        "a souhlasí s jeho obsahem.",
        s['body']))
    story.append(Spacer(1, 10*mm))

    # Podpisy
    story.append(_sig_table("Za pronajímatele", "Wayne Fleet s.r.o.", "Nájemce", data.get('jmeno', '')))

    doc.build(story)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# PDF: Plná moc k přepisu vozidla
# ─────────────────────────────────────────────────────────────────────────────

def generate_plna_moc_pdf(data: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=25*mm, rightMargin=25*mm,
                            topMargin=25*mm, bottomMargin=25*mm)
    s = _s()
    story = []

    # Nadpis
    title_style = ParagraphStyle('pm_title', fontName=FONT_BOLD, fontSize=20,
                                  alignment=TA_CENTER, spaceAfter=14, leading=26,
                                  underlineProportion=0.05)
    story.append(Paragraph("<u><b>Plná  moc</b></u>", title_style))
    story.append(Spacer(1, 6*mm))

    # Zmocnitel (naše firma)
    story.append(_fld("Já, níže podepsaný", "Wayne Fleet s.r.o.", s))
    story.append(_fld("se sídlem", "Příčná 1892/4, 110 00, Praha 1 – Nové Město", s))
    story.append(_fld("IČ/ rodné číslo", "24083127", s))
    story.append(_fld("zastoupený jednatelem", "Pavel Kropáč", s))
    story.append(Paragraph("<i>(dále jako zmocnitel)</i>", s['field']))
    story.append(Spacer(1, 6*mm))

    # Slovo zmocňuji
    zmoc_style = ParagraphStyle('zmocnuji', fontName=FONT_BOLD, fontSize=11,
                                 spaceAfter=8, leading=16,
                                 underlineProportion=0.05)
    story.append(Paragraph("<u><i>zmocňuji</i></u>", zmoc_style))
    story.append(Spacer(1, 4*mm))

    # Zmocněnec (řidič)
    story.append(_fld("Jméno a příjmení", data.get('jmeno'), s))
    story.append(_fld("bytem", data.get('adresa'), s))
    story.append(_fld("rodné číslo", data.get('rc'), s))
    story.append(Paragraph("<i>(dále jako zmocněnec)</i>", s['field']))
    story.append(Spacer(1, 6*mm))

    # Text plné moci
    story.append(Paragraph(
        "aby na příslušném MěU Odboru dopravy zapsal společnost <b>Wayne Fleet s.r.o., "
        "IČO: 24083127, se sídlem Příčná 1892/4, 110 00 Praha 1 – Nové Město</b> "
        "jako provozovatele motorového vozidla:",
        s['body']))
    story.append(Spacer(1, 4*mm))

    # Vozidlo
    model_v = data.get('model', '') or '_' * 35
    rok_v = data.get('rok_vyroby', '') or '_' * 12
    vin_v = data.get('vin', '') or '_' * 35
    spz_v = data.get('spz', '') or '_' * 18

    story.append(Paragraph(f"model {model_v} &nbsp;&nbsp;&nbsp;&nbsp; rok výroby {rok_v}", s['field']))
    story.append(Paragraph(f"číslo karosérie – VIN: {vin_v}", s['field']))
    story.append(Paragraph(f"SPZ: {spz_v}", s['field']))
    story.append(Spacer(1, 6*mm))

    # Závěrečná klauzule
    story.append(Paragraph(
        "tato plná moc není ve výše uvedeném rozsahu ničím omezena. "
        "Zplnomocnění v plném rozsahu zmocněnec přijímá. "
        "<b>Tato plná moc je platná po dobu 30 dnů od data podpisu.</b>",
        s['body']))
    story.append(Spacer(1, 10*mm))

    # Místo a datum
    misto = data.get('misto', 'Praha')
    datum_str = data.get('datum_podpisu', date.today().strftime('%d.%m.%Y'))
    story.append(Paragraph(f"V {misto} dne {datum_str}", s['field']))
    story.append(Spacer(1, 14*mm))

    # Podpisy
    story.append(_sig_table(
        "Zmocnitel",
        "Wayne Fleet s.r.o., Pavel Kropáč",
        "Zmocněnec",
        data.get('jmeno', ''),
    ))

    doc.build(story)
    return buf.getvalue()


def generate_zbaveni_odpovednosti_pdf(data: dict) -> bytes:
    """Prohlášení vlastníka vozidla o zbavení odpovědnosti Wayne Fleet s.r.o."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=25*mm, rightMargin=25*mm,
                            topMargin=25*mm, bottomMargin=25*mm)
    s = _s()
    story = []

    title_style = ParagraphStyle('zo_title', fontName=FONT_BOLD, fontSize=17,
                                  alignment=TA_CENTER, spaceAfter=4, leading=24)
    sub_style = ParagraphStyle('zo_sub', fontName=FONT, fontSize=11,
                                alignment=TA_CENTER, spaceAfter=14, leading=16)
    story.append(Paragraph("<u><b>Prohlášení o zbavení odpovědnosti</b></u>", title_style))
    story.append(Paragraph("provozovatele motorového vozidla", sub_style))
    story.append(Spacer(1, 4*mm))

    # Vlastník vozidla
    story.append(Paragraph("<b>I. Smluvní strany</b>", s['section']))
    story.append(Spacer(1, 2*mm))
    story.append(_fld("Vlastník vozidla – jméno a příjmení", data.get('vlastnik_jmeno'), s))
    story.append(_fld("bytem", data.get('vlastnik_adresa'), s))
    story.append(_fld("rodné číslo / IČO", data.get('vlastnik_rc'), s))
    story.append(Paragraph("<i>(dale jako &quot;vlastnik&quot;)</i>", s['field']))
    story.append(Spacer(1, 5*mm))

    story.append(Paragraph("a", ParagraphStyle('and', fontName=FONT, fontSize=10,
                                               alignment=TA_CENTER, spaceAfter=5)))

    story.append(_fld("Provozovatel", "Wayne Fleet s.r.o.", s))
    story.append(_fld("se sídlem", "Příčná 1892/4, 110 00 Praha 1 – Nové Město", s))
    story.append(_fld("IČO", "24083127", s))
    story.append(_fld("zastoupený jednatelem", "Pavel Kropáč", s))
    story.append(Paragraph("<i>(dale jako &quot;provozovatel&quot;)</i>", s['field']))
    story.append(Spacer(1, 5*mm))

    # Vozidlo
    story.append(Paragraph("<b>II. Vozidlo</b>", s['section']))
    story.append(Spacer(1, 2*mm))
    model_v = data.get('model', '') or '_' * 35
    rok_v   = data.get('rok_vyroby', '') or '_' * 12
    vin_v   = data.get('vin', '') or '_' * 35
    spz_v   = data.get('spz', '') or '_' * 18
    story.append(Paragraph(f"<b>Model:</b> {model_v} &nbsp;&nbsp;&nbsp;&nbsp; <b>Rok výroby:</b> {rok_v}", s['field']))
    story.append(Paragraph(f"<b>VIN:</b> {vin_v}", s['field']))
    story.append(Paragraph(f"<b>SPZ:</b> {spz_v}", s['field']))
    story.append(Spacer(1, 5*mm))

    # Prohlášení
    story.append(Paragraph("<b>III. Prohlášení</b>", s['section']))
    story.append(Spacer(1, 2*mm))

    body_texts = [
        "Vlastník výše uvedeného motorového vozidla tímto výslovně prohlašuje a potvrzuje, "
        "že společnost <b>Wayne Fleet s.r.o.</b> je evidována jako provozovatel vozidla výhradně "
        "pro administrativní účely, a to na základě dohody s vlastníkem.",

        "Vlastník prohlašuje, že <b>Wayne Fleet s.r.o. nenese žádnou odpovědnost</b> za škody "
        "na zdraví, škody na majetku třetích osob ani za jakékoli jiné újmy způsobené provozem "
        "tohoto vozidla, a to včetně škod vzniklých v důsledku dopravní nehody, odcizení vozidla, "
        "technické závady nebo jiné události spojené s provozem vozidla.",

        "Vlastník se zavazuje, že veškeré závazky vyplývající z provozu vozidla — zejména "
        "povinné ručení (zákonné pojištění odpovědnosti z provozu vozidla), havarijní pojištění, "
        "technickou způsobilost vozidla a dodržování platných právních předpisů — zajišťuje a "
        "hradí výlučně na vlastní náklady a odpovědnost.",

        "Vlastník se dále zavazuje odškodnit společnost Wayne Fleet s.r.o. za veškeré nároky, "
        "žaloby, pokuty nebo náklady uplatněné vůči provozovateli v souvislosti s provozem "
        "tohoto vozidla.",

        "Toto prohlášení je uzavřeno dobrovolně, na základě svobodné vůle obou stran, "
        "a je závazné po celou dobu, po kterou je Wayne Fleet s.r.o. evidována jako "
        "provozovatel výše uvedeného vozidla.",
    ]
    for txt in body_texts:
        story.append(Paragraph(txt, s['body']))
        story.append(Spacer(1, 3*mm))

    story.append(Spacer(1, 6*mm))
    misto = data.get('misto', 'Praha')
    datum_str = data.get('datum_podpisu', date.today().strftime('%d.%m.%Y'))
    story.append(Paragraph(f"V {misto} dne {datum_str}", s['field']))
    story.append(Spacer(1, 14*mm))

    story.append(_sig_table(
        "Vlastník vozidla", data.get('vlastnik_jmeno', ''),
        "Provozovatel", "Wayne Fleet s.r.o., Pavel Kropáč",
    ))

    doc.build(story)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# Streamlit UI
# ─────────────────────────────────────────────────────────────────────────────

def render_smlouvy_page():
    st.markdown("## 📄 Smlouvy")

    drivers = get_all_drivers()
    cars = get_all_cars()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🚗 Smlouva o pronájmu vozidla", "📱 Dohoda Bolt / Uber", "📋 Předávací protokol", "⚖️ Plná moc k přepisu", "🛡️ Zbavení odpovědnosti"])

    # ── TAB 1: Smlouva o pronájmu ──────────────────────────────────────────
    with tab1:
        st.markdown("#### Vyplň údaje")

        verze_smlouvy = st.radio(
            "Verze smlouvy",
            ["800 Kč / den (12h směna)", "Týdenní pronájem (cena z karty auta)"],
            horizontal=True,
            key="s1_verze",
        )
        tydeni_smlouva = verze_smlouvy.startswith("Týdenní")

        col_pre1, col_pre2 = st.columns(2)
        with col_pre1:
            driver_opts = {"— Nevybírat —": None}
            driver_opts.update({d.jmeno: d for d in drivers})
            sel_d = st.selectbox("Předvyplnit řidiče", list(driver_opts.keys()), key="s1_sel_d")
            d_obj = driver_opts[sel_d]
        with col_pre2:
            car_opts = {"— Nevybírat —": None}
            car_opts.update({f"{c.spz} – {c.model}": c for c in cars})
            sel_c = st.selectbox("Předvyplnit auto", list(car_opts.keys()), key="s1_sel_c")
            c_obj = car_opts[sel_c]

        did = d_obj.id if d_obj else 0
        cid = c_obj.id if c_obj else 0

        # Týdenní cena z karty auta
        default_cena_tyden = int(c_obj.cena_tyden_pronajem or 0) if c_obj else 0

        st.markdown("---")
        st.markdown("##### 👤 Nájemce")
        col1, col2 = st.columns(2)
        with col1:
            jmeno = st.text_input("Jméno a příjmení / název firmy",
                                  value=d_obj.jmeno if d_obj else "",
                                  key=f"s1_jmeno_{did}")
            adresa = st.text_input("Adresa trvalého bydliště",
                                   value=(d_obj.adresa or "") if d_obj else "",
                                   key=f"s1_adresa_{did}")
            rc_ico = st.text_input("RČ / IČO",
                                   value=(d_obj.rc or "") if d_obj else "",
                                   key=f"s1_rc_{did}")
        with col2:
            op_pas = st.text_input("Číslo OP nebo pasu",
                                   value=(d_obj.cislo_op or "") if d_obj else "",
                                   key=f"s1_op_{did}")
            telefon = st.text_input("Telefon",
                                    value=(d_obj.telefon or "") if d_obj else "",
                                    key=f"s1_tel_{did}")
            email = st.text_input("Email",
                                  value=(d_obj.email or "") if d_obj else "",
                                  key=f"s1_email_{did}")

        st.markdown("##### 🚗 Vozidlo")
        default_znacka, default_model = "", ""
        if c_obj and c_obj.model:
            parts = c_obj.model.split(None, 1)
            default_znacka = parts[0]
            default_model = parts[1] if len(parts) > 1 else ""

        col3, col4 = st.columns(2)
        with col3:
            znacka = st.text_input("Tovární značka", value=default_znacka, key=f"s1_znacka_{cid}")
            spz = st.text_input("Registrační značka (SPZ)",
                                value=c_obj.spz if c_obj else "", key=f"s1_spz_{cid}")
        with col4:
            model_auto = st.text_input("Model", value=default_model, key=f"s1_model_{cid}")
            vin = st.text_input("VIN", value=(c_obj.vin or "") if c_obj else "", key=f"s1_vin_{cid}")

        st.markdown("##### 📋 Podmínky smlouvy")
        col5, col6 = st.columns(2)
        with col5:
            obdobi_od = st.date_input("Období od", key="s1_od")
            palivo = st.selectbox("Typ paliva",
                                  ["nafta", "benzin", "CNG", "LPG", "elektřina"], key="s1_palivo")
            cena_skody_palivo = st.number_input(
                "Cena totální škody – špatné palivo (Kč)",
                min_value=0, value=300000, step=10000, key="s1_csk_pal")
        with col6:
            obdobi_do = st.date_input("Období do", key="s1_do")
            cena_skody_pojistovna = st.number_input(
                "Cena totální škody – pojišťovna (Kč)",
                min_value=0, value=50000, step=5000, key="s1_csk_poj")
            if tydeni_smlouva:
                cena_tyden = st.number_input(
                    "Cena pronájmu (Kč/týden)",
                    min_value=0, value=default_cena_tyden, step=500,
                    key=f"s1_cena_tyden_{cid}",
                    help="Předvyplněno z karty auta."
                )

        datum_podpisu = st.date_input("Datum podpisu", value=date.today(), key="s1_datum")

        if st.button("📄 Generovat PDF smlouvy", key="gen_smlouva", width='stretch'):
            pdf_data = {
                'jmeno': jmeno,
                'adresa': adresa,
                'rc_ico': rc_ico,
                'op_pas': op_pas,
                'telefon': telefon,
                'email': email,
                'znacka': znacka,
                'model': model_auto,
                'spz': spz,
                'vin': vin,
                'obdobi_od': obdobi_od.strftime('%d.%m.%Y'),
                'obdobi_do': obdobi_do.strftime('%d.%m.%Y'),
                'palivo': palivo,
                'cena_skody_palivo': f"{cena_skody_palivo:,}".replace(',', ' '),
                'cena_skody_pojistovna': f"{cena_skody_pojistovna:,}".replace(',', ' '),
                'cislo_uctu': '6456847004/5500',
                'datum_podpisu': datum_podpisu.strftime('%d.%m.%Y'),
            }
            if tydeni_smlouva:
                pdf_data['cena_tyden'] = f"{cena_tyden:,}".replace(',', ' ')
                pdf_data['cena_tyden_slovy'] = f"{cena_tyden} korun českých"
            try:
                if tydeni_smlouva:
                    pdf_bytes = generate_smlouva_pronajem_tydeni_pdf(pdf_data)
                    fname = f"Smlouva_pronajem_tydeni_{jmeno.replace(' ', '_') or 'ridic'}.pdf"
                else:
                    pdf_bytes = generate_smlouva_pronajem_pdf(pdf_data)
                    fname = f"Smlouva_pronajem_{jmeno.replace(' ', '_') or 'ridic'}.pdf"
                st.download_button(
                    "⬇️ Stáhnout smlouvu (PDF)",
                    data=pdf_bytes,
                    file_name=fname,
                    mime="application/pdf",
                    key="dl_smlouva",
                    width='stretch'
                )
                st.success("PDF vygenerováno — klikni na tlačítko pro stažení.")
            except Exception as e:
                st.error(f"Chyba při generování PDF: {e}")

    # ── TAB 2: Dohoda Bolt/Uber ────────────────────────────────────────────
    with tab2:
        st.markdown("#### Vyplň údaje")

        verze_dohody = st.radio(
            "Verze dohody",
            ["200 Kč / den (flotilové auto)", "1 000 Kč / týden (vlastní nebo týdenní pronájem)"],
            horizontal=True,
            key="d_verze",
        )

        driver_opts2 = {"— Nevybírat —": None}
        driver_opts2.update({d.jmeno: d for d in drivers})
        sel_d2 = st.selectbox("Předvyplnit řidiče", list(driver_opts2.keys()), key="d_sel_d")
        d_obj2 = driver_opts2[sel_d2]
        did2 = d_obj2.id if d_obj2 else 0

        st.markdown("---")
        st.markdown("##### 👤 Odběratel (řidič)")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            jmeno2 = st.text_input("Jméno a příjmení",
                                   value=d_obj2.jmeno if d_obj2 else "",
                                   key=f"d_jmeno_{did2}")
            _dn_default = (
                d_obj2.datum_narozeni.strftime('%d.%m.%Y')
                if d_obj2 and d_obj2.datum_narozeni else ""
            )
            datum_narozeni = st.text_input(
                "Datum narození (DD.MM.RRRR)",
                value=_dn_default,
                key=f"d_narozeni_{did2}"
            )
        with col_d2:
            adresa2 = st.text_input("Adresa bydliště",
                                    value=(d_obj2.adresa or "") if d_obj2 else "",
                                    key=f"d_adresa_{did2}")

        datum_podpisu2 = st.date_input("Datum podpisu", value=date.today(), key="d_datum")

        if st.button("📄 Generovat PDF dohody", key="gen_dohoda", width='stretch'):
            pdf_data2 = {
                'jmeno': jmeno2,
                'datum_narozeni': datum_narozeni,
                'adresa': adresa2,
                'datum_podpisu': datum_podpisu2.strftime('%d.%m.%Y'),
            }
            try:
                tydeni = verze_dohody.startswith("1 000")
                if tydeni:
                    pdf_bytes2 = generate_dohoda_bolt_tydeni_pdf(pdf_data2)
                    fname2 = f"Dohoda_Bolt_Uber_tydeni_{jmeno2.replace(' ', '_') or 'ridic'}.pdf"
                else:
                    pdf_bytes2 = generate_dohoda_bolt_pdf(pdf_data2)
                    fname2 = f"Dohoda_Bolt_Uber_{jmeno2.replace(' ', '_') or 'ridic'}.pdf"
                st.download_button(
                    "⬇️ Stáhnout dohodu (PDF)",
                    data=pdf_bytes2,
                    file_name=fname2,
                    mime="application/pdf",
                    key="dl_dohoda",
                    width='stretch'
                )
                st.success("PDF vygenerováno — klikni na tlačítko pro stažení.")
            except Exception as e:
                st.error(f"Chyba při generování PDF: {e}")

    # ── TAB 3: Předávací protokol ──────────────────────────────────────────
    with tab3:
        st.markdown("#### Vyplň údaje")

        col_pt1, col_pt2 = st.columns(2)
        with col_pt1:
            driver_opts3 = {"— Nevybírat —": None}
            driver_opts3.update({d.jmeno: d for d in drivers})
            sel_d3 = st.selectbox("Předvyplnit řidiče", list(driver_opts3.keys()), key="p_sel_d")
            d_obj3 = driver_opts3[sel_d3]
        with col_pt2:
            car_opts3 = {"— Nevybírat —": None}
            car_opts3.update({f"{c.spz} – {c.model}": c for c in cars})
            sel_c3 = st.selectbox("Předvyplnit auto", list(car_opts3.keys()), key="p_sel_c")
            c_obj3 = car_opts3[sel_c3]

        did3 = d_obj3.id if d_obj3 else 0
        cid3 = c_obj3.id if c_obj3 else 0

        typ_protokolu = st.radio(
            "Typ protokolu", ["předání", "vrácení"],
            horizontal=True, key="p_typ",
        )

        st.markdown("---")
        st.markdown("##### 👤 Nájemce")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            p_jmeno = st.text_input("Jméno a příjmení",
                                    value=d_obj3.jmeno if d_obj3 else "",
                                    key=f"p_jmeno_{did3}")
            p_adresa = st.text_input("Adresa",
                                     value=(d_obj3.adresa or "") if d_obj3 else "",
                                     key=f"p_adresa_{did3}")
            p_rc = st.text_input("RČ / IČO",
                                 value=(d_obj3.rc or "") if d_obj3 else "",
                                 key=f"p_rc_{did3}")
        with col_p2:
            p_op = st.text_input("Číslo OP",
                                 value=(d_obj3.cislo_op or "") if d_obj3 else "",
                                 key=f"p_op_{did3}")

        st.markdown("##### 🚗 Vozidlo")
        default_znacka3, default_model3 = "", ""
        if c_obj3 and c_obj3.model:
            parts3 = c_obj3.model.split(None, 1)
            default_znacka3 = parts3[0]
            default_model3 = parts3[1] if len(parts3) > 1 else ""

        col_p3, col_p4 = st.columns(2)
        with col_p3:
            p_znacka = st.text_input("Tovární značka", value=default_znacka3, key=f"p_znacka_{cid3}")
            p_spz = st.text_input("SPZ", value=c_obj3.spz if c_obj3 else "", key=f"p_spz_{cid3}")
            p_km = st.text_input("Stav kilometrů", key=f"p_km_{cid3}")
        with col_p4:
            p_model = st.text_input("Model", value=default_model3, key=f"p_model_{cid3}")
            p_vin = st.text_input("VIN", value=(c_obj3.vin or "") if c_obj3 else "", key=f"p_vin_{cid3}")
            p_palivo_stav = st.selectbox(
                "Stav paliva", ["plná nádrž", "3/4", "1/2", "1/4", "prázdná"],
                key=f"p_palivo_{cid3}",
            )

        st.markdown("##### 📅 Datum a čas")
        col_p5, col_p6 = st.columns(2)
        with col_p5:
            p_datum = st.date_input("Datum předání/vrácení", value=date.today(), key="p_datum")
        with col_p6:
            p_cas = st.text_input("Čas (HH:MM)", value="", placeholder="např. 08:30", key="p_cas")

        st.markdown("##### 🔍 Stav vozidla")
        stav_opts = ["OK", "poškozeno", "chybí", "—"]

        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.markdown("**Položka**")
        with col_s2:
            st.markdown("**Stav**")
        with col_s3:
            st.markdown("**Poznámka**")

        polozky = [
            ("karoserie", "Karoserie"),
            ("sklo", "Skla"),
            ("interior", "Interiér"),
            ("pneu", "Pneumatiky"),
            ("doklady", "Doklady (TP, pojistka)"),
            ("klice", "Klíče"),
            ("prislusenstvi", "Příslušenství / nabíječka"),
        ]

        stav_hodnoty = {}
        pozn_hodnoty = {}
        for key, label in polozky:
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(label)
            with c2:
                stav_hodnoty[key] = st.selectbox(
                    label, stav_opts, label_visibility="collapsed", key=f"p_stav_{key}"
                )
            with c3:
                pozn_hodnoty[key] = st.text_input(
                    f"Pozn. {label}", label_visibility="collapsed", key=f"p_pozn_{key}"
                )

        p_poznamky = st.text_area("Poznámky / zjištěné závady", height=80, key="p_poznamky")

        if st.button("📄 Generovat PDF protokolu", key="gen_protokol", width='stretch'):
            pdf_data3 = {
                'typ_protokolu': typ_protokolu,
                'jmeno': p_jmeno,
                'adresa': p_adresa,
                'rc_ico': p_rc,
                'op_pas': p_op,
                'znacka': p_znacka,
                'model': p_model,
                'spz': p_spz,
                'vin': p_vin,
                'km': p_km,
                'palivo_stav': p_palivo_stav,
                'datum_predani': p_datum.strftime('%d.%m.%Y'),
                'cas_predani': p_cas,
                'poznamky': p_poznamky,
            }
            for key, _ in polozky:
                pdf_data3[f'stav_{key}'] = stav_hodnoty[key]
                pdf_data3[f'pozn_{key}'] = pozn_hodnoty[key]

            try:
                pdf_bytes3 = generate_predavaci_protokol_pdf(pdf_data3)
                fname3 = f"Protokol_{typ_protokolu}_{p_jmeno.replace(' ', '_') or 'ridic'}_{p_datum.strftime('%Y%m%d')}.pdf"
                st.download_button(
                    "⬇️ Stáhnout protokol (PDF)",
                    data=pdf_bytes3,
                    file_name=fname3,
                    mime="application/pdf",
                    key="dl_protokol",
                    width='stretch'
                )
                st.success("PDF vygenerováno — klikni na tlačítko pro stažení.")
            except Exception as e:
                st.error(f"Chyba při generování PDF: {e}")

    # ── TAB 4: Plná moc k přepisu vozidla ─────────────────────────────────
    with tab4:
        st.markdown("#### Vyplň údaje")
        st.info("Wayne Fleet s.r.o. (zmocnitel) zmocňuje řidiče / jinou osobu (zmocněnce) k přepisu provozovatele vozidla na MěU Odboru dopravy.")

        driver_opts4 = {"— Nevybírat —": None}
        driver_opts4.update({d.jmeno: d for d in drivers})
        sel_d4 = st.selectbox("Předvyplnit řidiče (zmocněnec)", list(driver_opts4.keys()), key="pm_sel_d")
        d_obj4 = driver_opts4[sel_d4]
        did4 = d_obj4.id if d_obj4 else 0

        st.markdown("---")
        st.markdown("##### 👤 Zmocněnec (osoba provádějící přepis)")
        col_pm3, col_pm4 = st.columns(2)
        with col_pm3:
            pm_jmeno = st.text_input("Jméno a příjmení",
                                     value=d_obj4.jmeno if d_obj4 else "",
                                     key=f"pm_jmeno_{did4}")
            pm_adresa = st.text_input("Adresa (bytem)",
                                      value=(d_obj4.adresa or "") if d_obj4 else "",
                                      key=f"pm_adresa_{did4}")
        with col_pm4:
            pm_rc = st.text_input("Rodné číslo",
                                   value=(d_obj4.rc or "") if d_obj4 else "",
                                   key=f"pm_rc_{did4}")

        st.markdown("##### 🚗 Vozidlo (vyplní majitel)")
        col_pm5, col_pm6 = st.columns(2)
        with col_pm5:
            pm_model = st.text_input("Model vozidla", placeholder="např. Škoda Octavia", key="pm_model")
            pm_vin = st.text_input("Číslo karosérie – VIN", placeholder="________________", key="pm_vin")
        with col_pm6:
            pm_rok = st.text_input("Rok výroby", placeholder="________________", key="pm_rok")
            pm_spz = st.text_input("SPZ", placeholder="________________", key="pm_spz")

        st.markdown("##### 📅 Datum a místo")
        col_pm7, col_pm8 = st.columns(2)
        with col_pm7:
            pm_datum = st.date_input("Datum podpisu", value=date.today(), key="pm_datum")
        with col_pm8:
            pm_misto = st.text_input("Místo podpisu", value="Praha", key="pm_misto")

        if st.button("📄 Generovat PDF plné moci", key="gen_plna_moc", width='stretch'):
            pdf_data4 = {
                'jmeno': pm_jmeno,
                'adresa': pm_adresa,
                'rc': pm_rc,
                'model': pm_model,
                'rok_vyroby': pm_rok,
                'vin': pm_vin,
                'spz': pm_spz,
                'misto': pm_misto,
                'datum_podpisu': pm_datum.strftime('%d.%m.%Y'),
            }
            try:
                pdf_bytes4 = generate_plna_moc_pdf(pdf_data4)
                fname4 = f"Plna_moc_prepis_{pm_jmeno.replace(' ', '_') or 'zmocnenec'}.pdf"
                st.download_button(
                    "⬇️ Stáhnout plnou moc (PDF)",
                    data=pdf_bytes4,
                    file_name=fname4,
                    mime="application/pdf",
                    key="dl_plna_moc",
                    width='stretch'
                )
                st.success("PDF vygenerováno — klikni na tlačítko pro stažení.")
            except Exception as e:
                st.error(f"Chyba při generování PDF: {e}")

    # ── TAB 5: Zbavení odpovědnosti ─────────────────────────────────────────
    with tab5:
        st.markdown("#### Vyplň údaje")
        st.info("Vlastník vozidla podpisem prohlašuje, že Wayne Fleet s.r.o. (jako evidovaný provozovatel) nenese žádnou odpovědnost za provoz jeho vozidla.")

        driver_opts5 = {"— Nevybírat —": None}
        driver_opts5.update({d.jmeno: d for d in drivers})
        sel_d5 = st.selectbox("Předvyplnit řidiče (vlastník vozidla)", list(driver_opts5.keys()), key="zo_sel_d")
        d_obj5 = driver_opts5[sel_d5]
        did5 = d_obj5.id if d_obj5 else 0

        st.markdown("---")
        st.markdown("##### 👤 Vlastník vozidla")
        col_zo1, col_zo2 = st.columns(2)
        with col_zo1:
            zo_jmeno = st.text_input("Jméno a příjmení",
                                     value=d_obj5.jmeno if d_obj5 else "",
                                     key=f"zo_jmeno_{did5}")
            zo_adresa = st.text_input("Adresa (bytem)",
                                      value=(d_obj5.adresa or "") if d_obj5 else "",
                                      key=f"zo_adresa_{did5}")
        with col_zo2:
            zo_rc = st.text_input("Rodné číslo / IČO",
                                  value=(d_obj5.rc or "") if d_obj5 else "",
                                  key=f"zo_rc_{did5}")

        st.markdown("##### 🚗 Vozidlo")
        col_zo3, col_zo4 = st.columns(2)
        with col_zo3:
            zo_model = st.text_input("Model vozidla", placeholder="např. Škoda Octavia", key="zo_model")
            zo_vin = st.text_input("Číslo karosérie – VIN", placeholder="________________", key="zo_vin")
        with col_zo4:
            zo_rok = st.text_input("Rok výroby", placeholder="________________", key="zo_rok")
            zo_spz = st.text_input("SPZ", placeholder="________________", key="zo_spz")

        st.markdown("##### 📅 Datum a místo")
        col_zo5, col_zo6 = st.columns(2)
        with col_zo5:
            zo_datum = st.date_input("Datum podpisu", value=date.today(), key="zo_datum")
        with col_zo6:
            zo_misto = st.text_input("Místo podpisu", value="Praha", key="zo_misto")

        if st.button("📄 Generovat PDF prohlášení", key="gen_zbaveni", width='stretch'):
            pdf_data5 = {
                'vlastnik_jmeno': zo_jmeno,
                'vlastnik_adresa': zo_adresa,
                'vlastnik_rc': zo_rc,
                'model': zo_model,
                'rok_vyroby': zo_rok,
                'vin': zo_vin,
                'spz': zo_spz,
                'misto': zo_misto,
                'datum_podpisu': zo_datum.strftime('%d.%m.%Y'),
            }
            try:
                pdf_bytes5 = generate_zbaveni_odpovednosti_pdf(pdf_data5)
                fname5 = f"Zbaveni_odpovednosti_{zo_jmeno.replace(' ', '_') or 'vlastnik'}.pdf"
                st.download_button(
                    "⬇️ Stáhnout prohlášení (PDF)",
                    data=pdf_bytes5,
                    file_name=fname5,
                    mime="application/pdf",
                    key="dl_zbaveni",
                    width='stretch'
                )
                st.success("PDF vygenerováno — klikni na tlačítko pro stažení.")
            except Exception as e:
                st.error(f"Chyba při generování PDF: {e}")
