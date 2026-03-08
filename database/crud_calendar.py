"""
CRUD Operations for Calendar - Wayne Fleet Management System
Manage shift assignments for cars and drivers.

Typy směn (pole 'typ'):
  'ranni'    - ranní směna 06:00-18:00
  'vecerni'  - večerní směna 18:00-06:00
  'cely_den' - celý den 06:00-06:00 (blokuje ranní i večerní)
  'tydenni'  - týdenní pronájem Po-Ne (datum + datum_do)
  'servis'   - auto v servisu (blokuje vše)
"""

from database.models import CalendarAssignment, Car, Driver
from database.database import SessionLocal
from datetime import date, timedelta
from typing import List, Optional
from sqlalchemy.orm import joinedload

# Časy derivované z typu směny
TYP_TIMES = {
    'ranni':    ('07:00', '19:00'),
    'vecerni':  ('19:00', '07:00'),
    'cely_den': ('07:00', '07:00'),
    'tydenni':  ('00:00', '23:59'),
    'servis':   ('00:00', '23:59'),
}


def _times_from_typ(typ: str) -> tuple:
    """Vrátí (smena_od, smena_do) pro daný typ"""
    return TYP_TIMES.get(typ, ('06:00', '18:00'))


def _shift_to_dict(assignment: CalendarAssignment) -> dict:
    """Konverze CalendarAssignment na dict (bezpečné po zavření session)"""
    return {
        'id': assignment.id,
        'car_id': assignment.car_id,
        'driver_id': assignment.driver_id,
        'driver_name': assignment.driver.jmeno if assignment.driver else None,
        'datum': assignment.datum,
        'datum_do': assignment.datum_do,
        'smena_od': assignment.smena_od,
        'smena_do': assignment.smena_do,
        'status': assignment.status,
        'typ': assignment.typ,
        'poznamka': assignment.poznamka,
    }


# ==================== NOVÉ FUNKCE ====================

def get_week_assignments(week_start: date) -> dict:
    """
    Získat všechna přiřazení pro týden s eager loading.
    Zahrnuje i týdenní pronájmy (typ='tydenni') pokrývající daný týden.

    Returns:
        dict: {car_id: {datum: [shift_dict, ...]}}
        Speciální klíč pro týdenní pronájmy: car_data['__weekly__'] = [shift_dict]
    """
    db = SessionLocal()
    try:
        week_end = week_start + timedelta(days=6)

        # Normální záznamy v daném týdnu (vše mimo tydenni)
        normal_assignments = db.query(CalendarAssignment).options(
            joinedload(CalendarAssignment.driver),
            joinedload(CalendarAssignment.car)
        ).filter(
            CalendarAssignment.datum >= week_start,
            CalendarAssignment.datum <= week_end,
            CalendarAssignment.typ != 'tydenni'
        ).all()

        # Týdenní pronájmy překrývající daný týden
        weekly_rentals = db.query(CalendarAssignment).options(
            joinedload(CalendarAssignment.driver),
            joinedload(CalendarAssignment.car)
        ).filter(
            CalendarAssignment.typ == 'tydenni',
            CalendarAssignment.datum <= week_end,
            CalendarAssignment.datum_do >= week_start
        ).all()

        result = {}

        for assignment in normal_assignments:
            car_id = assignment.car_id
            if car_id not in result:
                result[car_id] = {}
            if assignment.datum not in result[car_id]:
                result[car_id][assignment.datum] = []
            result[car_id][assignment.datum].append(_shift_to_dict(assignment))

        for rental in weekly_rentals:
            car_id = rental.car_id
            if car_id not in result:
                result[car_id] = {}
            if '__weekly__' not in result[car_id]:
                result[car_id]['__weekly__'] = []
            result[car_id]['__weekly__'].append(_shift_to_dict(rental))

        return result
    finally:
        db.close()


