"""
Stats Page - Wayne Fleet Management System
Statistiky flotily: příjmy, výdaje, zisky, přehled aut a řidičů
"""

import calendar as cal_mod
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from utils.cached_queries import (
    cached_cars as get_all_cars,
    cached_car_stats as get_car_stats,
    cached_drivers as get_all_drivers,
    cached_monthly_summary as get_monthly_summary,
    cached_chart_data as get_monthly_chart_data,
    cached_chart_data_range as get_monthly_chart_data_range,
    cached_driver_stats as get_driver_stats,
    cached_service_cost as get_total_service_cost,
    cached_fines_summary as get_driver_fines_summary,
    cached_fleet_occupancy as get_fleet_occupancy_month,
)

MESICE_CZ = [
    'Leden', 'Únor', 'Březen', 'Duben', 'Květen', 'Červen',
    'Červenec', 'Srpen', 'Září', 'Říjen', 'Listopad', 'Prosinec',
]


def _month_label(m: dict) -> str:
    zkratky = ['Led', 'Úno', 'Bře', 'Dub', 'Kvě', 'Čer', 'Čvc', 'Srp', 'Zář', 'Říj', 'Lis', 'Pro']
    return f"{zkratky[m['mesic']-1]} {m['rok'] % 100:02d}"


def _kpi_card(label: str, value: str, sub: str = "", color: str = "#f5c518", icon: str = "") -> str:
    return (
        f"<div style='background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); "
        f"border-top:2px solid {color}; border-radius:10px; padding:1rem 1.2rem;'>"
        f"<div style='font-size:0.78rem; color:rgba(255,255,255,0.45); text-transform:uppercase; "
        f"letter-spacing:0.08em; margin-bottom:0.4rem;'>{icon} {label}</div>"
        f"<div style='font-size:1.5rem; font-weight:700; color:{color}; line-height:1.1;'>{value}</div>"
        f"{'<div style=\"font-size:0.78rem; color:rgba(255,255,255,0.4); margin-top:0.3rem;\">' + sub + '</div>' if sub else ''}"
        f"</div>"
    )


def render_stats_page():
    st.markdown("## Statistiky flotily")

    tab1, tab2, tab3, tab4 = st.tabs([
        "Finance",
        "Auta",
        "Řidiči",
        "Expirace & Nábor",
    ])

    with tab1:
        _render_financial_overview()
    with tab2:
        _render_auta()
    with tab3:
        _render_driver_overview()
    with tab4:
        _render_expirace_nabor()


# ══════════════════════════════════════════════════════════════════
# TAB 1: FINANCE
# ══════════════════════════════════════════════════════════════════

