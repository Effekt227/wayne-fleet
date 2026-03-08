"""
CRUD pro úkoly (todo_items) - Wayne Fleet Management System
"""

from datetime import date
from database.models import TodoItem, FinanceRecord, Driver
from database.database import SessionLocal


PRIORITY_ORDER = {'high': 0, 'medium': 1, 'low': 2}


def get_all_todos() -> list:
    db = SessionLocal()
    try:
        items = db.query(TodoItem).order_by(TodoItem.created_at.asc()).all()
        db.expunge_all()
        return items
    finally:
        db.close()


def create_todo(text: str, priority: str = 'medium', finance_ref_id: int = None) -> TodoItem:
    db = SessionLocal()
    try:
        item = TodoItem(text=text.strip(), priority=priority, finance_ref_id=finance_ref_id)
        db.add(item)
        db.commit()
        db.refresh(item)
        db.expunge(item)
        return item
    finally:
        db.close()


def set_todo_done(todo_id: int, done: bool) -> None:
    db = SessionLocal()
    try:
        item = db.query(TodoItem).filter(TodoItem.id == todo_id).first()
        if item:
            item.done = done
            db.commit()
    finally:
        db.close()


def delete_todo(todo_id: int) -> None:
    db = SessionLocal()
    try:
        item = db.query(TodoItem).filter(TodoItem.id == todo_id).first()
        if item:
            db.delete(item)
            db.commit()
    finally:
        db.close()


def sync_overdue_todos() -> int:
    """
    Automaticky přidá do TODO listu (priorita Vysoká) všechny nezaplacené
    finance_records po splatnosti, které tam ještě nejsou.
    Vrací počet nově přidaných položek.
    """
    today = date.today()
    db = SessionLocal()
    try:
        # Existující finance_ref_id v todo (nezaplacené/otevřené)
        existing_refs = {
            row[0]
            for row in db.query(TodoItem.finance_ref_id)
            .filter(TodoItem.finance_ref_id.isnot(None), TodoItem.done == False)
            .all()
        }

        # Přijde po splatnosti a stále nezaplaceno
        overdue = (
            db.query(FinanceRecord)
            .filter(
                FinanceRecord.status == 'nezaplaceno',
                FinanceRecord.datum_splatnosti < today,
                FinanceRecord.datum_splatnosti.isnot(None),
            )
            .all()
        )

        added = 0
        for rec in overdue:
            if rec.id not in existing_refs:
                typ_label = "Příjem" if rec.typ == 'vydana' else "Závazek"
                text = f"⚠️ {typ_label} po splatnosti: {rec.popis} ({rec.castka_kc:,.0f} Kč)"
                todo = TodoItem(text=text, priority='high', finance_ref_id=rec.id)
                db.add(todo)
                added += 1

        if added:
            db.commit()
        return added
    finally:
        db.close()


def sync_nabor_todos() -> int:
    """
    Pro každého řidiče ve stavu 'nabor':
    - Přidá do TODO (priorita Vysoká) chybějící položky (OP, ŘP, taxi licence).
    - Automaticky označí jako hotové TODO položky, které řidič mezitím splnil.
    Vrací počet nově přidaných položek.
    """
    db = SessionLocal()
    try:
        nabor_drivers = db.query(Driver).filter(Driver.status == 'nabor').all()

        # Mapa: text → TodoItem pro všechna pending nabor-todos
        existing_pending: dict[str, TodoItem] = {
            t.text: t
            for t in db.query(TodoItem).filter(TodoItem.done == False).all()
        }

        added = 0
        for driver in nabor_drivers:
            # Dvojice (label, splněno)
            items = [
                (f"👤 Nábor {driver.jmeno}: chybí Kopie OP", bool(driver.nabor_op)),
                (f"👤 Nábor {driver.jmeno}: chybí Kopie ŘP", bool(driver.nabor_ridicak)),
                (f"👤 Nábor {driver.jmeno}: chybí Taxi licence", bool(driver.nabor_taxi)),
            ]
            for text, done in items:
                if done:
                    # Pokud splněno a TODO existuje → auto-dokončit
                    if text in existing_pending:
                        existing_pending[text].done = True
                else:
                    # Chybí a TODO ještě neexistuje → přidat
                    if text not in existing_pending:
                        db.add(TodoItem(text=text, priority='high'))
                        existing_pending[text] = True  # zamezit duplicitě v téže iteraci
                        added += 1

        db.commit()
        return added
    finally:
        db.close()
