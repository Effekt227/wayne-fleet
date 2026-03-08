"""
Driver Detail Page - Wayne Fleet Management System
Detailní karta řidiče: kontakty, výchozí auto, kauce, směny, editace
"""

import streamlit as st
from datetime import datetime, timedelta
from database.crud_drivers import get_driver_by_id, get_driver_stats, update_driver, set_default_car, add_kauce_payment
from database.crud_finance_records import create_record, get_records
from database.crud_cars import get_all_cars
from database.crud_calendar import get_week_assignments
from database.crud_fines import get_driver_fines, create_fine, add_fine_payment, delete_fine


def render_driver_detail(driver_id: int):
    if not driver_id:
        st.error("Řidič nenalezen.")
        return

    driver = get_driver_by_id(driver_id)
    if not driver:
        st.error("Řidič nenalezen.")
        return

    stats = get_driver_stats(driver_id)
    today = datetime.now().date()

    # ── Zpět ──────────────────────────────────────────────────────
    if st.button("◀ Zpět na řidiče"):
        st.session_state['page'] = 'ridici'
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Hlavička řidiče ───────────────────────────────────────────
    initials = ''.join(n[0].upper() for n in driver.jmeno.split() if n)
    status_map = {
        'active':   ('✅ Aktivní',  '#10b981'),
        'inactive': ('⏸️ Neaktivní', '#f59e0b'),
        'archived': ('🗄️ Archivován','#6b7280'),
        'nabor':    ('🔍 Nábor',    '#f5c518'),
    }
    status_label, status_color = status_map.get(driver.status, (driver.status, '#6b7280'))

    col_av, col_info, col_status = st.columns([1, 4, 2])
    with col_av:
        st.markdown(
            f"<div style='width:80px; height:80px; border-radius:50%; "
            f"background: linear-gradient(135deg,#f5c518,#d4a017); "
            f"display:flex; align-items:center; justify-content:center; "
            f"font-size:1.8rem; font-weight:900; color:#0a0a0a;'>{initials}</div>",
            unsafe_allow_html=True
        )
    with col_info:
        st.markdown(f"### {driver.jmeno}")
        st.markdown(
            f"📧 {driver.email or '—'} &nbsp;|&nbsp; "
            f"📱 {driver.telefon or '—'} &nbsp;|&nbsp; "
            f"📅 Od {driver.datum_nastupu.strftime('%d.%m.%Y') if driver.datum_nastupu else '—'}",
            unsafe_allow_html=True
        )
        st.markdown(
            f"🏠 {driver.adresa or '—'} &nbsp;|&nbsp; "
            f"RČ: {driver.rc or '—'} &nbsp;|&nbsp; "
            f"OP: {driver.cislo_op or '—'}",
            unsafe_allow_html=True
        )
    with col_status:
        st.markdown(
            f"<div style='background:{status_color}; color:white; padding:0.4rem 1rem; "
            f"border-radius:20px; text-align:center; font-weight:700; margin-top:1rem;'>"
            f"{status_label}</div>",
            unsafe_allow_html=True
        )
        # Tlačítko ukončení – jen pro aktivní řidiče
        if driver.status in ('active', 'nabor', 'inactive') and not driver.datum_ukonceni:
            st.markdown("<div style='margin-top:0.5rem;'>", unsafe_allow_html=True)
            if st.button("🚫 Ukončit řidiče", key=f"btn_ukoncit_{driver.id}", width='stretch'):
                st.session_state[f'confirm_ukoncit_{driver.id}'] = True
            st.markdown("</div>", unsafe_allow_html=True)

    # ── Potvrzení ukončení ────────────────────────────────────────
    if st.session_state.get(f'confirm_ukoncit_{driver.id}'):
        st.warning(f"⚠️ Opravdu chceš ukončit spolupráci s **{driver.jmeno}**? Od dnešního dne poběží 60 dní, po kterých se vrací kauce.")
        col_uk1, col_uk2, col_uk3 = st.columns([2, 1, 1])
        with col_uk1:
            datum_uk = st.date_input("Datum ukončení", value=today, key=f"datum_ukonceni_input_{driver.id}")
        with col_uk2:
            if st.button("✅ Potvrdit ukončení", key=f"potvrdit_ukoncit_{driver.id}", width='stretch'):
                update_driver(driver.id, status='inactive', datum_ukonceni=datum_uk)
                # Automaticky vytvořit záznam vrácení kauce do finančního kalendáře
                kauce_k_vraceni = stats['kauce_zaplaceno']
                if kauce_k_vraceni > 0:
                    datum_vraceni_kauce = datum_uk + timedelta(days=60)
                    create_record(
                        typ='prijata',
                        popis=f"Vrácení kauce – {driver.jmeno}",
                        castka_kc=kauce_k_vraceni,
                        datum=datum_uk,
                        datum_splatnosti=datum_vraceni_kauce,
                        kategorie='Jiné',
                        driver_id=driver.id,
                    )
                st.session_state[f'confirm_ukoncit_{driver.id}'] = False
                st.success("Řidič ukončen. Odpočet 60 dní pro vrácení kauce spuštěn.")
                st.rerun()
        with col_uk3:
            if st.button("❌ Zrušit", key=f"zrusit_ukoncit_{driver.id}", width='stretch'):
                st.session_state[f'confirm_ukoncit_{driver.id}'] = False
                st.rerun()

    # ── Banner odpočtu kauce (pokud je datum ukončení) ───────────
    if driver.datum_ukonceni:
        datum_vraceni = driver.datum_ukonceni + timedelta(days=60)
        zbyvajici_dni = (datum_vraceni - today).days

        # Zkontrolovat, jestli záznam vrácení kauce ve financích existuje
        existujici = get_records(driver_id=driver.id)
        ma_zaznam = any(
            'Vrácení kauce' in (r.popis or '') for r in existujici
        )

        if zbyvajici_dni > 0:
            col_b1, col_b2 = st.columns([3, 1])
            with col_b1:
                st.markdown(
                    f"<div style='background:rgba(245,197,24,0.12); border:1px solid #f5c518; "
                    f"border-radius:10px; padding:0.8rem 1.2rem; margin:0.5rem 0;'>"
                    f"🕐 <b>Spolupráce ukončena</b> {driver.datum_ukonceni.strftime('%d.%m.%Y')} &nbsp;|&nbsp; "
                    f"Kauce k vrácení: <b>{datum_vraceni.strftime('%d.%m.%Y')}</b> "
                    f"<span style='color:#f5c518; font-weight:700;'>(za {zbyvajici_dni} dní)</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
            with col_b2:
                if not ma_zaznam and stats['kauce_zaplaceno'] > 0:
                    if st.button("📋 Přidat do\nfinančního kalendáře", key=f"add_kauce_finance_{driver.id}", width='stretch'):
                        create_record(
                            typ='prijata',
                            popis=f"Vrácení kauce – {driver.jmeno}",
                            castka_kc=stats['kauce_zaplaceno'],
                            datum=driver.datum_ukonceni,
                            datum_splatnosti=datum_vraceni,
                            kategorie='Jiné',
                            driver_id=driver.id,
                        )
                        st.success("Záznam přidán do finančního kalendáře.")
                        st.rerun()
                elif ma_zaznam:
                    st.markdown(
                        "<div style='color:#10b981; font-size:0.85rem; margin-top:0.8rem;'>✅ V kalendáři</div>",
                        unsafe_allow_html=True
                    )
        else:
            st.markdown(
                f"<div style='background:rgba(16,185,129,0.12); border:1px solid #10b981; "
                f"border-radius:10px; padding:0.8rem 1.2rem; margin:0.5rem 0;'>"
                f"✅ <b>Kauce k vrácení</b> — lhůta 60 dní uplynula {datum_vraceni.strftime('%d.%m.%Y')}. "
                f"Nezapomeň vrátit kauci řidiči."
                f"</div>",
                unsafe_allow_html=True
            )

    st.markdown("---")

    # ── Levý / pravý sloupec ──────────────────────────────────────
    col_left, col_right = st.columns([1, 1])

    # ── Výchozí auto ──────────────────────────────────────────────
    with col_left:
        st.markdown("#### 🚗 Výchozí auto")
        all_cars = get_all_cars()
        car_options = {"— Žádné —": None}
        car_options.update({f"{c.spz} – {c.model}": c.id for c in all_cars})

        current_car_label = "— Žádné —"
        if driver.default_car_id:
            for label, cid in car_options.items():
                if cid == driver.default_car_id:
                    current_car_label = label
                    break

        selected_car_label = st.selectbox(
            "Výchozí auto",
            list(car_options.keys()),
            index=list(car_options.keys()).index(current_car_label),
            key=f"default_car_{driver.id}",
            label_visibility="collapsed"
        )

        if selected_car_label != current_car_label:
            set_default_car(driver.id, car_options[selected_car_label])
            st.success("Výchozí auto uloženo.")
            st.rerun()

    # ── Kauce ─────────────────────────────────────────────────────
    with col_right:
        st.markdown("#### 💰 Kauce")

        kauce_celkem = stats['kauce_celkem']
        kauce_zaplaceno = stats['kauce_zaplaceno']
        kauce_zbyvajici = stats['kauce_zbyvajici']
        kauce_procento = stats['kauce_procento']

        col_k1, col_k2, col_k3 = st.columns(3)
        col_k1.metric("Celkem", f"{kauce_celkem:,.0f} Kč")
        col_k2.metric("Zaplaceno", f"{kauce_zaplaceno:,.0f} Kč")
        col_k3.metric("Zbývá", f"{kauce_zbyvajici:,.0f} Kč")

        st.markdown(
            f"<div style='background:rgba(255,255,255,0.1); border-radius:8px; height:10px; margin:0.5rem 0;'>"
            f"<div style='width:{min(kauce_procento,100):.1f}%; height:100%; "
            f"background:linear-gradient(90deg,#10b981,#059669); border-radius:8px;'></div></div>"
            f"<div style='color:rgba(255,255,255,0.6); font-size:0.85rem;'>{kauce_procento:.1f}% splaceno</div>",
            unsafe_allow_html=True
        )

        with st.form(f"kauce_form_{driver.id}"):
            castka = st.number_input("Splátka kauce (Kč)", min_value=0, value=1250, step=250)
            if st.form_submit_button("➕ Zadat splátku", width='stretch'):
                add_kauce_payment(driver.id, castka)
                st.success(f"Zaznamenáno {castka:,.0f} Kč")
                st.rerun()

    st.markdown("---")

    # ── Poslední směny ────────────────────────────────────────────
    st.markdown("#### 📅 Poslední směny (4 týdny)")
    shifts_found = []

    for week_offset in range(4):
        week_start = today - timedelta(days=today.weekday()) - timedelta(weeks=week_offset)
        week_data = get_week_assignments(week_start)
        for car_id, days in week_data.items():
            for datum, day_shifts in days.items():
                if datum == '__weekly__':
                    continue
                for s in day_shifts:
                    if s.get('driver_id') == driver.id:
                        # Najít SPZ auta
                        car_label = next(
                            (f"{c.spz}" for c in all_cars if c.id == car_id), str(car_id)
                        )
                        typ_label = {
                            'ranni': '☀️ 7–19',
                            'vecerni': '🌙 19–7',
                            'cely_den': '🕐 24h',
                            'servis': '🔧',
                        }.get(s.get('typ'), s.get('typ', ''))
                        shifts_found.append({
                            'datum': datum,
                            'auto': car_label,
                            'smena': typ_label,
                        })

    if shifts_found:
        shifts_found.sort(key=lambda x: x['datum'], reverse=True)
        import pandas as pd
        df = pd.DataFrame(shifts_found)
        df['datum'] = df['datum'].apply(lambda d: d.strftime('%d.%m.%Y') if hasattr(d, 'strftime') else str(d))
        df.columns = ['Datum', 'Auto', 'Směna']
        st.dataframe(df, width="stretch", hide_index=True)
    else:
        st.info("Žádné směny v posledních 4 týdnech.")

    st.markdown("---")

    # ── Pokuty ────────────────────────────────────────────────────
    col_pok_h, col_pok_btn = st.columns([3, 1])
    with col_pok_h:
        st.markdown("#### 🚔 Pokuty")
    with col_pok_btn:
        if st.button("➕ Přidat pokutu", width='stretch'):
            st.session_state[f'show_add_fine_{driver.id}'] = True

    # Formulář pro přidání pokuty
    if st.session_state.get(f'show_add_fine_{driver.id}'):
        with st.form(f"add_fine_{driver.id}"):
            col_f1, col_f2, col_f3 = st.columns([2, 3, 2])
            with col_f1:
                fine_datum = st.date_input("Datum pokuty", value=datetime.now().date())
            with col_f2:
                fine_popis = st.text_input("Popis pokuty", placeholder="Např. rychlost, parkování...")
            with col_f3:
                fine_castka = st.number_input("Výše pokuty (Kč)", min_value=0, value=2000, step=500)
            col_fs, col_fc = st.columns(2)
            with col_fs:
                fine_submitted = st.form_submit_button("💾 Uložit pokutu", width='stretch')
            with col_fc:
                fine_cancelled = st.form_submit_button("❌ Zrušit", width='stretch')
            if fine_submitted and fine_popis:
                create_fine(driver.id, fine_datum, fine_popis, fine_castka)
                st.session_state[f'show_add_fine_{driver.id}'] = False
                st.success(f"Pokuta {fine_castka:,.0f} Kč uložena.")
                st.rerun()
            if fine_cancelled:
                st.session_state[f'show_add_fine_{driver.id}'] = False
                st.rerun()

    # Seznam pokut
    fines = get_driver_fines(driver.id)
    if fines:
        for fine in fines:
            zbyvajici = max(0, fine.castka - (fine.zaplaceno or 0))
            procento = ((fine.zaplaceno or 0) / fine.castka * 100) if fine.castka > 0 else 0
            splaceno = procento >= 100

            col_d, col_p, col_c, col_z, col_bar, col_pay, col_del = st.columns([1.5, 3, 1.5, 1.5, 2, 1.5, 0.7])
            with col_d:
                st.markdown(fine.datum.strftime('%d.%m.%Y') if fine.datum else '—')
            with col_p:
                st.markdown(f"**{fine.popis}**")
            with col_c:
                st.markdown(f"{fine.castka:,.0f} Kč")
            with col_z:
                color = '#10b981' if splaceno else '#f59e0b'
                st.markdown(
                    f"<span style='color:{color};'>{fine.zaplaceno or 0:,.0f} / {fine.castka:,.0f}</span>",
                    unsafe_allow_html=True
                )
            with col_bar:
                bar_color = '#10b981' if splaceno else '#f59e0b'
                st.markdown(
                    f"<div style='background:rgba(255,255,255,0.1); border-radius:6px; height:8px; margin-top:0.6rem;'>"
                    f"<div style='width:{min(procento,100):.0f}%; height:100%; "
                    f"background:{bar_color}; border-radius:6px;'></div></div>",
                    unsafe_allow_html=True
                )
            with col_pay:
                if not splaceno:
                    if st.button("💳 Platba", key=f"fine_pay_btn_{fine.id}", width='stretch'):
                        st.session_state[f'fine_pay_{fine.id}'] = True
            with col_del:
                if st.button("🗑️", key=f"fine_del_{fine.id}", help="Smazat pokutu"):
                    delete_fine(fine.id)
                    st.rerun()

            # Inline formulář pro platbu
            if st.session_state.get(f'fine_pay_{fine.id}'):
                with st.form(f"fine_payment_{fine.id}"):
                    pay_castka = st.number_input(
                        f"Platba pokuty (max {zbyvajici:,.0f} Kč)",
                        min_value=0,
                        max_value=int(zbyvajici),
                        value=min(int(zbyvajici), 1000),
                        step=500,
                    )
                    col_ps, col_pc = st.columns(2)
                    with col_ps:
                        if st.form_submit_button("✅ Zadat platbu", width='stretch'):
                            add_fine_payment(fine.id, pay_castka)
                            st.session_state[f'fine_pay_{fine.id}'] = False
                            st.success(f"Zaznamenáno {pay_castka:,.0f} Kč")
                            st.rerun()
                    with col_pc:
                        if st.form_submit_button("❌ Zrušit", width='stretch'):
                            st.session_state[f'fine_pay_{fine.id}'] = False
                            st.rerun()
    else:
        st.info("Žádné pokuty.")

    st.markdown("---")

    # ── Editace řidiče ────────────────────────────────────────────
    with st.expander("✏️ Upravit řidiče"):
        with st.form(f"edit_driver_{driver.id}"):
            col1, col2 = st.columns(2)
            with col1:
                edit_jmeno = st.text_input("Jméno", value=driver.jmeno)
                edit_email = st.text_input("Email", value=driver.email or "")
                edit_telefon = st.text_input("Telefon", value=driver.telefon or "")
                edit_adresa = st.text_input("Trvalá adresa", value=driver.adresa or "")
                edit_cislo_uctu = st.text_input("Číslo účtu (CZ / IBAN)", value=driver.cislo_uctu or "")
            with col2:
                edit_datum = st.date_input("Datum nástupu", value=driver.datum_nastupu)
                edit_status = st.selectbox(
                    "Status",
                    ["active", "inactive", "archived", "nabor"],
                    index=["active", "inactive", "archived", "nabor"].index(driver.status)
                    if driver.status in ["active", "inactive", "archived", "nabor"] else 0
                )
                edit_kauce_celkem = st.number_input(
                    "Celková kauce (Kč)", min_value=0, value=int(driver.kauce_celkem or 10000), step=500
                )
                edit_rc = st.text_input("RČ (rodné číslo)", value=driver.rc or "")
                edit_cislo_op = st.text_input("Číslo OP", value=driver.cislo_op or "")
                from datetime import date as _date
                edit_datum_narozeni = st.date_input(
                    "Datum narození",
                    value=driver.datum_narozeni if driver.datum_narozeni else None,
                    min_value=_date(1960, 1, 1),
                    format="DD.MM.YYYY",
                )

            if driver.status == 'nabor':
                st.markdown("**Nábor checklist**")
                col_nb1, col_nb2, col_nb3 = st.columns(3)
                with col_nb1:
                    edit_nabor_op = st.checkbox(
                        "✅ Kopie OP předána", value=bool(driver.nabor_op)
                    )
                with col_nb2:
                    edit_nabor_ridicak = st.checkbox(
                        "✅ Kopie ŘP předána", value=bool(driver.nabor_ridicak)
                    )
                with col_nb3:
                    edit_nabor_taxi = st.checkbox(
                        "✅ Taxi licence", value=bool(driver.nabor_taxi)
                    )
            else:
                edit_nabor_op = bool(driver.nabor_op)
                edit_nabor_ridicak = bool(driver.nabor_ridicak)
                edit_nabor_taxi = bool(driver.nabor_taxi)

            col_s, col_c = st.columns(2)
            with col_s:
                submitted = st.form_submit_button("✅ Uložit", width='stretch')
            with col_c:
                cancelled = st.form_submit_button("❌ Zrušit", width='stretch')

            if submitted:
                update_driver(
                    driver.id,
                    jmeno=edit_jmeno,
                    email=edit_email,
                    telefon=edit_telefon,
                    datum_nastupu=edit_datum,
                    status=edit_status,
                    kauce_celkem=edit_kauce_celkem,
                    adresa=edit_adresa,
                    cislo_uctu=edit_cislo_uctu,
                    rc=edit_rc,
                    cislo_op=edit_cislo_op,
                    datum_narozeni=edit_datum_narozeni,
                    nabor_op=edit_nabor_op,
                    nabor_ridicak=edit_nabor_ridicak,
                    nabor_taxi=edit_nabor_taxi,
                )
                st.success("Řidič aktualizován.")
                st.rerun()

            if cancelled:
                st.rerun()
