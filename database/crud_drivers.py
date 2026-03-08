"""
CRUD Operations for Drivers - Wayne Fleet Management System
Create, Read, Update, Delete operations for drivers
"""

from database.models import Driver, Car
from database.database import SessionLocal
from datetime import date
from typing import List, Optional


def get_all_drivers() -> List[Driver]:
    """Získat všechny řidiče"""
    db = SessionLocal()
    try:
        return db.query(Driver).all()
    finally:
        db.close()


def get_driver_by_id(driver_id: int) -> Optional[Driver]:
    """Získat řidiče podle ID"""
    db = SessionLocal()
    try:
        return db.query(Driver).filter(Driver.id == driver_id).first()
    finally:
        db.close()


def get_active_drivers() -> List[Driver]:
    """Získat pouze aktivní řidiče"""
    db = SessionLocal()
    try:
        return db.query(Driver).filter(Driver.status == 'active').all()
    finally:
        db.close()


def create_driver(
    jmeno: str,
    email: str = None,
    telefon: str = None,
    datum_nastupu: date = None
) -> Driver:
    """Vytvořit nového řidiče"""
    db = SessionLocal()
    try:
        driver = Driver(
            jmeno=jmeno,
            email=email,
            telefon=telefon,
            datum_nastupu=datum_nastupu or date.today(),
            status='active'
        )
        db.add(driver)
        db.commit()
        db.refresh(driver)
        return driver
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def update_driver(driver_id: int, **kwargs) -> Optional[Driver]:
    """Aktualizovat řidiče"""
    db = SessionLocal()
    try:
        driver = db.query(Driver).filter(Driver.id == driver_id).first()
        if driver:
            for key, value in kwargs.items():
                if hasattr(driver, key):
                    setattr(driver, key, value)
            db.commit()
            db.refresh(driver)
        return driver
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def delete_driver(driver_id: int) -> bool:
    """Smazat řidiče (soft delete - změnit status na archived)"""
    db = SessionLocal()
    try:
        driver = db.query(Driver).filter(Driver.id == driver_id).first()
        if driver:
            driver.status = 'archived'
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def find_driver_by_name(name: str) -> Optional[Driver]:
    """Najít řidiče podle jména (normalizované)"""
    import unicodedata
    
    def normalize_name(text):
        """Normalizovat jméno pro matching"""
        text = unicodedata.normalize('NFD', text)
        text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
        return text.lower().replace(' ', '').strip()
    
    db = SessionLocal()
    try:
        normalized_search = normalize_name(name)
        
        # Získat všechny řidiče
        all_drivers = db.query(Driver).all()
        
        # Najít matching
        for driver in all_drivers:
            if normalize_name(driver.jmeno) == normalized_search:
                return driver
        
        return None
    finally:
        db.close()


def get_driver_stats(driver_id: int) -> dict:
    """Získat statistiky řidiče včetně kauce"""
    db = SessionLocal()
    try:
        driver = db.query(Driver).filter(Driver.id == driver_id).first()
        if not driver:
            return None

        kauce_celkem = driver.kauce_celkem or 0
        kauce_zaplaceno = driver.kauce_zaplaceno or 0
        kauce_zbyvajici = max(0, kauce_celkem - kauce_zaplaceno)
        kauce_procento = (kauce_zaplaceno / kauce_celkem * 100) if kauce_celkem > 0 else 0

        return {
            'driver': driver,
            'kauce_celkem': kauce_celkem,
            'kauce_zaplaceno': kauce_zaplaceno,
            'kauce_zbyvajici': kauce_zbyvajici,
            'kauce_procento': kauce_procento,
            'celkovy_vydelek': 0,  # TODO po implementaci invoices CRUD
        }
    finally:
        db.close()


def set_default_car(driver_id: int, car_id: Optional[int]) -> Optional[Driver]:
    """Nastaví výchozí auto řidiče (None = žádné auto)"""
    return update_driver(driver_id, default_car_id=car_id)


def add_kauce_payment(driver_id: int, castka: float) -> Optional[Driver]:
    """Přičte splátku kauce k zaplacené částce"""
    db = SessionLocal()
    try:
        driver = db.query(Driver).filter(Driver.id == driver_id).first()
        if driver:
            driver.kauce_zaplaceno = (driver.kauce_zaplaceno or 0) + castka
            db.commit()
            db.refresh(driver)
        return driver
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
