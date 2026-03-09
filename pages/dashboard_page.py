"""
Dashboard Page - Wayne Fleet Management System
Hlavní přehled: KPI, stav flotily, dnešní směny, upozornění
"""

import streamlit as st
from datetime import date, timedelta, datetime
from database.crud_todos import create_todo, set_todo_done, delete_todo, sync_overdue_todos, sync_nabor_todos, PRIORITY_ORDER
from utils.cached_queries import (
    cached_cars, cached_drivers, cached_car_stats,
    cached_week_assignments, cached_monthly_summary,
    cached_pending_records, cached_next_service, cached_todos,
)


def _get_monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


# ── Konstanty pro prioritu ─────────────────────────────────────────────────────
_PRIORITY_DOT = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
_PRIORITY_LABEL = {'high': 'Vysoká', 'medium': 'Střední', 'low': 'Nízká'}
_PRIORITY_COLOR = {'high': '#ef4444', 'medium': '#f5c518', 'low': '#10b981'}


def _render_todo_widget():
    # Sync todos max 1x za minutu (ne při každém renderu)
    last_sync = st.session_state.get('todos_synced_at')
    if not last_sync or (datetime.now() - last_sync).seconds > 60:
        sync_overdue_todos()
        sync_nabor_todos()
        st.session_state['todos_synced_at'] = datetime.now()
        cached_todos.clear()

    todos = cached_todos()

    # Rozdělit na hotové / nehotové a seřadit podle priority
    pending_todos = sorted(
        [t for t in todos if not t.done],
        key=lambda t: (PRIORITY_ORDER.get(t.priority, 1), t.created_at)
    )
    done_todos = sorted(
        [t for t in todos if t.done],
        key=lambda t: t.created_at
    )

    # ── Hlavička ──────────────────────────────────────────────────────
    col_h, col_btn = st.columns([5, 1])
    with col_h:
        pending_count = len(pending_todos)
        badge = (
            f" <span style='background:#ef4444; color:white; font-size:0.7rem; "
            f"padding:1px 7px; border-radius:10px; font-weight:700;'>{pending_count}</span>"
            if pending_count else ""
        )
        st.markdown(
            f"<div style='font-size:1.15rem; font-weight:700; color:white; padding-top:0.2rem;'>"
            f"✅ Úkoly{badge}</div>",
            unsafe_allow_html=True,
        )
    with col_btn:
        if st.button("➕ Přidat", key='todo_add_btn', width='stretch'):
            st.session_state['todo_show_form'] = True

    # ── Formulář pro přidání ──────────────────────────────────────────
    if st.session_state.get('todo_show_form'):
        with st.form('todo_add_form', clear_on_submit=True):
            col_txt, col_pri, col_sub, col_can = st.columns([5, 2, 1, 1])
            with col_txt:
                new_text = st.text_input("Úkol", placeholder="Co je potřeba udělat...", label_visibility='collapsed')
            with col_pri:
                new_priority = st.selectbox(
                    "Priorita", ['high', 'medium', 'low'],
                    format_func=lambda x: _PRIORITY_LABEL[x],
                    label_visibility='collapsed'
                )
            with col_sub:
                save = st.form_submit_button("✅", width="stretch")
            with col_can:
                cancel = st.form_submit_button("❌", width="stretch")

            if save and new_text.strip():
                create_todo(new_text.strip(), new_priority)
                st.session_state['todo_show_form'] = False
                cached_todos.clear()
                st.rerun()
            if cancel:
                st.session_state['todo_show_form'] = False
                st.rerun()

    # ── Seznam nehotových úkolů ───────────────────────────────────────
    if not pending_todos and not done_todos:
        st.markdown(
            "<div style='color:rgba(255,255,255,0.35); font-size:0.85rem; "
            "padding:0.6rem 0; font-style:italic;'>Žádné úkoly. Klikni ➕ Přidat a vytvoř první.</div>",
            unsafe_allow_html=True,
        )
    else:
        for todo in pending_todos:
            col_check, col_dot, col_text, col_del = st.columns([0.5, 0.3, 8, 0.5])
            with col_check:
                checked = st.checkbox('Hotovo', value=False, key=f'todo_chk_{todo.id}', label_visibility='collapsed')
                if checked:
                    set_todo_done(todo.id, True)
                    cached_todos.clear()
                    st.rerun()
            with col_dot:
                st.markdown(
                    f"<div style='padding-top:0.45rem; font-size:0.9rem;'>{_PRIORITY_DOT[todo.priority]}</div>",
                    unsafe_allow_html=True,
                )
            with col_text:
                st.markdown(
                    f"<div style='padding-top:0.42rem; font-size:0.9rem; color:white;'>{todo.text}</div>",
                    unsafe_allow_html=True,
                )
            with col_del:
                if st.button('🗑️', key=f'todo_del_{todo.id}', help='Smazat'):
                    delete_todo(todo.id)
                    cached_todos.clear()
                    st.rerun()

        # ── Hotové (sbalené) ─────────────────────────────────────────
        if done_todos:
            with st.expander(f"Hotové ({len(done_todos)})", expanded=False):
                for todo in done_todos:
                    col_check, col_text, col_del = st.columns([0.5, 8.3, 0.5])
                    with col_check:
                        checked = st.checkbox('', value=True, key=f'todo_chk_{todo.id}', label_visibility='collapsed')
                        if not checked:
                            set_todo_done(todo.id, False)
                            cached_todos.clear()
                            st.rerun()
                    with col_text:
                        st.markdown(
                            f"<div style='padding-top:0.42rem; font-size:0.85rem; "
                            f"color:rgba(255,255,255,0.35); text-decoration:line-through;'>{todo.text}</div>",
                            unsafe_allow_html=True,
                        )
                    with col_del:
                        if st.button('🗑️', key=f'todo_del_{todo.id}', help='Smazat'):
                            delete_todo(todo.id)
                            cached_todos.clear()
                            st.rerun()

    st.markdown("<hr style='border-color:rgba(255,255,255,0.08); margin:0.8rem 0 1rem;'>", unsafe_allow_html=True)