def create_or_update_shift(
    car_id: int,
    datum: date,
    typ: str,
    driver_id: Optional[int] = None,
    poznamka: str = None
) -> CalendarAssignment:
    """
    Inteligentní upsert směny pro auto v daný den.

    Byznys pravidla:
    - 'cely_den' / 'servis' → smaže existující ranni+vecerni, vytvoří jeden záznam
    - 'ranni' / 'vecerni' → pokud existuje cely_den/servis, smaže je; pak upsert daného typu
    """
    smena_od, smena_do = _times_from_typ(typ)
    status_map = {
        'ranni': 'assigned' if driver_id else 'free',
        'vecerni': 'assigned' if driver_id else 'free',
        'cely_den': 'full_day',
        'servis': 'service',
        'tydenni': 'assigned',
    }

    db = SessionLocal()
    try:
        existing = db.query(CalendarAssignment).filter(
            CalendarAssignment.car_id == car_id,
            CalendarAssignment.datum == datum,
            CalendarAssignment.typ != 'tydenni'
        ).all()

        if typ in ('cely_den', 'servis'):
            # Smazat vše pro daný den a vytvořit nový záznam
            for e in existing:
                db.delete(e)

            new_shift = CalendarAssignment(
                car_id=car_id,
                driver_id=driver_id,
                datum=datum,
                smena_od=smena_od,
                smena_do=smena_do,
                status=status_map.get(typ, 'assigned'),
                typ=typ,
                poznamka=poznamka
            )
            db.add(new_shift)

        elif typ in ('ranni', 'vecerni'):
            # Smazat cely_den nebo servis pokud existuje
            for e in existing:
                if e.typ in ('cely_den', 'servis'):
                    db.delete(e)
            db.flush()

            # Hledat existující záznam stejného typu
            existing_same = db.query(CalendarAssignment).filter(
                CalendarAssignment.car_id == car_id,
                CalendarAssignment.datum == datum,
                CalendarAssignment.typ == typ
            ).first()

            if existing_same:
                existing_same.driver_id = driver_id
                existing_same.smena_od = smena_od
                existing_same.smena_do = smena_do
                existing_same.status = status_map.get(typ, 'assigned')
                existing_same.poznamka = poznamka
                new_shift = existing_same
            else:
                new_shift = CalendarAssignment(
                    car_id=car_id,
                    driver_id=driver_id,
                    datum=datum,
                    smena_od=smena_od,
                    smena_do=smena_do,
                    status=status_map.get(typ, 'assigned'),
                    typ=typ,
                    poznamka=poznamka
                )
                db.add(new_shift)

        db.commit()
        db.refresh(new_shift)
        return new_shift

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def clear_shift(car_id: int, datum: date, typ: str) -> bool:
    """Smazat záznam daného typu pro auto v daný den"""
    db = SessionLocal()
    try:
        shifts = db.query(CalendarAssignment).filter(
            CalendarAssignment.car_id == car_id,
            CalendarAssignment.datum == datum,
            CalendarAssignment.typ == typ
        ).all()
        for s in shifts:
            db.delete(s)
        db.commit()
        return len(shifts) > 0
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def get_weekly_rental(car_id: int, week_start: date) -> Optional[dict]:
    """
    Vrátí týdenní pronájem pro auto v daném týdnu, nebo None.
    """
    week_end = week_start + timedelta(days=6)
    db = SessionLocal()
    try:
        rental = db.query(CalendarAssignment).options(
            joinedload(CalendarAssignment.driver)
        ).filter(
            CalendarAssignment.car_id == car_id,
            CalendarAssignment.typ == 'tydenni',
            CalendarAssignment.datum <= week_end,
            CalendarAssignment.datum_do >= week_start
        ).first()

        return _shift_to_dict(rental) if rental else None
    finally:
        db.close()


