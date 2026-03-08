"""
Car Detail Page - Wayne Fleet Management System
Detailní karta auta: finance, splátky, servisní historie, editace
"""

import streamlit as st
from datetime import date, datetime
from database.crud_cars import get_car_by_id, update_car
from utils.cached_queries import cached_car_stats as get_car_stats
from database.crud_payments import zadat_platbu
from database.crud_services import (
    get_car_services, create_service, delete_service,
    get_next_service, get_total_service_cost,
)

SERVICE_TYPES = ['Olej', 'STK', 'Brzdy', 'Pneumatiky', 'Karoserie', 'Elektrika', 'Jiné']


def render_car_detail(car_id: int):
    if not car_id:
        st.error("Auto nenalezeno.")
        return

    car = get_car_by_id(car_id)
    if not car:
        st.error("Auto nenalezeno.")
        return

    stats = get_car_stats(car_id)

    # ── Zpět ──────────────────────────────────────────────────────
    if st.button("◀ Zpět na auta"):
        st.session_state['page'] = 'auta'
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Hlavička auta ─────────────────────────────────────────────
    status_map = {
        'active':  ('✅ Aktivní', '#10b981'),
        'service': ('🔧 Servis',  '#f59e0b'),
        'retired': ('🗄️ Vyřazeno','#6b7280'),
    }
    status_label, status_color = status_map.get(car.status, (car.status, '#6b7280'))
    typ_label = "🔑 Vlastní" if car.typ_vlastnictvi == 'vlastni' else "📋 Pronájem"

    col_spz, col_info, col_status = st.columns([2, 4, 2])
    with col_spz:
        st.markdown(
            f"<div style='font-size:2rem; font-weight:900; color:white;'>🚗 {car.spz}</div>"
            f"<div style='color:rgba(255,255,255,0.6);'>{car.model} ({car.rok})</div>",
            unsafe_allow_html=True
        )
    with col_info:
        cena_tyden = car.cena_tyden_pronajem or 0
        st.markdown(
            f"<div style='margin-top:0.5rem; color:rgba(255,255,255,0.7);'>"
            f"VIN: <strong>{car.vin or '—'}</strong> &nbsp;|&nbsp; "
            f"🛣️ <strong>{car.celkem_km:,} km</strong> &nbsp;|&nbsp; {typ_label}"
            + (f" &nbsp;|&nbsp; 📋 Pronájem řidiče: <strong>{cena_tyden:,.0f} Kč/týden</strong>" if cena_tyden else "")
            + f"</div>",
            unsafe_allow_html=True
        )
    with col_status:
        st.markdown(
            f"<div style='background:{status_color}; color:white; padding:0.4rem 1rem; "
            f"border-radius:20px; text-align:center; font-weight:700; margin-top:1rem;'>"
            f"{status_label}</div>",
            unsafe_allow_html=True
        )

    st.markdown("---")

    # ── Finance ───────────────────────────────────────────────────
    st.markdown("#### 💰 Finance")

    if car.typ_vlastnictvi == 'vlastni':
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Kauce", f"{car.kauce:,.0f} Kč")
        col2.metric("Splátka/týden", f"{car.splatka_tyden:,.0f} Kč")
        col3.metric("Splátky", f"{car.zaplaceno_splatek} / {car.celkem_splatek}")
        col4.metric("Celkem km", f"{car.celkem_km:,}")

        procento = stats['procento_splaceno'] if stats else 0
        zaplaceno = stats['zaplaceno'] if stats else 0
        celkova_cena = stats['celkova_cena'] if stats else 0
        zbyvajici = stats['zbyvajici_splatka'] if stats else 0
        zbyvajici_splatek = stats['zbyvajici_splatek'] if stats else 0

        st.markdown(
            f"<div style='display:flex; justify-content:space-between; margin-bottom:4px;'>"
            f"<span style='color:rgba(255,255,255,0.6);'>Splaceno</span>"
            f"<span style='color:white; font-weight:600;'>{zaplaceno:,.0f} / {celkova_cena:,.0f} Kč</span></div>"
            f"<div style='background:rgba(255,255,255,0.1); border-radius:8px; height:10px;'>"
            f"<div style='width:{min(procento,100):.1f}%; height:100%; "
            f"background:linear-gradient(90deg,#10b981,#059669); border-radius:8px;'></div></div>"
            f"<div style='display:flex; justify-content:space-between; margin-top:4px; "
            f"color:rgba(255,255,255,0.5); font-size:0.85rem;'>"
            f"<span>{procento:.1f}% splaceno ({car.zaplaceno_splatek} z {car.celkem_splatek} splátek)</span>"
            f"<span>Zbývá: {zbyvajici:,.0f} Kč ({zbyvajici_splatek} splátek)</span></div>",
            unsafe_allow_html=True
        )

        st.markdown("<br>", unsafe_allow_html=True)
        col_pay, col_edit = st.columns(2)

        with col_pay:
            if zbyvajici_splatek > 0:
                with st.form(f"payment_form_{car.id}"):
                    pocet = st.number_input(
                        "Počet splátek", min_value=1, max_value=zbyvajici_splatek, value=1
                    )
                    castka = pocet * car.splatka_tyden
                    st.metric("Částka", f"{castka:,.0f} Kč")
                    col_ps, col_pc = st.columns(2)
                    with col_ps:
                        if st.form_submit_button("💳 Zadat platbu", width='stretch'):
                            zadat_platbu(car.id, pocet)
                            st.success(f"Platba {castka:,.0f} Kč zaznamenána.")
                            st.rerun()
            else:
                st.success("✅ Auto je plně splaceno!")

    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Nájem/týden", f"{car.splatka_tyden:,.0f} Kč")
        col2.metric("Celkem km", f"{car.celkem_km:,}")
        col3.metric("VIN", car.vin or "—")
        st.info("Toto auto je na pronájem.")

    st.markdown("---")

    # ── Servisní historie ─────────────────────────────────────────
    col_serv_h, col_serv_btn = st.columns([3, 1])
    with col_serv_h:
        st.markdown("#### 🔧 Servisní historie")
    with col_serv_btn:
        if st.button("➕ Přidat servis", width='stretch'):
            st.session_state[f'show_add_service_{car.id}'] = True

    # Formulář pro přidání servisu
    if st.session_state.get(f'show_add_service_{car.id}'):
        with st.form(f"add_service_{car.id}"):
            st.markdown("**Nový servisní záznam**")
            col1, col2 = st.columns(2)
            with col1:
                s_datum = st.date_input("Datum servisu", value=date.today())
                s_typ = st.selectbox("Typ servisu", SERVICE_TYPES)
                s_naklady = st.number_input("Náklady (Kč)", min_value=0, value=0, step=100)
                s_km = st.number_input("KM při servisu", min_value=0, value=car.celkem_km)
            with col2:
                s_popis = st.text_area("Popis", placeholder="Co bylo provedeno...")
                st.markdown("**Příští servis (volitelné)**")
                s_pristi_datum = st.date_input("Datum příštího servisu", value=None)
                s_pristi_km = st.number_input("KM příštího servisu", min_value=0, value=0)
                s_pristi_popis = st.text_input("Co příště provést", placeholder="Výměna oleje, STK...")

            col_ss, col_sc = st.columns(2)
            with col_ss:
                submitted = st.form_submit_button("💾 Uložit servis", width='stretch')
            with col_sc:
                cancelled = st.form_submit_button("❌ Zrušit", width='stretch')

            if submitted:
                create_service(
                    car_id=car.id,
                    datum=s_datum,
                    typ=s_typ,
                    popis=s_popis if s_popis else None,
                    naklady=s_naklady,
                    km_pri_servisu=s_km if s_km > 0 else None,
                    pristi_servis_datum=s_pristi_datum,
                    pristi_servis_km=s_pristi_km if s_pristi_km > 0 else None,
                    pristi_servis_popis=s_pristi_popis if s_pristi_popis else None,
                )
                st.session_state[f'show_add_service_{car.id}'] = False
                st.success("Servis uložen.")
                st.rerun()

            if cancelled:
                st.session_state[f'show_add_service_{car.id}'] = False
                st.rerun()

    # Tabulka servisů
    services = get_car_services(car.id)
    next_service = get_next_service(car.id)
    total_cost = get_total_service_cost(car.id)

    if services:
        for s in services:
            col_d, col_t, col_p, col_km, col_c, col_del = st.columns([2, 1.5, 3, 1.5, 1.5, 1])
            with col_d:
                st.markdown(s.datum.strftime('%d.%m.%Y') if s.datum else '—')
            with col_t:
                st.markdown(f"**{s.typ or '—'}**")
            with col_p:
                st.markdown(s.popis or '—')
            with col_km:
                st.markdown(f"{s.km_pri_servisu:,} km" if s.km_pri_servisu else '—')
            with col_c:
                st.markdown(f"{s.naklady:,.0f} Kč" if s.naklady else '—')
            with col_del:
                if st.button("🗑️", key=f"del_service_{s.id}", help="Smazat"):
                    delete_service(s.id)
                    st.rerun()

        st.markdown(
            f"<div style='text-align:right; color:rgba(255,255,255,0.8); margin-top:0.5rem;'>"
            f"Celkové náklady na servisy: <strong>{total_cost:,.0f} Kč</strong></div>",
            unsafe_allow_html=True
        )
    else:
        st.info("Zatím žádné servisní záznamy.")

    # Příští servis
    if next_service:
        parts = []
        if next_service.get('datum'):
            parts.append(f"📅 {next_service['datum'].strftime('%d.%m.%Y')}")
        if next_service.get('km'):
            parts.append(f"🛣️ {next_service['km']:,} km")
        if next_service.get('popis'):
            parts.append(f"– {next_service['popis']}")
        st.info(f"Příští servis: {' &nbsp;|&nbsp; '.join(parts)}")

    st.markdown("---")

    # ── Editace auta ──────────────────────────────────────────────
    with st.expander("✏️ Upravit auto"):
        with st.form(f"edit_car_{car.id}"):
            col1, col2 = st.columns(2)
            with col1:
                edit_spz = st.text_input("SPZ", value=car.spz)
                edit_model = st.text_input("Model", value=car.model)
                edit_rok = st.number_input("Rok", min_value=2000, max_value=2030, value=car.rok)
                edit_vin = st.text_input("VIN", value=car.vin or "")
            with col2:
                edit_km = st.number_input("Celkem KM", min_value=0, value=car.celkem_km)
                edit_status = st.selectbox(
                    "Status", ["active", "service", "retired"],
                    index=["active", "service", "retired"].index(car.status)
                    if car.status in ["active", "service", "retired"] else 0
                )
                edit_barva = st.text_input("Barva", value=car.barva or "")

            if car.typ_vlastnictvi == 'vlastni':
                st.markdown("**Finance**")
                col3, col4 = st.columns(2)
                with col3:
                    edit_kauce = st.number_input("Kauce (Kč)", min_value=0, value=int(car.kauce or 0))
                    edit_splatka = st.number_input("Splátka/týden (Kč)", min_value=0, value=int(car.splatka_tyden or 0))
                with col4:
                    edit_celkem_splatek = st.number_input("Celkem splátek", min_value=1, value=car.celkem_splatek or 1)
                    edit_zaplaceno_splatek = st.number_input(
                        "Zaplaceno splátek", min_value=0,
                        max_value=car.celkem_splatek or 1,
                        value=car.zaplaceno_splatek or 0
                    )

            st.markdown("**Pronájem pro řidiče**")
            edit_cena_tyden_pronajem = st.number_input(
                "Cena pronájmu pro řidiče (Kč/týden)",
                min_value=0, value=int(car.cena_tyden_pronajem or 0), step=500,
                help="Tato cena se automaticky předvyplní do týdenní smlouvy o pronájmu."
            )

            st.markdown("**Expirace dokladů**")
            col_exp1, col_exp2 = st.columns(2)
            with col_exp1:
                edit_stk_datum = st.date_input(
                    "Platnost STK do", value=car.stk_datum or None, key=f"stk_{car.id}"
                )
            with col_exp2:
                edit_pojistka_datum = st.date_input(
                    "Platnost pojistky do", value=car.pojistka_datum or None, key=f"poj_{car.id}"
                )

            col_ss, col_sc = st.columns(2)
            with col_ss:
                submitted = st.form_submit_button("✅ Uložit", width='stretch')
            with col_sc:
                cancelled = st.form_submit_button("❌ Zrušit", width='stretch')

            if submitted:
                update_data = {
                    'spz': edit_spz,
                    'model': edit_model,
                    'rok': edit_rok,
                    'vin': edit_vin,
                    'celkem_km': edit_km,
                    'status': edit_status,
                    'barva': edit_barva,
                }
                if car.typ_vlastnictvi == 'vlastni':
                    nova_cena = edit_kauce + (edit_celkem_splatek * edit_splatka)
                    nove_zaplaceno = edit_kauce + (edit_zaplaceno_splatek * edit_splatka)
                    update_data.update({
                        'kauce': edit_kauce,
                        'splatka_tyden': edit_splatka,
                        'celkem_splatek': edit_celkem_splatek,
                        'zaplaceno_splatek': edit_zaplaceno_splatek,
                        'cena': nova_cena,
                        'zaplaceno': nove_zaplaceno,
                    })
                update_data['cena_tyden_pronajem'] = edit_cena_tyden_pronajem
                update_data['stk_datum'] = edit_stk_datum
                update_data['pojistka_datum'] = edit_pojistka_datum
                update_car(car.id, **update_data)
                st.success("Auto aktualizováno.")
                st.rerun()

            if cancelled:
                st.rerun()
