"""
Wayne Fleet Management System - MAIN APPLICATION
Complete system with real database integration
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database.database import init_db
if 'db_initialized' not in st.session_state:
    init_db()
    st.session_state['db_initialized'] = True
from database.crud_cars import get_active_cars, create_car, update_car
from database.crud_drivers import get_active_drivers, create_driver, update_driver
from utils.cached_queries import cached_cars as get_all_cars, cached_drivers as get_all_drivers, cached_car_stats as get_car_stats
from database.crud_payments import zadat_platbu, get_payment_info, je_splaceno
from utils.vyuctovani import parse_uber_csv, parse_bolt_csv, generate_driver_invoice_pdf, normalize_name
from database.crud_drivers import find_driver_by_name
from database.crud_calendar import (
    get_week_assignments, get_day_shifts, create_shift, update_shift,
    delete_shift, check_driver_conflict, create_default_week,
    get_weekly_rental, set_weekly_rental, clear_weekly_rental,
    create_or_update_shift, clear_shift,
)
from database.models import CalendarAssignment
from database.crud_payments import zadat_platbu, get_payment_info, je_splaceno

# Konfigurace stránky
st.set_page_config(
    page_title="Wayne Fleet | Management System",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state
if 'page' not in st.session_state:
    st.session_state['page'] = 'dashboard'
if 'show_add_car_form' not in st.session_state:
    st.session_state['show_add_car_form'] = False
if 'show_add_driver_form' not in st.session_state:
    st.session_state['show_add_driver_form'] = False
if 'payment_car_id' not in st.session_state:
    st.session_state['payment_car_id'] = None
if 'edit_car_id' not in st.session_state:
    st.session_state['edit_car_id'] = None
if 'uber_data' not in st.session_state:
    st.session_state['uber_data'] = None
if 'bolt_data' not in st.session_state:
    st.session_state['bolt_data'] = None
if 'generated_pdfs' not in st.session_state:
    st.session_state['generated_pdfs'] = {}
if 'calendar_week_start' not in st.session_state:
    from datetime import datetime, timedelta
    today = datetime.now().date()
    days_since_monday = today.weekday()
    st.session_state['calendar_week_start'] = today - timedelta(days=days_since_monday)
if 'edit_shift_id' not in st.session_state:
    st.session_state['edit_shift_id'] = None
if 'payment_car_id' not in st.session_state:
    st.session_state['payment_car_id'] = None

# HI-TECH CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@400;700;900&family=Rajdhani:wght@400;600;700&display=swap');

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .block-container {
        padding-top: 0rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 100%;
    }

    /* === POZADÍ s tech gridem === */
    .stApp, [data-testid="stAppViewContainer"] {
        background: #050505 !important;
        background-image:
            linear-gradient(rgba(245,197,24,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(245,197,24,0.03) 1px, transparent 1px) !important;
        background-size: 40px 40px !important;
    }
    [data-testid="stHeader"] {
        background: transparent !important;
    }

    /* Scanline overlay */
    .stApp::after {
        content: '';
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: repeating-linear-gradient(
            0deg,
            transparent,
            transparent 2px,
            rgba(0,0,0,0.08) 2px,
            rgba(0,0,0,0.08) 4px
        );
        pointer-events: none;
        z-index: 9999;
    }

    /* === LOGO === */
    .logo {
        font-family: 'Orbitron', monospace !important;
        font-size: 1.6rem;
        font-weight: 900;
        color: #f5c518 !important;
        text-shadow: 0 0 10px rgba(245,197,24,0.8), 0 0 30px rgba(245,197,24,0.4);
        letter-spacing: 4px;
        -webkit-text-fill-color: #f5c518 !important;
    }

    /* === STAT KARTY – tech styl === */
    .stat-card {
        background: rgba(0,0,0,0.6);
        border: 1px solid rgba(245,197,24,0.4);
        border-radius: 2px;
        padding: 1.5rem;
        text-align: center;
        transition: all 0.2s ease;
        height: 100%;
        position: relative;
        clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 12px 100%, 0 calc(100% - 12px));
        box-shadow: inset 0 0 20px rgba(245,197,24,0.05), 0 0 15px rgba(245,197,24,0.1);
    }
    .stat-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, #f5c518, transparent);
    }
    .stat-card::after {
        content: '';
        position: absolute;
        top: 4px; right: 4px;
        width: 6px; height: 6px;
        background: #f5c518;
        box-shadow: 0 0 8px #f5c518;
    }
    .stat-card:hover {
        border-color: rgba(245,197,24,0.8);
        box-shadow: 0 0 25px rgba(245,197,24,0.25), inset 0 0 30px rgba(245,197,24,0.08);
        transform: translateY(-2px);
    }
    .stat-icon { font-size: 2rem; margin-bottom: 0.5rem; }
    .stat-value {
        font-family: 'Orbitron', monospace !important;
        font-size: 2.2rem;
        font-weight: 700;
        color: #f5c518 !important;
        text-shadow: 0 0 15px rgba(245,197,24,0.6);
        margin: 0.5rem 0;
    }
    .stat-label {
        font-family: 'Share Tech Mono', monospace;
        color: rgba(245,197,24,0.6);
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 3px;
        font-weight: 400;
    }
    .stat-change { color: #39ff14; font-size: 0.85rem; font-weight: 600; margin-top: 0.5rem; font-family: 'Share Tech Mono', monospace; }

    /* === PREMIUM CARD === */
    .premium-card {
        background: rgba(0,0,0,0.5);
        border: 1px solid rgba(245,197,24,0.2);
        border-radius: 0;
        padding: 1.5rem;
        margin: 1rem 0;
        position: relative;
        clip-path: polygon(0 0, calc(100% - 16px) 0, 100% 16px, 100% 100%, 0 100%);
        box-shadow: 0 0 20px rgba(245,197,24,0.05);
    }
    .premium-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 40px; height: 2px;
        background: #f5c518;
        box-shadow: 0 0 8px #f5c518;
    }
    .premium-card::after {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 2px; height: 40px;
        background: #f5c518;
        box-shadow: 0 0 8px #f5c518;
    }

    /* === CAR CARD === */
    .car-card {
        background: rgba(5,5,5,0.8);
        border: 1px solid rgba(245,197,24,0.3);
        border-radius: 0;
        padding: 1.5rem;
        margin: 1rem 0;
        position: relative;
        overflow: hidden;
        transition: all 0.2s ease;
        clip-path: polygon(0 0, calc(100% - 20px) 0, 100% 20px, 100% 100%, 20px 100%, 0 calc(100% - 20px));
    }
    .car-card:hover {
        border-color: rgba(245,197,24,0.7);
        box-shadow: 0 0 30px rgba(245,197,24,0.2), inset 0 0 40px rgba(245,197,24,0.04);
    }
    .car-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 100%; height: 2px;
        background: linear-gradient(90deg, #f5c518 0%, rgba(245,197,24,0.3) 60%, transparent 100%);
        box-shadow: 0 0 10px rgba(245,197,24,0.5);
    }
    .car-spz {
        font-family: 'Orbitron', monospace !important;
        font-size: 1.6rem;
        font-weight: 700;
        color: #f5c518 !important;
        text-shadow: 0 0 12px rgba(245,197,24,0.5);
        letter-spacing: 3px;
    }

    /* === STATUS BADGES === */
    .status-active {
        background: transparent;
        border: 1px solid #39ff14;
        color: #39ff14;
        padding: 0.3rem 0.8rem;
        border-radius: 0;
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.75rem;
        font-weight: 400;
        text-transform: uppercase;
        letter-spacing: 2px;
        text-shadow: 0 0 8px #39ff14;
        box-shadow: 0 0 8px rgba(57,255,20,0.2), inset 0 0 8px rgba(57,255,20,0.05);
    }
    .status-service {
        background: transparent;
        border: 1px solid #f5c518;
        color: #f5c518;
        padding: 0.3rem 0.8rem;
        border-radius: 0;
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.75rem;
        font-weight: 400;
        text-transform: uppercase;
        letter-spacing: 2px;
        text-shadow: 0 0 8px #f5c518;
        box-shadow: 0 0 8px rgba(245,197,24,0.2);
    }

    /* === INFO BOX === */
    .info-box {
        background: rgba(245,197,24,0.03);
        padding: 0.8rem;
        border-radius: 0;
        border-left: 2px solid rgba(245,197,24,0.5);
        border-bottom: 1px solid rgba(245,197,24,0.15);
    }
    .info-label {
        font-family: 'Share Tech Mono', monospace;
        color: rgba(245,197,24,0.5);
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 0.3rem;
    }
    .info-value {
        font-family: 'Orbitron', monospace;
        color: #f0f0f0;
        font-size: 1.1rem;
        font-weight: 700;
    }
    .info-value.success { color: #39ff14; text-shadow: 0 0 8px rgba(57,255,20,0.5); }
    .info-value.warning { color: #f5c518; text-shadow: 0 0 8px rgba(245,197,24,0.5); }

    /* === PROGRESS BAR === */
    .progress-bar {
        background: rgba(245,197,24,0.08);
        border: 1px solid rgba(245,197,24,0.2);
        border-radius: 0;
        height: 6px;
        overflow: hidden;
        margin: 0.5rem 0;
    }
    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #f5c518 0%, #ffd700 100%);
        box-shadow: 0 0 10px rgba(245,197,24,0.8);
        border-radius: 0;
        transition: width 0.5s ease;
    }

    /* === DRIVER CARD === */
    .driver-card {
        background: rgba(5,5,5,0.8);
        border: 1px solid rgba(245,197,24,0.25);
        border-radius: 0;
        padding: 1.5rem;
        margin: 1rem 0;
        display: flex;
        align-items: center;
        gap: 1.5rem;
        transition: all 0.2s ease;
        clip-path: polygon(0 0, calc(100% - 16px) 0, 100% 16px, 100% 100%, 0 100%);
        position: relative;
    }
    .driver-card:hover {
        border-color: rgba(245,197,24,0.6);
        box-shadow: 0 0 20px rgba(245,197,24,0.15);
    }
    .driver-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 60px; height: 2px;
        background: #f5c518;
        box-shadow: 0 0 8px rgba(245,197,24,0.6);
    }
    .driver-avatar {
        width: 70px;
        height: 70px;
        border-radius: 0;
        background: rgba(245,197,24,0.1);
        border: 2px solid #f5c518;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'Orbitron', monospace;
        font-size: 1.4rem;
        font-weight: 700;
        color: #f5c518;
        text-shadow: 0 0 10px rgba(245,197,24,0.8);
        box-shadow: 0 0 15px rgba(245,197,24,0.2), inset 0 0 15px rgba(245,197,24,0.05);
        clip-path: polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 8px 100%, 0 calc(100% - 8px));
        flex-shrink: 0;
    }
    .driver-name {
        font-family: 'Rajdhani', sans-serif;
        font-size: 1.4rem;
        font-weight: 700;
        color: white;
        margin-bottom: 0.3rem;
        letter-spacing: 1px;
    }
    .driver-meta {
        font-family: 'Share Tech Mono', monospace;
        color: rgba(245,197,24,0.5);
        font-size: 0.8rem;
        line-height: 1.6;
    }

    /* === HEADINGS === */
    h1, h2, h3 {
        font-family: 'Rajdhani', sans-serif !important;
        color: white !important;
        letter-spacing: 2px;
        text-transform: uppercase;
    }
    h2::after {
        content: '';
        display: block;
        width: 60px;
        height: 2px;
        background: #f5c518;
        box-shadow: 0 0 8px #f5c518;
        margin-top: 4px;
    }
    p, div, span { color: rgba(255,255,255,0.8); }

    /* === BUTTONS === */
    .stButton > button,
    button[kind="secondary"],
    button[kind="primary"] {
        background: transparent !important;
        color: #f5c518 !important;
        border: 1px solid rgba(245,197,24,0.6) !important;
        border-radius: 0 !important;
        font-family: 'Share Tech Mono', monospace !important;
        font-weight: 400 !important;
        font-size: 0.85rem !important;
        letter-spacing: 2px !important;
        text-transform: uppercase !important;
        transition: all 0.15s ease !important;
        clip-path: polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%) !important;
        box-shadow: 0 0 8px rgba(245,197,24,0.1) !important;
    }
    .stButton > button:hover {
        background: rgba(245,197,24,0.1) !important;
        border-color: #f5c518 !important;
        box-shadow: 0 0 20px rgba(245,197,24,0.3), inset 0 0 20px rgba(245,197,24,0.05) !important;
        color: #ffd700 !important;
        text-shadow: 0 0 8px rgba(245,197,24,0.8) !important;
    }
    .stButton > button:active {
        background: rgba(245,197,24,0.2) !important;
    }

    /* Aktivní stránka v menu (type=primary) */
    .stButton > button[kind="primary"] {
        background: rgba(245,197,24,0.15) !important;
        border-color: #f5c518 !important;
        color: #f5c518 !important;
        text-shadow: 0 0 8px rgba(245,197,24,0.7) !important;
        box-shadow: 0 0 15px rgba(245,197,24,0.2), inset 0 0 15px rgba(245,197,24,0.05) !important;
    }

    /* === METRIKY === */
    [data-testid="stMetricValue"] {
        font-family: 'Orbitron', monospace !important;
        color: #f5c518 !important;
        font-size: 1.6rem !important;
        text-shadow: 0 0 10px rgba(245,197,24,0.5);
    }
    [data-testid="stMetricLabel"] {
        font-family: 'Share Tech Mono', monospace !important;
        color: rgba(245,197,24,0.5) !important;
        font-size: 0.75rem !important;
        letter-spacing: 2px !important;
        text-transform: uppercase !important;
    }
    [data-testid="stMetricDelta"] {
        font-family: 'Share Tech Mono', monospace !important;
    }
    [data-testid="stMetric"] {
        background: rgba(245,197,24,0.03) !important;
        border: 1px solid rgba(245,197,24,0.15) !important;
        border-left: 2px solid #f5c518 !important;
        padding: 0.8rem !important;
    }

    /* === INPUT FIELDS === */
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stSelectbox"] select,
    textarea {
        background: #0a0a0a !important;
        border: 1px solid rgba(245,197,24,0.3) !important;
        border-radius: 0 !important;
        color: #f5c518 !important;
        font-family: 'Share Tech Mono', monospace !important;
    }
    [data-testid="stTextInput"] input:focus,
    [data-testid="stNumberInput"] input:focus {
        border-color: #f5c518 !important;
        box-shadow: 0 0 12px rgba(245,197,24,0.3) !important;
    }

    /* === TABS === */
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        background: transparent;
        border-bottom: 1px solid rgba(245,197,24,0.3);
        gap: 0;
    }
    [data-testid="stTabs"] [data-baseweb="tab"] {
        font-family: 'Share Tech Mono', monospace !important;
        font-size: 0.8rem !important;
        letter-spacing: 2px !important;
        text-transform: uppercase !important;
        color: rgba(245,197,24,0.4) !important;
        border-radius: 0 !important;
        padding: 0.6rem 1.2rem !important;
    }
    [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
        color: #f5c518 !important;
        background: rgba(245,197,24,0.08) !important;
        border-bottom: 2px solid #f5c518 !important;
        text-shadow: 0 0 8px rgba(245,197,24,0.5) !important;
    }

    /* === EXPANDER === */
    [data-testid="stExpander"] {
        border: 1px solid rgba(245,197,24,0.2) !important;
        border-radius: 0 !important;
        background: rgba(0,0,0,0.4) !important;
    }
    [data-testid="stExpander"] summary {
        font-family: 'Share Tech Mono', monospace !important;
        letter-spacing: 1px !important;
    }

    /* === SELECT / RADIO === */
    [data-baseweb="select"] [data-baseweb="select-container"] {
        background: #0a0a0a !important;
        border: 1px solid rgba(245,197,24,0.3) !important;
        border-radius: 0 !important;
    }

    /* === TOGGLE / CHECKBOX === */
    [data-testid="stCheckbox"] label,
    [data-testid="stToggle"] label {
        font-family: 'Share Tech Mono', monospace !important;
        font-size: 0.85rem !important;
        letter-spacing: 1px !important;
        color: rgba(245,197,24,0.7) !important;
    }

    /* === ALERTS & INFO === */
    [data-testid="stAlert"] {
        border-radius: 0 !important;
        border-left: 3px solid #f5c518 !important;
        background: rgba(245,197,24,0.05) !important;
        font-family: 'Share Tech Mono', monospace !important;
    }

    /* === DIVIDER === */
    hr {
        border: none !important;
        border-top: 1px solid rgba(245,197,24,0.15) !important;
        box-shadow: 0 0 8px rgba(245,197,24,0.1) !important;
    }

    /* === DATAFRAME === */
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(245,197,24,0.2) !important;
    }
    [data-testid="stDataFrame"] th {
        background: rgba(245,197,24,0.1) !important;
        font-family: 'Share Tech Mono', monospace !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
        color: #f5c518 !important;
    }

    /* === SIDEBAR (pokud je) === */
    [data-testid="stSidebar"] {
        background: #050505 !important;
        border-right: 1px solid rgba(245,197,24,0.2) !important;
    }

    /* === CAPTION / SMALL TEXT === */
    [data-testid="stCaptionContainer"] {
        font-family: 'Share Tech Mono', monospace !important;
        color: rgba(245,197,24,0.4) !important;
    }

    /* === FORM === */
    [data-testid="stForm"] {
        border: 1px solid rgba(245,197,24,0.15) !important;
        border-radius: 0 !important;
        background: rgba(0,0,0,0.3) !important;
        padding: 1rem !important;
    }

    /* Corner decoration helper */
    .hud-corner {
        position: absolute;
        width: 12px; height: 12px;
    }
    .hud-corner.tl { top: 0; left: 0; border-top: 2px solid #f5c518; border-left: 2px solid #f5c518; }
    .hud-corner.tr { top: 0; right: 0; border-top: 2px solid #f5c518; border-right: 2px solid #f5c518; }
    .hud-corner.bl { bottom: 0; left: 0; border-bottom: 2px solid #f5c518; border-left: 2px solid #f5c518; }
    .hud-corner.br { bottom: 0; right: 0; border-bottom: 2px solid #f5c518; border-right: 2px solid #f5c518; }
</style>
""", unsafe_allow_html=True)

