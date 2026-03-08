# 🚀 Wayne Fleet Management System

Ultra-modern fleet management system s databází!

## 📦 Instalace

```bash
# 1. Nainstaluj závislosti
pip install -r requirements.txt

# 2. Inicializuj databázi s reálnými daty
python -m database.init_db

# 3. Spusť aplikaci
streamlit run wayne_fleet_complete.py
```

## 🗄️ Databázová struktura

### Tabulky:
- **cars** - Auta (SPZ, model, finance, km, status)
- **drivers** - Řidiči (jméno, kontakty, status)
- **car_services** - Servisy aut
- **invoices** - Vyúčtování (Uber + Bolt)
- **calendar_assignments** - Kalendář přiřazení

## 📊 Reálná data (z Uber Fleet Portal):

### 🚗 Auta:
1. **4AT 4091** - Škoda Octavia 2015 (VIN: TMBAM7NE6F0173889)
2. **1AB F428** - Škoda Octavia 2023 (VIN: TMBAG8NX9RY059082)

### 👥 Řidiči:
1. Pavel Kropac - waynefleet22@gmail.com
2. Milos Novy - milosnovy25@gmail.com  
3. Jiri Vasylascuk - jirivasylascuk@gmail.com
4. Julius Samo - Juliussamo@post.cz
5. Michal Karvai - boltmiguelkarvai@gmail.com

## 🎯 CRUD Funkce

### Auta:
```python
from database.crud_cars import *

# Získat všechna auta
cars = get_all_cars()

# Vytvořit auto
car = create_car(
    spz="4AT 4091",
    model="Škoda Octavia",
    rok=2015
)

# Aktualizovat
update_car(car.id, celkem_km=130000)

# Statistiky
stats = get_car_stats(car.id)
```

### Řidiči:
```python
from database.crud_drivers import *

# Získat všechny řidiče
drivers = get_all_drivers()

# Najít podle jména
driver = find_driver_by_name("Milos Novy")

# Vytvořit
driver = create_driver(
    jmeno="Jan Novak",
    email="jan@example.com"
)
```

## 🔄 Next Steps:

1. ✅ Database setup - HOTOVO
2. ✅ CRUD funkce - HOTOVO
3. 🔜 Propojit s UI
4. 🔜 CSV import
5. 🔜 PDF vyúčtování integrace

## 📁 Struktura:

```
wayne-fleet/
├── database/
│   ├── __init__.py
│   ├── models.py           # SQLAlchemy modely
│   ├── database.py         # DB connection
│   ├── init_db.py          # Inicializace + data
│   ├── crud_cars.py        # CRUD pro auta
│   └── crud_drivers.py     # CRUD pro řidiče
├── wayne_fleet_complete.py # Streamlit UI
└── requirements.txt
```

## 🎨 Features:

- ✅ SQLite databáze (lokální, žádný server)
- ✅ SQLAlchemy ORM
- ✅ Reálná data z Uber
- ✅ CRUD operations
- ✅ Premium UI design
- 🔜 CSV import
- 🔜 PDF generování
- 🔜 Kalendář
- 🔜 Statistiky

---

**Made with ❤️ for Wayne Fleet**
