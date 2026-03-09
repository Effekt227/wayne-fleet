"""
Finance Page - Wayne Fleet Management System
Kalendář plateb: vydané i přijaté faktury, opakující se platby
"""

import streamlit as st
import calendar as cal_module
from datetime import date, timedelta
from database.crud_finance_records import (
    get_records, get_records_for_month, get_records_by_date,
    create_record, create_recurring_records,
    mark_paid, mark_unpaid, delete_record,
    delete_recurring_from, get_monthly_summary,
)
from utils.cached_queries import (
    cached_drivers as get_all_drivers, cached_cars as get_all_cars,
    cached_pending_records as _cp, cached_monthly_summary as _cs,
)


def _clear_fin():
    _cp.clear()
    _cs.clear()

MESICE_CZ = [
    'Leden', 'Únor', 'Březen', 'Duben', 'Květen', 'Červen',
    'Červenec', 'Srpen', 'Září', 'Říjen', 'Listopad', 'Prosinec',
]
DNY_CZ = ['Po', 'Út', 'St', 'Čt', 'Pá', 'So', 'Ne']

KATEGORIE_VYDANE = ['Nájem/splátka řidiče', 'Kauce řidiče', 'Pokuta řidiče', 'Jiné']
KATEGORIE_PRIJATE = ['Splátka za auto', 'Pronájem auta', 'Pojistka', 'Servis/oprava', 'Provozní náklady', 'Jiné']


def render_finance_page():
    # ── Session state ──────────────────────────────────────────────
    today = date.today()
    if 'fin_rok' not in st.session_state:
        st.session_state['fin_rok'] = today.year
    if 'fin_mesic' not in st.session_state:
        st.session_state['fin_mesic'] = today.month
    if 'fin_selected_day' not in st.session_state:
        st.session_state['fin_selected_day'] = today

    rok = st.session_state['fin_rok']
    mesic = st.session_state['fin_mesic']

    # ── Navigace měsícem ──────────────────────────────────────────
    col_prev, col_title, col_next = st.columns([1, 4, 1])
    with col_prev:
        if st.button("◀", width='stretch', key='fin_prev'):
            if mesic == 1:
                st.session_state['fin_mesic'] = 12
                st.session_state['fin_rok'] -= 1
            else:
                st.session_state['fin_mesic'] -= 1
            st.rerun()
    with col_title:
        st.markdown(
            f"<div style='text-align:center; font-size:1.5rem; font-weight:700; padding:0.4rem;'>"
            f"💳 {MESICE_CZ[mesic-1]} {rok}</div>",
            unsafe_allow_html=True
        )
    with col_next:
        if st.button("▶", width='stretch', key='fin_next'):
            if mesic == 12:
                st.session_state['fin_mesic'] = 1
                st.session_state['fin_rok'] += 1
            else:
                st.session_state['fin_mesic'] += 1
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tlačítka pro přidání ──────────────────────────────────────
    col_add1, col_add2, col_add3 = st.columns(3)
    with col_add1:
        if st.button("➕ Přidat vydanou fakturu", width='stretch'):
            st.session_state['fin_add_vydana'] = True
    with col_add2:
        if st.button("➕ Přidat výdaj / přijatou", width='stretch'):
            st.session_state['fin_add_prijata'] = True
    with col_add3:
        if st.button("🔄 Přidat opakující se platbu", width='stretch'):
            st.session_state['fin_add_recurring'] = True

    all_drivers = get_all_drivers()
    all_cars = get_all_cars()

    # ── Formuláře ─────────────────────────────────────────────────
    _render_add_form('vydana', all_drivers, all_cars)
    _render_add_form('prijata', all_drivers, all_cars)
    _render_recurring_form(all_drivers, all_cars)

    # ── Načíst data pro měsíc ─────────────────────────────────────
    month_records = get_records_for_month(rok, mesic)
    by_date: dict[date, list] = {}
    for r in month_records:
        d = r.datum_splatnosti
        if d:
            by_date.setdefault(d, []).append(r)

    # ── Kalendářní grid ───────────────────────────────────────────
    _render_calendar_grid(rok, mesic, by_date, today)

    # ── Legendy ───────────────────────────────────────────────────
    st.markdown(
        "<div style='display:flex; gap:1.5rem; margin:0.5rem 0 1rem; font-size:0.82rem; color:rgba(255,255,255,0.6);'>"
        "<span>🟢 Vydaná (příjem)</span>"
        "<span>🟠 Přijatá – čeká na platbu</span>"
        "<span>🔴 Přijatá – po splatnosti</span>"
        "<span>⬜ Zaplaceno</span>"
        "</div>",
        unsafe_allow_html=True
    )

    st.markdown("---")

    # ── Detail vybraného dne ──────────────────────────────────────
    selected = st.session_state['fin_selected_day']
    sel_col, _ = st.columns([2, 4])
    with sel_col:
        new_sel = st.date_input(
            "Zobrazit den",
            value=selected,
            key='fin_day_picker',
        )
        if new_sel != selected:
            st.session_state['fin_selected_day'] = new_sel
            st.rerun()

    day_records = by_date.get(selected, [])
    st.markdown(
        f"#### 📅 {selected.strftime('%d. %m. %Y')} "
        f"– {DNY_CZ[selected.weekday()]}"
    )

    if day_records:
        _render_day_records(day_records, all_drivers, all_cars)
    else:
        st.info("Tento den nemáš žádné platby.")

    # ── Měsíční přehled ───────────────────────────────────────────
    st.markdown("---")
    summary = get_monthly_summary(rok, mesic)
    st.markdown(f"#### 📊 Souhrn – {MESICE_CZ[mesic-1]} {rok}")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📤 Vydáno celkem", f"{summary['vydano_celkem']:,.0f} Kč")
    col2.metric("📥 Výdaje celkem", f"{summary['prijato_celkem']:,.0f} Kč")
    col3.metric("💰 Bilance (zaplaceno)", f"{summary['bilance']:,.0f} Kč")
    col4.metric("⏳ Nezaplacené výdaje", f"{summary['prijato_nezaplaceno']:,.0f} Kč")

    # ── Kompletní seznam měsíce ───────────────────────────────────
    if month_records:
        st.markdown("---")
        with st.expander(f"📋 Všechny platby v {MESICE_CZ[mesic-1]} ({len(month_records)} záznamů)"):
            _render_month_list(month_records, all_drivers, all_cars)