# ── Navigační session state ───────────────────────────────────────────
if 'nav_open' not in st.session_state:
    st.session_state['nav_open'] = False

# Mapa stránek: klíč → (label, ikona)
_NAV_PAGES = {
    'dashboard':  ('Dashboard',   '◈'),
    'auta':       ('Auta',        '◉'),
    'ridici':     ('Řidiči',      '◉'),
    'vyuctovani': ('Vyúčtování',  '◉'),
    'kalendar':   ('Kalendář',    '◉'),
    'finance':    ('Finance',     '◉'),
    'statistiky': ('Statistiky',  '◉'),
    'smlouvy':    ('Smlouvy',     '◉'),
    'banka':      ('Banka',       '◉'),
}

current_page = st.session_state.get('page', 'dashboard')
current_label = _NAV_PAGES.get(current_page, ('–', '◈'))[0]

# ── Top bar: Logo | Breadcrumb | Hamburger ────────────────────────────
nb_logo, nb_mid, nb_btn = st.columns([3, 5, 2])

with nb_logo:
    st.markdown('<div class="logo">▸ WAYNE//FLEET</div>', unsafe_allow_html=True)

with nb_mid:
    st.markdown(
        f"<div style='padding-top:0.55rem; font-family:Share Tech Mono,monospace; "
        f"font-size:0.75rem; color:rgba(245,197,24,0.4); letter-spacing:3px;'>"
        f"SYS / <span style='color:#f5c518; text-shadow:0 0 8px rgba(245,197,24,0.5);'>"
        f"{current_label.upper()}</span></div>",
        unsafe_allow_html=True
    )

