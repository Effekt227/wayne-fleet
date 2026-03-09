"""
Raiffeisenbank CZ Premium API klient - Wayne Fleet Management System
Autentizace: mTLS (PKCS#12 certifikát) + X-IBM-Client-Id header
Dokumentace: https://developers.rb.cz/premium
"""

import os
import base64
import tempfile
import uuid
import requests
from datetime import date, datetime
from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption
from cryptography.hazmat.backends import default_backend

# ── Konfigurace ──────────────────────────────────────────────────────────────
CERT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'WayneFleetAPI.p12')
CERT_PASSWORD = b'WayneFleet227'
BASE_URL = 'https://api.rb.cz/rbcz/premium/api'


def _get_cert_data() -> bytes:
    """Načte P12 certifikát: přednostně z env/secrets (cloud), fallback ze souboru (lokálně)."""
    # Cloud: certifikát uložen jako base64 string v secrets
    cert_b64 = os.environ.get('RB_CERT_B64', '')
    if not cert_b64:
        try:
            import streamlit as st
            cert_b64 = st.secrets.get('RB_CERT_B64', '')
        except Exception:
            pass
    if cert_b64:
        return base64.b64decode(cert_b64)
    # Lokálně: číst ze souboru
    with open(CERT_PATH, 'rb') as f:
        return f.read()


def _get_cert_password() -> bytes:
    pwd = os.environ.get('RB_CERT_PASSWORD', '')
    if not pwd:
        try:
            import streamlit as st
            pwd = st.secrets.get('RB_CERT_PASSWORD', '')
        except Exception:
            pass
    return pwd.encode() if pwd else CERT_PASSWORD


class RBApiError(Exception):
    pass


def _load_pem_files():
    """Načte P12 certifikát a vrátí dočasné PEM soubory (cert_path, key_path)."""
    p12_data = _get_cert_data()
    cert_password = _get_cert_password()

    private_key, certificate, _ = pkcs12.load_key_and_certificates(
        p12_data, cert_password, default_backend()
    )

    cert_pem = certificate.public_bytes(Encoding.PEM)
    key_pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())

    cert_file = tempfile.NamedTemporaryFile(delete=False, suffix='_cert.pem')
    cert_file.write(cert_pem)
    cert_file.close()

    key_file = tempfile.NamedTemporaryFile(delete=False, suffix='_key.pem')
    key_file.write(key_pem)
    key_file.close()

    return cert_file.name, key_file.name


def _request(method, path, client_id, params=None, json=None):
    """Provede autentizované volání RB API."""
    cert_path, key_path = _load_pem_files()
    try:
        headers = {
            'X-IBM-Client-Id': client_id,
            'X-Request-Id': str(uuid.uuid4()),
            'Accept': 'application/json',
        }
        url = BASE_URL + path
        response = requests.request(
            method, url,
            cert=(cert_path, key_path),
            headers=headers,
            params=params,
            json=json,
            timeout=30,
        )
        if response.status_code == 429:
            raise RBApiError('Překročen limit API požadavků (429). Zkuste za chvíli.')
        if response.status_code == 401:
            raise RBApiError('Neplatný certifikát nebo ClientID (401).')
        if response.status_code == 403:
            raise RBApiError('Přístup odepřen (403). Ověřte oprávnění certifikátu.')
        if not response.ok:
            raise RBApiError(f'Chyba API: {response.status_code} — {response.text[:300]}')
        return response.json()
    finally:
        os.unlink(cert_path)
        os.unlink(key_path)


def get_accounts(client_id: str) -> list[dict]:
    """Vrátí seznam účtů."""
    data = _request('GET', '/accounts', client_id)
    return data.get('accounts', data) if isinstance(data, dict) else data


def get_account_balance(client_id: str, account_number: str) -> dict:
    """Vrátí zůstatek účtu."""
    return _request('GET', f'/accounts/{account_number}/balance', client_id)


def get_transactions(
    client_id: str,
    account_number: str,
    currency: str,
    date_from: date,
    date_to: date,
    page: int = 1,
) -> dict:
    """
    Vrátí transakce účtu.
    API max: 90 dní najednou.
    """
    params = {
        'from': date_from.strftime('%Y-%m-%d'),
        'to': date_to.strftime('%Y-%m-%d'),
        'page': page,
    }
    return _request('GET', f'/accounts/{account_number}/{currency}/transactions', client_id, params=params)


def get_all_transactions(
    client_id: str,
    account_number: str,
    currency: str,
    date_from: date,
    date_to: date,
) -> list[dict]:
    """Stáhne všechny stránky transakcí pro dané období."""
    all_txns = []
    page = 1
    while True:
        data = get_transactions(client_id, account_number, currency, date_from, date_to, page)
        txns = data.get('transactions', [])
        all_txns.extend(txns)
        if data.get('lastPage', True):
            break
        page += 1
    return all_txns


def parse_transaction(txn: dict) -> dict:
    """Normalizuje surová data transakce do jednoduchého slovníku."""
    amount_obj = txn.get('amount', {})
    amount = amount_obj.get('value', 0)
    currency = amount_obj.get('currency', 'CZK')
    credit_debit = txn.get('creditDebitIndication', '')  # CRDT / DBIT

    booking_raw = (txn.get('bookingDate') or txn.get('valueDate')
                   or txn.get('transactionDate') or '')
    try:
        booking_date = datetime.fromisoformat(booking_raw.replace('Z', '+00:00')).date()
    except Exception:
        booking_date = date.today()  # fallback na dnešek místo NULL

    # Protiúčet a zpráva (mohou být zanořené různě dle verze API)
    details = txn.get('entryDetails', {}).get('transactionDetails', {})
    related = details.get('relatedParties', {})
    counterparty = related.get('counterParty', {})
    cp_name = counterparty.get('name', '')
    cp_account = counterparty.get('financialInstitutionAccount', {}).get('identification', {}).get('iban', '')
    if not cp_account:
        cp_account = counterparty.get('account', {}).get('identification', {}).get('iban', '')

    remittance = details.get('remittanceInformation', {})
    info = remittance.get('unstructured', '') or remittance.get('structured', {}).get('additionalRemittanceInformation', '')

    return {
        'entry_reference': txn.get('entryReference', ''),
        'amount': abs(amount),
        'currency': currency,
        'credit_debit': credit_debit,   # CRDT = příchozí, DBIT = odchozí
        'booking_date': booking_date,
        'counterparty_name': cp_name,
        'counterparty_account': cp_account,
        'transaction_info': info,
    }
