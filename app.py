"""
Wayne Fleet Management System - MAIN APPLICATION
Complete system with real database integration
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database.database import init_db
init_db()
from database.crud_cars import get_all_cars, get_active_cars, create_car, update_car, get_car_stats
from database.crud_drivers import get_all_drivers, get_active_drivers, create_driver, update_driver
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

# Ultra Premium CSS (same as before)
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .block-container {
        padding-top: 0rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 100%;
    }

    /* Pozadí – černé */
    .stApp, [data-testid="stAppViewContainer"] {
        background: #0a0a0a !important;
    }
    [data-testid="stHeader"] {
        background: transparent !important;
    }

    /* Logo */
    .logo {
        font-size: 2rem;
        font-weight: 900;
        background: linear-gradient(135deg, #f5c518 0%, #d4a017 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -1px;
    }

    /* Karty */
    .stat-card {
        background: rgba(245,197,24,0.08);
        border: 1px solid rgba(245,197,24,0.25);
        border-radius: 20px;
        padding: 2rem;
        text-align: center;
        transition: all 0.3s ease;
        height: 100%;
    }
    .stat-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px rgba(245,197,24,0.2);
    }
    .stat-icon { font-size: 3rem; margin-bottom: 1rem; }
    .stat-value {
        font-size: 3rem;
        font-weight: 900;
        background: linear-gradient(135deg, #f5c518 0%, #d4a017 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0.5rem 0;
    }
    .stat-label {
        color: rgba(255,255,255,0.6);
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }
    .stat-change { color: #10b981; font-size: 0.9rem; font-weight: 600; margin-top: 0.5rem; }

    .premium-card {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(245,197,24,0.15);
        border-radius: 20px;
        padding: 2rem;
        margin: 1rem 0;
        box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    }

    .car-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 16px;
        padding: 2rem;
        margin: 1rem 0;
        position: relative;
        overflow: hidden;
        transition: all 0.3s ease;
    }
    .car-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px rgba(245,197,24,0.15);
    }
    .car-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 100%; height: 4px;
        background: linear-gradient(90deg, #f5c518 0%, #d4a017 100%);
    }
    .car-spz { font-size: 1.8rem; font-weight: 800; color: white; }

    .status-active {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white; padding: 0.5rem 1rem; border-radius: 20px;
        font-size: 0.8rem; font-weight: 700; text-transform: uppercase;
    }
    .status-service {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        color: white; padding: 0.5rem 1rem; border-radius: 20px;
        font-size: 0.8rem; font-weight: 700; text-transform: uppercase;
    }

    .info-box {
        background: rgba(255,255,255,0.03);
        padding: 1rem; border-radius: 8px;
        border: 1px solid rgba(245,197,24,0.1);
    }
    .info-label {
        color: rgba(255,255,255,0.5); font-size: 0.75rem;
        text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.5rem;
    }
    .info-value { color: white; font-size: 1.3rem; font-weight: 700; }
    .info-value.success { color: #10b981; }
    .info-value.warning { color: #f5c518; }

    .progress-bar {
        background: rgba(255,255,255,0.1);
        border-radius: 10px; height: 8px; overflow: hidden; margin: 0.5rem 0;
    }
    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #f5c518 0%, #d4a017 100%);
        border-radius: 10px; transition: width 0.3s ease;
    }

    .driver-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 16px; padding: 2rem; margin: 1rem 0;
        display: flex; align-items: center; gap: 2rem; transition: all 0.3s ease;
    }
    .driver-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 30px rgba(245,197,24,0.15);
    }
    .driver-avatar {
        width: 80px; height: 80px; border-radius: 50%;
        background: linear-gradient(135deg, #f5c518 0%, #d4a017 100%);
        display: flex; align-items: center; justify-content: center;
        font-size: 2rem; font-weight: 900; color: #0a0a0a;
    }
    .driver-name { font-size: 1.5rem; font-weight: 700; color: white; margin-bottom: 0.5rem; }
    .driver-meta { color: rgba(255,255,255,0.6); font-size: 0.9rem; }

    h1, h2, h3 { color: white !important; }
    p, div, span { color: rgba(255,255,255,0.8); }

    /* Tlačítka – žlutá */
    .stButton > button,
    button[kind="secondary"],
    button[kind="primary"] {
        background: linear-gradient(135deg, #f5c518 0%, #d4a017 100%) !important;
        color: #0a0a0a !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(245,197,24,0.4) !important;
        background: linear-gradient(135deg, #ffd700 0%, #f5c518 100%) !important;
    }
    .stButton > button:active {
        transform: translateY(0) !important;
    }

    /* Metriky */
    [data-testid="stMetricValue"] { color: white; font-size: 2rem; }
    [data-testid="stMetricLabel"] { color: rgba(255,255,255,0.6); }

    /* Input fields */
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stSelectbox"] select,
    textarea {
        background: #1a1a1a !important;
        border-color: rgba(245,197,24,0.3) !important;
        color: white !important;
    }

    /* Tabs */
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        background: #111111;
        border-bottom: 2px solid rgba(245,197,24,0.2);
    }
    [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
        color: #f5c518 !important;
        border-bottom-color: #f5c518 !important;
    }

    /* Expander */
    [data-testid="stExpander"] {
        border-color: rgba(245,197,24,0.2) !important;
        background: rgba(255,255,255,0.02) !important;
    }
</style>
""", unsafe_allow_html=True)

