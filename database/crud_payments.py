"""
Payment Operations for Cars - Wayne Fleet Management System
Record payments and update car financing status
"""

from database.models import Car
from database.database import SessionLocal
from datetime import date
from typing import Optional


def zadat_platbu(car_id: int, pocet_splatek: int = 1, datum: date = None) -> Optional[Car]:
    """
    Zadat platbu pro auto
    
    Args:
        car_id: ID auta
        pocet_splatek: Kolik splátek platíš (obvykle 1)
        datum: Datum platby (default dnes)
    
    Returns:
        Aktualizované auto nebo None
    """
    db = SessionLocal()
    try:
        car = db.query(Car).filter(Car.id == car_id).first()
        
        if not car:
            return None
        
        if car.typ_vlastnictvi != 'vlastni':
            raise ValueError("Nelze zadat platbu pro pronájem!")
        
        # Přidat splátky
        car.zaplaceno_splatek += pocet_splatek
        
        # Nemůže být víc než celkem
        if car.zaplaceno_splatek > car.celkem_splatek:
            car.zaplaceno_splatek = car.celkem_splatek
        
        # Přepočítat zaplacenou částku
        car.zaplaceno = car.kauce + (car.zaplaceno_splatek * car.splatka_tyden)
        
        db.commit()
        db.refresh(car)
        
        return car
        
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def get_payment_info(car_id: int) -> dict:
    """Získat info o platbách pro auto"""
    db = SessionLocal()
    try:
        car = db.query(Car).filter(Car.id == car_id).first()
        
        if not car or car.typ_vlastnictvi != 'vlastni':
            return None
        
        zbyvajici_splatek = car.celkem_splatek - car.zaplaceno_splatek
        zbyvajici_castka = zbyvajici_splatek * car.splatka_tyden
        
        return {
            'car': car,
            'zaplaceno_splatek': car.zaplaceno_splatek,
            'celkem_splatek': car.celkem_splatek,
            'zbyvajici_splatek': zbyvajici_splatek,
            'splatka_tyden': car.splatka_tyden,
            'zbyvajici_castka': zbyvajici_castka,
            'celkova_cena': car.cena,
            'zaplaceno_celkem': car.zaplaceno,
            'procento': (car.zaplaceno / car.cena * 100) if car.cena > 0 else 0
        }
    finally:
        db.close()


def je_splaceno(car_id: int) -> bool:
    """Zkontrolovat jestli je auto splacené"""
    db = SessionLocal()
    try:
        car = db.query(Car).filter(Car.id == car_id).first()
        
        if not car or car.typ_vlastnictvi != 'vlastni':
            return False
        
        return car.zaplaceno_splatek >= car.celkem_splatek
    finally:
        db.close()