def render_dashboard():
    today = date.today()

    # ── Načtení dat (z cache) ──────────────────────────────────────────
    all_cars = cached_cars()
    all_drivers = cached_drivers()
    active_cars = [c for c in all_cars if c.status == 'active']
    active_drivers = [d for d in all_drivers if d.status == 'active']

    this_month = cached_monthly_summary(today.year, today.month)
    pending = cached_pending_records()

    monday = _get_monday(today)
    week_data = cached_week_assignments(monday)  # {car_id: {datum: [shift_dict], '__weekly__': [...]}}

    # Shift_dict pro dnešní den: běžné směny + týdenní pronájmy
    def get_today_shifts_for_car(car_id):
        car_week = week_data.get(car_id, {})
        today_shifts = list(car_week.get(today, []))
        weekly = car_week.get('__weekly__', [])
        # Týdenní pronájem pokrývá celý týden → přidáme jako "celý den"
        for w in weekly:
            if w.get('datum') and w.get('datum_do'):
                if w['datum'] <= today <= w['datum_do']:
                    today_shifts.append(w)
        return today_shifts

    # ── To Do widget ──────────────────────────────────────────────────
    _render_todo_widget()

    # ── Nadpis + datum ────────────────────────────────────────────────
    col_t, col_d = st.columns([5, 1])
    with col_t:
        st.markdown("## 📊 Dashboard")
    with col_d:
        mesice = ['led', 'úno', 'bře', 'dub', 'kvě', 'čer', 'čvc', 'srp', 'zář', 'říj', 'lis', 'pro']
        st.markdown(
            f"<div style='text-align:right; color:rgba(255,255,255,0.45); "
            f"font-size:0.9rem; padding-top:0.7rem;'>"
            f"{today.day}. {mesice[today.month-1]} {today.year}</div>",
            unsafe_allow_html=True
        )

    # ── KPI ───────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)

    k1.metric(
        "🚗 Aktivní auta",
        len(active_cars),
        delta=f"z {len(all_cars)} celkem",
        delta_color='off',
    )
    k2.metric(
        "👥 Aktivní řidiči",
        len(active_drivers),
        delta=f"z {len(all_drivers)} celkem",
        delta_color='off',
    )
    k3.metric(
        "📤 Příjmy (měsíc)",
        f"{this_month['vydano_celkem']:,.0f} Kč",
        delta=f"zaplaceno {this_month['vydano_zaplaceno']:,.0f} Kč",
    )
    k4.metric(
        "📥 Výdaje (měsíc)",
        f"{this_month['prijato_celkem']:,.0f} Kč",
        delta=f"uhrazeno {this_month['prijato_zaplaceno']:,.0f} Kč",
        delta_color='inverse',
    )
    bilance = this_month['bilance']
    k5.metric(
        "💰 Bilance",
        f"{bilance:,.0f} Kč",
        delta="inkasováno",
        delta_color='normal' if bilance >= 0 else 'inverse',
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Hlavní obsah ──────────────────────────────────────────────────
    col_fleet, col_side = st.columns([3, 2])

    # ────────── LEVÝ SLOUPEC: Stav flotily ────────────────────────────
    with col_fleet:
        st.markdown("#### 🚗 Stav flotily")

        if not all_cars:
            st.info("Žádná auta v databázi.")
        else:
            for car in all_cars:
                stats = cached_car_stats(car.id) or {}
                today_shifts = get_today_shifts_for_car(car.id)

                status_color = {
                    'active': '#10b981',
                    'service': '#f59e0b',
                    'retired': '#6b7280',
                }.get(car.status, '#6b7280')
                status_emoji = {
                    'active': '✅',
                    'service': '🔧',
                    'retired': '🗄️',
                }.get(car.status, '❓')

                # Dnešní řidič
                typ_labels = {
                    'ranni': 'ranní', 'vecerni': 'večerní',
                    'cely_den': 'celý den', 'servis': 'servis',
                    'tydenni': 'celý týden',
                }
                if today_shifts:
                    parts = []
                    for s in today_shifts:
                        name = s.get('driver_name') or '?'
                        typ = typ_labels.get(s.get('typ', ''), s.get('typ', ''))
                        parts.append(f"<strong style='color:white;'>{name}</strong>"
                                     f"<span style='color:rgba(255,255,255,0.45);'> · {typ}</span>")
                    driver_line = "👤 " + " &nbsp;|&nbsp; ".join(parts)
                else:
                    driver_line = "<span style='color:rgba(255,255,255,0.3);'>Nikdo dnes nepracuje</span>"

                # Finance / progress
                if car.typ_vlastnictvi == 'vlastni':
                    procento = stats.get('procento_splaceno', 0)
                    bar_color = '#10b981' if procento >= 100 else '#f5c518'
                    zaplaceno = stats.get('zaplaceno', 0)
                    celkova = stats.get('celkova_cena', 0)
                    finance_html = (
                        f"<div style='font-size:0.78rem; color:rgba(255,255,255,0.45); margin:3px 0 2px;'>"
                        f"Splaceno {zaplaceno:,.0f} / {celkova:,.0f} Kč &nbsp;·&nbsp; "
                        f"<span style='color:{bar_color};'>{procento:.0f}%</span></div>"
                        f"<div style='background:rgba(255,255,255,0.1); border-radius:3px; height:4px;'>"
                        f"<div style='width:{min(procento,100):.0f}%; height:100%; "
                        f"background:{bar_color}; border-radius:3px;'></div></div>"
                    )
                else:
                    finance_html = (
                        f"<div style='font-size:0.78rem; color:rgba(255,255,255,0.4); margin-top:3px;'>"
                        f"Pronájem · {car.splatka_tyden:,.0f} Kč/týden</div>"
                    )

                # Příští servis
                try:
                    next_svc = cached_next_service(car.id) or {}
                except Exception:
                    next_svc = {}
                svc_html = ""
                if next_svc.get('pristi_servis_datum'):
                    d = next_svc['pristi_servis_datum']
                    days_left = (d - today).days
                    sc = '#ef4444' if days_left < 14 else '#f59e0b' if days_left < 45 else 'rgba(255,255,255,0.35)'
                    svc_html = (
                        f"<span style='color:{sc}; font-size:0.75rem;'>"
                        f"🔧 servis {d.strftime('%d.%m.%Y')} ({days_left} dní)</span>"
                    )
                elif next_svc.get('pristi_servis_km'):
                    svc_html = (
                        f"<span style='color:rgba(255,255,255,0.35); font-size:0.75rem;'>"
                        f"🔧 servis při {next_svc['pristi_servis_km']:,} km</span>"
                    )

                st.markdown(
                    f"<div style='background:rgba(255,255,255,0.04); "
                    f"border:1px solid rgba(255,255,255,0.1); "
                    f"border-left:3px solid {status_color}; "
                    f"border-radius:10px; padding:0.85rem 1rem; margin-bottom:0.55rem;'>"
                    # Header řádek
                    f"<div style='display:flex; justify-content:space-between; align-items:center;'>"
                    f"<div>"
                    f"<strong style='color:white; font-size:1.05rem;'>{status_emoji} {car.spz}</strong>"
                    f"<span style='color:rgba(255,255,255,0.5); font-size:0.85rem; margin-left:0.5rem;'>"
                    f"{car.model} ({car.rok})</span>"
                    f"</div>"
                    f"<span style='font-size:0.8rem; color:rgba(255,255,255,0.4);'>🛣️ {car.celkem_km:,} km</span>"
                    f"</div>"
                    # Řidič
                    f"<div style='margin-top:0.35rem; font-size:0.85rem;'>{driver_line}</div>"
                    # Finance
                    f"<div style='margin-top:0.2rem;'>{finance_html}</div>"
                    # Servis
                    + (f"<div style='margin-top:0.3rem;'>{svc_html}</div>" if svc_html else "")
                    + "</div>",
                    unsafe_allow_html=True,
                )

            # Rychlé přístupy
            st.markdown("<br>", unsafe_allow_html=True)
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                if st.button("🚗 Správa aut", width='stretch', key='dash_q_auta'):
                    st.session_state['page'] = 'auta'
                    st.rerun()
            with col_b:
                if st.button("👥 Správa řidičů", width='stretch', key='dash_q_ridici'):
                    st.session_state['page'] = 'ridici'
                    st.rerun()
            with col_c:
                if st.button("📅 Kalendář", width='stretch', key='dash_q_kalendar'):
                    st.session_state['page'] = 'kalendar'
                    st.rerun()

    # ────────── PRAVÝ SLOUPEC: Dnes + Upozornění + Kauce ─────────────
    with col_side:

        # DNES PRACUJÍ
        st.markdown("#### 📅 Dnes pracují")
        all_today = []
        for car in all_cars:
            for s in get_today_shifts_for_car(car.id):
                all_today.append((car, s))

        if all_today:
            for car, s in all_today:
                name = s.get('driver_name') or '?'
                typ = {'ranni': '🌅 ranní', 'vecerni': '🌆 večerní',
                       'cely_den': '☀️ celý den', 'servis': '🔧 servis',
                       'tydenni': '🗓️ celý týden'}.get(s.get('typ', ''), s.get('typ', ''))
                st.markdown(
                    f"<div style='background:rgba(255,255,255,0.04); border-radius:8px; "
                    f"padding:0.55rem 0.8rem; margin-bottom:0.35rem; font-size:0.85rem;'>"
                    f"<strong style='color:white;'>{name}</strong>"
                    f"<span style='color:rgba(255,255,255,0.45);'> · {typ} · 🚗 {car.spz}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                "<span style='color:rgba(255,255,255,0.3); font-size:0.85rem;'>Žádné směny dnes</span>",
                unsafe_allow_html=True,
            )

        # UPOZORNĚNÍ
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### ⚠️ Upozornění")

        overdue_vydane = [
            r for r in pending['vydane']
            if r.datum_splatnosti and r.datum_splatnosti < today
        ]
        overdue_prijate = [
            r for r in pending['prijate']
            if r.datum_splatnosti and r.datum_splatnosti < today
        ]
        upcoming_prijate = [
            r for r in pending['prijate']
            if r.datum_splatnosti and today <= r.datum_splatnosti <= today + timedelta(days=7)
        ]

        anything = False

        if overdue_vydane:
            anything = True
            st.markdown(
                f"<div style='color:#ef4444; font-size:0.82rem; font-weight:600; margin-bottom:3px;'>"
                f"📤 Neuhrazené příjmy ({len(overdue_vydane)})</div>",
                unsafe_allow_html=True,
            )
            for r in overdue_vydane[:4]:
                days_ago = (today - r.datum_splatnosti).days
                st.markdown(
                    f"<div style='font-size:0.8rem; color:rgba(255,255,255,0.7); "
                    f"padding:0.15rem 0 0.15rem 0.6rem; border-left:2px solid #ef4444; margin-bottom:2px;'>"
                    f"{r.popis[:28]} — <strong style='color:#ef4444;'>{r.castka_kc:,.0f} Kč</strong>"
                    f"<span style='color:rgba(255,255,255,0.35); font-size:0.75rem;'> ({days_ago}d zpět)</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        if overdue_prijate:
            anything = True
            st.markdown(
                f"<div style='color:#f59e0b; font-size:0.82rem; font-weight:600; margin:6px 0 3px;'>"
                f"📥 Nezaplacené závazky ({len(overdue_prijate)})</div>",
                unsafe_allow_html=True,
            )
            for r in overdue_prijate[:4]:
                days_ago = (today - r.datum_splatnosti).days
                st.markdown(
                    f"<div style='font-size:0.8rem; color:rgba(255,255,255,0.7); "
                    f"padding:0.15rem 0 0.15rem 0.6rem; border-left:2px solid #f59e0b; margin-bottom:2px;'>"
                    f"{r.popis[:28]} — <strong style='color:#f59e0b;'>{r.castka_kc:,.0f} Kč</strong>"
                    f"<span style='color:rgba(255,255,255,0.35); font-size:0.75rem;'> ({days_ago}d zpět)</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        if upcoming_prijate:
            anything = True
            st.markdown(
                f"<div style='color:#f5c518; font-size:0.82rem; font-weight:600; margin:6px 0 3px;'>"
                f"🔔 Splatné tento týden ({len(upcoming_prijate)})</div>",
                unsafe_allow_html=True,
            )
            for r in upcoming_prijate[:4]:
                st.markdown(
                    f"<div style='font-size:0.8rem; color:rgba(255,255,255,0.7); "
                    f"padding:0.15rem 0 0.15rem 0.6rem; border-left:2px solid #f5c518; margin-bottom:2px;'>"
                    f"{r.popis[:28]} — {r.castka_kc:,.0f} Kč"
                    f"<span style='color:rgba(255,255,255,0.35); font-size:0.75rem;'>"
                    f" (do {r.datum_splatnosti.strftime('%d.%m')})</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        if not anything:
            st.markdown(
                "<div style='color:#10b981; font-size:0.85rem;'>✅ Žádná upozornění</div>",
                unsafe_allow_html=True,
            )

        # KAUCE ŘIDIČŮ
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 💰 Kauce řidičů")

        active_with_kauce = [
            d for d in all_drivers
            if d.status == 'active' and (d.kauce_celkem or 0) > 0
        ]

        if active_with_kauce:
            for driver in active_with_kauce:
                kauce_c = driver.kauce_celkem or 0
                kauce_z = driver.kauce_zaplaceno or 0
                procento = min(100, kauce_z / kauce_c * 100) if kauce_c else 0
                zbyvajici = kauce_c - kauce_z
                bar_color = '#10b981' if procento >= 100 else '#f59e0b'
                initials = ''.join(n[0].upper() for n in driver.jmeno.split() if n)

                st.markdown(
                    f"<div style='display:flex; align-items:center; gap:0.5rem; margin-bottom:0.45rem;'>"
                    f"<div style='width:26px; height:26px; border-radius:50%; flex-shrink:0; "
                    f"background:linear-gradient(135deg,#f5c518,#d4a017); "
                    f"display:flex; align-items:center; justify-content:center; "
                    f"font-size:0.65rem; font-weight:700; color:#0a0a0a;'>{initials}</div>"
                    f"<div style='flex:1; min-width:0;'>"
                    f"<div style='display:flex; justify-content:space-between; "
                    f"font-size:0.8rem; color:rgba(255,255,255,0.8);'>"
                    f"<span>{driver.jmeno}</span>"
                    f"<span style='color:{bar_color};'>{procento:.0f}%</span></div>"
                    f"<div style='background:rgba(255,255,255,0.1); border-radius:3px; height:5px; margin-top:2px;'>"
                    f"<div style='width:{procento:.0f}%; height:100%; background:{bar_color}; border-radius:3px;'></div>"
                    f"</div>"
                    f"<div style='font-size:0.72rem; color:rgba(255,255,255,0.35);'>"
                    f"zbývá {zbyvajici:,.0f} Kč</div>"
                    f"</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                "<span style='color:rgba(255,255,255,0.3); font-size:0.85rem;'>Žádní aktivní řidiči s kaucí</span>",
                unsafe_allow_html=True,
            )

        # Rychlé přístupy
        st.markdown("<br>", unsafe_allow_html=True)
        col_x, col_y = st.columns(2)
        with col_x:
            if st.button("💳 Finance", width='stretch', key='dash_q_finance'):
                st.session_state['page'] = 'finance'
                st.rerun()
        with col_y:
            if st.button("📈 Statistiky", width='stretch', key='dash_q_statistiky'):
                st.session_state['page'] = 'statistiky'
                st.rerun()