def _render_calendar_grid(rok: int, mesic: int, by_date: dict, today: date):
    """Vykreslí HTML kalendářní grid se splatnými platbami."""
    weeks = cal_module.monthcalendar(rok, mesic)

    # Záhlaví dnů
    header = "".join(
        f"<th style='padding:0.5rem; color:rgba(255,255,255,0.5); font-size:0.82rem; "
        f"text-align:center; font-weight:600; border-bottom:1px solid rgba(255,255,255,0.1);'>"
        f"{d}</th>"
        for d in DNY_CZ
    )

    rows_html = ""
    for week in weeks:
        row = ""
        for day_num in week:
            if day_num == 0:
                row += "<td style='padding:0.5rem; height:80px; border:1px solid rgba(255,255,255,0.05);'></td>"
                continue

            d = date(rok, mesic, day_num)
            is_today = d == today
            selected = st.session_state.get('fin_selected_day') == d
            day_records = by_date.get(d, [])

            if is_today:
                border = "border:2px solid #f5c518;"
                bg = "background:rgba(245,197,24,0.12);"
            elif selected:
                border = "border:2px solid #10b981;"
                bg = "background:rgba(16,185,129,0.1);"
            else:
                border = "border:1px solid rgba(255,255,255,0.07);"
                bg = ""

            day_color = "#f5c518" if is_today else "rgba(255,255,255,0.8)"

            # Indikátory plateb
            indicators = ""
            for r in day_records[:4]:  # max 4 indikátory na buňku
                if r.status == 'zaplaceno':
                    color = 'rgba(255,255,255,0.25)'
                elif r.typ == 'vydana':
                    color = '#10b981'
                elif r.datum_splatnosti and r.datum_splatnosti < today:
                    color = '#ef4444'
                else:
                    color = '#f59e0b'

                short = f"#{r.id} " + (r.popis[:9] + '…' if len(r.popis) > 9 else r.popis)
                paid_style = "text-decoration:line-through;" if r.status == 'zaplaceno' else ""
                indicators += (
                    f"<div style='font-size:0.68rem; color:{color}; white-space:nowrap; "
                    f"overflow:hidden; text-overflow:ellipsis; {paid_style} margin-top:1px;'>"
                    f"{'•'} {short}</div>"
                )
            if len(day_records) > 4:
                indicators += f"<div style='font-size:0.65rem; color:rgba(255,255,255,0.4);'>+{len(day_records)-4} další</div>"

            row += (
                f"<td style='padding:0.4rem 0.5rem; height:80px; vertical-align:top; "
                f"cursor:pointer; {bg} {border} border-radius:4px;'>"
                f"<div style='font-size:0.88rem; font-weight:600; color:{day_color};'>{day_num}</div>"
                f"{indicators}"
                f"</td>"
            )
        rows_html += f"<tr>{row}</tr>"

    html = (
        f"<table style='width:100%; border-collapse:separate; border-spacing:3px; table-layout:fixed;'>"
        f"<thead><tr>{header}</tr></thead>"
        f"<tbody>{rows_html}</tbody>"
        f"</table>"
    )
    st.markdown(html, unsafe_allow_html=True)


