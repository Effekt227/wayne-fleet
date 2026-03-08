"""
CRUD Operations for DriverFine - Wayne Fleet Management System
Pokuty řidičů: přidání, sledování plateb, smazání
"""

from database.models import DriverFine
from database.database import SessionLocal
from datetime import date
from typing import List, Optional


def get_driver_fines(driver_id: int) -> List[DriverFine]:
    """Vrátí všechny pokuty daného řidiče, seřazené od nejnovější"""
    db = SessionLocal()
    try:
        return (
            db.query(DriverFine)
            .filter(DriverFine.driver_id == driver_id)
            .order_by(DriverFine.datum.desc())
            .all()
        )
    finally:
        db.close()


def create_fine(driver_id: int, datum: date, popis: str, castka: float) -> DriverFine:
    """Vytvoří nový záznam pokuty"""
    db = SessionLocal()
    try:
        fine = DriverFine(
            driver_id=driver_id,
            datum=datum,
            popis=popis,
            castka=castka,
            zaplaceno=0,
        )
        db.add(fine)
        db.commit()
        db.refresh(fine)
        return fine
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def add_fine_payment(fine_id: int, castka: float) -> Optional[DriverFine]:
    """Přičte platbu k zaplacené části pokuty (max do výše pokuty)"""
    db = SessionLocal()
    try:
        fine = db.query(DriverFine).filter(DriverFine.id == fine_id).first()
        if fine:
            fine.zaplaceno = min(fine.castka, (fine.zaplaceno or 0) + castka)
            db.commit()
            db.refresh(fine)
        return fine
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def delete_fine(fine_id: int) -> bool:
    """Smaže pokutu"""
    db = SessionLocal()
    try:
        fine = db.query(DriverFine).filter(DriverFine.id == fine_id).first()
        if fine:
            db.delete(fine)
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def get_driver_fines_summary(driver_id: int) -> dict:
    """Souhrnné statistiky pokut řidiče"""
    fines = get_driver_fines(driver_id)
    celkem = sum(f.castka for f in fines)
    zaplaceno = sum(f.zaplaceno or 0 for f in fines)
    return {
        'pocet': len(fines),
        'celkem': celkem,
        'zaplaceno': zaplaceno,
        'zbyvajici': max(0, celkem - zaplaceno),
    }
