"""
Database Models - Wayne Fleet Management System
SQLAlchemy ORM models
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Car(Base):
    """Model pro auta"""
    __tablename__ = 'cars'
    
    id = Column(Integer, primary_key=True)
    spz = Column(String(20), unique=True, nullable=False)
    model = Column(String(100), nullable=False)
    rok = Column(Integer, nullable=False)
    vin = Column(String(50), unique=True)
    barva = Column(String(50))
    
    # Finance
    typ_vlastnictvi = Column(String(20), default='vlastni')  # vlastni, pronajem
    cena = Column(Float, default=0)
    kauce = Column(Float, default=0)  # Kauce při pořízení
    splatka_tyden = Column(Float, default=0)
    splatka_mesic = Column(Float, default=0)
    celkem_splatek = Column(Integer, default=0)  # Celkový počet splátek
    zaplaceno_splatek = Column(Integer, default=0)  # Kolik splátek už zaplaceno
    zaplaceno = Column(Float, default=0)
    datum_porizeni = Column(Date)
    cena_tyden_pronajem = Column(Float, default=0)  # Cena pronájmu pro řidiče (Kč/týden)

    # Expirace
    stk_datum = Column(Date, nullable=True)       # Datum platnosti STK
    pojistka_datum = Column(Date, nullable=True)  # Datum platnosti pojistky

    # Status
    status = Column(String(20), default='active')  # active, service, retired
    celkem_km = Column(Integer, default=0)
    
    # Relationships
    services = relationship("CarService", back_populates="car", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="car", cascade="all, delete-orphan")
    calendar_assignments = relationship("CalendarAssignment", back_populates="car", cascade="all, delete-orphan")
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<Car {self.spz} - {self.model}>"


class Driver(Base):
    """Model pro řidiče"""
    __tablename__ = 'drivers'
    
    id = Column(Integer, primary_key=True)
    jmeno = Column(String(100), nullable=False)
    email = Column(String(100))
    telefon = Column(String(20))
    datum_nastupu = Column(Date)
    datum_ukonceni = Column(Date, nullable=True)   # datum ukončení spolupráce
    status = Column(String(20), default='active')  # active, inactive, archived, nabor

    # Osobní údaje
    adresa = Column(String(255), nullable=True)    # trvalá adresa
    rc = Column(String(20), nullable=True)         # rodné číslo
    cislo_op = Column(String(50), nullable=True)   # číslo občanského průkazu
    datum_narozeni = Column(Date, nullable=True)   # datum narození

    # Nábor checklist
    nabor_smlouva = Column(Boolean, default=False)  # Smlouva podepsána (legacy)
    nabor_op = Column(Boolean, default=False)       # Kopie OP předána
    nabor_ridicak = Column(Boolean, default=False)  # Kopie ŘP předána
    nabor_taxi = Column(Boolean, default=False)     # Taxi licence předána

    # Výchozí auto a kauce
    default_car_id = Column(Integer, ForeignKey('cars.id'), nullable=True)
    kauce_celkem = Column(Float, default=10000)    # celková kauce k zaplacení (Kč)
    kauce_zaplaceno = Column(Float, default=0)     # kolik řidič zaplatil (Kč)

    # Relationships
    default_car = relationship("Car", foreign_keys=[default_car_id])
    invoices = relationship("Invoice", back_populates="driver", cascade="all, delete-orphan")
    calendar_assignments = relationship("CalendarAssignment", back_populates="driver", cascade="all, delete-orphan")
    fines = relationship("DriverFine", back_populates="driver", cascade="all, delete-orphan")
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<Driver {self.jmeno}>"


class CarService(Base):
    """Model pro servisy aut"""
    __tablename__ = 'car_services'
    
    id = Column(Integer, primary_key=True)
    car_id = Column(Integer, ForeignKey('cars.id'), nullable=False)
    datum = Column(Date, nullable=False)
    typ = Column(String(50))  # olej, brzdy, STK, pneumatiky, jiné
    popis = Column(Text)
    naklady = Column(Float, default=0)
    km_pri_servisu = Column(Integer)
    
    # Příští servis
    pristi_servis_datum = Column(Date)
    pristi_servis_km = Column(Integer)
    pristi_servis_popis = Column(Text)
    
    # Relationships
    car = relationship("Car", back_populates="services")
    
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<Service {self.car.spz} - {self.typ} - {self.datum}>"


class Invoice(Base):
    """Model pro vyúčtování"""
    __tablename__ = 'invoices'
    
    id = Column(Integer, primary_key=True)
    driver_id = Column(Integer, ForeignKey('drivers.id'), nullable=False)
    car_id = Column(Integer, ForeignKey('cars.id'), nullable=False)
    
    # Období
    tyden_od = Column(Date, nullable=False)
    tyden_do = Column(Date, nullable=False)
    
    # Částky
    uber_amount = Column(Float, default=0)
    bolt_amount = Column(Float, default=0)
    uber_commission = Column(Float, default=0)
    bolt_commission = Column(Float, default=0)
    total_commission = Column(Float, default=0)
    vat = Column(Float, default=0)
    total_with_vat = Column(Float, default=0)
    
    # Dodatečné náklady
    najem = Column(Float, default=0)
    poplatek_flotila = Column(Float, default=0)
    kauce = Column(Float, default=0)
    palivo = Column(Float, default=0)
    pokuty = Column(Float, default=0)
    
    # Výsledek
    vysledek = Column(Float, default=0)  # kladné = výplata, záporné = doplatek
    
    # Status
    status = Column(String(20), default='nezaplaceno')  # zaplaceno, nezaplaceno
    pdf_path = Column(String(500))
    
    # Relationships
    driver = relationship("Driver", back_populates="invoices")
    car = relationship("Car", back_populates="invoices")
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<Invoice {self.driver.jmeno} - {self.tyden_od}>"


class FinanceRecord(Base):
    """Model pro finanční záznamy – vydané i přijaté faktury/platby"""
    __tablename__ = 'finance_records'

    id = Column(Integer, primary_key=True)

    # Typ záznamu
    typ = Column(String(10), nullable=False)   # 'vydana' | 'prijata'
    kategorie = Column(String(50))             # viz KATEGORIE_* konstanty v finance_page

    # Popis
    popis = Column(String(255), nullable=False)

    # Finance
    castka_kc = Column(Float, nullable=False)

    # Datum
    datum = Column(Date, nullable=False)           # datum vystavení / vzniku
    datum_splatnosti = Column(Date, nullable=True) # kdy je splatná

    # Stav
    status = Column(String(20), default='nezaplaceno')  # nezaplaceno | zaplaceno
    datum_zaplaceni = Column(Date, nullable=True)

    # Vazby (volitelné)
    driver_id = Column(Integer, ForeignKey('drivers.id'), nullable=True)
    car_id = Column(Integer, ForeignKey('cars.id'), nullable=True)

    driver = relationship("Driver", foreign_keys=[driver_id])
    car = relationship("Car", foreign_keys=[car_id])

    # Opakující se platby
    recurring_group_id = Column(String(36), nullable=True)  # UUID skupiny opakování

    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<FinanceRecord {self.typ} {self.popis} {self.castka_kc} Kč>"


class DriverFine(Base):
    """Model pro pokuty řidičů"""
    __tablename__ = 'driver_fines'

    id = Column(Integer, primary_key=True)
    driver_id = Column(Integer, ForeignKey('drivers.id'), nullable=False)
    datum = Column(Date, nullable=False)
    popis = Column(String(255), nullable=False)
    castka = Column(Float, nullable=False)       # celková výše pokuty
    zaplaceno = Column(Float, default=0)         # kolik řidič zaplatil

    driver = relationship("Driver", back_populates="fines")

    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<DriverFine driver_id={self.driver_id} {self.popis} {self.castka} Kč>"


class TodoItem(Base):
    """Model pro úkoly na dashboardu"""
    __tablename__ = 'todo_items'

    id = Column(Integer, primary_key=True)
    text = Column(String(500), nullable=False)
    done = Column(Boolean, default=False)
    priority = Column(String(10), default='medium')  # low | medium | high
    finance_ref_id = Column(Integer, nullable=True)  # vazba na finance_record (pro auto-upomínky)
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<TodoItem {'✓' if self.done else '○'} {self.text[:30]}>"


class BankTransaction(Base):
    """Bankovní transakce stažené z RB Premium API"""
    __tablename__ = 'bank_transactions'

    id = Column(Integer, primary_key=True)
    entry_reference = Column(String(100), unique=True, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default='CZK')
    credit_debit = Column(String(10))          # CRDT = příchozí, DBIT = odchozí
    booking_date = Column(Date)
    counterparty_name = Column(String(255), nullable=True)
    counterparty_account = Column(String(100), nullable=True)
    transaction_info = Column(Text, nullable=True)

    # Párování s vyúčtováním nebo finance record
    matched_finance_id = Column(Integer, ForeignKey('finance_records.id'), nullable=True)
    matched_invoice_id = Column(Integer, ForeignKey('invoices.id'), nullable=True)

    matched_finance = relationship('FinanceRecord', foreign_keys=[matched_finance_id])
    matched_invoice = relationship('Invoice', foreign_keys=[matched_invoice_id])

    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        direction = 'IN' if self.credit_debit == 'CRDT' else 'OUT'
        return f"<BankTxn {direction} {self.amount} {self.currency} {self.booking_date}>"


class CalendarAssignment(Base):
    """Model pro kalendář přiřazení"""
    __tablename__ = 'calendar_assignments'
    
    id = Column(Integer, primary_key=True)
    car_id = Column(Integer, ForeignKey('cars.id'), nullable=False)
    driver_id = Column(Integer, ForeignKey('drivers.id'), nullable=True)
    datum = Column(Date, nullable=False)
    smena_od = Column(String(5), default='06:00')  # Formát: "06:00"
    smena_do = Column(String(5), default='18:00')  # Formát: "18:00"
    status = Column(String(20), default='assigned')  # assigned, free, service, full_day
    poznamka = Column(Text)

    # Typ přiřazení (nový explicitní model)
    typ = Column(String(20), nullable=True)
    # 'ranni' | 'vecerni' | 'cely_den' | 'tydenni' | 'servis'
    datum_do = Column(Date, nullable=True)  # pouze pro typ='tydenni'
    
    # Relationships
    car = relationship("Car", back_populates="calendar_assignments")
    driver = relationship("Driver", back_populates="calendar_assignments")
    
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        shift_info = f"{self.smena_od}-{self.smena_do}" if self.smena_od else ""
        driver_name = self.driver.jmeno if self.driver else 'Free'
        return f"<Assignment {self.car.spz} - {driver_name} - {self.datum} {shift_info}>"
