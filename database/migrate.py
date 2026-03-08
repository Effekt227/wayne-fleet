"""
Migrace databáze - Wayne Fleet Management System
Přidá sloupce do calendar_assignments a drivers.

Spuštění: python -m database.migrate
"""

import sqlite3
import os


DB_PATH = os.path.join(os.path.dirname(__file__), 'wayne_fleet.db')


def run_migration():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Spouštím migraci databáze...")

    # 1. Zkontrolovat a přidat sloupce (idempotentní)
    existing_columns = [
        row[1] for row in cursor.execute("PRAGMA table_info(calendar_assignments)").fetchall()
    ]

    if 'typ' not in existing_columns:
        cursor.execute("ALTER TABLE calendar_assignments ADD COLUMN typ VARCHAR(20)")
        print("  Přidán sloupec: typ")
    else:
        print("  Sloupec 'typ' již existuje, přeskakuji")

    if 'datum_do' not in existing_columns:
        cursor.execute("ALTER TABLE calendar_assignments ADD COLUMN datum_do DATE")
        print("  Přidán sloupec: datum_do")
    else:
        print("  Sloupec 'datum_do' již existuje, přeskakuji")

    # 2. Backfill - naplnit 'typ' z existujících dat
    rows = cursor.execute(
        "SELECT id, smena_od, status FROM calendar_assignments WHERE typ IS NULL"
    ).fetchall()

    print(f"\nBackfill: zpracovávám {len(rows)} záznamů...")

    updated = 0
    for row_id, smena_od, status in rows:
        if status == 'service':
            new_typ = 'servis'
        elif status == 'full_day':
            new_typ = 'cely_den'
        elif smena_od and smena_od < '12:00':
            new_typ = 'ranni'
        elif smena_od and smena_od >= '12:00':
            new_typ = 'vecerni'
        else:
            new_typ = 'ranni'

        cursor.execute(
            "UPDATE calendar_assignments SET typ = ? WHERE id = ?",
            (new_typ, row_id)
        )
        updated += 1

    conn.commit()
    print(f"  Aktualizováno {updated} záznamů")

    # 3. Statistiky
    stats = cursor.execute(
        "SELECT typ, COUNT(*) FROM calendar_assignments GROUP BY typ"
    ).fetchall()
    print("\nRozdělení typů po migraci:")
    for typ, count in stats:
        print(f"  {typ}: {count} záznamů")

    # ── Tabulka drivers ──────────────────────────────────────────────
    print("\nMigrace tabulky drivers...")
    existing_driver_columns = [
        row[1] for row in cursor.execute("PRAGMA table_info(drivers)").fetchall()
    ]

    for col, definition in [
        ('default_car_id',  'INTEGER REFERENCES cars(id)'),
        ('kauce_celkem',    'REAL DEFAULT 10000'),
        ('kauce_zaplaceno', 'REAL DEFAULT 0'),
        ('datum_ukonceni',  'DATE'),
        ('adresa',          'VARCHAR(255)'),
        ('rc',              'VARCHAR(20)'),
        ('cislo_op',        'VARCHAR(50)'),
        ('datum_narozeni',  'DATE'),
        ('nabor_smlouva',   'BOOLEAN DEFAULT 0'),
        ('nabor_op',        'BOOLEAN DEFAULT 0'),
        ('nabor_ridicak',   'BOOLEAN DEFAULT 0'),
        ('nabor_taxi',      'BOOLEAN DEFAULT 0'),
    ]:
        if col not in existing_driver_columns:
            cursor.execute(f"ALTER TABLE drivers ADD COLUMN {col} {definition}")
            print(f"  Přidán sloupec: {col}")
        else:
            print(f"  Sloupec '{col}' již existuje, přeskakuji")

    conn.commit()

    # ── Tabulka cars ─────────────────────────────────────────────────────────
    print("\nMigrace tabulky cars...")
    existing_car_columns = [
        row[1] for row in cursor.execute("PRAGMA table_info(cars)").fetchall()
    ]
    for col, definition in [
        ('cena_tyden_pronajem', 'REAL DEFAULT 0'),
        ('stk_datum',           'DATE'),
        ('pojistka_datum',      'DATE'),
    ]:
        if col not in existing_car_columns:
            cursor.execute(f"ALTER TABLE cars ADD COLUMN {col} {definition}")
            print(f"  Přidán sloupec: {col}")
        else:
            print(f"  Sloupec '{col}' již existuje, přeskakuji")
    conn.commit()

    # ── Tabulka finance_records ──────────────────────────────────────
    print("\nMigrace tabulky finance_records...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS finance_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            typ VARCHAR(10) NOT NULL,
            kategorie VARCHAR(50),
            popis VARCHAR(255) NOT NULL,
            castka_kc REAL NOT NULL,
            datum DATE NOT NULL,
            datum_splatnosti DATE,
            status VARCHAR(20) DEFAULT 'nezaplaceno',
            datum_zaplaceni DATE,
            driver_id INTEGER REFERENCES drivers(id),
            car_id INTEGER REFERENCES cars(id),
            recurring_group_id VARCHAR(36),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Přidat recurring_group_id ke stávající tabulce pokud chybí
    existing_fr_cols = [row[1] for row in cursor.execute("PRAGMA table_info(finance_records)").fetchall()]
    if 'recurring_group_id' not in existing_fr_cols:
        cursor.execute("ALTER TABLE finance_records ADD COLUMN recurring_group_id VARCHAR(36)")
        print("  Přidán sloupec: recurring_group_id")
    print("  Tabulka finance_records OK")

    conn.commit()

    # ── Tabulka driver_fines ─────────────────────────────────────────
    print("\nMigrace tabulky driver_fines...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS driver_fines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_id INTEGER NOT NULL REFERENCES drivers(id),
            datum DATE NOT NULL,
            popis VARCHAR(255) NOT NULL,
            castka REAL NOT NULL,
            zaplaceno REAL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  Tabulka driver_fines OK")

    # ── Tabulka todo_items ───────────────────────────────────────────
    print("\nMigrace tabulky todo_items...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS todo_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text VARCHAR(500) NOT NULL,
            done BOOLEAN DEFAULT 0,
            priority VARCHAR(10) DEFAULT 'medium',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  Tabulka todo_items OK")
    # Přidat finance_ref_id pokud chybí
    existing_todo_cols = [row[1] for row in cursor.execute("PRAGMA table_info(todo_items)").fetchall()]
    if 'finance_ref_id' not in existing_todo_cols:
        cursor.execute("ALTER TABLE todo_items ADD COLUMN finance_ref_id INTEGER")
        print("  Přidán sloupec: finance_ref_id")

    conn.commit()
    conn.close()
    print("\nMigrace dokončena.")


if __name__ == "__main__":
    run_migration()
