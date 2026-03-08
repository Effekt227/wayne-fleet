"""
Cached DB queries - Wayne Fleet Management System
Wraps frequently-called read functions with @st.cache_data to avoid
hitting PostgreSQL on every Streamlit re-render.

Cache is cleared after mutations using .clear() calls.
"""

import streamlit as st
from datetime import date

from database.crud_cars import get_all_cars as _cars, get_car_stats as _car_stats
from database.crud_drivers import get_all_drivers as _drivers
from database.crud_calendar import get_week_assignments as _week
from database.crud_finance_records import get_monthly_summary as _monthly, get_pending_records as _pending
from database.crud_services import get_next_service as _next_svc
from database.crud_todos import get_all_todos as _todos


@st.cache_data(ttl=30)
def cached_cars():
    return _cars()


@st.cache_data(ttl=30)
def cached_drivers():
    return _drivers()


@st.cache_data(ttl=30)
def cached_car_stats(car_id: int):
    return _car_stats(car_id)


@st.cache_data(ttl=30)
def cached_week_assignments(monday: date):
    return _week(monday)


@st.cache_data(ttl=60)
def cached_monthly_summary(year: int, month: int):
    return _monthly(year, month)


@st.cache_data(ttl=30)
def cached_pending_records():
    return _pending()


@st.cache_data(ttl=30)
def cached_next_service(car_id: int):
    return _next_svc(car_id)


@st.cache_data(ttl=15)
def cached_todos():
    return _todos()