def _render_day_records(records: list, all_drivers, all_cars):
    """Vykreslí záznamy pro vybraný den s akcemi."""
    today = date.today()
    for r in records:
        overdue = r.datum_splatnosti and r.datum_splatnosti < today and r.status == 'nezaplaceno'
        if r.status == 'zaplaceno':
            color = '#10b981'
            badge = '✅ Zaplaceno'
        elif overdue:
            color = '#ef4444'
            badge = '⚠️ Po splatnosti'
        else:
            color = '#f59e0b'
            badge = '⏳ Nezaplaceno'

        typ_icon = '📤' if r.typ == 'vydana' else '📥'
        drv = next((d.jmeno for d in all_drivers if d.id == r.driver_id), None)
        car = next((f"{c.spz}" for c in all_cars if c.id == r.car_id), None)
        meta_parts = []
        if drv:
            meta_parts.append(f"👤 {drv}")
        if car:
            meta_parts.append(f"🚗 {car}")
        if r.kategorie:
            meta_parts.append(r.kategorie)
        if r.recurring_group_id:
            meta_parts.append("🔄 opakující se")

        col_info, col_amt, col_st, col_act1, col_act2, col_del = st.columns([4, 2, 2, 1.5, 1.5, 0.8])
        with col_info:
            st.markdown(
                f"**{typ_icon} {r.popis}**  \n"
                f"<span style='color:rgba(255,255,255,0.5); font-size:0.82rem;'>"
                f"{' &nbsp;|&nbsp; '.join(meta_parts)}</span>",
                unsafe_allow_html=True
            )
        with col_amt:
            st.markdown(f"<strong style='color:white;'>{r.castka_kc:,.0f} Kč</strong>", unsafe_allow_html=True)
        with col_st:
            st.markdown(f"<span style='color:{color};'>{badge}</span>", unsafe_allow_html=True)
        with col_act1:
            if r.status == 'nezaplaceno':
                if st.button("✅", key=f"dp_pay_{r.id}", help="Označit jako zaplaceno", width='stretch'):
                    mark_paid(r.id)
                    _clear_fin()
                    st.rerun()
        with col_act2:
            if r.status == 'zaplaceno':
                if st.button("↩️", key=f"dp_unpay_{r.id}", help="Vrátit na nezaplaceno", width='stretch'):
                    mark_unpaid(r.id)
                    _clear_fin()
                    st.rerun()
        with col_del:
            if st.button("🗑️", key=f"dp_del_{r.id}", help="Smazat"):
                if r.recurring_group_id:
                    st.session_state[f'confirm_del_recurring_{r.id}'] = r
                else:
                    delete_record(r.id)
                    _clear_fin()
                    st.rerun()

        # Potvrzení smazání opakující se
        if st.session_state.get(f'confirm_del_recurring_{r.id}'):
            with st.form(f"del_rec_confirm_{r.id}"):
                st.warning("Opakující se platba – co smazat?")
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    only_this = st.form_submit_button("Jen tento", width='stretch')
                with col_b:
                    from_here = st.form_submit_button("Od tohoto dne dál", width='stretch')
                with col_c:
                    cancel_del = st.form_submit_button("Zrušit", width='stretch')
                if only_this:
                    delete_record(r.id)
                    del st.session_state[f'confirm_del_recurring_{r.id}']
                    _clear_fin()
                    st.rerun()
                if from_here:
                    delete_recurring_from(r.recurring_group_id, from_date=r.datum_splatnosti)
                    del st.session_state[f'confirm_del_recurring_{r.id}']
                    _clear_fin()
                    st.rerun()
                if cancel_del:
                    del st.session_state[f'confirm_del_recurring_{r.id}']
                    st.rerun()

        st.markdown("<hr style='margin:0.3rem 0; opacity:0.1;'>", unsafe_allow_html=True)


