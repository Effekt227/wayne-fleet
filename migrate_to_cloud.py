"""
Migrace dat ze SQLite → Supabase PostgreSQL
Spustit JEDNOU lokálně po nastavení Supabase:

  python migrate_to_cloud.py

Před spuštěním nastav proměnnou prostředí DATABASE_URL:
  set DATABASE_URL=postgresql://postgres.xxx:heslo@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
"""

import os
import sys

CLOUD_URL = os.environ.get('DATABASE_URL', '')
if not CLOUD_URL:
    print("❌ Chybí proměnná DATABASE_URL")
    print("   Nastav ji: set DATABASE_URL=postgresql://...")
    sys.exit(1)

if CLOUD_URL.startswith('postgres://'):
    CLOUD_URL = CLOUD_URL.replace('postgres://', 'postgresql://', 1)

print(f"🔗 Zdroj: SQLite (wayne_fleet.db)")
print(f"🔗 Cíl:   PostgreSQL (Supabase)")
print()

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Lokální SQLite
LOCAL_DB = os.path.join(os.path.dirname(__file__), 'database', 'wayne_fleet.db')
local_engine = create_engine(f'sqlite:///{LOCAL_DB}', connect_args={'check_same_thread': False})
LocalSession = sessionmaker(bind=local_engine)

# Cloud PostgreSQL
cloud_engine = create_engine(CLOUD_URL)
CloudSession = sessionmaker(bind=cloud_engine)

# Vytvoř tabulky v cloudu
from database.models import Base
print("📦 Vytvářím tabulky v Supabase...")
Base.metadata.create_all(bind=cloud_engine)
print("✅ Tabulky vytvořeny")
print()

# Načti všechny modely
from database.models import (
    Car, Driver, CarService, Invoice, FinanceRecord,
    DriverFine, TodoItem, BankTransaction, CalendarAssignment
)

def migrate_table(model, label):
    with LocalSession() as local_db:
        rows = local_db.query(model).all()
        count = len(rows)
        if count == 0:
            print(f"  ⬜ {label}: prázdná tabulka, přeskočeno")
            return

        # Detach objekty ze SQLite session
        local_db.expunge_all()

        with CloudSession() as cloud_db:
            # Smaž existující záznamy v cloudu pro čistou migraci
            cloud_db.query(model).delete()
            cloud_db.commit()

            for row in rows:
                # Vytvoř nový objekt pro cloud session
                local_db.add(row)
            local_db.expunge_all()

            # Použij INSERT přes bulk_insert_mappings
            from sqlalchemy import inspect
            mapper = inspect(model)
            data = []
            with LocalSession() as fresh_local:
                fresh_rows = fresh_local.query(model).all()
                for row in fresh_rows:
                    d = {}
                    for col in mapper.columns:
                        d[col.key] = getattr(row, col.key)
                    data.append(d)

            if data:
                cloud_db.bulk_insert_mappings(mapper, data)
                cloud_db.commit()

        print(f"  ✅ {label}: {count} záznamů přeneseno")

print("📤 Přenáším data...")
migrate_table(Car, "Auta")
migrate_table(Driver, "Řidiči")
migrate_table(CarService, "Servisní záznamy")
migrate_table(FinanceRecord, "Finance záznamy")
migrate_table(DriverFine, "Pokuty řidičů")
migrate_table(TodoItem, "Todo úkoly")
migrate_table(Invoice, "Vyúčtování")
migrate_table(CalendarAssignment, "Kalendář")
migrate_table(BankTransaction, "Bankovní transakce")

print()
print("🎉 Migrace dokončena! Wayne Fleet data jsou nyní v Supabase.")