with nb_btn:
    menu_label = "✕  ZAVŘÍT" if st.session_state['nav_open'] else "≡  MENU"
    if st.button(menu_label, key='nav_toggle', width='stretch'):
        st.session_state['nav_open'] = not st.session_state['nav_open']
        st.rerun()

# ── Rozbalovací menu ──────────────────────────────────────────────────
if st.session_state['nav_open']:
    st.markdown("""
    <div style='border:1px solid rgba(245,197,24,0.25);
         border-top:2px solid #f5c518;
         background:rgba(0,0,0,0.92);
         padding:1rem 1.5rem 1.2rem;
         margin-bottom:0.5rem;
         box-shadow:0 8px 40px rgba(245,197,24,0.1);
         position:relative;'>
      <div style='position:absolute; top:0; left:0; width:60px; height:2px;
           background:#f5c518; box-shadow:0 0 10px #f5c518;'></div>
      <div style='font-family:Share Tech Mono,monospace; font-size:0.65rem;
           color:rgba(245,197,24,0.3); letter-spacing:3px; margin-bottom:0.8rem;'>
           NAVIGACE — VYBERTE MODUL</div>
    </div>
    """, unsafe_allow_html=True)

    # Řada 1: 5 tlačítek
    mn1, mn2, mn3, mn4, mn5 = st.columns(5)
    with mn1:
        active = current_page == 'dashboard'
        if st.button("◈  Dashboard", key='nav_dashboard', width='stretch',
                     type='primary' if active else 'secondary'):
            st.session_state['page'] = 'dashboard'
            st.session_state['nav_open'] = False
            st.rerun()
    with mn2:
        active = current_page == 'auta'
        if st.button("◉  Auta", key='nav_auta', width='stretch',
                     type='primary' if active else 'secondary'):
            st.session_state['page'] = 'auta'
            st.session_state['nav_open'] = False
            st.rerun()
    with mn3:
        active = current_page == 'ridici'
        if st.button("◉  Řidiči", key='nav_ridici', width='stretch',
                     type='primary' if active else 'secondary'):
            st.session_state['page'] = 'ridici'
            st.session_state['nav_open'] = False
            st.rerun()
    with mn4:
        active = current_page == 'vyuctovani'
        if st.button("◉  Vyúčtování", key='nav_vyuctovani', width='stretch',
                     type='primary' if active else 'secondary'):
            st.session_state['page'] = 'vyuctovani'
            st.session_state['nav_open'] = False
            st.rerun()
    with mn5:
        active = current_page == 'kalendar'
        if st.button("◉  Kalendář", key='nav_kalendar', width='stretch',
                     type='primary' if active else 'secondary'):
            st.session_state['page'] = 'kalendar'
            st.session_state['nav_open'] = False
            st.rerun()

    # Řada 2: 4 tlačítka
    mn6, mn7, mn8, mn9 = st.columns(4)
    with mn6:
        active = current_page == 'finance'
        if st.button("◉  Finance", key='nav_finance', width='stretch',
                     type='primary' if active else 'secondary'):
            st.session_state['page'] = 'finance'
            st.session_state['nav_open'] = False
            st.rerun()
    with mn7:
        active = current_page == 'statistiky'
        if st.button("◉  Statistiky", key='nav_statistiky', width='stretch',
                     type='primary' if active else 'secondary'):
            st.session_state['page'] = 'statistiky'
            st.session_state['nav_open'] = False
            st.rerun()
    with mn8:
        active = current_page == 'smlouvy'
        if st.button("◉  Smlouvy", key='nav_smlouvy', width='stretch',
                     type='primary' if active else 'secondary'):
            st.session_state['page'] = 'smlouvy'
            st.session_state['nav_open'] = False
            st.rerun()
    with mn9:
        active = current_page == 'banka'
        if st.button("◉  Banka", key='nav_banka', width='stretch',
                     type='primary' if active else 'secondary'):
            st.session_state['page'] = 'banka'
            st.session_state['nav_open'] = False
            st.rerun()

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

