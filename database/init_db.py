"""
Database Initialization - Wayne Fleet Management System
Initialize database with real data from Uber Fleet Portal
"""

from database.database import init_db, SessionLocal
from database.models import Car, Driver
from datetime import date

def seed_initial_data():
    """Naplnit databázi reálnými daty z Uber"""
    
    print("🚀 Starting database initialization...")
    
    # Initialize database tables
    init_db()
    
    # Create session
    db = SessionLocal()
    
    try:
        # === AUTA ===
        print("\n🚗 Adding cars...")
        
        cars_data = [
            {
                'spz': '4AT 4091',
                'model': 'Škoda Octavia',
                'rok': 2015,
                'vin': 'TMBAM7NE6F0173889',
                'status': 'active',
                'typ_vlastnictvi': 'vlastni',
                'kauce': 10000,
                'splatka_tyden': 5240,
                'celkem_splatek': 53,
                'zaplaceno_splatek': 5,  # Zaplaceno 5 splátek
                'zaplaceno': 10000 + (5 * 5240),  # Kauce + 5 splátek = 36,200
                'cena': 10000 + (53 * 5240),  # Kauce + všechny splátky = 287,720
                'celkem_km': 125450,
                'datum_porizeni': date(2024, 1, 15)
            },
            {
                'spz': '1AB F428',
                'model': 'Škoda Octavia',
                'rok': 2023,
                'vin': 'TMBAG8NX9RY059082',
                'status': 'active',
                'typ_vlastnictvi': 'vlastni',  # Taky vlastní!
                'kauce': 10000,
                'splatka_tyden': 4200,
                'celkem_splatek': 265,  # 265 splátek
                'zaplaceno_splatek': 1,  # Zaplacena první splátka
                'zaplaceno': 10000 + (1 * 4200),  # Kauce + 1 splátka = 14,200
                'cena': 10000 + (265 * 4200),  # Kauce + všechny splátky = 1,123,000
                'celkem_km': 45200,
                'datum_porizeni': date(2023, 6, 1)
            }
        ]
        
        for car_data in cars_data:
            car = Car(**car_data)
            db.add(car)
            print(f"  ✅ {car.spz} - {car.model} ({car.rok})")
        
        # === ŘIDIČI ===
        print("\n👥 Adding drivers...")
        
        drivers_data = [
            {
                'jmeno': 'Pavel Kropac',
                'email': 'waynefleet22@gmail.com',
                'telefon': '+420603472082',
                'status': 'nabor',
                'datum_nastupu': date(2024, 1, 15)
            },
            {
                'jmeno': 'Milos Novy',
                'email': 'milosnovy25@gmail.com',
                'telefon': '+420603472082',
                'status': 'active',
                'datum_nastupu': date(2024, 1, 20)
            },
            {
                'jmeno': 'Jiri Vasylascuk',
                'email': 'jirivasylascuk@gmail.com',
                'telefon': '+420722344699',
                'status': 'active',
                'datum_nastupu': date(2024, 2, 1)
            },
            {
                'jmeno': 'Julius Samo',
                'email': 'Juliussamo@post.cz',
                'telefon': '+420703129164',
                'status': 'active',
                'datum_nastupu': date(2024, 2, 10)
            },
            {
                'jmeno': 'Michal Karvai',
                'email': 'boltmiguelkarvai@gmail.com',
                'telefon': '+420739644040',
                'status': 'active',
                'datum_nastupu': date(2024, 2, 15)
            }
        ]
        
        for driver_data in drivers_data:
            driver = Driver(**driver_data)
            db.add(driver)
            print(f"  ✅ {driver.jmeno} - {driver.email}")
        
        # Commit všechny změny
        db.commit()
        
        print("\n✅ Database initialized successfully!")
        print(f"   - {len(cars_data)} cars added")
        print(f"   - {len(drivers_data)} drivers added")
        
        # Zobrazit statistiky
        car_count = db.query(Car).count()
        driver_count = db.query(Driver).count()
        
        print(f"\n📊 Database stats:")
        print(f"   - Total cars: {car_count}")
        print(f"   - Total drivers: {driver_count}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_initial_data()
