"""
CRUD Operations for Cars - Wayne Fleet Management System
Create, Read, Update, Delete operations for cars
"""

from database.models import Car, Driver
from database.database import SessionLocal
from datetime import date
from typing import List, Optional


def get_all_cars() -> List[Car]:
    """Získat všechna auta"""
    db = SessionLocal()
    try:
        return db.query(Car).all()
    finally:
        db.close()


def get_car_by_id(car_id: int) -> Optional[Car]:
    """Získat auto podle ID"""
    db = SessionLocal()
    try:
        return db.query(Car).filter(Car.id == car_id).first()
    finally:
        db.close()


def get_car_by_spz(spz: str) -> Optional[Car]:
    """Získat auto podle SPZ"""
    db = SessionLocal()
    try:
        return db.query(Car).filter(Car.spz == spz).first()
    finally:
        db.close()


def get_active_cars() -> List[Car]:
    """Získat pouze aktivní auta"""
    db = SessionLocal()
    try:
        return db.query(Car).filter(Car.status == 'active').all()
    finally:
        db.close()


def create_car(
    spz: str,
    model: str,
    rok: int,
    vin: str = None,
    barva: str = None,
    typ_vlastnictvi: str = 'vlastni',
    kauce: float = 0,
    cena: float = 0,
    splatka_tyden: float = 0,
    splatka_mesic: float = 0,
    celkem_splatek: int = 0,
    zaplaceno_splatek: int = 0,
    datum_porizeni: date = None
) -> Car:
    """Vytvořit nové auto"""
    db = SessionLocal()
    try:
        car = Car(
            spz=spz,
            model=model,
            rok=rok,
            vin=vin,
            barva=barva,
            typ_vlastnictvi=typ_vlastnictvi,
            kauce=kauce,
            cena=cena,
            splatka_tyden=splatka_tyden,
            splatka_mesic=splatka_mesic,
            celkem_splatek=celkem_splatek,
            zaplaceno_splatek=zaplaceno_splatek,
            zaplaceno=kauce + (zaplaceno_splatek * splatka_tyden),
            datum_porizeni=datum_porizeni or date.today(),
            status='active'
        )
        db.add(car)
        db.commit()
        db.refresh(car)
        return car
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def update_car(car_id: int, **kwargs) -> Optional[Car]:
    """Aktualizovat auto"""
    db = SessionLocal()
    try:
        car = db.query(Car).filter(Car.id == car_id).first()
        if car:
            for key, value in kwargs.items():
                if hasattr(car, key):
                    setattr(car, key, value)
            db.commit()
            db.refresh(car)
        return car
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def delete_car(car_id: int) -> bool:
    """Smazat auto (soft delete - změnit status na retired)"""
    db = SessionLocal()
    try:
        car = db.query(Car).filter(Car.id == car_id).first()
        if car:
            car.status = 'retired'
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def update_car_km(car_id: int, km: int) -> Optional[Car]:
    """Aktualizovat kilometry"""
    return update_car(car_id, celkem_km=km)


def update_car_payment(car_id: int, zaplaceno: float) -> Optional[Car]:
    """Aktualizovat zaplacenou částku"""
    return update_car(car_id, zaplaceno=zaplaceno)


def set_car_status(car_id: int, status: str) -> Optional[Car]:
    """Změnit status auta (active, service, retired)"""
    return update_car(car_id, status=status)


def get_car_stats(car_id: int) -> dict:
    """Získat statistiky auta"""
    db = SessionLocal()
    try:
        car = db.query(Car).filter(Car.id == car_id).first()
        if not car:
            return None
        
        # Výpočet podle typu vlastnictví
        if car.typ_vlastnictvi == 'vlastni':
            # Auto na splátky
            celkova_cena = car.cena if car.cena > 0 else (car.kauce + (car.celkem_splatek * car.splatka_tyden))
            zaplaceno = car.zaplaceno if car.zaplaceno > 0 else (car.kauce + (car.zaplaceno_splatek * car.splatka_tyden))
            zbyvajici = celkova_cena - zaplaceno
            procento_splaceno = (zaplaceno / celkova_cena * 100) if celkova_cena > 0 else 0
            zbyvajici_splatek = car.celkem_splatek - car.zaplaceno_splatek
        else:
            # Pronájem
            celkova_cena = 0
            zaplaceno = 0
            zbyvajici = 0
            procento_splaceno = 0
            zbyvajici_splatek = 0
        
        # Celkový výdělek (z invoices) - TODO: implementovat po vytvoření invoices CRUD
        celkovy_vydelek = 0
        
        # ROI
        roi = (celkovy_vydelek / celkova_cena * 100) if celkova_cena > 0 else 0
        
        return {
            'car': car,
            'celkova_cena': celkova_cena,
            'zaplaceno': zaplaceno,
            'zbyvajici_splatka': zbyvajici,
            'procento_splaceno': procento_splaceno,
            'zbyvajici_splatek': zbyvajici_splatek,
            'celkovy_vydelek': celkovy_vydelek,
            'roi': roi
        }
    finally:
        db.close()