def _render_month_list(records: list, all_drivers, all_cars):
    """Kompletní seznam záznamů měsíce s akcemi."""
    today = date.today()
    for r in records:
        overdue = r.datum_splatnosti and r.datum_splatnosti < today and r.status == 'nezaplaceno'
        if r.status == 'zaplaceno':
            color = '#10b981'
        elif overdue:
            color = '#ef4444'
        else:
            color = '#f59e0b'

        typ_icon = '📤' if r.typ == 'vydana' else '📥'
        drv = next((d.jmeno for d in all_drivers if d.id == r.driver_id), None)
        car = next((f"{c.spz}" for c in all_cars if c.id == r.car_id), None)

        col_d, col_pop, col_rel, col_amt, col_act = st.columns([1.5, 3.5, 2, 1.5, 1.5])
        with col_d:
            st.markdown(
                f"<span style='font-size:0.85rem;'>{r.datum_splatnosti.strftime('%d.%m.') if r.datum_splatnosti else '—'}</span>",
                unsafe_allow_html=True
            )
        with col_pop:
            st.markdown(f"{typ_icon} **{r.popis}**")
        with col_rel:
            parts = [p for p in [drv, car] if p]
            st.markdown(
                f"<span style='color:rgba(255,255,255,0.5); font-size:0.82rem;'>{' / '.join(parts) or '—'}</span>",
                unsafe_allow_html=True
            )
        with col_amt:
            st.markdown(f"<strong style='color:{color};'>{r.castka_kc:,.0f} Kč</strong>", unsafe_allow_html=True)
        with col_act:
            if r.status == 'nezaplaceno':
                if st.button("✅", key=f"ml_pay_{r.id}", help="Zaplaceno", width='stretch'):
                    mark_paid(r.id)
                    _clear_fin()
                    st.rerun()
            else:
                if st.button("↩️", key=f"ml_unpay_{r.id}", help="Vrátit", width='stretch'):
                    mark_unpaid(r.id)
                    _clear_fin()
                    st.rerun()

        st.markdown("<hr style='margin:0.2rem 0; opacity:0.08;'>", unsafe_allow_html=True)

    total = sum(r.castka_kc for r in records)
    paid = sum(r.castka_kc for r in records if r.status == 'zaplaceno')
    st.markdown(
        f"<div style='text-align:right; margin-top:0.5rem; color:rgba(255,255,255,0.7);'>"
        f"Celkem: <strong style='color:white;'>{total:,.0f} Kč</strong> &nbsp;|&nbsp; "
        f"Zaplaceno: <strong style='color:#10b981;'>{paid:,.0f} Kč</strong> &nbsp;|&nbsp; "
        f"Zbývá: <strong style='color:#f59e0b;'>{total - paid:,.0f} Kč</strong>"
        f"</div>",
        unsafe_allow_html=True
    )


def _render_add_form(typ: str, all_drivers, all_cars):
    """Formulář pro přidání jedné faktury/platby."""
    key = f'fin_add_{typ}'
    if not st.session_state.get(key):
        return

    nadpis = "📤 Nová vydaná faktura" if typ == 'vydana' else "📥 Nový výdaj / přijatá faktura"
    kategorie_list = KATEGORIE_VYDANE if typ == 'vydana' else KATEGORIE_PRIJATE

    with st.form(f"add_form_{typ}"):
        st.markdown(f"**{nadpis}**")
        col1, col2, col3 = st.columns([3, 2, 2])
        with col1:
            popis = st.text_input("Popis *", key=f"af_pop_{typ}")
        with col2:
            kategorie = st.selectbox("Kategorie", kategorie_list, key=f"af_kat_{typ}")
        with col3:
            castka = st.number_input("Částka (Kč) *", min_value=0.0, step=100.0, key=f"af_cst_{typ}")

        col4, col5 = st.columns(2)
        with col4:
            datum_splatnosti = st.date_input(
                "Datum splatnosti *",
                value=st.session_state.get('fin_selected_day', date.today()),
                key=f"af_dat_{typ}"
            )
        with col5:
            driver_opts = {'— Žádný —': None}
            driver_opts.update({d.jmeno: d.id for d in all_drivers})
            car_opts = {'— Žádné —': None}
            car_opts.update({f"{c.spz} – {c.model}": c.id for c in all_cars})
            sel_drv = st.selectbox("Řidič", list(driver_opts.keys()), key=f"af_drv_{typ}")
            sel_car = st.selectbox("Auto", list(car_opts.keys()), key=f"af_car_{typ}")

        col_s, col_c = st.columns(2)
        with col_s:
            submitted = st.form_submit_button("💾 Uložit", width='stretch')
        with col_c:
            cancelled = st.form_submit_button("❌ Zrušit", width='stretch')

        if submitted:
            if popis and castka > 0:
                create_record(
                    typ=typ,
                    popis=popis,
                    castka_kc=castka,
                    datum=datum_splatnosti,
                    datum_splatnosti=datum_splatnosti,
                    kategorie=kategorie,
                    driver_id=driver_opts[sel_drv],
                    car_id=car_opts[sel_car],
                )
                st.session_state[key] = False
                st.session_state['fin_selected_day'] = datum_splatnosti
                _clear_fin()
                st.success("Uloženo.")
                st.rerun()
            else:
                st.error("Vyplň popis a částku.")
        if cancelled:
            st.session_state[key] = False
            st.rerun()


