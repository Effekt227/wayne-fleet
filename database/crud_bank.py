"""
CRUD pro bankovní transakce - Wayne Fleet Management System
"""

from sqlalchemy import desc
from database.database import SessionLocal
from database.models import BankTransaction, FinanceRecord, Invoice
from datetime import date


def upsert_transactions(transactions: list[dict]) -> int:
    """
    Uloží transakce do DB (přeskočí duplicity dle entry_reference).
    Vrátí počet nově přidaných.
    """
    added = 0
    with SessionLocal() as db:
        for txn in transactions:
            ref = txn.get('entry_reference', '')
            if not ref:
                continue
            exists = db.query(BankTransaction).filter(BankTransaction.entry_reference == ref).first()
            if not exists:
                obj = BankTransaction(
                    entry_reference=ref,
                    amount=txn.get('amount', 0),
                    currency=txn.get('currency', 'CZK'),
                    credit_debit=txn.get('credit_debit', ''),
                    booking_date=txn.get('booking_date'),
                    counterparty_name=txn.get('counterparty_name', ''),
                    counterparty_account=txn.get('counterparty_account', ''),
                    transaction_info=txn.get('transaction_info', ''),
                )
                db.add(obj)
                added += 1
        db.commit()
    return added


def get_transactions(date_from: date = None, date_to: date = None,
                     credit_debit: str = None, only_unmatched: bool = False) -> list:
    """Vrátí transakce z DB, volitelně filtrované."""
    with SessionLocal() as db:
        q = db.query(BankTransaction)
        if date_from:
            q = q.filter(BankTransaction.booking_date >= date_from)
        if date_to:
            q = q.filter(BankTransaction.booking_date <= date_to)
        if credit_debit:
            q = q.filter(BankTransaction.credit_debit == credit_debit)
        if only_unmatched:
            q = q.filter(
                BankTransaction.matched_finance_id == None,
                BankTransaction.matched_invoice_id == None,
            )
        results = q.order_by(desc(BankTransaction.booking_date)).all()
        db.expunge_all()
        return results


def get_transaction_stats() -> dict:
    """Vrátí souhrnné statistiky všech transakcí v DB."""
    from sqlalchemy import func
    with SessionLocal() as db:
        total = db.query(BankTransaction).count()
        oldest = db.query(func.min(BankTransaction.booking_date)).scalar()
        newest = db.query(func.max(BankTransaction.booking_date)).scalar()
        unmatched = db.query(BankTransaction).filter(
            BankTransaction.matched_finance_id == None,
            BankTransaction.matched_invoice_id == None,
        ).count()
    return {'total': total, 'oldest': oldest, 'newest': newest, 'unmatched': unmatched}


def match_transaction_to_finance(txn_id: int, finance_id: int):
    with SessionLocal() as db:
        txn = db.query(BankTransaction).get(txn_id)
        if txn:
            txn.matched_finance_id = finance_id
            txn.matched_invoice_id = None
            db.commit()


def match_transaction_to_invoice(txn_id: int, invoice_id: int):
    with SessionLocal() as db:
        txn = db.query(BankTransaction).get(txn_id)
        if txn:
            txn.matched_invoice_id = invoice_id
            txn.matched_finance_id = None
            db.commit()


def unmatch_transaction(txn_id: int):
    with SessionLocal() as db:
        txn = db.query(BankTransaction).get(txn_id)
        if txn:
            txn.matched_finance_id = None
            txn.matched_invoice_id = None
            db.commit()


def auto_match_transactions():
    """
    Pokusí se automaticky spárovat nepárované transakce.
    Logika: hledá nezaplacenou FinanceRecord nebo Invoice se stejnou částkou
    a jménem/popisem obsaženým v transaction_info nebo counterparty_name.
    Vrátí počet spárovaných.
    """
    matched_count = 0
    with SessionLocal() as db:
        unpaired = db.query(BankTransaction).filter(
            BankTransaction.matched_finance_id == None,
            BankTransaction.matched_invoice_id == None,
            BankTransaction.credit_debit == 'CRDT',   # jen příchozí platby
        ).all()

        finance_open = db.query(FinanceRecord).filter(
            FinanceRecord.status == 'nezaplaceno'
        ).all()

        invoices_open = db.query(Invoice).filter(
            Invoice.status == 'nezaplaceno'
        ).all()

        for txn in unpaired:
            info_lower = (txn.transaction_info or '').lower()
            cp_lower = (txn.counterparty_name or '').lower()
            search_text = info_lower + ' ' + cp_lower

            # Zkusit spárovat s FinanceRecord
            for fr in finance_open:
                if abs(fr.castka_kc - txn.amount) < 1:  # shoda částky (±1 Kč)
                    popis_lower = fr.popis.lower()
                    driver_name = (fr.driver.jmeno if fr.driver else '').lower()
                    if popis_lower in search_text or (driver_name and driver_name in search_text):
                        txn.matched_finance_id = fr.id
                        matched_count += 1
                        break
            else:
                # Zkusit spárovat s Invoice
                for inv in invoices_open:
                    celkem = abs(inv.vysledek)
                    if abs(celkem - txn.amount) < 1:
                        driver_name = (inv.driver.jmeno if inv.driver else '').lower()
                        if driver_name and driver_name in search_text:
                            txn.matched_invoice_id = inv.id
                            matched_count += 1
                            break

        db.commit()
    return matched_count