# Top Navigation
nav_col1, nav_col2, nav_col3, nav_col4, nav_col5, nav_col6, nav_col7, nav_col8, nav_col9, nav_col10 = st.columns([2, 1, 1, 1, 1, 1, 1, 1, 1, 1])

with nav_col1:
    st.markdown('<div class="logo">⚡ WAYNE FLEET</div>', unsafe_allow_html=True)

with nav_col2:
    if st.button("📊 Dashboard", width='stretch', key='nav_dashboard'):
        st.session_state['page'] = 'dashboard'

with nav_col3:
    if st.button("🚗 Auta", width='stretch', key='nav_auta'):
        st.session_state['page'] = 'auta'

with nav_col4:
    if st.button("👥 Řidiči", width='stretch', key='nav_ridici'):
        st.session_state['page'] = 'ridici'

with nav_col5:
    if st.button("💰 Vyúčtování", width='stretch', key='nav_vyuctovani'):
        st.session_state['page'] = 'vyuctovani'

with nav_col6:
    if st.button("📅 Kalendář", width='stretch', key='nav_kalendar'):
        st.session_state['page'] = 'kalendar'

with nav_col7:
    if st.button("💳 Finance", width='stretch', key='nav_finance'):
        st.session_state['page'] = 'finance'

with nav_col8:
    if st.button("📈 Statistiky", width='stretch', key='nav_statistiky'):
        st.session_state['page'] = 'statistiky'

with nav_col9:
    if st.button("📄 Smlouvy", width='stretch', key='nav_smlouvy'):
        st.session_state['page'] = 'smlouvy'

with nav_col10:
    if st.button("🏦 Banka", width='stretch', key='nav_banka'):
        st.session_state['page'] = 'banka'

st.markdown("<br>", unsafe_allow_html=True)

# ==================== DASHBOARD PAGE ====================
if st.session_state['page'] == 'dashboard':
    from pages.dashboard_page import render_dashboard
    render_dashboard()

# ==================== AUTA PAGE ====================
elif st.session_state['page'] == 'auta':
    st.markdown("## 🚗 Správa aut")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### Fleet Overview - REAL DATA")
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
            typ_badge = "🔑 VLASTNÍ" if car.typ_vlastnictvi == 'vlastni' else "📋 PRONÁJEM"
            typ_class = "background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);" if car.typ_vlastnictvi == 'vlastni' else "background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);"
            
            st.markdown(f"""
            <div class="car-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                    <div>
                        <div class="car-spz">🚗 {car.spz}</div>
                        <div style="color: rgba(255,255,255,0.6); margin-top: 0.5rem;">{car.model} ({car.rok})</div>
                    </div>
                    <div style="display: flex; gap: 0.5rem;">
                        <div style="{typ_class} color: white; padding: 0.5rem 1rem; border-radius: 20px; font-size: 0.8rem; font-weight: 700;">{typ_badge}</div>
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
        st.markdown("### Řidiči - REAL DATA")
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
        <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 2rem; border-radius: 16px; text-align: center; color: white; margin-top: 2rem;">
            <div style="font-size: 1rem; opacity: 0.9; margin-bottom: 0.5rem;">CELKOVÉ DPH K ODVEDENÍ</div>
            <div style="font-size: 3rem; font-weight: 900;">{total_vat:,.2f} Kč</div>
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
