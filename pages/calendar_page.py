"""
Calendar page - Wayne Fleet Management System
Podporuje: ranní/večerní 12h směny, celý den 24h, týdenní pronájem, servis
"""

import streamlit as st
from datetime import datetime, timedelta
from utils.cached_queries import cached_cars as get_all_cars, cached_week_assignments
from database.crud_drivers import get_active_drivers
from database.crud_calendar import (
    get_week_assignments,
    set_weekly_rental,
    clear_weekly_rental,
    create_or_update_shift,
    clear_shift,
)

DAYS_CZ = ['Po', 'Út', 'St', 'Čt', 'Pá', 'So', 'Ne']

VOLNE = '--- Volné ---'
CELY_DEN = '--- Celý den (24h) ---'
SERVIS = '--- Servis ---'
ZADNY = '--- Žádný ---'


def render_calendar_page():
    st.markdown("## Kalendář směn")

    # Inicializace session state
    if 'calendar_week_start' not in st.session_state:
        today = datetime.now().date()
        st.session_state['calendar_week_start'] = today - timedelta(days=today.weekday())

    week_start = st.session_state['calendar_week_start']
    week_end = week_start + timedelta(days=6)

    # Navigace týdnem
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        if st.button("◀ Předchozí", width='stretch'):
            st.session_state['calendar_week_start'] -= timedelta(days=7)
            st.rerun()
    with col2:
        st.markdown(
            f"<div style='text-align:center; font-size:1.2rem; font-weight:600; padding:0.5rem;'>"
            f"Týden: {week_start.strftime('%d.%m')} – {week_end.strftime('%d.%m.%Y')}</div>",
            unsafe_allow_html=True
        )
    with col3:
        if st.button("Další ▶", width='stretch'):
            st.session_state['calendar_week_start'] += timedelta(days=7)
            st.rerun()

    # Data
    all_cars = get_all_cars()
    active_drivers = get_active_drivers()
    week_data = cached_week_assignments(week_start)

    if not all_cars:
        st.info("Nejprve přidej auta na stránce Auta.")
        return
    if not active_drivers:
        st.info("Nejprve přidej řidiče na stránce Řidiči.")
        return

    driver_names = [d.jmeno for d in active_drivers]
    driver_map = {d.jmeno: d.id for d in active_drivers}

    # Blok pro každé auto
    for car in all_cars:
        car_data = week_data.get(car.id, {})
        with st.expander(f"🚗 {car.spz} – {car.model}", expanded=True):
            _render_car_block(car, week_start, week_end, car_data, driver_names, driver_map)


def _render_car_block(car, week_start, week_end, car_data, driver_names, driver_map):
    """Vykreslí blok jednoho auta: týdenní pronájem + denní grid"""

    # ── Týdenní pronájem ──────────────────────────────────────────
    weekly_list = car_data.get('__weekly__', [])
    weekly_rental = weekly_list[0] if weekly_list else None

    weekly_options = [ZADNY] + driver_names
    current_weekly_idx = 0
    if weekly_rental and weekly_rental.get('driver_name'):
        try:
            current_weekly_idx = weekly_options.index(weekly_rental['driver_name'])
        except ValueError:
            current_weekly_idx = 0

    col_label, col_select = st.columns([1, 3])
    with col_label:
        st.markdown("**🔑 Týdenní pronájem:**")
    with col_select:
        selected_weekly = st.selectbox(
            "Týdenní pronájem",
            weekly_options,
            index=current_weekly_idx,
            key=f"weekly_{car.id}_{week_start}",
            label_visibility="collapsed"
        )

    # Zpracovat změnu týdenního pronájmu
    if selected_weekly != weekly_options[current_weekly_idx]:
        if selected_weekly == ZADNY:
            clear_weekly_rental(car.id, week_start)
        else:
            set_weekly_rental(car.id, week_start, driver_map[selected_weekly])
        cached_week_assignments.clear()
        st.rerun()

    # Pokud je týdenní pronájem aktivní, zobrazit banner a skrýt grid
    if weekly_rental:
        driver_label = weekly_rental.get('driver_name') or 'neznámý řidič'
        st.info(
            f"🔑 PRONAJATO: **{driver_label}** "
            f"({week_start.strftime('%d.%m')} – {week_end.strftime('%d.%m.%Y')})"
        )
        return

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Denní grid ────────────────────────────────────────────────
    # Záhlaví: štítek + 7 dnů
    header_cols = st.columns([1] + [1] * 7)
    with header_cols[0]:
        st.markdown("**Směna**")
    for i, day_name in enumerate(DAYS_CZ):
        day_date = week_start + timedelta(days=i)
        with header_cols[i + 1]:
            st.markdown(f"**{day_name}**<br>{day_date.strftime('%d.%m')}", unsafe_allow_html=True)

    # Ranní řádek
    morning_cols = st.columns([1] + [1] * 7)
    with morning_cols[0]:
        st.markdown("☀️ **7–19**")
    for idx in range(7):
        day_date = week_start + timedelta(days=idx)
        day_shifts = car_data.get(day_date, [])
        ranni = next((s for s in day_shifts if s.get('typ') == 'ranni'), None)
        cely_den = next((s for s in day_shifts if s.get('typ') == 'cely_den'), None)
        servis = next((s for s in day_shifts if s.get('typ') == 'servis'), None)
        with morning_cols[idx + 1]:
            _render_morning_slot(car, day_date, ranni, cely_den, servis, driver_names, driver_map)

    # Večerní řádek
    evening_cols = st.columns([1] + [1] * 7)
    with evening_cols[0]:
        st.markdown("🌙 **19–7**")
    for idx in range(7):
        day_date = week_start + timedelta(days=idx)
        day_shifts = car_data.get(day_date, [])
        vecerni = next((s for s in day_shifts if s.get('typ') == 'vecerni'), None)
        cely_den = next((s for s in day_shifts if s.get('typ') == 'cely_den'), None)
        servis = next((s for s in day_shifts if s.get('typ') == 'servis'), None)
        with evening_cols[idx + 1]:
            _render_evening_slot(car, day_date, vecerni, cely_den, servis, driver_names, driver_map)