# Tenká dělící linka pod navbarem
st.markdown(
    "<div style='height:1px; background:linear-gradient(90deg,#f5c518,rgba(245,197,24,0.1),transparent); "
    "box-shadow:0 0 8px rgba(245,197,24,0.2); margin-bottom:1rem;'></div>",
    unsafe_allow_html=True
)

# ==================== DASHBOARD PAGE ====================
if st.session_state['page'] == 'dashboard':
    from pages.dashboard_page import render_dashboard
    render_dashboard()

# ==================== AUTA PAGE ====================
elif st.session_state['page'] == 'auta':
    st.markdown("## 🚗 Správa aut")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### ◈ Fleet Overview")
    with col2:
        if st.button("➕ Přidat auto", width='stretch', type="primary"):
            st.session_state['show_add_car_form'] = not st.session_state['show_add_car_form']
    
    # Add car form
    if st.session_state['show_add_car_form']:
        with st.form("add_car_form"):
            st.markdown("### ➕ Nové auto")
            
            col1, col2 = st.columns(2)
            with col1:
                new_spz = st.text_input("SPZ *", placeholder="4AT 4091")
                new_model = st.text_input("Model *", placeholder="Škoda Octavia")
                new_rok = st.number_input("Rok *", min_value=2000, max_value=2025, value=2023)
            with col2:
                new_vin = st.text_input("VIN", placeholder="TMBAM7NE6F0173889")
                new_typ = st.selectbox("Typ *", ["vlastni", "pronajem"], format_func=lambda x: "🔑 Vlastní (na splátky)" if x == "vlastni" else "📋 Pronájem")
            
            if new_typ == "vlastni":
                st.markdown("#### 💰 Finance - Vlastní auto")
                col1, col2, col3 = st.columns(3)
                with col1:
                    new_kauce = st.number_input("Kauce (Kč)", min_value=0, value=10000, step=1000)
                with col2:
                    new_splatka = st.number_input("Splátka/týden (Kč)", min_value=0, value=5240, step=100)
                with col3:
                    new_pocet_splatek = st.number_input("Počet splátek", min_value=1, value=53, step=1)
            else:
                st.markdown("#### 💰 Finance - Pronájem")
                new_kauce = 0
                new_pocet_splatek = 0
                new_splatka = st.number_input("Nájem/týden (Kč)", min_value=0, value=4200, step=100)
            
            submitted = st.form_submit_button("💾 Uložit auto", width='stretch')
            
            if submitted:
                if new_spz and new_model:
                    try:
                        celkova_cena = new_kauce + (new_pocet_splatek * new_splatka) if new_typ == "vlastni" else 0
                        
                        car = create_car(
                            spz=new_spz,
                            model=new_model,
                            rok=new_rok,
                            vin=new_vin,
                            typ_vlastnictvi=new_typ,
                            kauce=new_kauce,
                            splatka_tyden=new_splatka,
                            celkem_splatek=new_pocet_splatek,
                            cena=celkova_cena
                        )
                        st.success(f"✅ Auto {car.spz} úspěšně přidáno!")
                        get_all_cars.clear()
                        st.session_state['show_add_car_form'] = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Chyba: {e}")
                else:
                    st.error("❌ Vyplň SPZ a Model")
    
    # Display all cars from database
    cars = get_all_cars()
    
    if not cars:
        st.info("💡 Nemáš ještě žádná auta. Klikni na 'Přidat auto'")
    else:
        for car in cars:
            stats = get_car_stats(car.id)
            status_class = 'status-active' if car.status == 'active' else 'status-service'
            status_text = '✅ AKTIVNÍ' if car.status == 'active' else '🔧 SERVIS'
            
            procento_splaceno = stats['procento_splaceno'] if stats else 0
            
            # Car card header
            typ_badge = "VLASTNÍ" if car.typ_vlastnictvi == 'vlastni' else "PRONÁJEM"
            typ_border = "border:1px solid #a78bfa; color:#a78bfa; text-shadow:0 0 6px rgba(167,139,250,0.6);" if car.typ_vlastnictvi == 'vlastni' else "border:1px solid #f5c518; color:#f5c518; text-shadow:0 0 6px rgba(245,197,24,0.6);"

            st.markdown(f"""
            <div class="car-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                    <div>
                        <div class="car-spz">{car.spz}</div>
                        <div style="font-family:Share Tech Mono,monospace; color: rgba(245,197,24,0.4); font-size:0.8rem; margin-top: 0.3rem; letter-spacing:1px;">{car.model.upper()} · {car.rok}</div>
                    </div>
                    <div style="display: flex; gap: 0.5rem; align-items:center;">
                        <div style="{typ_border} background:transparent; padding: 0.25rem 0.7rem;
                             font-family:Share Tech Mono,monospace; font-size: 0.7rem; letter-spacing:2px;">{typ_badge}</div>
                        <div class="{status_class}">{status_text}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Info using Streamlit columns
            if car.typ_vlastnictvi == 'vlastni':
                # Auto na splátky
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("💰 Kauce", f"{car.kauce:,} Kč")
                with col2:
                    st.metric("📅 Splátka/týden", f"{car.splatka_tyden:,} Kč")
                with col3:
                    st.metric("📊 Zaplaceno", f"{car.zaplaceno_splatek}/{car.celkem_splatek}")
                with col4:
                    st.metric("🛣️ Celkem KM", f"{car.celkem_km:,}")
                
                # Progress bar pro splátky
                st.markdown(f"""
                <div style="margin-top: 1rem;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                        <span style="color: rgba(255,255,255,0.6);">Splaceno</span>
                        <span style="color: white; font-weight: 600;">{stats['zaplaceno']:,.0f} / {stats['celkova_cena']:,.0f} Kč</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {procento_splaceno:.0f}%"></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-top: 0.5rem;">
                        <span style="color: rgba(255,255,255,0.5); font-size: 0.85rem;">{procento_splaceno:.1f}% splaceno ({car.zaplaceno_splatek} z {car.celkem_splatek} splátek)</span>
                        <span style="color: rgba(255,255,255,0.5); font-size: 0.85rem;">Zbývá: {stats['zbyvajici_splatka']:,.0f} Kč ({stats['zbyvajici_splatek']} splátek)</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Tlačítka pro akce
                st.markdown("<br>", unsafe_allow_html=True)
                col_edit, col_pay = st.columns(2)
                with col_edit:
                    if st.button(f"✏️ Upravit", key=f"edit_{car.id}"):
                        st.session_state['edit_car_id'] = car.id
                        st.rerun()
                with col_pay:
                    if st.button(f"💳 Zadat platbu", key=f"pay_{car.id}"):
                        st.session_state['payment_car_id'] = car.id
                        st.rerun()
                
                # Formulář pro editaci
                if st.session_state.get('edit_car_id') == car.id:
                    with st.form(f"edit_form_{car.id}"):
                        st.markdown("### ✏️ Upravit auto")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            edit_spz = st.text_input("SPZ", value=car.spz)
                            edit_model = st.text_input("Model", value=car.model)
                            edit_rok = st.number_input("Rok", min_value=2000, max_value=2025, value=car.rok)
                        with col2:
                            edit_vin = st.text_input("VIN", value=car.vin or "")
                            edit_km = st.number_input("Celkem KM", min_value=0, value=car.celkem_km)
                            edit_status = st.selectbox("Status", ["active", "service", "retired"], 
                                                      index=["active", "service", "retired"].index(car.status))
                        
                        st.markdown("#### 💰 Finance")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            edit_kauce = st.number_input("Kauce (Kč)", min_value=0, value=int(car.kauce))
                            edit_splatka = st.number_input("Splátka/týden (Kč)", min_value=0, value=int(car.splatka_tyden))
                        with col2:
                            edit_celkem_splatek = st.number_input("Celkem splátek", min_value=1, value=car.celkem_splatek)
                            edit_zaplaceno_splatek = st.number_input("Zaplaceno splátek", min_value=0, 
                                                                     max_value=car.celkem_splatek, 
                                                                     value=car.zaplaceno_splatek)
                        with col3:
                            nova_cena = edit_kauce + (edit_celkem_splatek * edit_splatka)
                            st.metric("Celková cena", f"{nova_cena:,} Kč")
                            nove_zaplaceno = edit_kauce + (edit_zaplaceno_splatek * edit_splatka)
                            st.metric("Zaplaceno", f"{nove_zaplaceno:,} Kč")
                        
                        col_submit, col_cancel = st.columns(2)
                        with col_submit:
                            submitted = st.form_submit_button("✅ Uložit změny", width='stretch')
                        with col_cancel:
                            cancel = st.form_submit_button("❌ Zrušit", width='stretch')
                        
                        if submitted:
                            try:
                                update_data = {
                                    'spz': edit_spz,
                                    'model': edit_model,
                                    'rok': edit_rok,
                                    'vin': edit_vin,
                                    'celkem_km': edit_km,
                                    'status': edit_status,
                                    'kauce': edit_kauce,
                                    'splatka_tyden': edit_splatka,
                                    'celkem_splatek': edit_celkem_splatek,
                                    'zaplaceno_splatek': edit_zaplaceno_splatek,
                                    'cena': nova_cena,
                                    'zaplaceno': nove_zaplaceno
                                }
                                
                                update_car(car.id, **update_data)
                                st.success(f"✅ Auto {edit_spz} úspěšně aktualizováno!")
                                get_all_cars.clear()
                                get_car_stats.clear()
                                st.session_state['edit_car_id'] = None
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Chyba: {e}")
                        
                        if cancel:
                            st.session_state['edit_car_id'] = None
                            st.rerun()
                
                # Formulář pro platbu
                if st.session_state.get('payment_car_id') == car.id:
                    with st.form(f"payment_form_{car.id}"):
                        st.markdown("### 💳 Nová platba")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            pocet_splatek = st.number_input(
                                "Počet splátek", 
                                min_value=1, 
                                max_value=stats['zbyvajici_splatek'],
                                value=1
                            )
                        with col2:
                            castka = pocet_splatek * car.splatka_tyden
                            st.metric("Částka", f"{castka:,} Kč")
                        
                        col_submit, col_cancel = st.columns(2)
                        with col_submit:
                            submitted = st.form_submit_button("✅ Potvrdit platbu", width='stretch')
                        with col_cancel:
                            cancel = st.form_submit_button("❌ Zrušit", width='stretch')
                        
                        if submitted:
                            try:
                                zadat_platbu(car.id, pocet_splatek)
                                st.success(f"✅ Platba {pocet_splatek} splátek ({castka:,} Kč) zaznamenána!")
                                get_all_cars.clear()
                                get_car_stats.clear()
                                st.session_state['payment_car_id'] = None
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Chyba: {e}")
                        
                        if cancel:
                            st.session_state['payment_car_id'] = None
                            st.rerun()
            else:
                # Pronájem
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📅 Nájem/týden", f"{car.splatka_tyden:,} Kč")
                with col2:
                    st.metric("🛣️ Celkem KM", f"{car.celkem_km:,}")
                with col3:
                    st.metric("📍 VIN", car.vin or 'N/A')
                
                st.info("💡 Toto auto je na pronájem - nikdy nebude vaše")

            # Detail tlačítko pro všechna auta
            if st.button("📋 Detail auta", key=f"detail_car_{car.id}"):
                st.session_state['page'] = 'auto_detail'
                st.session_state['detail_car_id'] = car.id
                st.rerun()

            st.markdown("---")

# ==================== ŘIDIČI PAGE ====================
elif st.session_state['page'] == 'ridici':
    st.markdown("## 👥 Správa řidičů")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### ◈ Správa řidičů")
    with col2:
        if st.button("➕ Přidat řidiče", width='stretch', type="primary"):
            st.session_state['show_add_driver_form'] = not st.session_state['show_add_driver_form']
    
    # Add driver form
    if st.session_state['show_add_driver_form']:
        with st.form("add_driver_form"):
            st.markdown("### ➕ Nový řidič")
            
            col1, col2 = st.columns(2)
            with col1:
                new_jmeno = st.text_input("Jméno *", placeholder="Jan Novák")
                new_email = st.text_input("Email", placeholder="jan@example.com")
            with col2:
                new_telefon = st.text_input("Telefon", placeholder="+420 777 888 999")
                new_datum = st.date_input("Datum nástupu")
            
            submitted = st.form_submit_button("💾 Uložit řidiče", width='stretch')
            
            if submitted:
                if new_jmeno:
                    try:
                        driver = create_driver(
                            jmeno=new_jmeno,
                            email=new_email,
                            telefon=new_telefon,
                            datum_nastupu=new_datum
                        )
                        st.success(f"✅ Řidič {driver.jmeno} úspěšně přidán!")
                        get_all_drivers.clear()
                        st.session_state['show_add_driver_form'] = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Chyba: {e}")
                else:
                    st.error("❌ Vyplň jméno")
    
    # Display all drivers from database
    drivers = get_all_drivers()

    if not drivers:
        st.info("💡 Nemáš ještě žádné řidiče. Klikni na 'Přidat řidiče'")
    else:
        hide_inactive = st.toggle("Skrýt Inactive řidiče", value=True, key="hide_inactive_drivers")
        visible_drivers = [d for d in drivers if not (hide_inactive and d.status == 'inactive')] if hide_inactive else drivers
        inactive_count = sum(1 for d in drivers if d.status == 'inactive')
        if hide_inactive and inactive_count:
            st.caption(f"🙈 {inactive_count} inactive řidič{'i' if inactive_count > 1 else ''} skryt{'i' if inactive_count > 1 else ''}")
        for driver in visible_drivers:
            initials = ''.join([n[0] for n in driver.jmeno.split()])

            col_card, col_btn = st.columns([5, 1])
            with col_card:
                st.markdown(f"""
                <div class="driver-card">
                    <div class="driver-avatar">{initials}</div>
                    <div style="flex: 1;">
                        <div class="driver-name">{driver.jmeno}</div>
                        <div class="driver-meta">
                            📧 {driver.email or 'N/A'} | 📱 {driver.telefon or 'N/A'}
                            <br/>📅 Od {driver.datum_nastupu.strftime('%d.%m.%Y') if driver.datum_nastupu else 'N/A'}
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <div style="color: rgba(255,255,255,0.6); font-size: 0.9rem;">Status</div>
                        <div style="font-size: 1.5rem; font-weight: 700; color: #10b981;">
                            {'✅ Aktivní' if driver.status == 'active' else '📋 ' + driver.status.title()}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with col_btn:
                st.markdown("<br><br>", unsafe_allow_html=True)
                if st.button("📋 Detail", key=f"detail_driver_{driver.id}", width='stretch'):
                    st.session_state['page'] = 'ridic_detail'
                    st.session_state['detail_driver_id'] = driver.id
                    st.rerun()

# ==================== OTHER PAGES ====================
elif st.session_state['page'] == 'vyuctovani':
    st.markdown("## 💰 Týdenní vyúčtování")
    st.markdown("Nahraj CSV soubory z Uber a Bolt pro automatické vygenerování vyúčtování")
    
    # Upload CSV
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="premium-card">', unsafe_allow_html=True)
        st.markdown("### 🚕 Uber CSV")
        uber_file = st.file_uploader("Nahrát Uber CSV", type=['csv'], key='uber_upload')
        
        if uber_file:
            try:
                content = uber_file.read()
                st.session_state['uber_data'] = parse_uber_csv(content)
                st.success(f"✅ Načteno {len(st.session_state['uber_data'])} řidičů z Uber")
            except Exception as e:
                st.error(f"❌ Chyba při načítání Uber CSV: {e}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="premium-card">', unsafe_allow_html=True)
        st.markdown("### ⚡ Bolt CSV")
        bolt_file = st.file_uploader("Nahrát Bolt CSV", type=['csv'], key='bolt_upload')
        
        if bolt_file:
            try:
                content = bolt_file.read()
                st.session_state['bolt_data'] = parse_bolt_csv(content)
                st.success(f"✅ Načteno {len(st.session_state['bolt_data'])} řidičů z Bolt")
            except Exception as e:
                st.error(f"❌ Chyba při načítání Bolt CSV: {e}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Pokud jsou načtená data, zobraz přehled
    if st.session_state['uber_data'] or st.session_state['bolt_data']:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="premium-card">', unsafe_allow_html=True)
        st.markdown("### 📊 Přehled DPH podle řidičů")
        
        # Spojit data z obou platforem
        all_drivers = {}
        
        if st.session_state['uber_data']:
            for normalized, data in st.session_state['uber_data'].items():
                if normalized not in all_drivers:
                    all_drivers[normalized] = {
                        'name': data['name'],
                        'uber_amount': 0,
                        'uber_commission': 0,
                        'uber_hotovost': 0,
                        'bolt_amount': 0,
                        'bolt_commission': 0,
                        'bolt_hotovost': 0
                    }
                all_drivers[normalized]['uber_amount'] = data['uber_amount']
                all_drivers[normalized]['uber_commission'] = data['uber_commission']
                all_drivers[normalized]['uber_hotovost'] = data.get('uber_hotovost', 0)
        
        if st.session_state['bolt_data']:
            for normalized, data in st.session_state['bolt_data'].items():
                if normalized not in all_drivers:
                    all_drivers[normalized] = {
                        'name': data['name'],
                        'uber_amount': 0,
                        'uber_commission': 0,
                        'uber_hotovost': 0,
                        'bolt_amount': 0,
                        'bolt_commission': 0,
                        'bolt_hotovost': 0
                    }
                all_drivers[normalized]['bolt_amount'] = data['bolt_amount']
                all_drivers[normalized]['bolt_commission'] = data['bolt_commission']
                all_drivers[normalized]['bolt_hotovost'] = data.get('bolt_hotovost', 0)
        
        # Zobrazit pro každého řidiče
        total_vat = 0
        
        for normalized, driver_data in all_drivers.items():
            total_commission = driver_data['uber_commission'] + driver_data['bolt_commission']
            vat = total_commission * 0.21
            total_vat += vat
            
            # Najít řidiče v DB
            db_driver = find_driver_by_name(driver_data['name'])
            
            # Výpočty pro zobrazení
            celkova_mzda = driver_data['uber_amount'] + driver_data['bolt_amount']
            celkovy_poplatek = total_commission
            cista_mzda = celkova_mzda - celkovy_poplatek
            celkova_hotovost = driver_data.get('uber_hotovost', 0) + driver_data.get('bolt_hotovost', 0)
            k_vyplate = cista_mzda - celkova_hotovost
            
            st.markdown(f"""
            <div class="driver-card">
                <div class="driver-info">
                    <div class="driver-name">{driver_data['name']}</div>
                    <div class="driver-meta">
                        💰 <strong>Celková mzda:</strong> {celkova_mzda:,.2f} Kč
                        <br/>
                        🚕 Uber: {driver_data['uber_amount']:,.2f} Kč | ⚡ Bolt: {driver_data['bolt_amount']:,.2f} Kč
                        <br/>
                        📊 <strong>Poplatek:</strong> {celkovy_poplatek:,.2f} Kč (DPH 21%: {vat:,.2f} Kč)
                        <br/>
                        ✅ <strong>Čistá mzda:</strong> {cista_mzda:,.2f} Kč
                        <br/>
                        💵 <strong>Hotovost:</strong> {celkova_hotovost:,.2f} Kč
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="color: rgba(255,255,255,0.6); font-size: 0.9rem;">K VÝPLATĚ</div>
                    <div style="font-size: 2rem; font-weight: 700; color: #10b981;">{k_vyplate:,.2f} Kč</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Formulář pro generování PDF
            with st.expander(f"📄 Vygenerovat PDF pro {driver_data['name']}"):
                with st.form(f"pdf_form_{normalized}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Získat všechna auta z DB
                        all_cars_list = get_all_cars()
                        car_options = [""] + [f"{car.spz} - {car.model}" for car in all_cars_list]
                        car_spz_only = [""] + [car.spz for car in all_cars_list]

                        selected_car_idx = st.selectbox(
                            "SPZ vozidla",
                            range(len(car_options)),
                            format_func=lambda x: car_options[x] if car_options[x] else "-- Vyberte auto --",
                            key=f"car_select_{normalized}"
                        )
                        spz = car_spz_only[selected_car_idx]

                        # Typ pronájmu
                        typ_najmu = st.radio(
                            "Typ pronájmu",
                            ["Denní (800 Kč/den + 200 Kč/den flotila)", "Týdenní (z karty auta)", "Vlastní vůz (1 000 Kč flotila + DPH)"],
                            key=f"typ_najmu_{normalized}"
                        )

                        if typ_najmu.startswith("Denní"):
                            num_days = st.number_input("Počet dní", min_value=1, max_value=7, value=7, key=f"days_{normalized}")
                            najem_override = None
                            poplatek_override = None
                            vlastni_vuz = False
                        elif typ_najmu.startswith("Vlastní"):
                            num_days = 7
                            najem_override = 0
                            poplatek_override = 1000
                            vlastni_vuz = True
                        else:
                            # Týdenní pronájem – načíst cenu z vybraného auta
                            selected_car_obj = all_cars_list[selected_car_idx - 1] if selected_car_idx > 0 else None
                            default_najem = int(selected_car_obj.cena_tyden_pronajem or 0) if selected_car_obj else 0
                            najem_override = st.number_input(
                                "Najem vozidla (Kč/týden)",
                                min_value=0, value=default_najem, step=100,
                                key=f"najem_tyden_{normalized}"
                            )
                            poplatek_override = st.number_input(
                                "Poplatek flotila (Kč/týden)",
                                min_value=0, value=1000, step=100,
                                key=f"poplatek_tyden_{normalized}"
                            )
                            num_days = 7
                            vlastni_vuz = False

                        kauce_check = st.checkbox("Účtovat kauci (prvních 8 týdnů)", key=f"kauce_check_{normalized}")
                        kauce = 1250 if kauce_check else 0

                    with col2:
                        palivo = st.number_input("Palivo (Kč)", min_value=0, value=0, key=f"palivo_{normalized}")
                        pokuty = st.number_input("Pokuty/škody (Kč)", min_value=0, value=0, key=f"pokuty_{normalized}")
                        period_start = st.date_input("Období od", key=f"start_{normalized}")
                        period_end = st.date_input("Období do", key=f"end_{normalized}")

                    submitted = st.form_submit_button("📥 Vygenerovat PDF", width='stretch')

                    if submitted:
                        try:
                            pdf_buffer = generate_driver_invoice_pdf(
                                driver_name=driver_data['name'],
                                uber_amount=driver_data['uber_amount'],
                                bolt_amount=driver_data['bolt_amount'],
                                vat_amount=vat,
                                period_start=period_start.strftime('%d.%m.%Y'),
                                period_end=period_end.strftime('%d.%m.%Y'),
                                license_plate=spz,
                                num_days=num_days,
                                kauce=kauce,
                                penalties=pokuty,
                                palivo=palivo,
                                uber_hotovost=driver_data.get('uber_hotovost', 0),
                                bolt_hotovost=driver_data.get('bolt_hotovost', 0),
                                najem_override=najem_override if not typ_najmu.startswith("Denní") else None,
                                poplatek_override=poplatek_override if not typ_najmu.startswith("Denní") else None,
                                vlastni_vuz=vlastni_vuz,
                            )
                            
                            st.session_state['generated_pdfs'][normalized] = {
                                'buffer': pdf_buffer,
                                'filename': f"vyuctovani_{normalize_name(driver_data['name'])}_{period_start.strftime('%Y%m%d')}.pdf"
                            }
                            
                            st.success(f"✅ PDF vygenerováno!")
                        except Exception as e:
                            st.error(f"❌ Chyba: {e}")
                
                # Download button
                if normalized in st.session_state.get('generated_pdfs', {}):
                    pdf_info = st.session_state['generated_pdfs'][normalized]
                    st.download_button(
                        label="💾 Stáhnout vygenerované PDF",
                        data=pdf_info['buffer'],
                        file_name=pdf_info['filename'],
                        mime="application/pdf",
                        key=f"download_{normalized}"
                    )
        
        # Celkové DPH
        st.markdown(f"""
        <div style="background: rgba(57,255,20,0.05); border: 1px solid #39ff14;
             clip-path: polygon(0 0, calc(100% - 20px) 0, 100% 20px, 100% 100%, 20px 100%, 0 calc(100% - 20px));
             padding: 2rem; text-align: center; color: white; margin-top: 2rem;
             box-shadow: 0 0 30px rgba(57,255,20,0.15), inset 0 0 30px rgba(57,255,20,0.04);">
            <div style="font-family: Share Tech Mono, monospace; font-size: 0.75rem; letter-spacing: 3px;
                 color: rgba(57,255,20,0.6); margin-bottom: 0.5rem;">◈ CELKOVÉ DPH K ODVEDENÍ</div>
            <div style="font-family: Orbitron, monospace; font-size: 2.5rem; font-weight: 700;
                 color: #39ff14; text-shadow: 0 0 20px rgba(57,255,20,0.7);">{total_vat:,.2f} KČ</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("💡 Nahraj CSV soubory z Uber a/nebo Bolt pro zobrazení vyúčtování")

elif st.session_state['page'] == 'kalendar':
    from pages.calendar_page import render_calendar_page
    render_calendar_page()

elif st.session_state['page'] == 'finance':
    from pages.finance_page import render_finance_page
    render_finance_page()

elif st.session_state['page'] == 'statistiky':
    from pages.stats_page import render_stats_page
    render_stats_page()

elif st.session_state['page'] == 'ridic_detail':
    from pages.driver_detail import render_driver_detail
    render_driver_detail(st.session_state.get('detail_driver_id'))

elif st.session_state['page'] == 'auto_detail':
    from pages.car_detail import render_car_detail
    render_car_detail(st.session_state.get('detail_car_id'))

elif st.session_state['page'] == 'smlouvy':
    from pages.smlouvy_page import render_smlouvy_page
    render_smlouvy_page()

elif st.session_state['page'] == 'banka':
    from pages.banka_page import render_banka_page
    render_banka_page()