def set_weekly_rental(car_id: int, week_start: date, driver_id: int) -> CalendarAssignment:
    """
    Nastaví týdenní pronájem pro auto (Po-Ne).
    Smaže existující týdenní pronájem i všechny denní záznamy v daném týdnu.
    """
    week_end = week_start + timedelta(days=6)

    db = SessionLocal()
    try:
        # Smazat existující týdenní pronájem překrývající tento týden
        existing_weekly = db.query(CalendarAssignment).filter(
            CalendarAssignment.car_id == car_id,
            CalendarAssignment.typ == 'tydenni',
            CalendarAssignment.datum <= week_end,
            CalendarAssignment.datum_do >= week_start
        ).all()
        for e in existing_weekly:
            db.delete(e)

        # Smazat všechny denní záznamy v týdnu
        daily = db.query(CalendarAssignment).filter(
            CalendarAssignment.car_id == car_id,
            CalendarAssignment.datum >= week_start,
            CalendarAssignment.datum <= week_end,
            CalendarAssignment.typ != 'tydenni'
        ).all()
        for d in daily:
            db.delete(d)

        # Vytvořit nový týdenní pronájem
        rental = CalendarAssignment(
            car_id=car_id,
            driver_id=driver_id,
            datum=week_start,
            datum_do=week_end,
            smena_od='00:00',
            smena_do='23:59',
            status='assigned',
            typ='tydenni',
        )
        db.add(rental)
        db.commit()
        db.refresh(rental)
        return rental

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def clear_weekly_rental(car_id: int, week_start: date) -> bool:
    """Odstraní týdenní pronájem pro auto v daném týdnu"""
    week_end = week_start + timedelta(days=6)
    db = SessionLocal()
    try:
        rentals = db.query(CalendarAssignment).filter(
            CalendarAssignment.car_id == car_id,
            CalendarAssignment.typ == 'tydenni',
            CalendarAssignment.datum <= week_end,
            CalendarAssignment.datum_do >= week_start
        ).all()
        for r in rentals:
            db.delete(r)
        db.commit()
        return len(rentals) > 0
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


# ==================== ZACHOVANÉ PŮVODNÍ FUNKCE ====================

def get_day_shifts(car_id: int, datum: date) -> List[CalendarAssignment]:
    """Získat všechny směny pro auto v daný den"""
    db = SessionLocal()
    try:
        return db.query(CalendarAssignment).filter(
            CalendarAssignment.car_id == car_id,
            CalendarAssignment.datum == datum
        ).order_by(CalendarAssignment.smena_od).all()
    finally:
        db.close()


def create_shift(
    car_id: int,
    datum: date,
    smena_od: str = "06:00",
    smena_do: str = "18:00",
    driver_id: Optional[int] = None,
    status: str = "assigned",
    poznamka: str = None
) -> CalendarAssignment:
    """Vytvořit novou směnu (původní funkce, zachována pro kompatibilitu)"""
    db = SessionLocal()
    try:
        shift = CalendarAssignment(
            car_id=car_id,
            driver_id=driver_id,
            datum=datum,
            smena_od=smena_od,
            smena_do=smena_do,
            status=status if driver_id else 'free',
            poznamka=poznamka
        )
        db.add(shift)
        db.commit()
        db.refresh(shift)
        return shift
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def update_shift(
    shift_id: int,
    driver_id: Optional[int] = None,
    smena_od: str = None,
    smena_do: str = None,
    status: str = None,
    poznamka: str = None
) -> Optional[CalendarAssignment]:
    """Aktualizovat směnu (původní funkce, zachována pro kompatibilitu)"""
    db = SessionLocal()
    try:
        shift = db.query(CalendarAssignment).filter(CalendarAssignment.id == shift_id).first()

        if shift:
            if driver_id is not None:
                shift.driver_id = driver_id
                shift.status = 'assigned' if driver_id else 'free'
            if smena_od:
                shift.smena_od = smena_od
            if smena_do:
                shift.smena_do = smena_do
            if status:
                shift.status = status
            if poznamka is not None:
                shift.poznamka = poznamka

            db.commit()
            db.refresh(shift)

        return shift
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def delete_shift(shift_id: int) -> bool:
    """Smazat směnu"""
    db = SessionLocal()
    try:
        shift = db.query(CalendarAssignment).filter(CalendarAssignment.id == shift_id).first()
        if shift:
            db.delete(shift)
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def get_driver_shifts(driver_id: int, period_start: date, period_end: date) -> List[CalendarAssignment]:
    """Získat všechny směny řidiče v období"""
    db = SessionLocal()
    try:
        return db.query(CalendarAssignment).filter(
            CalendarAssignment.driver_id == driver_id,
            CalendarAssignment.datum >= period_start,
            CalendarAssignment.datum <= period_end
        ).all()
    finally:
        db.close()


