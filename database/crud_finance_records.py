"""
CRUD Operations for FinanceRecord - Wayne Fleet Management System
Vydané faktury + Přijaté faktury/platby, včetně opakujících se
"""

import uuid
import calendar as cal_module
from database.models import FinanceRecord
from database.database import SessionLocal
from datetime import date, timedelta
from typing import List, Optional, Dict


def get_records(
    typ: str = None,
    car_id: int = None,
    driver_id: int = None,
    rok: int = None,
    mesic: int = None,
    status: str = None,
    by_splatnost: bool = False,
) -> List[FinanceRecord]:
    """Vrátí záznamy s filtry. Seřazené dle data."""
    db = SessionLocal()
    try:
        q = db.query(FinanceRecord)
        if typ:
            q = q.filter(FinanceRecord.typ == typ)
        if car_id:
            q = q.filter(FinanceRecord.car_id == car_id)
        if driver_id:
            q = q.filter(FinanceRecord.driver_id == driver_id)
        if status:
            q = q.filter(FinanceRecord.status == status)
        if rok and mesic:
            mesic_od = date(rok, mesic, 1)
            last_day = cal_module.monthrange(rok, mesic)[1]
            mesic_do = date(rok, mesic, last_day)
            date_col = FinanceRecord.datum_splatnosti if by_splatnost else FinanceRecord.datum
            q = q.filter(date_col >= mesic_od, date_col <= mesic_do)
        order_col = FinanceRecord.datum_splatnosti if by_splatnost else FinanceRecord.datum
        return q.order_by(order_col.desc()).all()
    finally:
        db.close()


def get_records_for_month(rok: int, mesic: int) -> List[FinanceRecord]:
    """Všechny záznamy kde datum_splatnosti padá do daného měsíce."""
    db = SessionLocal()
    try:
        mesic_od = date(rok, mesic, 1)
        last_day = cal_module.monthrange(rok, mesic)[1]
        mesic_do = date(rok, mesic, last_day)
        return (
            db.query(FinanceRecord)
            .filter(
                FinanceRecord.datum_splatnosti >= mesic_od,
                FinanceRecord.datum_splatnosti <= mesic_do,
            )
            .order_by(FinanceRecord.datum_splatnosti.asc())
            .all()
        )
    finally:
        db.close()


def get_records_by_date(d: date) -> List[FinanceRecord]:
    """Záznamy splatné v konkrétní den."""
    db = SessionLocal()
    try:
        return (
            db.query(FinanceRecord)
            .filter(FinanceRecord.datum_splatnosti == d)
            .order_by(FinanceRecord.typ.asc())
            .all()
        )
    finally:
        db.close()


def create_record(
    typ: str,
    popis: str,
    castka_kc: float,
    datum: date,
    kategorie: str = None,
    datum_splatnosti: date = None,
    driver_id: int = None,
    car_id: int = None,
    recurring_group_id: str = None,
) -> FinanceRecord:
    db = SessionLocal()
    try:
        r = FinanceRecord(
            typ=typ,
            popis=popis,
            castka_kc=castka_kc,
            datum=datum,
            kategorie=kategorie,
            datum_splatnosti=datum_splatnosti or datum,
            status='nezaplaceno',
            driver_id=driver_id,
            car_id=car_id,
            recurring_group_id=recurring_group_id,
        )
        db.add(r)
        db.commit()
        db.refresh(r)
        return r
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def create_recurring_records(
    typ: str,
    popis: str,
    castka_kc: float,
    kategorie: str,
    datum_od: date,
    datum_do: date,
    interval: str,          # 'tydne' | 'mesicne'
    interval_hodnota: int = 1,
    driver_id: int = None,
    car_id: int = None,
) -> List[FinanceRecord]:
    """
    Vygeneruje opakující se záznamy a vrátí seznam.
    Všechny záznamy sdílejí stejný recurring_group_id.
    """
    group_id = str(uuid.uuid4())
    created = []
    current = datum_od

    while current <= datum_do:
        r = create_record(
            typ=typ,
            popis=popis,
            castka_kc=castka_kc,
            datum=current,
            datum_splatnosti=current,
            kategorie=kategorie,
            driver_id=driver_id,
            car_id=car_id,
            recurring_group_id=group_id,
        )
        created.append(r)

        if interval == 'tydne':
            current += timedelta(weeks=interval_hodnota)
        elif interval == 'mesicne':
            m = current.month + interval_hodnota
            y = current.year + (m - 1) // 12
            m = (m - 1) % 12 + 1
            last = cal_module.monthrange(y, m)[1]
            current = date(y, m, min(current.day, last))

    return created