def _render_financial_overview():
    today = date.today()

    # ── Filtr ────────────────────────────────────────────────────────
    col_f, col_spacer = st.columns([3, 5])
    with col_f:
        mode = st.segmented_control(
            "Období",
            options=["Tento měsíc", "Posledních 6M", f"Rok {today.year}"],
            default="Posledních 6M",
            key="stats_mode",
            label_visibility="collapsed",
        )

    if mode == "Tento měsíc":
        s = get_monthly_summary(today.year, today.month)
        s['rok'] = today.year
        s['mesic'] = today.month
        s['label'] = f"{today.year}-{today.month:02d}"
        monthly_data = [s]
    elif mode == f"Rok {today.year}":
        monthly_data = get_monthly_chart_data_range(today.year, 1, today.year, 12)
    else:  # Posledních 6M
        start = today - timedelta(days=180)
        monthly_data = get_monthly_chart_data_range(
            start.year, start.month, today.year, today.month
        )
        # Omezit pouze na minulé/aktuální měsíce (bez nulových budoucích)
        monthly_data = [
            m for m in monthly_data
            if (m['rok'], m['mesic']) <= (today.year, today.month)
        ]

    if not monthly_data:
        st.info("Žádná data pro vybrané období.")
        return

    # ── KPI karty ────────────────────────────────────────────────────
    this_month = next(
        (m for m in monthly_data if m['rok'] == today.year and m['mesic'] == today.month), {}
    )
    total_vydano = sum(m['vydano_celkem'] for m in monthly_data)
    total_prijato = sum(m['prijato_celkem'] for m in monthly_data)
    total_bilance = sum(m['bilance'] for m in monthly_data)
    total_pohledavky = sum(m['vydano_nezaplaceno'] for m in monthly_data)

    bilance_color = "#10b981" if total_bilance >= 0 else "#ef4444"
    pohledavky_color = "#f59e0b" if total_pohledavky > 0 else "#10b981"

    is_multi = len(monthly_data) > 1
    sub_vydano = f"Tento měsíc: {this_month.get('vydano_celkem', 0):,.0f} Kč" if is_multi and this_month else ""
    sub_prijato = f"Tento měsíc: {this_month.get('prijato_celkem', 0):,.0f} Kč" if is_multi and this_month else ""
    sub_bilance = f"Inkasováno (zaplaceno)" if is_multi else ""

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(_kpi_card("Příjmy celkem", f"{total_vydano:,.0f} Kč", sub_vydano, "#10b981", "↑"), unsafe_allow_html=True)
    c2.markdown(_kpi_card("Výdaje celkem", f"{total_prijato:,.0f} Kč", sub_prijato, "#ef4444", "↓"), unsafe_allow_html=True)
    c3.markdown(_kpi_card("Bilance", f"{total_bilance:,.0f} Kč", sub_bilance, bilance_color, "="), unsafe_allow_html=True)
    c4.markdown(_kpi_card("Pohledávky", f"{total_pohledavky:,.0f} Kč", "Čekám na příjem", pohledavky_color, "⏳"), unsafe_allow_html=True)

    st.markdown("<div style='height:1.5rem;'></div>", unsafe_allow_html=True)

    # ── Grafy ─────────────────────────────────────────────────────────
    has_data = any(m['vydano_celkem'] > 0 or m['prijato_celkem'] > 0 for m in monthly_data)
    labels = [_month_label(m) for m in monthly_data]

    if has_data:
        chart_df = pd.DataFrame(
            {
                'Příjmy': [m['vydano_celkem'] for m in monthly_data],
                'Výdaje': [m['prijato_celkem'] for m in monthly_data],
            },
            index=labels,
        )
        st.bar_chart(chart_df, color=['#10b981', '#ef4444'])

    if len(monthly_data) > 1 and has_data:
        st.markdown(
            "<div style='font-size:0.82rem; color:rgba(255,255,255,0.45); margin:0.5rem 0 0.2rem;'>Bilance / Zisk</div>",
            unsafe_allow_html=True,
        )
        profit_df = pd.DataFrame(
            {'Bilance': [m['bilance'] for m in monthly_data]},
            index=labels,
        )
        st.line_chart(profit_df, color=['#f5c518'])

    # ── Tabulka ───────────────────────────────────────────────────────
    st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
    rows = []
    for m in monthly_data:
        je_aktualni = m['rok'] == today.year and m['mesic'] == today.month
        znacka = " ◀" if je_aktualni else ""
        bilance_val = m['bilance']
        rows.append({
            'Měsíc': f"{MESICE_CZ[m['mesic']-1]} {m['rok']}{znacka}",
            'Příjmy': f"{m['vydano_celkem']:,.0f} Kč",
            'Výdaje': f"{m['prijato_celkem']:,.0f} Kč",
            'Bilance': f"{bilance_val:+,.0f} Kč".replace("+", "+") if bilance_val >= 0 else f"{bilance_val:,.0f} Kč",
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════
# TAB 2: AUTA (Flotila + Výnosnost)
# ══════════════════════════════════════════════════════════════════

def _render_auta():
    today = date.today()
    all_cars = get_all_cars()
    if not all_cars:
        st.info("Žádná auta v databázi.")
        return

    days_in_month = cal_mod.monthrange(today.year, today.month)[1]
    occupancy = get_fleet_occupancy_month(today.year, today.month)

    active_cars = [c for c in all_cars if c.status == 'active']
    total_weekly = sum((c.splatka_tyden or 0) for c in all_cars)
    ocekavane_mesic = sum((c.cena_tyden_pronajem or 0) * 4.33 for c in active_cars)

    # ── KPI ───────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    c1.markdown(_kpi_card("Aktivních aut", str(len(active_cars)), f"Celkem: {len(all_cars)}", "#f5c518", "🚗"), unsafe_allow_html=True)
    c2.markdown(_kpi_card("Týdenní náklady", f"{total_weekly:,.0f} Kč", f"Měsíčně: {total_weekly*4.33:,.0f} Kč", "#ef4444", "💸"), unsafe_allow_html=True)
    c3.markdown(_kpi_card("Očekávané příjmy / měsíc", f"{ocekavane_mesic:,.0f} Kč", "Aktivní auta × sazba", "#10b981", "💵"), unsafe_allow_html=True)

    st.markdown("<div style='height:1.2rem;'></div>", unsafe_allow_html=True)

    # ── Karty aut ─────────────────────────────────────────────────────
    alerts = []

    for car in all_cars:
        stats = get_car_stats(car.id) or {}
        service_cost = get_total_service_cost(car.id)

        prijmy_mesic = (car.cena_tyden_pronajem or 0) * 4.33
        naklady_splatka = (car.splatka_tyden or 0) * 4.33
        naklady_servis = service_cost / 12
        naklady_celkem = naklady_splatka + naklady_servis
        zisk = prijmy_mesic - naklady_celkem

        obsazeno_dni = occupancy.get(car.id, 0)
        obsazenost_pct = obsazeno_dni / days_in_month * 100 if days_in_month > 0 else 0

        if car.status == 'active' and obsazeno_dni == 0:
            alerts.append(car.spz)

        # Barva borderu
        if car.status == 'retired':
            border_color = "#4b5563"
        elif zisk >= 0:
            border_color = "#10b981"
        else:
            border_color = "#ef4444"

        status_label = {'active': 'aktivní', 'service': 'servis', 'retired': 'vyřazeno'}.get(car.status, car.status)
        status_color = {'active': '#10b981', 'service': '#f59e0b', 'retired': '#6b7280'}.get(car.status, '#6b7280')
        zisk_color = "#10b981" if zisk >= 0 else "#ef4444"
        zisk_sign = "+" if zisk >= 0 else ""

        # Progress bar obsazenost
        occ_pct_clamped = min(obsazenost_pct, 100)
        occ_color = "#10b981" if occ_pct_clamped >= 70 else ("#f59e0b" if occ_pct_clamped >= 30 else "#ef4444")
        occ_bar = (
            f"<div style='flex:1; background:rgba(255,255,255,0.08); border-radius:4px; height:8px; margin:auto 0;'>"
            f"<div style='width:{occ_pct_clamped:.0f}%; height:100%; background:{occ_color}; border-radius:4px;'></div>"
            f"</div>"
        )

        # Progress bar splácení (pouze vlastní auta)
        splaceni_html = ""
        if car.typ_vlastnictvi == 'vlastni':
            procento = stats.get('procento_splaceno', 0)
            clamped = min(procento, 100)
            sp_color = "#10b981" if clamped >= 100 else "#f5c518"
            splaceni_html = (
                f"<div style='display:flex; align-items:center; gap:0.6rem; margin-top:0.5rem;'>"
                f"<span style='font-size:0.75rem; color:rgba(255,255,255,0.4); white-space:nowrap;'>Splácení</span>"
                f"<div style='flex:1; background:rgba(255,255,255,0.08); border-radius:4px; height:6px;'>"
                f"<div style='width:{clamped:.0f}%; height:100%; background:{sp_color}; border-radius:4px;'></div>"
                f"</div>"
                f"<span style='font-size:0.75rem; color:{sp_color}; white-space:nowrap;'>{procento:.0f}%</span>"
                f"</div>"
            )

        typ_badge = (
            "<span style='font-size:0.72rem; color:rgba(255,255,255,0.35); "
            "border:1px solid rgba(255,255,255,0.15); border-radius:4px; padding:1px 6px;'>"
            + ("vlastní" if car.typ_vlastnictvi == 'vlastni' else "pronájem") +
            "</span>"
        )

        card_html = (
            f"<div style='background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.07); "
            f"border-left:3px solid {border_color}; border-radius:10px; padding:0.9rem 1.1rem; margin-bottom:0.5rem;'>"
            # Hlavička
            f"<div style='display:flex; align-items:center; gap:0.8rem; margin-bottom:0.6rem;'>"
            f"<span style='font-size:1rem; font-weight:700; color:white; letter-spacing:0.05em;'>{car.spz}</span>"
            f"<span style='color:rgba(255,255,255,0.5); font-size:0.88rem;'>{car.model} ({car.rok})</span>"
            f"{typ_badge}"
            f"<span style='margin-left:auto; font-size:0.78rem; color:{status_color};'>{status_label}</span>"
            f"</div>"
            # Metriky
            f"<div style='display:flex; gap:1.5rem; flex-wrap:wrap;'>"
            f"<div><div style='font-size:0.72rem; color:rgba(255,255,255,0.35);'>Příjmy/měs</div>"
            f"<div style='font-size:0.95rem; font-weight:600; color:#10b981;'>{prijmy_mesic:,.0f} Kč</div></div>"
            f"<div><div style='font-size:0.72rem; color:rgba(255,255,255,0.35);'>Náklady/měs</div>"
            f"<div style='font-size:0.95rem; font-weight:600; color:#ef4444;'>{naklady_celkem:,.0f} Kč</div></div>"
            f"<div><div style='font-size:0.72rem; color:rgba(255,255,255,0.35);'>Zisk/měs (est.)</div>"
            f"<div style='font-size:0.95rem; font-weight:700; color:{zisk_color};'>{zisk_sign}{zisk:,.0f} Kč</div></div>"
            f"<div style='flex:1; min-width:120px;'>"
            f"<div style='font-size:0.72rem; color:rgba(255,255,255,0.35); margin-bottom:4px;'>Obsazenost {today.month}/{today.year} — {obsazeno_dni} dní ({obsazenost_pct:.0f}%)</div>"
            f"<div style='display:flex; align-items:center; gap:0.5rem;'>"
            f"<span style='font-size:0.78rem; color:{occ_color};'>▐</span>"
            f"{occ_bar}"
            f"</div></div>"
            f"</div>"
            + splaceni_html +
            f"</div>"
        )
        st.markdown(card_html, unsafe_allow_html=True)

    # ── Upozornění ────────────────────────────────────────────────────
    if alerts:
        st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
        for spz in alerts:
            st.warning(f"Auto **{spz}** nemá tento měsíc žádného řidiče.")
    else:
        st.markdown(
            "<div style='color:#10b981; font-size:0.85rem; margin-top:0.5rem;'>"
            "✓ Všechna aktivní auta mají přiřazeného řidiče.</div>",
            unsafe_allow_html=True
        )

    # ── Obsazenost — bar chart ─────────────────────────────────────────
    visible_cars = [c for c in all_cars if c.status != 'retired']
    if visible_cars:
        st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='font-size:0.82rem; color:rgba(255,255,255,0.45); margin-bottom:0.2rem;'>"
            f"Obsazenost aut — {MESICE_CZ[today.month-1]} {today.year} (dní)</div>",
            unsafe_allow_html=True,
        )
        occ_df = pd.DataFrame(
            {'Obsazené dny': [occupancy.get(c.id, 0) for c in visible_cars]},
            index=[c.spz for c in visible_cars],
        )
        st.bar_chart(occ_df, color=['#10b981'])


# ══════════════════════════════════════════════════════════════════
# TAB 3: ŘIDIČI
# ══════════════════════════════════════════════════════════════════

def _render_driver_overview():
    all_drivers = get_all_drivers()
    if not all_drivers:
        st.info("Žádní řidiči v databázi.")
        return

    all_cars = get_all_cars()

    active = [d for d in all_drivers if d.status == 'active']
    total_kauce_zbyvajici = sum(
        max(0, (d.kauce_celkem or 0) - (d.kauce_zaplaceno or 0))
        for d in all_drivers
    )

    # ── KPI ───────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    c1.markdown(_kpi_card("Aktivní řidiči", str(len(active)), f"Celkem: {len(all_drivers)}", "#10b981", "👤"), unsafe_allow_html=True)
    c2.markdown(_kpi_card("Celkem řidičů", str(len(all_drivers)), "", "#f5c518", "👥"), unsafe_allow_html=True)
    c3.markdown(_kpi_card("Nezaplacené kauce", f"{total_kauce_zbyvajici:,.0f} Kč", "Zbývá vybrat", "#f59e0b", "💰"), unsafe_allow_html=True)

    st.markdown("<div style='height:1.2rem;'></div>", unsafe_allow_html=True)

    # ── Záhlaví tabulky ───────────────────────────────────────────────
    header_cols = st.columns([3, 1.5, 3, 3, 2])
    for col, text in zip(header_cols, ["Řidič", "Status", "Kauce", "Pokuty", "Auto"]):
        col.markdown(f"<span style='font-size:0.78rem; color:rgba(255,255,255,0.4); text-transform:uppercase; letter-spacing:0.07em;'>{text}</span>", unsafe_allow_html=True)
    st.markdown("<hr style='margin:0.3rem 0; border-color:rgba(255,255,255,0.08);'>", unsafe_allow_html=True)

    for driver in all_drivers:
        stats = get_driver_stats(driver.id) or {}
        fines = get_driver_fines_summary(driver.id)

        kauce_celkem = stats.get('kauce_celkem', 0)
        kauce_zaplaceno = stats.get('kauce_zaplaceno', 0)
        kauce_procento = stats.get('kauce_procento', 0)
        kauce_zbyvajici = stats.get('kauce_zbyvajici', 0)

        status_color = {
            'active': '#10b981', 'inactive': '#f59e0b',
            'archived': '#6b7280', 'nabor': '#f5c518',
        }.get(driver.status, '#6b7280')

        kauce_bar_color = '#10b981' if kauce_procento >= 100 else '#f59e0b'
        default_car = next((c for c in all_cars if c.id == driver.default_car_id), None)

        col1, col2, col3, col4, col5 = st.columns([3, 1.5, 3, 3, 2])

        with col1:
            initials = ''.join(n[0].upper() for n in driver.jmeno.split() if n)
            st.markdown(
                f"<div style='display:flex; align-items:center; gap:0.6rem;'>"
                f"<div style='width:30px; height:30px; border-radius:50%; "
                f"background:linear-gradient(135deg,#f5c518,#d4a017); "
                f"display:flex; align-items:center; justify-content:center; "
                f"font-weight:700; font-size:0.78rem; color:#0a0a0a; flex-shrink:0;'>{initials}</div>"
                f"<strong style='font-size:0.9rem;'>{driver.jmeno}</strong>"
                f"</div>",
                unsafe_allow_html=True
            )

        with col2:
            st.markdown(
                f"<span style='color:{status_color}; font-size:0.82rem;'>{driver.status}</span>",
                unsafe_allow_html=True
            )

        with col3:
            st.markdown(
                f"<div style='font-size:0.82rem;'>{kauce_zaplaceno:,.0f} / {kauce_celkem:,.0f} Kč</div>"
                f"<div style='background:rgba(255,255,255,0.08); border-radius:4px; height:5px; margin:4px 0;'>"
                f"<div style='width:{min(kauce_procento,100):.0f}%; height:100%; "
                f"background:{kauce_bar_color}; border-radius:4px;'></div></div>"
                f"<div style='font-size:0.72rem; color:rgba(255,255,255,0.35);'>zbývá {kauce_zbyvajici:,.0f} Kč</div>",
                unsafe_allow_html=True
            )

        with col4:
            if fines['pocet'] > 0:
                zb = fines['zbyvajici']
                fc = '#ef4444' if zb > 0 else '#10b981'
                st.markdown(
                    f"<span style='font-size:0.82rem;'>{fines['pocet']}× &nbsp;"
                    f"<span style='color:{fc};'>zbývá {zb:,.0f} Kč</span></span>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown("<span style='color:rgba(255,255,255,0.25); font-size:0.82rem;'>—</span>", unsafe_allow_html=True)

        with col5:
            if default_car:
                st.markdown(f"<span style='font-size:0.88rem;'>🚗 {default_car.spz}</span>", unsafe_allow_html=True)
            else:
                st.markdown("<span style='color:rgba(255,255,255,0.25);'>—</span>", unsafe_allow_html=True)

        st.markdown("<hr style='margin:0.2rem 0; border-color:rgba(255,255,255,0.05);'>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# TAB 4: EXPIRACE & NÁBOR
# ══════════════════════════════════════════════════════════════════

def _render_expirace_nabor():
    today = date.today()
    all_drivers = get_all_drivers()
    all_cars = get_all_cars()

    # ── Expirace ──────────────────────────────────────────────────────
    st.markdown(
        "<div style='font-size:0.88rem; font-weight:600; color:rgba(255,255,255,0.5); "
        "text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.8rem;'>STK & Pojistka</div>",
        unsafe_allow_html=True
    )

    def _urgency(d):
        if not d:
            return 9999, "—", "rgba(255,255,255,0.25)"
        days = (d - today).days
        if days < 0:
            return days, f"⛔ {d.strftime('%d.%m.%Y')} (prošlé!)", "#ef4444"
        elif days <= 30:
            return days, f"🔴 {d.strftime('%d.%m.%Y')} (za {days} dní)", "#ef4444"
        elif days <= 90:
            return days, f"🟡 {d.strftime('%d.%m.%Y')} (za {days} dní)", "#f59e0b"
        else:
            return days, f"🟢 {d.strftime('%d.%m.%Y')} (za {days} dní)", "#10b981"

    exp_rows = []
    for car in all_cars:
        if car.status == 'retired':
            continue
        stk_days, stk_str, stk_color = _urgency(car.stk_datum)
        poj_days, poj_str, poj_color = _urgency(car.pojistka_datum)
        urgency = min(stk_days, poj_days)
        status_emoji = {'active': '✅', 'service': '🔧'}.get(car.status, '❓')
        exp_rows.append((urgency, car.spz, car.model, car.rok, status_emoji, stk_str, stk_color, poj_str, poj_color))

    if exp_rows:
        exp_rows.sort(key=lambda x: x[0])

        # Záhlaví
        h1, h2, h3, h4 = st.columns([2, 2, 3, 3])
        for col, txt in zip([h1, h2, h3, h4], ["Auto", "Model", "STK", "Pojistka"]):
            col.markdown(f"<span style='font-size:0.75rem; color:rgba(255,255,255,0.4); text-transform:uppercase; letter-spacing:0.07em;'>{txt}</span>", unsafe_allow_html=True)
        st.markdown("<hr style='margin:0.3rem 0; border-color:rgba(255,255,255,0.08);'>", unsafe_allow_html=True)

        for _, spz, model, rok, status_emoji, stk_str, stk_color, poj_str, poj_color in exp_rows:
            c1, c2, c3, c4 = st.columns([2, 2, 3, 3])
            c1.markdown(f"<strong>{status_emoji} {spz}</strong>", unsafe_allow_html=True)
            c2.markdown(f"<span style='color:rgba(255,255,255,0.6); font-size:0.88rem;'>{model} ({rok})</span>", unsafe_allow_html=True)
            c3.markdown(f"<span style='color:{stk_color}; font-size:0.88rem;'>{stk_str}</span>", unsafe_allow_html=True)
            c4.markdown(f"<span style='color:{poj_color}; font-size:0.88rem;'>{poj_str}</span>", unsafe_allow_html=True)
            st.markdown("<hr style='margin:0.2rem 0; border-color:rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
    else:
        st.info("Žádná aktivní auta.")

    st.markdown("<div style='height:1.5rem;'></div>", unsafe_allow_html=True)

    # ── Nábor pipeline ────────────────────────────────────────────────
    st.markdown(
        "<div style='font-size:0.88rem; font-weight:600; color:rgba(255,255,255,0.5); "
        "text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.8rem;'>Nábor — pipeline</div>",
        unsafe_allow_html=True
    )

    nabor_drivers = [d for d in all_drivers if d.status == 'nabor']

    if not nabor_drivers:
        st.info("Žádní řidiči ve stavu Nábor.")
        return

    for driver in nabor_drivers:
        kauce_zapl = driver.kauce_zaplaceno or 0
        kauce_cel = driver.kauce_celkem or 10000
        kauce_ok = kauce_zapl >= kauce_cel
        kauce_label = f"Kauce {kauce_zapl:,.0f}/{kauce_cel:,.0f} Kč".replace(",", " ")
        auto_ok = driver.default_car_id is not None

        checks = [
            ("Kopie OP", bool(driver.nabor_op)),
            ("Kopie ŘP", bool(driver.nabor_ridicak)),
            ("Taxi licence", bool(driver.nabor_taxi)),
            (kauce_label, kauce_ok),
            ("Auto přiřazeno", auto_ok),
        ]
        done_count = sum(1 for _, ok in checks if ok)
        all_done = done_count == len(checks)
        progress_color = '#10b981' if all_done else ('#f5c518' if done_count >= 3 else '#ef4444')

        checks_html = " &nbsp; ".join(
            f"<span style='color:{'#10b981' if ok else 'rgba(255,255,255,0.3)'};'>"
            f"{'✓' if ok else '○'} {label}</span>"
            for label, ok in checks
        )

        st.markdown(
            f"<div style='background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.07); "
            f"border-left:3px solid {progress_color}; border-radius:10px; "
            f"padding:0.8rem 1rem; margin-bottom:0.5rem;'>"
            f"<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;'>"
            f"<strong style='color:white;'>{driver.jmeno}</strong>"
            f"<span style='color:{progress_color}; font-size:0.82rem;'>{done_count}/{len(checks)}</span>"
            f"</div>"
            f"<div style='font-size:0.82rem;'>{checks_html}</div>"
            + (f"<div style='color:#10b981; font-size:0.78rem; margin-top:0.4rem;'>Připraven k aktivaci</div>" if all_done else "")
            + "</div>",
            unsafe_allow_html=True
        )