def check_driver_conflict(driver_id: int, datum: date, smena_od: str, smena_do: str, exclude_shift_id: int = None) -> bool:
    """Zkontrolovat jestli řidič už nemá směnu ve stejnou dobu"""
    db = SessionLocal()
    try:
        query = db.query(CalendarAssignment).filter(
            CalendarAssignment.driver_id == driver_id,
            CalendarAssignment.datum == datum
        )
        if exclude_shift_id:
            query = query.filter(CalendarAssignment.id != exclude_shift_id)
        return query.count() > 0
    finally:
        db.close()


def create_default_week(week_start: date):
    """Vytvořit prázdný týden s defaultními směnami pro všechna auta"""
    db = SessionLocal()
    try:
        cars = db.query(Car).filter(Car.status == 'active').all()

        for day_offset in range(7):
            current_date = week_start + timedelta(days=day_offset)

            for car in cars:
                morning = CalendarAssignment(
                    car_id=car.id,
                    datum=current_date,
                    smena_od='07:00',
                    smena_do='19:00',
                    status='free',
                    typ='ranni'
                )
                db.add(morning)

                evening = CalendarAssignment(
                    car_id=car.id,
                    datum=current_date,
                    smena_od='19:00',
                    smena_do='07:00',
                    status='free',
                    typ='vecerni'
                )
                db.add(evening)

        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════
# Obsazenost aut
# ══════════════════════════════════════════════════════════════════

def get_fleet_occupancy_month(year: int, month: int) -> dict:
    """
    Vrací slovník {car_id: obsazene_dny} pro daný měsíc.
    Počítá dny kdy auto má přiřazeného řidiče (driver_id != NULL).
    Zahrnuje i týdenní pronájmy (typ='tydenni').
    """
    import calendar as cal_mod
    from datetime import date

    first_day = date(year, month, 1)
    last_day = date(year, month, cal_mod.monthrange(year, month)[1])

    db = SessionLocal()
    try:
        # Denní směny v daném měsíci s řidičem
        daily = (
            db.query(CalendarAssignment.car_id, CalendarAssignment.datum)
            .filter(
                CalendarAssignment.driver_id.isnot(None),
                CalendarAssignment.datum >= first_day,
                CalendarAssignment.datum <= last_day,
                CalendarAssignment.typ != 'tydenni',
            )
            .distinct()
            .all()
        )

        # Týdenní pronájmy překrývající daný měsíc
        weekly = (
            db.query(CalendarAssignment)
            .filter(
                CalendarAssignment.driver_id.isnot(None),
                CalendarAssignment.typ == 'tydenni',
                CalendarAssignment.datum <= last_day,
                CalendarAssignment.datum_do >= first_day,
            )
            .all()
        )

        # Sestavit set (car_id, datum) pro každé auto
        occupied: dict[int, set] = {}

        for car_id, datum in daily:
            occupied.setdefault(car_id, set()).add(datum)

        for w in weekly:
            start = max(w.datum, first_day)
            end = min(w.datum_do, last_day)
            current = start
            while current <= end:
                occupied.setdefault(w.car_id, set()).add(current)
                current += timedelta(days=1)

        return {car_id: len(days) for car_id, days in occupied.items()}
    finally:
        db.close()
