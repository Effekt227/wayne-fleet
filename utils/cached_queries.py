"""
Cached DB queries - Wayne Fleet Management System
Wraps frequently-called read functions with @st.cache_data to avoid
hitting PostgreSQL on every Streamlit re-render.

Cache is cleared after mutations using .clear() calls.
Uses lazy imports to avoid module-level side effects.
"""

import streamlit as st
from datetime import date


@st.cache_data(ttl=30)
def cached_cars():
    from database.crud_cars import get_all_cars
    return get_all_cars()


@st.cache_data(ttl=30)
def cached_drivers():
    from database.crud_drivers import get_all_drivers
    return get_all_drivers()


@st.cache_data(ttl=30)
def cached_car_stats(car_id: int):
    from database.crud_cars import get_car_stats
    return get_car_stats(car_id)


@st.cache_data(ttl=30)
def cached_week_assignments(monday: date):
    from database.crud_calendar import get_week_assignments
    return get_week_assignments(monday)


@st.cache_data(ttl=60)
def cached_monthly_summary(year: int, month: int):
    from database.crud_finance_records import get_monthly_summary
    return get_monthly_summary(year, month)


@st.cache_data(ttl=30)
def cached_pending_records():
    from database.crud_finance_records import get_pending_records
    return get_pending_records()


@st.cache_data(ttl=30)
def cached_next_service(car_id: int):
    from database.crud_services import get_next_service
    return get_next_service(car_id)


@st.cache_data(ttl=15)
def cached_todos():
    from database.crud_todos import get_all_todos
    return get_all_todos()