def _render_recurring_form(all_drivers, all_cars):
    """Formulář pro opakující se platby – vygeneruje záznamy na celé období."""
    if not st.session_state.get('fin_add_recurring'):
        return

    with st.form("recurring_form"):
        st.markdown("**🔄 Opakující se platba**")

        col1, col2, col3 = st.columns([3, 2, 2])
        with col1:
            popis = st.text_input("Popis *", placeholder="Např. Splátka 4AT 4091")
        with col2:
            typ = st.selectbox("Typ", ['vydana', 'prijata'],
                               format_func=lambda x: '📤 Vydaná (příjem)' if x == 'vydana' else '📥 Přijatá (výdaj)')
        with col3:
            castka = st.number_input("Částka (Kč) *", min_value=0.0, step=100.0)

        col4, col5, col6 = st.columns(3)
        with col4:
            kategorie_list = KATEGORIE_VYDANE if True else KATEGORIE_PRIJATE  # dynamicky níže
            # musíme vybrat kategorie podle typu – použijeme combined list
            all_kat = ['— Vybrat —'] + KATEGORIE_VYDANE + [k for k in KATEGORIE_PRIJATE if k not in KATEGORIE_VYDANE]
            kategorie = st.selectbox("Kategorie", all_kat)
        with col5:
            interval = st.selectbox(
                "Opakování",
                ['tydne', 'mesicne'],
                format_func=lambda x: 'Každý týden' if x == 'tydne' else 'Každý měsíc'
            )
        with col6:
            interval_hodnota = st.number_input("Každých N", min_value=1, max_value=52, value=1)

        col7, col8 = st.columns(2)
        with col7:
            datum_od = st.date_input("Od *", value=date.today())
        with col8:
            datum_do = st.date_input("Do *", value=date(date.today().year, 12, 31))

        col9, col10 = st.columns(2)
        with col9:
            driver_opts = {'— Žádný —': None}
            driver_opts.update({d.jmeno: d.id for d in all_drivers})
            sel_drv = st.selectbox("Řidič", list(driver_opts.keys()))
        with col10:
            car_opts = {'— Žádné —': None}
            car_opts.update({f"{c.spz} – {c.model}": c.id for c in all_cars})
            sel_car = st.selectbox("Auto", list(car_opts.keys()))

        col_s, col_c = st.columns(2)
        with col_s:
            submitted = st.form_submit_button("💾 Vygenerovat platby", width='stretch')
        with col_c:
            cancelled = st.form_submit_button("❌ Zrušit", width='stretch')

        if submitted:
            if popis and castka > 0 and datum_od <= datum_do:
                records = create_recurring_records(
                    typ=typ,
                    popis=popis,
                    castka_kc=castka,
                    kategorie=kategorie if kategorie != '— Vybrat —' else None,
                    datum_od=datum_od,
                    datum_do=datum_do,
                    interval=interval,
                    interval_hodnota=int(interval_hodnota),
                    driver_id=driver_opts[sel_drv],
                    car_id=car_opts[sel_car],
                )
                st.session_state['fin_add_recurring'] = False
                st.session_state['fin_rok'] = datum_od.year
                st.session_state['fin_mesic'] = datum_od.month
                st.session_state['fin_selected_day'] = datum_od
                _clear_fin()
                st.success(f"Vygenerováno {len(records)} opakujících se záznamů.")
                st.rerun()
            else:
                st.error("Vyplň popis, částku a správné datum od/do.")
        if cancelled:
            st.session_state['fin_add_recurring'] = False
            st.rerun()
