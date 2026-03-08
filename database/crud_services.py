"""
CRUD Operations for CarService - Wayne Fleet Management System
Servisní záznamy aut (olej, STK, brzdy, pneumatiky, ...)
"""

from database.models import CarService
from database.database import SessionLocal
from datetime import date
from typing import List, Optional


def get_car_services(car_id: int) -> List[CarService]:
    """Vrátí všechny servisy daného auta, seřazené od nejnovějšího"""
    db = SessionLocal()
    try:
        return (
            db.query(CarService)
            .filter(CarService.car_id == car_id)
            .order_by(CarService.datum.desc())
            .all()
        )
    finally:
        db.close()


def create_service(
    car_id: int,
    datum: date,
    typ: str,
    popis: str = None,
    naklady: float = 0,
    km_pri_servisu: int = None,
    pristi_servis_datum: date = None,
    pristi_servis_km: int = None,
    pristi_servis_popis: str = None,
) -> CarService:
    """Vytvoří nový servisní záznam"""
    db = SessionLocal()
    try:
        service = CarService(
            car_id=car_id,
            datum=datum,
            typ=typ,
            popis=popis,
            naklady=naklady,
            km_pri_servisu=km_pri_servisu,
            pristi_servis_datum=pristi_servis_datum,
            pristi_servis_km=pristi_servis_km,
            pristi_servis_popis=pristi_servis_popis,
        )
        db.add(service)
        db.commit()
        db.refresh(service)
        return service
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def update_service(service_id: int, **kwargs) -> Optional[CarService]:
    """Aktualizuje servisní záznam"""
    db = SessionLocal()
    try:
        service = db.query(CarService).filter(CarService.id == service_id).first()
        if service:
            for key, value in kwargs.items():
                if hasattr(service, key):
                    setattr(service, key, value)
            db.commit()
            db.refresh(service)
        return service
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def delete_service(service_id: int) -> bool:
    """Smaže servisní záznam"""
    db = SessionLocal()
    try:
        service = db.query(CarService).filter(CarService.id == service_id).first()
        if service:
            db.delete(service)
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def get_next_service(car_id: int) -> Optional[dict]:
    """
    Vrátí info o příštím plánovaném servisu z posledního záznamu.
    Returns None pokud žádný záznam neexistuje nebo příští servis není naplánován.
    """
    db = SessionLocal()
    try:
        last = (
            db.query(CarService)
            .filter(
                CarService.car_id == car_id,
                CarService.pristi_servis_datum.isnot(None),
            )
            .order_by(CarService.datum.desc())
            .first()
        )
        if not last:
            return None
        return {
            'datum': last.pristi_servis_datum,
            'km': last.pristi_servis_km,
            'popis': last.pristi_servis_popis,
        }
    finally:
        db.close()


def get_total_service_cost(car_id: int) -> float:
    """Vrátí celkové náklady na servisy daného auta"""
    db = SessionLocal()
    try:
        services = db.query(CarService).filter(CarService.car_id == car_id).all()
        return sum(s.naklady or 0 for s in services)
    finally:
        db.close()