def _render_morning_slot(car, day_date, ranni, cely_den, servis, driver_names, driver_map):
    """Vykreslí ranní slot (6–18) nebo celý den / servis"""

    # Pokud je celý den ale bez řidiče: zobrazit výběr řidiče
    if cely_den and not cely_den.get('driver_name'):
        opts = ['— Vybrat řidiče —'] + driver_names
        chosen = st.selectbox(
            "24h řidič",
            opts,
            key=f"cd_pick_{car.id}_{day_date}",
            label_visibility="collapsed"
        )
        if chosen != '— Vybrat řidiče —':
            create_or_update_shift(car.id, day_date, 'cely_den', driver_map[chosen])
            cached_week_assignments.clear()
            st.rerun()
        return

    # Pokud je celý den s řidičem: zobrazit dropdown se jménem
    if cely_den and cely_den.get('driver_name'):
        driver_label = cely_den['driver_name']
        opts = [f"🕐 {driver_label}", VOLNE] + driver_names
        chosen = st.selectbox(
            "24h",
            opts,
            index=0,
            key=f"cd_sel_{car.id}_{day_date}",
            label_visibility="collapsed"
        )
        if chosen != opts[0]:
            if chosen == VOLNE:
                clear_shift(car.id, day_date, 'cely_den')
            else:
                create_or_update_shift(car.id, day_date, 'cely_den', driver_map[chosen])
            cached_week_assignments.clear()
            st.rerun()
        return

    # Pokud je servis
    if servis:
        if st.button("🔧 Servis", key=f"servis_morn_{car.id}_{day_date}", width='stretch'):
            clear_shift(car.id, day_date, 'servis')
            cached_week_assignments.clear()
            st.rerun()
        return

    # Normální ranní dropdown
    morning_options = [VOLNE, CELY_DEN, SERVIS] + driver_names

    current_idx = 0
    if ranni and ranni.get('driver_name'):
        try:
            current_idx = morning_options.index(ranni['driver_name'])
        except ValueError:
            current_idx = 0

    selected = st.selectbox(
        "Ranní",
        morning_options,
        index=current_idx,
        key=f"morn_{car.id}_{day_date}",
        label_visibility="collapsed"
    )

    if selected == morning_options[current_idx]:
        return

    if selected == VOLNE:
        clear_shift(car.id, day_date, 'ranni')
    elif selected == CELY_DEN:
        # Vytvořit celý den bez řidiče – další rerun ukáže výběr řidiče
        create_or_update_shift(car.id, day_date, 'cely_den', driver_id=None)
    elif selected == SERVIS:
        create_or_update_shift(car.id, day_date, 'servis', driver_id=None)
    else:
        create_or_update_shift(car.id, day_date, 'ranni', driver_map[selected])

    cached_week_assignments.clear()
    st.rerun()


def _render_evening_slot(car, day_date, vecerni, cely_den, servis, driver_names, driver_map):
    """Vykreslí večerní slot (18–6); uzamčen pokud je celý den nebo servis"""

    # Pokud je celý den: zobrazit informaci (slot uzamčen)
    if cely_den:
        driver_label = cely_den.get('driver_name') or '...'
        st.markdown(
            f"<div style='color:rgba(255,255,255,0.35); font-size:0.8rem; text-align:center;'>"
            f"🕐 {driver_label}</div>",
            unsafe_allow_html=True
        )
        return

    # Pokud je servis: zobrazit info
    if servis:
        st.markdown(
            "<div style='color:rgba(255,255,255,0.35); font-size:0.8rem; text-align:center;'>"
            "🔧</div>",
            unsafe_allow_html=True
        )
        return

    # Normální večerní dropdown
    evening_options = [VOLNE, SERVIS] + driver_names

    current_idx = 0
    if vecerni and vecerni.get('driver_name'):
        try:
            current_idx = evening_options.index(vecerni['driver_name'])
        except ValueError:
            current_idx = 0

    selected = st.selectbox(
        "Večerní",
        evening_options,
        index=current_idx,
        key=f"eve_{car.id}_{day_date}",
        label_visibility="collapsed"
    )

    if selected == evening_options[current_idx]:
        return

    if selected == VOLNE:
        clear_shift(car.id, day_date, 'vecerni')
    elif selected == SERVIS:
        create_or_update_shift(car.id, day_date, 'servis', driver_id=None)
    else:
        create_or_update_shift(car.id, day_date, 'vecerni', driver_map[selected])

    cached_week_assignments.clear()
    st.rerun()
