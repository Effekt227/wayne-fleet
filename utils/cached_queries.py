"""
Cached DB queries - Wayne Fleet Management System
Uses st.cache_resource (no TTL — data held until explicitly cleared after mutations).
Cache cleared after mutations via .clear() calls.
"""

import streamlit as st
from datetime import date


@st.cache_resource
def cached_cars():
    from database.crud_cars import get_all_cars
    return get_all_cars()


@st.cache_resource
def cached_drivers():
    from database.crud_drivers import get_all_drivers
    return get_all_drivers()


@st.cache_resource
def cached_car_stats(car_id: int):
    from database.crud_cars import get_car_stats
    return get_car_stats(car_id)


@st.cache_resource
def cached_week_assignments(monday: date):
    from database.crud_calendar import get_week_assignments
    return get_week_assignments(monday)


@st.cache_resource
def cached_monthly_summary(year: int, month: int):
    from database.crud_finance_records import get_monthly_summary
    return get_monthly_summary(year, month)


@st.cache_resource
def cached_pending_records():
    from database.crud_finance_records import get_pending_records
    return get_pending_records()


@st.cache_resource
def cached_next_service(car_id: int):
    from database.crud_services import get_next_service
    return get_next_service(car_id)


@st.cache_resource
def cached_todos():
    from database.crud_todos import get_all_todos
    return get_all_todos()


@st.cache_resource
def cached_chart_data(months_back: int, months_forward: int):
    from database.crud_finance_records import get_monthly_chart_data
    return get_monthly_chart_data(months_back=months_back, months_forward=months_forward)


@st.cache_resource
def cached_chart_data_range(year_from: int, month_from: int, year_to: int, month_to: int):
    from database.crud_finance_records import get_monthly_chart_data_range
    return get_monthly_chart_data_range(year_from, month_from, year_to, month_to)


@st.cache_resource
def cached_driver_stats(driver_id: int):
    from database.crud_drivers import get_driver_stats
    return get_driver_stats(driver_id)


@st.cache_resource
def cached_service_cost(car_id: int):
    from database.crud_services import get_total_service_cost
    return get_total_service_cost(car_id)


@st.cache_resource
def cached_fines_summary(driver_id: int):
    from database.crud_fines import get_driver_fines_summary
    return get_driver_fines_summary(driver_id)


@st.cache_resource
def cached_fleet_occupancy(year: int, month: int):
    from database.crud_calendar import get_fleet_occupancy_month
    return get_fleet_occupancy_month(year, month)


@st.cache_resource
def cached_transaction_stats():
    from database.crud_bank import get_transaction_stats
    return get_transaction_stats()


@st.cache_resource
def cached_transactions(date_from, date_to, credit_debit, only_unmatched: bool):
    from database.crud_bank import get_transactions
    return get_transactions(date_from, date_to, credit_debit, only_unmatched)