def delete_recurring_from(group_id: str, from_date: date = None) -> int:
    """Smaže záznamy ze skupiny. Pokud from_date, smaže jen od tohoto data dále."""
    db = SessionLocal()
    try:
        q = db.query(FinanceRecord).filter(FinanceRecord.recurring_group_id == group_id)
        if from_date:
            q = q.filter(FinanceRecord.datum_splatnosti >= from_date)
        rows = q.all()
        count = len(rows)
        for r in rows:
            db.delete(r)
        db.commit()
        return count
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def mark_paid(record_id: int, datum_zaplaceni: date = None) -> Optional[FinanceRecord]:
    db = SessionLocal()
    try:
        r = db.query(FinanceRecord).filter(FinanceRecord.id == record_id).first()
        if r:
            r.status = 'zaplaceno'
            r.datum_zaplaceni = datum_zaplaceni or date.today()
            db.commit()
            db.refresh(r)
        return r
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def mark_unpaid(record_id: int) -> Optional[FinanceRecord]:
    db = SessionLocal()
    try:
        r = db.query(FinanceRecord).filter(FinanceRecord.id == record_id).first()
        if r:
            r.status = 'nezaplaceno'
            r.datum_zaplaceni = None
            db.commit()
            db.refresh(r)
        return r
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def delete_record(record_id: int) -> bool:
    db = SessionLocal()
    try:
        r = db.query(FinanceRecord).filter(FinanceRecord.id == record_id).first()
        if r:
            db.delete(r)
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def get_monthly_summary(rok: int, mesic: int) -> dict:
    records = get_records_for_month(rok, mesic)
    vydane = [r for r in records if r.typ == 'vydana']
    prijate = [r for r in records if r.typ == 'prijata']

    vydano_celkem = sum(r.castka_kc for r in vydane)
    prijato_celkem = sum(r.castka_kc for r in prijate)
    vydano_zaplaceno = sum(r.castka_kc for r in vydane if r.status == 'zaplaceno')
    prijato_zaplaceno = sum(r.castka_kc for r in prijate if r.status == 'zaplaceno')

    return {
        'vydano_celkem': vydano_celkem,
        'prijato_celkem': prijato_celkem,
        'vydano_zaplaceno': vydano_zaplaceno,
        'prijato_zaplaceno': prijato_zaplaceno,
        'vydano_nezaplaceno': vydano_celkem - vydano_zaplaceno,
        'prijato_nezaplaceno': prijato_celkem - prijato_zaplaceno,
        'bilance': vydano_zaplaceno - prijato_zaplaceno,
    }


def get_monthly_chart_data(months_back: int = 3, months_forward: int = 9) -> list:
    """
    Vrátí měsíční souhrny od months_back měsíců zpět do months_forward dopředu.
    Label ve formátu 'YYYY-MM' pro správné abecední (= chronologické) řazení.
    """
    today = date.today()
    total = months_back + 1 + months_forward

    curr_year = today.year
    curr_month = today.month - months_back
    while curr_month <= 0:
        curr_month += 12
        curr_year -= 1

    result = []
    for _ in range(total):
        summary = get_monthly_summary(curr_year, curr_month)
        summary['rok'] = curr_year
        summary['mesic'] = curr_month
        summary['label'] = f"{curr_year}-{curr_month:02d}"   # sortable
        result.append(summary)
        curr_month += 1
        if curr_month > 12:
            curr_month = 1
            curr_year += 1
    return result


def get_monthly_chart_data_range(from_rok: int, from_mesic: int, to_rok: int, to_mesic: int) -> list:
    """Vrátí měsíční souhrny pro explicitní rozsah (max 60 měsíců)."""
    result = []
    curr_year, curr_month = from_rok, from_mesic
    count = 0
    while (curr_year, curr_month) <= (to_rok, to_mesic) and count < 60:
        summary = get_monthly_summary(curr_year, curr_month)
        summary['rok'] = curr_year
        summary['mesic'] = curr_month
        summary['label'] = f"{curr_year}-{curr_month:02d}"
        result.append(summary)
        curr_month += 1
        if curr_month > 12:
            curr_month = 1
            curr_year += 1
        count += 1
    return result


def get_pending_records() -> dict:
    db = SessionLocal()
    try:
        nezaplacene = (
            db.query(FinanceRecord)
            .filter(FinanceRecord.status == 'nezaplaceno')
            .order_by(FinanceRecord.datum_splatnosti.asc())
            .all()
        )
        return {
            'vydane': [r for r in nezaplacene if r.typ == 'vydana'],
            'prijate': [r for r in nezaplacene if r.typ == 'prijata'],
        }
    finally:
        db.close()
