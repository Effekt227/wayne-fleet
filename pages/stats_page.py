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


def render_stats_page():
    st.markdown("## 📈 Statistiky flotily")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Finanční přehled",
        "🚗 Flotila",
        "👥 Řidiči",
        "💡 Výnosnost & Obsazenost",
        "📋 Nábor & Expirace",
    ])

    with tab1:
        _render_financial_overview()

    with tab2:
        _render_fleet_overview()

    with tab3:
        _render_driver_overview()

    with tab4:
        _render_profitability()

    with tab5:
        _render_nabor_expirace()


# ══════════════════════════════════════════════════════════════════
# TAB 1: FINANČNÍ PŘEHLED
# ══════════════════════════════════════════════════════════════════

def _month_label(m: dict) -> str:
    """Krátký popisek měsíce: 'Bře 26'"""
    zkratky = ['Led', 'Úno', 'Bře', 'Dub', 'Kvě', 'Čer', 'Čvc', 'Srp', 'Zář', 'Říj', 'Lis', 'Pro']
    return f"{zkratky[m['mesic']-1]} {m['rok'] % 100:02d}"


def _render_financial_overview():
    today = date.today()

    # ── Filtr období ──────────────────────────────────────────────────
    mode = st.radio(
        "Zobrazit období:",
        options=["Přehled (13 měs.)", "Konkrétní měsíc", "Konkrétní rok", "Vlastní období"],
        horizontal=True,
        key="stats_filter_mode",
    )

    if mode == "Přehled (13 měs.)":
        monthly_data = get_monthly_chart_data(3, 9)
        popis_obdobi = f"{_month_label(monthly_data[0])} – {_month_label(monthly_data[-1])} (3 měs. zpět + 9 dopředu)"

    elif mode == "Konkrétní měsíc":
        col_m, col_y, _ = st.columns([1, 1, 2])
        sel_m = col_m.selectbox(
            "Měsíc", range(1, 13), index=today.month - 1,
            format_func=lambda x: MESICE_CZ[x - 1], key="stats_sel_m",
        )
        sel_y = col_y.number_input(
            "Rok", min_value=2020, max_value=2035, value=today.year, key="stats_sel_y",
        )
        s = get_monthly_summary(int(sel_y), sel_m)
        s['rok'] = int(sel_y)
        s['mesic'] = sel_m
        s['label'] = f"{int(sel_y)}-{sel_m:02d}"
        monthly_data = [s]
        popis_obdobi = f"{MESICE_CZ[sel_m - 1]} {int(sel_y)}"

    elif mode == "Konkrétní rok":
        col_y, _ = st.columns([1, 3])
        sel_y = col_y.number_input(
            "Rok", min_value=2020, max_value=2035, value=today.year, key="stats_rok_y",
        )
        monthly_data = get_monthly_chart_data_range(int(sel_y), 1, int(sel_y), 12)
        popis_obdobi = f"Celý rok {int(sel_y)}"

    else:  # Vlastní období
        col1, col2, col3, col4 = st.columns(4)
        od_m = col1.selectbox(
            "Od měsíce", range(1, 13),
            format_func=lambda x: MESICE_CZ[x - 1], key="stats_od_m",
        )
        od_y = col2.number_input(
            "Od roku", min_value=2020, max_value=2035, value=today.year, key="stats_od_y",
        )
        do_m = col3.selectbox(
            "Do měsíce", range(1, 13), index=today.month - 1,
            format_func=lambda x: MESICE_CZ[x - 1], key="stats_do_m",
        )
        do_y = col4.number_input(
            "Do roku", min_value=2020, max_value=2035, value=today.year, key="stats_do_y",
        )
        od_y, do_y = int(od_y), int(do_y)
        if (od_y, od_m) > (do_y, do_m):
            st.warning("Počáteční datum musí být před koncovým.")
            return
        monthly_data = get_monthly_chart_data_range(od_y, od_m, do_y, do_m)
        popis_obdobi = f"{MESICE_CZ[od_m - 1]} {od_y} – {MESICE_CZ[do_m - 1]} {do_y}"

    if not monthly_data:
        st.info("Žádná data pro vybrané období.")
        return

    st.markdown(
        f"<div style='color:rgba(255,255,255,0.5); font-size:0.85rem; margin-bottom:0.5rem;'>"
        f"Zobrazené období: <strong style='color:rgba(255,255,255,0.8);'>{popis_obdobi}</strong>"
        f"</div>",
        unsafe_allow_html=True
    )

    # ── Metriky ───────────────────────────────────────────────────────
    this_month = next(
        (m for m in monthly_data if m['rok'] == today.year and m['mesic'] == today.month), {}
    )
    total_vydano = sum(m['vydano_celkem'] for m in monthly_data)
    total_prijato = sum(m['prijato_celkem'] for m in monthly_data)
    total_bilance = sum(m['bilance'] for m in monthly_data)
    total_nezaplaceno_vydane = sum(m['vydano_nezaplaceno'] for m in monthly_data)
    total_nezaplaceno_prijate = sum(m['prijato_nezaplaceno'] for m in monthly_data)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "📤 Příjmy celkem",
        f"{total_vydano:,.0f} Kč",
        delta=f"{this_month.get('vydano_celkem', 0):,.0f} Kč tento měsíc" if this_month else None,
    )
    col2.metric(
        "📥 Výdaje celkem",
        f"{total_prijato:,.0f} Kč",
        delta=f"-{this_month.get('prijato_celkem', 0):,.0f} Kč tento měsíc" if this_month else None,
        delta_color='inverse',
    )
    col3.metric(
        "💰 Bilance (inkasováno)",
        f"{total_bilance:,.0f} Kč",
        delta=f"{this_month.get('bilance', 0):,.0f} Kč tento měsíc" if this_month else None,
    )
    col4.metric(
        "⏳ Pohledávky / Závazky",
        f"{total_nezaplaceno_vydane:,.0f} / {total_nezaplaceno_prijate:,.0f} Kč",
        help="Nezaplaceno: vydané (čekám na příjem) / přijaté (mám uhradit)",
    )

    has_data = any(m['vydano_celkem'] > 0 or m['prijato_celkem'] > 0 for m in monthly_data)
    sortable_labels = [m['label'] for m in monthly_data]

    # ── Grafy ─────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Příjmy vs Výdaje")

    if has_data:
        chart_df = pd.DataFrame(
            {
                'Příjmy': [m['vydano_celkem'] for m in monthly_data],
                'Výdaje': [m['prijato_celkem'] for m in monthly_data],
            },
            index=sortable_labels,
        )
        st.bar_chart(chart_df, color=['#10b981', '#ef4444'])
    else:
        st.info("Zatím nejsou data pro toto období.")

    if len(monthly_data) > 1:
        st.markdown("#### Zisk / bilance")
        if has_data:
            profit_df = pd.DataFrame(
                {'Zisk': [m['bilance'] for m in monthly_data]},
                index=sortable_labels,
            )
            st.line_chart(profit_df, color=['#f5c518'])

    # ── Tabulka ───────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### Měsíční přehled")
    rows = []
    for m in monthly_data:
        je_aktualni = m['rok'] == today.year and m['mesic'] == today.month
        je_budouci = (m['rok'], m['mesic']) > (today.year, today.month)
        znacka = " 📍" if je_aktualni else (" 🔮" if je_budouci else "")
        rows.append({
            'Měsíc': f"{MESICE_CZ[m['mesic']-1]} {m['rok']}{znacka}",
            'Příjmy': f"{m['vydano_celkem']:,.0f} Kč",
            'Zaplaceno (příjmy)': f"{m['vydano_zaplaceno']:,.0f} Kč",
            'Výdaje': f"{m['prijato_celkem']:,.0f} Kč",
            'Zaplaceno (výdaje)': f"{m['prijato_zaplaceno']:,.0f} Kč",
            'Bilance': f"{m['bilance']:,.0f} Kč",
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.markdown(
        "<div style='font-size:0.8rem; color:rgba(255,255,255,0.4); margin-top:0.3rem;'>"
        "📍 = aktuální měsíc &nbsp;|&nbsp; 🔮 = budoucí (naplánované platby)"
        "</div>",
        unsafe_allow_html=True
    )


# ══════════════════════════════════════════════════════════════════
# TAB 2: FLOTILA
# ══════════════════════════════════════════════════════════════════

def _render_fleet_overview():
    all_cars = get_all_cars()
    if not all_cars:
        st.info("Žádná auta v databázi.")
        return

    total_weekly = 0
    total_service = 0
    rows = []

    for car in all_cars:
        stats = get_car_stats(car.id) or {}
        service_cost = get_total_service_cost(car.id)
        weekly = car.splatka_tyden or 0
        total_weekly += weekly
        total_service += service_cost

        if car.typ_vlastnictvi == 'vlastni':
            splaceno_str = f"{car.zaplaceno_splatek}/{car.celkem_splatek} splátek"
            procento = stats.get('procento_splaceno', 0)
            zbyvajici = stats.get('zbyvajici_splatka', 0)
        else:
            splaceno_str = "Pronájem"
            procento = 100
            zbyvajici = 0

        km = car.celkem_km or 0
        kc_per_km = f"{service_cost / km:.2f} Kč/km" if km > 0 else "—"

        status_emoji = {'active': '✅', 'service': '🔧', 'retired': '🗄️'}.get(car.status, '❓')

        rows.append({
            'Auto': f"{status_emoji} {car.spz}",
            'Model': f"{car.model} ({car.rok})",
            'Typ': '🔑 Vlastní' if car.typ_vlastnictvi == 'vlastni' else '📋 Pronájem',
            'Náklady/týden': f"{weekly:,.0f} Kč",
            'Splaceno': splaceno_str,
            '% splaceno': f"{procento:.1f}%",
            'Zbývá': f"{zbyvajici:,.0f} Kč" if zbyvajici > 0 else '—',
            'Km celkem': f"{km:,}",
            'Servisy': f"{service_cost:,.0f} Kč",
            'Kč/km': kc_per_km,
        })

    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    col1.metric("🚗 Počet aut", len(all_cars))
    col2.metric("💸 Týdenní náklady flotily", f"{total_weekly:,.0f} Kč")
    col3.metric("🔧 Celkové náklady na servisy", f"{total_service:,.0f} Kč")

    st.markdown(
        f"<div style='color:rgba(255,255,255,0.5); font-size:0.85rem; margin-top:0.5rem;'>"
        f"Odhadované měsíční náklady (×4 týdny): "
        f"<strong style='color:white;'>{total_weekly * 4:,.0f} Kč</strong> &nbsp;|&nbsp; "
        f"Ročně (×52): <strong style='color:white;'>{total_weekly * 52:,.0f} Kč</strong>"
        f"</div>",
        unsafe_allow_html=True
    )

    # Progress bary pro vlastní auta
    owned_cars = [c for c in all_cars if c.typ_vlastnictvi == 'vlastni']
    if owned_cars:
        st.markdown("---")
        st.markdown("#### 📊 Průběh splácení vlastních aut")
        for car in owned_cars:
            stats = get_car_stats(car.id) or {}
            procento = stats.get('procento_splaceno', 0)
            zaplaceno = stats.get('zaplaceno', 0)
            celkova_cena = stats.get('celkova_cena', 0)
            bar_color = '#10b981' if procento >= 100 else '#f5c518'

            col_name, col_bar, col_pct = st.columns([2, 5, 1])
            with col_name:
                st.markdown(f"**{car.spz}** – {car.model}")
            with col_bar:
                st.markdown(
                    f"<div style='background:rgba(255,255,255,0.1); border-radius:8px; height:16px; margin-top:0.4rem;'>"
                    f"<div style='width:{min(procento,100):.1f}%; height:100%; "
                    f"background:{bar_color}; border-radius:8px;'></div></div>"
                    f"<div style='font-size:0.78rem; color:rgba(255,255,255,0.5); margin-top:2px;'>"
                    f"{zaplaceno:,.0f} / {celkova_cena:,.0f} Kč</div>",
                    unsafe_allow_html=True
                )
            with col_pct:
                st.markdown(
                    f"<div style='text-align:right; margin-top:0.3rem; font-weight:700; color:{bar_color};'>"
                    f"{procento:.0f}%</div>",
                    unsafe_allow_html=True
                )


# ══════════════════════════════════════════════════════════════════
# TAB 3: ŘIDIČI
# ══════════════════════════════════════════════════════════════════

def _render_driver_overview():
    all_drivers = get_all_drivers()
    if not all_drivers:
        st.info("Žádní řidiči v databázi.")
        return

    all_cars = get_all_cars()

    # Souhrnné metriky
    active = [d for d in all_drivers if d.status == 'active']
    col1, col2, col3 = st.columns(3)
    col1.metric("👥 Aktivní řidiči", len(active))
    col2.metric("📋 Celkem řidičů", len(all_drivers))

    total_kauce_zbyvajici = sum(
        max(0, (d.kauce_celkem or 0) - (d.kauce_zaplaceno or 0))
        for d in all_drivers
    )
    col3.metric("💰 Nezaplacené kauce celkem", f"{total_kauce_zbyvajici:,.0f} Kč")

    st.markdown("---")
    st.markdown("#### Přehled řidičů")

    # Záhlaví
    header_cols = st.columns([3, 1.5, 3, 3, 2])
    header_cols[0].markdown("**Řidič**")
    header_cols[1].markdown("**Status**")
    header_cols[2].markdown("**Kauce**")
    header_cols[3].markdown("**Pokuty**")
    header_cols[4].markdown("**Auto**")
    st.markdown("<hr style='margin:0.3rem 0; opacity:0.2;'>", unsafe_allow_html=True)

    for driver in all_drivers:
        stats = get_driver_stats(driver.id) or {}
        fines = get_driver_fines_summary(driver.id)

        kauce_celkem = stats.get('kauce_celkem', 0)
        kauce_zaplaceno = stats.get('kauce_zaplaceno', 0)
        kauce_procento = stats.get('kauce_procento', 0)
        kauce_zbyvajici = stats.get('kauce_zbyvajici', 0)

        status_color = {
            'active': '#10b981',
            'inactive': '#f59e0b',
            'archived': '#6b7280',
            'nabor': '#f5c518',
        }.get(driver.status, '#6b7280')

        kauce_bar_color = '#10b981' if kauce_procento >= 100 else '#f59e0b'
        default_car = next((c for c in all_cars if c.id == driver.default_car_id), None)

        col1, col2, col3, col4, col5 = st.columns([3, 1.5, 3, 3, 2])

        with col1:
            initials = ''.join(n[0].upper() for n in driver.jmeno.split() if n)
            st.markdown(
                f"<div style='display:flex; align-items:center; gap:0.6rem;'>"
                f"<div style='width:32px; height:32px; border-radius:50%; "
                f"background:linear-gradient(135deg,#f5c518,#d4a017); "
                f"display:flex; align-items:center; justify-content:center; "
                f"font-weight:700; font-size:0.82rem; color:#0a0a0a; flex-shrink:0;'>{initials}</div>"
                f"<strong>{driver.jmeno}</strong>"
                f"</div>",
                unsafe_allow_html=True
            )

        with col2:
            st.markdown(
                f"<span style='color:{status_color}; font-size:0.85rem;'>{driver.status}</span>",
                unsafe_allow_html=True
            )

        with col3:
            st.markdown(
                f"<div style='font-size:0.82rem;'>{kauce_zaplaceno:,.0f} / {kauce_celkem:,.0f} Kč</div>"
                f"<div style='background:rgba(255,255,255,0.1); border-radius:4px; height:6px; margin-top:3px;'>"
                f"<div style='width:{min(kauce_procento,100):.0f}%; height:100%; "
                f"background:{kauce_bar_color}; border-radius:4px;'></div></div>"
                f"<div style='font-size:0.75rem; color:rgba(255,255,255,0.4);'>"
                f"zbývá {kauce_zbyvajici:,.0f} Kč</div>",
                unsafe_allow_html=True
            )

        with col4:
            if fines['pocet'] > 0:
                zb = fines['zbyvajici']
                fc = '#ef4444' if zb > 0 else '#10b981'
                st.markdown(
                    f"<span style='font-size:0.85rem;'>{fines['pocet']} pokut &nbsp;|&nbsp; "
                    f"<span style='color:{fc};'>zbývá {zb:,.0f} Kč</span></span>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    "<span style='color:rgba(255,255,255,0.3); font-size:0.85rem;'>—</span>",
                    unsafe_allow_html=True
                )

        with col5:
            if default_car:
                st.markdown(f"🚗 {default_car.spz}")
            else:
                st.markdown(
                    "<span style='color:rgba(255,255,255,0.3);'>—</span>",
                    unsafe_allow_html=True
                )

        st.markdown("<hr style='margin:0.25rem 0; opacity:0.08;'>", unsafe_allow_html=True)

    # Kauce progress bary
    st.markdown("---")
    st.markdown("#### 💰 Průběh kauce řidičů")
    for driver in all_drivers:
        stats = get_driver_stats(driver.id) or {}
        kauce_celkem = stats.get('kauce_celkem', 0)
        kauce_zaplaceno = stats.get('kauce_zaplaceno', 0)
        kauce_procento = stats.get('kauce_procento', 0) if kauce_celkem > 0 else 0
        bar_color = '#10b981' if kauce_procento >= 100 else '#f59e0b'

        col_name, col_bar, col_pct = st.columns([2, 5, 1])
        with col_name:
            st.markdown(f"**{driver.jmeno}**")
        with col_bar:
            st.markdown(
                f"<div style='background:rgba(255,255,255,0.1); border-radius:8px; height:14px; margin-top:0.4rem;'>"
                f"<div style='width:{min(kauce_procento,100):.1f}%; height:100%; "
                f"background:{bar_color}; border-radius:8px;'></div></div>"
                f"<div style='font-size:0.75rem; color:rgba(255,255,255,0.4); margin-top:2px;'>"
                f"{kauce_zaplaceno:,.0f} / {kauce_celkem:,.0f} Kč</div>",
                unsafe_allow_html=True
            )
        with col_pct:
            st.markdown(
                f"<div style='text-align:right; margin-top:0.3rem; font-weight:700; color:{bar_color};'>"
                f"{kauce_procento:.0f}%</div>",
                unsafe_allow_html=True
            )


# ══════════════════════════════════════════════════════════════════
# TAB 4: VÝNOSNOST & OBSAZENOST
# ══════════════════════════════════════════════════════════════════

def _render_profitability():
    today = date.today()
    all_cars = get_all_cars()
    if not all_cars:
        st.info("Žádná auta v databázi.")
        return

    days_in_month = cal_mod.monthrange(today.year, today.month)[1]
    occupancy = get_fleet_occupancy_month(today.year, today.month)

    # ── Prognóza příjmů ───────────────────────────────────────────────
    st.markdown("#### 📈 Prognóza měsíčních příjmů")

    active_cars = [c for c in all_cars if c.status == 'active']
    ocekavane = sum((c.cena_tyden_pronajem or 0) * 4.33 for c in active_cars)
    naklady_flotily = sum((c.splatka_tyden or 0) * 4.33 for c in all_cars)
    ocekavany_zisk = ocekavane - naklady_flotily

    c1, c2, c3 = st.columns(3)
    c1.metric(
        "💵 Očekávané příjmy (měsíc)",
        f"{ocekavane:,.0f} Kč",
        help="Součet cena_tyden_pronajem × 4,33 pro všechna aktivní auta"
    )
    c2.metric(
        "💸 Náklady flotily (měsíc)",
        f"{naklady_flotily:,.0f} Kč",
        help="Splátky/nájmy aut × 4,33"
    )
    profit_color = "normal" if ocekavany_zisk >= 0 else "inverse"
    c3.metric(
        "💰 Očekávaný zisk",
        f"{ocekavany_zisk:,.0f} Kč",
        delta_color=profit_color
    )

    st.markdown("---")

    # ── Výnosnost a obsazenost každého auta ──────────────────────────
    st.markdown("#### 🚗 Výnosnost každého auta (odhadovaná za měsíc)")

    rows = []
    alerts = []

    for car in all_cars:
        service_cost = get_total_service_cost(car.id)
        prijmy_mesic = (car.cena_tyden_pronajem or 0) * 4.33
        naklady_splatka = (car.splatka_tyden or 0) * 4.33
        # Průměrné měsíční náklady na servis (celkové / počet měsíců od pořízení, min 1)
        naklady_servis = service_cost / 12  # průměr za rok (konzervativní odhad)
        naklady_celkem = naklady_splatka + naklady_servis
        zisk = prijmy_mesic - naklady_celkem

        # Obsazenost v aktuálním měsíci
        obsazeno_dni = occupancy.get(car.id, 0)
        obsazenost_pct = obsazeno_dni / days_in_month * 100 if days_in_month > 0 else 0

        # Detekce volných aut (méně než 3 dny obsazení v posledních 7 dnech)
        if car.status == 'active' and obsazeno_dni == 0:
            alerts.append(f"🔴 **{car.spz}** nemá žádného řidiče tento měsíc ({today.strftime('%B')})")

        status_emoji = {'active': '✅', 'service': '🔧', 'retired': '🗄️'}.get(car.status, '❓')
        zisk_str = f"+{zisk:,.0f} Kč" if zisk >= 0 else f"{zisk:,.0f} Kč"

        rows.append({
            'Auto': f"{status_emoji} {car.spz}",
            'Model': car.model,
            'Příjmy/měs (est.)': f"{prijmy_mesic:,.0f} Kč",
            'Splátka/měs': f"{naklady_splatka:,.0f} Kč",
            'Servis/měs (avg)': f"{naklady_servis:,.0f} Kč",
            'Náklady celkem': f"{naklady_celkem:,.0f} Kč",
            'Zisk/měs (est.)': zisk_str,
            f'Obsazenost ({today.month}/{today.year})': f"{obsazeno_dni} dní ({obsazenost_pct:.0f}%)",
        })

    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    st.markdown(
        "<div style='font-size:0.78rem; color:rgba(255,255,255,0.4); margin-top:0.3rem;'>"
        "Příjmy = cena pronájmu řidiči × 4,33 týdne &nbsp;|&nbsp; "
        "Servis/měs = celkové náklady na servis ÷ 12 (roční průměr)"
        "</div>",
        unsafe_allow_html=True
    )

    # ── Upozornění na volná auta ──────────────────────────────────────
    if alerts:
        st.markdown("---")
        st.markdown("#### ⚠️ Volná auta")
        for a in alerts:
            st.warning(a)
    else:
        st.markdown(
            "<div style='color:#10b981; font-size:0.85rem; margin-top:0.5rem;'>"
            "✅ Všechna aktivní auta mají přiřazeného řidiče tento měsíc.</div>",
            unsafe_allow_html=True
        )

    # ── Obsazenost — sloupcový graf ───────────────────────────────────
    st.markdown("---")
    st.markdown(f"#### 📅 Obsazenost flotily — {MESICE_CZ[today.month-1]} {today.year}")

    chart_data = {car.spz: occupancy.get(car.id, 0) for car in all_cars if car.status != 'retired'}
    if chart_data:
        occ_df = pd.DataFrame(
            {'Obsazené dny': list(chart_data.values())},
            index=list(chart_data.keys())
        )
        st.bar_chart(occ_df, color=['#10b981'])
        st.markdown(
            f"<div style='font-size:0.78rem; color:rgba(255,255,255,0.4);'>"
            f"Celkem dní v měsíci: {days_in_month}</div>",
            unsafe_allow_html=True
        )


# ══════════════════════════════════════════════════════════════════
# TAB 5: NÁBOR & EXPIRACE
# ══════════════════════════════════════════════════════════════════

def _render_nabor_expirace():
    today = date.today()
    all_drivers = get_all_drivers()
    all_cars = get_all_cars()

    # ── Nábor pipeline ────────────────────────────────────────────────
    st.markdown("#### 👤 Nábor — pipeline")

    nabor_drivers = [d for d in all_drivers if d.status == 'nabor']

    if not nabor_drivers:
        st.info("Žádní řidiči ve stavu Nábor.")
    else:
        for driver in nabor_drivers:
            # Checklist kritérií
            kauce_zapl = driver.kauce_zaplaceno or 0
            kauce_cel = driver.kauce_celkem or 10000
            kauce_ok = kauce_zapl >= kauce_cel
            kauce_label = f"Kauce {kauce_zapl:,.0f}/{kauce_cel:,.0f} Kč".replace(",", " ")
            auto_ok = driver.default_car_id is not None
            op_ok = bool(driver.nabor_op)
            ridicak_ok = bool(driver.nabor_ridicak)
            taxi_ok = bool(driver.nabor_taxi)

            checks = [
                ("Kopie OP", op_ok),
                ("Kopie ŘP", ridicak_ok),
                ("Taxi licence", taxi_ok),
                (kauce_label, kauce_ok),
                ("Auto přiřazeno", auto_ok),
            ]

            done_count = sum(1 for _, ok in checks if ok)
            all_done = done_count == len(checks)
            progress_color = '#10b981' if all_done else ('#f5c518' if done_count >= 3 else '#ef4444')

            checks_html = " &nbsp;".join(
                f"<span style='color:{'#10b981' if ok else '#ef4444'};'>{'✅' if ok else '❌'} {label}</span>"
                for label, ok in checks
            )

            st.markdown(
                f"<div style='background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.1); "
                f"border-left:3px solid {progress_color}; border-radius:10px; "
                f"padding:0.8rem 1rem; margin-bottom:0.5rem;'>"
                f"<div style='display:flex; justify-content:space-between; align-items:center;'>"
                f"<strong style='color:white;'>{driver.jmeno}</strong>"
                f"<span style='color:{progress_color}; font-weight:700;'>{done_count}/{len(checks)} hotovo</span>"
                f"</div>"
                f"<div style='font-size:0.82rem; margin-top:0.5rem;'>{checks_html}</div>"
                + (f"<div style='color:#10b981; font-size:0.8rem; margin-top:0.4rem;'>🎉 Připraven k aktivaci!</div>" if all_done else "")
                + "</div>",
                unsafe_allow_html=True
            )

    st.markdown("---")

    # ── Přehled expirací ──────────────────────────────────────────────
    st.markdown("#### 📅 Přehled expirací (STK, pojistka)")

    exp_rows = []
    for car in all_cars:
        if car.status == 'retired':
            continue

        def _exp_cell(d):
            if not d:
                return "—", 9999
            days = (d - today).days
            if days < 0:
                return f"⛔ {d.strftime('%d.%m.%Y')} (prošlé!)", days
            elif days <= 30:
                return f"🔴 {d.strftime('%d.%m.%Y')} (za {days} dní)", days
            elif days <= 90:
                return f"🟡 {d.strftime('%d.%m.%Y')} (za {days} dní)", days
            else:
                return f"🟢 {d.strftime('%d.%m.%Y')} (za {days} dní)", days

        stk_str, stk_days = _exp_cell(car.stk_datum)
        poj_str, poj_days = _exp_cell(car.pojistka_datum)
        urgency = min(stk_days, poj_days)

        status_emoji = {'active': '✅', 'service': '🔧'}.get(car.status, '❓')
        exp_rows.append((urgency, {
            'Auto': f"{status_emoji} {car.spz}",
            'Model': f"{car.model} ({car.rok})",
            'STK': stk_str,
            'Pojistka': poj_str,
        }))

    if exp_rows:
        # Seřadit od nejnaléhavějších
        exp_rows.sort(key=lambda x: x[0])
        df_exp = pd.DataFrame([r for _, r in exp_rows])
        st.dataframe(df_exp, width="stretch", hide_index=True)
        st.markdown(
            "<div style='font-size:0.78rem; color:rgba(255,255,255,0.4); margin-top:0.3rem;'>"
            "Datumy expirací zadáš v detailu každého auta (Upravit auto)."
            "</div>",
            unsafe_allow_html=True
        )
    else:
        st.info("Žádná auta ke zobrazení.")
