"""
Banka Page - Wayne Fleet Management System
Propojení s Raiffeisenbank Premium API.
DB drží celou historii transakcí. Každé stažení přidá pouze nové.
"""

import streamlit as st
import json
import os
from datetime import date, timedelta
from database.crud_bank import (
    upsert_transactions, get_transactions, get_transaction_stats,
    match_transaction_to_finance, unmatch_transaction, auto_match_transactions,
    delete_all_transactions,
)
from database.crud_finance_records import get_records
from database.database import init_db

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config_bank.json')


def _load_config() -> dict:
    # Cloud: načíst ze Streamlit secrets
    try:
        bank_secrets = st.secrets.get('bank', {})
        if bank_secrets and bank_secrets.get('client_id'):
            return {
                'client_id': bank_secrets.get('client_id', ''),
                'account_number': bank_secrets.get('account_number', ''),
                'currency': bank_secrets.get('currency', 'CZK'),
            }
    except Exception:
        pass
    # Lokálně: načíst ze souboru
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    return {}


def _save_config(cfg: dict):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(cfg, f)


def render_banka_page():
    init_db()

    st.markdown("## 🏦 Bankovní účet – RB Premium API")

    cfg = _load_config()

    # ── Nastavení ──────────────────────────────────────────────────────────
    with st.expander("⚙️ Nastavení připojení", expanded=not cfg.get('client_id')):
        st.info(
            "Pro přístup k API potřebuješ **ClientID** ze svého účtu na "
            "[developers.rb.cz](https://developers.rb.cz/premium). "
            "Certifikát (`WayneFleetAPI.p12`) a heslo jsou již nastaveny v aplikaci."
        )
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            client_id_input = st.text_input(
                "ClientID (X-IBM-Client-Id)",
                value=cfg.get('client_id', ''),
                type='password',
                key='bank_client_id',
            )
            account_number_input = st.text_input(
                "Číslo účtu (bez předčíslí, bez kódu banky)",
                value=cfg.get('account_number', ''),
                placeholder='192000145399',
                key='bank_account_number',
            )
        with col_s2:
            currency_input = st.selectbox(
                "Měna",
                ['CZK', 'EUR', 'USD'],
                index=['CZK', 'EUR', 'USD'].index(cfg.get('currency', 'CZK')),
                key='bank_currency',
            )
            st.markdown("")
            if st.button("💾 Uložit nastavení", key='bank_save_cfg'):
                _save_config({
                    'client_id': client_id_input,
                    'account_number': account_number_input,
                    'currency': currency_input,
                })
                st.success("Nastavení uloženo.")
                st.rerun()

    cfg = _load_config()
    client_id = cfg.get('client_id', '')
    account_number = cfg.get('account_number', '')
    currency = cfg.get('currency', 'CZK')

    if not client_id or not account_number:
        st.warning("Nejdřív nastav ClientID a číslo účtu v sekci ⚙️ Nastavení.")
        return

    # ── Stav databáze ──────────────────────────────────────────────────────
    stats = get_transaction_stats()
    col_st1, col_st2, col_st3, col_st4 = st.columns(4)
    col_st1.metric("Transakcí v DB", stats['total'])
    col_st2.metric("Nejstarší", stats['oldest'].strftime('%d.%m.%Y') if stats['oldest'] else '—')
    col_st3.metric("Nejnovější", stats['newest'].strftime('%d.%m.%Y') if stats['newest'] else '—')
    col_st4.metric("Nespárovaných", stats['unmatched'])

    with st.expander("🗑️ Smazat všechny transakce z DB"):
        st.warning("Smaže všechny transakce z databáze. Nelze vrátit zpět.")
        if st.button("🗑️ Potvrdit smazání", key="bank_delete_all", type="primary"):
            count = delete_all_transactions()
            st.success(f"Smazáno {count} transakcí.")
            st.rerun()

    st.markdown("---")

    # ── Stažení nových transakcí ───────────────────────────────────────────
    st.markdown("### 📥 Stáhnout nové transakce z banky")
    st.caption("Každé stažení přidá pouze nové transakce — duplicity jsou automaticky přeskočeny.")

    col_d1, col_d2, col_d3 = st.columns([2, 2, 1])
    with col_d1:
        fetch_from = st.date_input("Od", value=date.today() - timedelta(days=30), key='bank_fetch_from')
    with col_d2:
        fetch_to = st.date_input("Do", value=date.today(), key='bank_fetch_to')
    with col_d3:
        st.markdown("")
        fetch_btn = st.button("🔄 Načíst z banky", key='bank_fetch', width='stretch')

    if fetch_btn:
        if (fetch_to - fetch_from).days > 90:
            st.error("API umožňuje maximálně 90 dní najednou.")
        else:
            with st.spinner("Načítám transakce z Raiffeisenbank..."):
                try:
                    from utils.rb_api import get_all_transactions, parse_transaction
                    raw = get_all_transactions(client_id, account_number, currency, fetch_from, fetch_to)
                    parsed = [parse_transaction(t) for t in raw]
                    new_count = upsert_transactions(parsed)
                    auto_n = auto_match_transactions()
                    st.success(
                        f"Staženo {len(parsed)} transakcí → **{new_count} nových** přidáno do DB."
                        + (f" Automaticky spárováno: {auto_n}." if auto_n else "")
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Chyba při načítání z API: {e}")

    st.markdown("---")

    # ── Zobrazení transakcí z DB ───────────────────────────────────────────
    st.markdown("### 📋 Historie transakcí (databáze)")

    col_f1, col_f2, col_f3, col_f4 = st.columns([2, 2, 2, 1])
    with col_f1:
        view_from = st.date_input("Zobrazit od", value=date.today() - timedelta(days=30), key='bank_view_from')
    with col_f2:
        view_to = st.date_input("Zobrazit do", value=date.today(), key='bank_view_to')
    with col_f3:
        direction_filter = st.selectbox("Směr", ['Vše', '🟢 Příchozí', '🔴 Odchozí'], key='bank_dir')
    with col_f4:
        only_unmatched = st.checkbox("Jen nespárované", key='bank_unmatched')

    cd_filter = None
    if direction_filter == '🟢 Příchozí':
        cd_filter = 'CRDT'
    elif direction_filter == '🔴 Odchozí':
        cd_filter = 'DBIT'

    transactions = get_transactions(view_from, view_to, cd_filter, only_unmatched)

    if not transactions:
        st.info("Žádné transakce pro zvolené filtry.")
        return

    # Souhrn viditelných transakcí
    prijate = sum(t.amount for t in transactions if t.credit_debit == 'CRDT')
    odeslane = sum(t.amount for t in transactions if t.credit_debit == 'DBIT')
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Zobrazeno", len(transactions))
    col_m2.metric("Příchozí celkem", f"{prijate:,.0f} Kč")
    col_m3.metric("Odchozí celkem", f"{odeslane:,.0f} Kč")

    st.markdown("")

    # Finance Records pro párování
    finance_open = {
        f"#{fr.id} | {fr.popis} | {fr.castka_kc:.0f} Kč": fr.id
        for fr in get_records()
        if fr.status == 'nezaplaceno'
    }

    for txn in transactions:
        is_in = txn.credit_debit == 'CRDT'
        color = "#22c55e" if is_in else "#ef4444"
        direction_label = "▲ IN" if is_in else "▼ OUT"

        matched_label = ""
        if txn.matched_finance_id:
            matched_label = f"✅ spárováno s Finance #{txn.matched_finance_id}"
        elif txn.matched_invoice_id:
            matched_label = f"✅ spárováno s Vyúčtováním #{txn.matched_invoice_id}"

        col1, col2, col3, col4 = st.columns([1, 2, 3, 2])

        with col1:
            st.markdown(
                f"<b style='color:{color}'>{direction_label}</b><br>"
                f"<small>{txn.booking_date.strftime('%d.%m.%Y') if txn.booking_date else '—'}</small>",
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                f"<b style='font-size:1.05rem'>{txn.amount:,.2f} {txn.currency}</b><br>"
                f"<small style='color:#9ca3af'>{txn.counterparty_name or '—'}</small>",
                unsafe_allow_html=True,
            )
        with col3:
            info = txn.transaction_info or txn.counterparty_account or ''
            st.markdown(
                f"<small style='color:#6b7280'>{info[:120]}</small>"
                + (f"<br><small style='color:#22c55e'>{matched_label}</small>" if matched_label else ""),
                unsafe_allow_html=True,
            )
        with col4:
            if matched_label:
                if st.button("❌ Zrušit", key=f"unmatch_{txn.id}", width="stretch"):
                    unmatch_transaction(txn.id)
                    st.rerun()
            else:
                fr_keys = ['— spárovat s —'] + list(finance_open.keys())
                sel = st.selectbox("", fr_keys, key=f"sel_{txn.id}", label_visibility='collapsed')
                if sel != '— spárovat s —':
                    if st.button("✅ Párovat", key=f"match_{txn.id}", width="stretch"):
                        match_transaction_to_finance(txn.id, finance_open[sel])
                        _mark_fr_paid(finance_open[sel], txn.booking_date)
                        st.rerun()

        st.divider()


def _mark_fr_paid(finance_id: int, payment_date):
    from database.database import SessionLocal
    from database.models import FinanceRecord
    with SessionLocal() as db:
        fr = db.query(FinanceRecord).get(finance_id)
        if fr:
            fr.status = 'zaplaceno'
            fr.datum_zaplaceni = payment_date
            db.commit()
