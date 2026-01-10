### IMPORTS ###

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sympy import rem
import functions as fn
import numpy as np
import pydeck as pdk
import subprocess 
import os          
import urllib.parse
import streamlit.components.v1 as components

st.set_page_config(
    page_title="MyCubing",
    page_icon="🎲",
    layout="wide",  # Esto ayuda a que en PC aproveche todo el ancho
    initial_sidebar_state="expanded" # Opciones: "auto", "expanded", "collapsed"
)

APP_NAME = "MyCubing"
ICON_URL = "https://github.com/rulo1023/AppCubos/blob/master/game_die.png" # Esto no funciona cuando descargo la app en móvil

st.markdown("""
    <style>
        /* Optimizar el padding en computadoras */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            padding-left: 3rem;
            padding-right: 3rem;
        }
        /* Hacer que el sidebar sea más consistente */
        [data-testid="stSidebarNav"] {
            background-size: contain;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown(f"""
<link rel="manifest" href='data:application/json,{{
  "name": "{APP_NAME}",
  "short_name": "{APP_NAME}",
  "start_url": ".",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#FF2C2C",
  "icons": [
    {{
      "src": "{ICON_URL}",
      "sizes": "512x512",
      "type": "image/png"
    }}
  ]
}}'>
<script>
  if ('serviceWorker' in navigator) {{
    window.addEventListener('load', function() {{
      navigator.serviceWorker.register('sw.js');
    }});
  }}
</script>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 24px; font-weight: bold; }
    
    /* Contenedor de la tarjeta con espacio extra al final */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 15px;
        background-color: #f8f9fa;
        padding: 15px;
        padding-bottom: 25px; /* Añade espacio extra antes del borde inferior */
        margin-bottom: 10px;
    }
    
    .pr-card-title { font-size: 18px; color: #777; margin-bottom: 0px; }
    .pr-card-time { font-size: 26px; font-weight: 800; color: #FF2C2C ; margin: 5px 0; }
    
    .pr-card-comp { 
        font-size: 15px; 
        color: #777; 
        line-height: 1.2;
        margin-bottom: 5px; 
    }
    
    /* Clase para la fecha con un margen inferior para asegurar el hueco */
    .pr-card-date { 
        font-size: 15px; 
        color: #777;
        margin-bottom: 5px; /* Este es el "espacio vacío" después de la fecha */
    }

    [data-testid="column"] { min-width: 45% !important; flex: 1 1 45% !important; }
    @media (min-width: 768px) {
        [data-testid="column"] { min-width: 20% !important; flex: 1 1 20% !important; }
    }
     /* Inversión de iconos SVG en modo oscuro */
    @media (prefers-color-scheme: dark) {
        img[src*=".svg"] {
            filter: invert(1) brightness(2);
        }
        /* Mantenemos el fondo del cabecero claro para que el texto negro sea legible */
        .wca-table thead th {
            background-color: #e0e0e0 !important;
            color: #000000 !important;
        }
        .wca-table td { color: white; }
    }
            /* Hacer que las imágenes de scramble sean más grandes en móvil */
    @media (max-width: 767px) {
        [data-testid="stImage"] img {
            width: 100% !important;
            max-width: 300px !important; /* Ajusta este valor a tu gusto */
            margin: 0 auto;
            display: block;
        }
    }
    </style>
    """, unsafe_allow_html=True)

event_dict = {
            "333": "3x3x3", "222": "2x2x2", "444": "4x4x4", 
            "555": "5x5x5", "666": "6x6x6", "777": "7x7x7", "333fm": "3x3x3 Fewest Moves",
            "333bf": "3x3x3 Blindfolded", "333oh": "3x3x3 One-Handed", 
            "minx": "Megaminx", "pyram": "Pyraminx", "skewb": "Skewb", 
            "sq1": "Square-1", "clock": "Clock", "444bf": "4x4x4 Blindfolded",
            "555bf": "5x5x5 Blindfolded", "333mbf": "3x3x3 Multi-Blind","333ft": "3x3x3 With Feet",
            "magic": "Magic", "mmagic": "Master Magic",
        } 

def render_metric(label, value):
    with st.container(border=True):
        st.metric(label=label, value=value)

def render_pr_card(title, time_str, comp_name, date_str):
    with st.container(border=True):
        st.markdown(f"""
        <div class="pr-card-title">{title}</div>
        <div class="pr-card-time">{time_str}</div>
        <div class="pr-card-comp">📍 {comp_name}</div>
        <div class="pr-card-date">📅 {date_str}</div>
        <div style="height: 10px;"></div> """, unsafe_allow_html=True)

### MAIN DATA LOADING FUNCTION ###
@st.cache_data(ttl=3600, show_spinner=False)
def load_all_data(wca_id):
    try:
        results = fn.get_wca_results(wca_id)
        if results.empty: return None

        info = fn.get_wcaid_info(wca_id)
        prs_dict = fn.prs_info(wca_id, results_df=results)
        stats_prs = fn.number_of_prs(wca_id, results_df=results)
        map_data = list(fn.generate_map_data(wca_id, results_df=results))

        return {
            "info": info,
            "results": results,
            "prs_dict": prs_dict,
            "stats_prs": stats_prs,
            "map_data": map_data
        }
    except Exception as e:
        st.error(f"Error loading profile: {e}")
        return None

### RENDERING FUNCTIONS ###
def render_summary_enhanced(data, wca_id):
    info = data["info"]
    df = data["results"]
    
    # Preparamos variables de cabecera
    iso_code = info.get('person.country.iso2', 'N/A')
    flag = fn.get_flag_emoji(iso_code)
    
    # Recuperamos el diccionario de eventos GLOBAL. 
    # Si por alguna razón no existe, usamos uno vacío para no romper la app.
    local_event_dict = globals().get('event_dict', {})

    # --- 2. CABECERA ---
    col_profile, col_empty = st.columns([2, 1])
    with col_profile:
        st.markdown(f"## {flag} {info.get('person.name', wca_id)}")
        st.caption(f"WCA ID: {wca_id}")

    st.divider()

    # --- 3. TARJETAS GENERALES ---
    col1, col2, col3 = st.columns(3)
    
    # Medallas
    with col1:
        with st.container(border=True):
            st.markdown("### 🏆 Medals")
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("🥇 Gold", info.get('medals.gold', 0))
            mc2.metric("🥈 Silver", info.get('medals.silver', 0))
            mc3.metric("🥉 Bronze", info.get('medals.bronze', 0))

    # Volumen
    with col2:
        with st.container(border=True):
            st.markdown("### 📊 Volume")
            vc1, vc2 = st.columns(2)
            
            total_solves = info.get('total_solves', 0)
            if total_solves == 0 and not df.empty: total_solves = len(df)
            
            competition_count = info.get('competition_count', len(df['Competition'].unique()))
            
            vc1.metric("Comps", competition_count)
            vc2.metric("Solves", total_solves)

    # Trayectoria
    with col3:
        with st.container(border=True):
            st.markdown("### 📅 Career")
            years_active = 0
            date_range_str = "-"
            fav_event_name = "-"
            
            if not df.empty:
                min_date = df['CompDate'].min()
                max_date = df['CompDate'].max()
                years_active = max_date.year - min_date.year + 1
                date_range_str = f"{min_date.strftime('%b %Y')} - {max_date.strftime('%b %Y')}"
                
                fav_event_code = df['Event'].value_counts().idxmax()
                # Usamos el diccionario local seguro
                fav_event_name = local_event_dict.get(fav_event_code, fav_event_code)

            cc1, cc2 = st.columns(2)
            cc1.metric("Years active", years_active)
            cc2.metric("Most solved event", fav_event_name)
            st.caption(f"📅 {date_range_str}")

    # --- 4. TARJETAS DE RÉCORDS (NR/CR/WR) ---
    nr = info.get('records.national', 0)
    cr = info.get('records.continental', 0)
    wr = info.get('records.world', 0)
    
    if (nr + cr + wr) > 0:
        st.markdown("### 🎖️ Current Records Held")
        r1, r2, r3 = st.columns(3)
        with r1:
            with st.container(border=True):
                st.metric("🇺🇳 National Records", nr)
        with r2:
            with st.container(border=True):
                st.metric("🌍 Continental Records", cr)
        with r3:
            with st.container(border=True):
                st.metric("🪐 World Records", wr)

    st.divider()

    
    # --- LÓGICA DE PRs ACTIVOS (Basada en tu función de cards) ---
    if not df.empty:
        active_prs = []
        # Iteramos por cada evento que tiene el usuario
        for event_code in df['Event'].unique():

            # if event is 333ft, magic, mmagic, skip
            if event_code.startswith('333ft') or event_code.startswith('magic') or event_code.startswith('mmagic'):
                continue

            ev_df = df[df['Event'] == event_code]
            
            # Encontramos el PB de Single para este evento (el más rápido y antiguo en caso de empate)
            s_df = ev_df[ev_df['best_cs'] > 0]
            if not s_df.empty:
                best_s = s_df.sort_values(by=['best_cs', 'CompDate']).iloc[0]
                active_prs.append({
                    'date': best_s['CompDate'],
                    'event': event_code,
                    'type': 'Single',
                    'time': fn.format_wca_time(best_s['best_cs'], event_code=event_code),
                    'comp': best_s['CompName']
                })

            # Encontramos el PB de Average para este evento
            a_df = ev_df[ev_df['avg_cs'] > 0]
            if not a_df.empty:
                best_a = a_df.sort_values(by=['avg_cs', 'CompDate']).iloc[0]
                active_prs.append({
                    'date': best_a['CompDate'],
                    'event': event_code,
                    'type': 'Average',
                    'time': fn.format_wca_time(best_a['avg_cs'], event_code=event_code),
                    'comp': best_a['CompName']
                })

        if active_prs:
            # Ordenamos todos los PBs encontrados por fecha
            active_prs_sorted = sorted(active_prs, key=lambda x: x['date'])
            oldest = active_prs_sorted[0]
            newest = active_prs_sorted[-1]

            # --- 3. RENDERIZADO DE TARJETAS ---
            st.markdown("### ⏳ Record Milestones")
            c_old, c_new = st.columns(2)

            with c_old:
                event_label = f"{event_dict.get(oldest['event'], oldest['event'])} ({oldest['type']})"
                render_pr_card(
                    "Oldest active PR", 
                    oldest['time'], 
                    f"{event_label} \n\n {oldest['comp']}", 
                    oldest['date'].strftime('%d %b %Y')
                )

            with c_new:
                event_label = f"{event_dict.get(newest['event'], newest['event'])} ({newest['type']})"
                render_pr_card(
                    "Most recent PR", 
                    newest['time'], 
                    f"{event_label} \n\n {newest['comp']}", 
                    newest['date'].strftime('%d %b %Y')
                )
    st.divider()

    # --- 6. RANKINGS (Tabla) ---
    st.subheader("🌍 Current Global Rankings")
    
    WCA_ORDER = [
        "333", "222", "444", "555", "666", "777", 
        "333bf", "333fm", "333oh", "clock", "minx", 
        "pyram", "skewb", "sq1", "444bf", "555bf", "333mbf"
    ]
    
    if not df.empty:
        user_events = df['Event'].unique().tolist()
        # Ordenamos según WCA_ORDER
        sorted_events = [ev for ev in WCA_ORDER if ev in user_events] + \
                        [ev for ev in user_events if ev not in WCA_ORDER]

        rank_rows = []

        for ev_code in sorted_events:
            ev_name = local_event_dict.get(ev_code, ev_code)
            
            # Helper interno para extraer rankings
            def get_val(code, type_, rank_type):
                # Construimos la clave: personal_records.333.single.world_rank
                key = f"personal_records.{code}.{type_}.{rank_type}"
                return info.get(key, "-")

            s_world = get_val(ev_code, "single", "world_rank")
            s_cont = get_val(ev_code, "single", "continent_rank")
            s_country = get_val(ev_code, "single", "country_rank")
            
            a_world = get_val(ev_code, "average", "world_rank")
            a_cont = get_val(ev_code, "average", "continent_rank")
            a_country = get_val(ev_code, "average", "country_rank")
            
            if s_world != "-" or a_world != "-":
                rank_rows.append({
                    "Event": ev_name,
                    "NR (Single)": s_country, "CR (Single)": s_cont, "WR (Single)": s_world,
                    "NR (Avg)": a_country, "CR (Avg)": a_cont, "WR (Avg)": a_world
                })
            
        if rank_rows:
            rdf = pd.DataFrame(rank_rows)
            st.dataframe(
                rdf.set_index("Event"), 
                use_container_width=True,
                column_config={
                    "NR (Single)": st.column_config.NumberColumn("NR (Single)", format="%d"),
                    "CR (Single)": st.column_config.NumberColumn("CR (Single)", format="%d"),
                    "WR (Single)": st.column_config.NumberColumn("WR (Single)", format="%d"),
                    "NR (Avg)": st.column_config.NumberColumn("NR (Avg)", format="%d"),
                    "CR (Avg)": st.column_config.NumberColumn("CR (Avg)", format="%d"),
                    "WR (Avg)": st.column_config.NumberColumn("WR (Avg)", format="%d"),
                }
            )
        else:
            st.info("No ranking data available.")

def render_competitions_tab(data):
    st.header("🌍 Competitions Hub")
 
    tab1, tab2, tab3 = st.tabs(["📜 History List", "🗺️ Travel Map", "🔥 Competition Heatmap"])
    
    with tab1:
        render_competition_list(data)
        
    with tab2:
        render_competition_map(data)
        
    with tab3:
        render_activity_heatmap(data)

def render_scrambles(data):
    # --- CSS PARA ARREGLAR MÓVILES ---
    st.markdown("""
        <style>
            /* Forzar que el código salte de línea y no se salga de la pantalla */
            code {
                white-space: pre-wrap !important;
                word-break: break-word !important;
                font-size: 0.85rem !important;
            }
            /* Optimizar espaciado en contenedores para móviles */
            [data-testid="stVerticalBlock"] {
                gap: 0.5rem;
            }
        </style>
    """, unsafe_allow_html=True)

    # --- 1. CONFIGURACIÓN Y MAPEOS (Igual que antes) ---
    twizzle_puzzle_map = {
        '333': '3x3x3', '222': '2x2x2', '444': '4x4x4', '555': '5x5x5', '666': '6x6x6', '777': '7x7x7',
        '333oh': '3x3x3', '333bf': '3x3x3', '333fm': '3x3x3',
        'minx': 'megaminx', 'pyram': 'pyraminx', 'skewb': 'skewb', 'clock': 'clock', 'sq1': 'square1',
        '444bf': '4x4x4', '555bf': '5x5x5', '333mbf': '3x3x3'
    }
    wca_event_map = {
        '333': '333', '222': '222', '444': '444', '555': '555', '666': '666', '777': '777',
        '333oh': '333', '333bf': '333', 'minx': 'minx', 'pyram': 'pyram', 
        'skewb': 'skewb', 'clock': 'clock', 'sq1': 'sq1', '444bf': '444', '555bf': '555'
    }

    st.header("🔀 Scrambles Explorer")

    # --- 2. SELECCIÓN DE COMPETICIÓN ---
    col_type, col_search = st.columns([1, 2])
    with col_type:
        mode = st.radio("Search mode:", ["My Competitions", "Manual ID"])

    comp_id = None
    if mode == "My Competitions":
        df = data.get("results", None)
        if df is not None and not df.empty:
            comps_df = df[['CompName', 'CompDate', 'Competition']].drop_duplicates().sort_values(by='CompDate', ascending=False)
            selected_comp_name = st.selectbox("Select one of your comps:", comps_df['CompName'])
            comp_id = comps_df[comps_df['CompName'] == selected_comp_name].iloc[0]['Competition']
        else:
            st.warning("No personal competition history found.")
    else:
        comp_id = st.text_input("Enter WCA Competition ID:", placeholder="Example: SpanishChampionship2025").strip()

    if not comp_id: return

    # --- 3. CARGA DE DATOS ---
    import functions as fn 
    scramble_data = fn.get_scrambles(comp_id)
    if not scramble_data:
        st.warning(f"No public scrambles available for '{comp_id}'.")
        return

    st.info(f"Showing: **{comp_id}**")
    
    # --- 4. SELECTORES Y VISTA ---
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        selected_event_code = st.selectbox("Event:", list(scramble_data.keys()))
    with col_sel2:
        available_rounds = list(scramble_data[selected_event_code].keys())
        round_map = {'1': 'First Round', '2': 'Second Round', '3': 'Semi-final', 'f': 'Final', 'c': 'Combined Final', 'd': 'Combined First Round'}
        round_options = {round_map.get(r, f"Round {r}"): r for r in available_rounds}
        selected_round_code = round_options[st.selectbox("Round:", list(round_options.keys()))]

    view_type = st.segmented_control("View:", ["2D", "3D"], default="2D")
    st.divider()

    # --- 5. PROCESAMIENTO DE GRUPOS (Simplificado para el ejemplo) ---
    groups_data = scramble_data[selected_event_code][selected_round_code]
    processed_groups = {}
    for group_id, scramble_list in groups_data.items():
        if selected_event_code == '333mbf':
            # ... (tu lógica de MBF se mantiene igual)
            pass 
        else:
            processed_groups[group_id] = scramble_list

    # --- 6. RENDERIZADO FINAL ---
    for g_id in sorted(processed_groups.keys()):
        current_scrambles = processed_groups[g_id]
        with st.container(border=True):
            st.subheader(f"📂 Group {g_id}")
            for item in current_scrambles:
                num = item['num']
                scram_str = item['scramble'].replace('\n', ' ') if selected_event_code == 'minx' else item['scramble']
                label_num = f"E{num}" if item.get('is_extra') else f"{num}"
                
                puzzle_twizzle = twizzle_puzzle_map.get(selected_event_code, '3x3x3')
                puzzle_wca = wca_event_map.get(selected_event_code, '333')
                twizzle_url = f"https://alpha.twizzle.net/edit/?setup-alg={urllib.parse.quote(scram_str)}&puzzle={puzzle_twizzle}"
                
                # Ajustamos el ratio de columnas para que el texto tenga más espacio [1, 3]
                c_img, c_text = st.columns([1, 3]) 
                
                with c_img:
                    html_code = f"""
                    <script src="https://cdn.cubing.net/v0/js/scramble-display" type="module"></script>
                    <style>
                        body {{ margin: 0; background: transparent; display: flex; justify-content: center; align-items: center; overflow: hidden; }}
                        scramble-display {{ width: 120px; height: 120px; --scramble-display-bg-color: transparent; }}
                    </style>
                    <scramble-display event="{puzzle_wca}" scramble="{scram_str}" visualization="{view_type}"></scramble-display>
                    """
                    components.html(html_code, height=130)
                
                with c_text:
                    # Título y botón más compactos
                    col_t1, col_t2 = st.columns([1, 2])
                    col_t1.markdown(f"**{label_num}.**")
                    col_t2.markdown(f'''<a href="{twizzle_url}" target="_blank"><button style="width:100%; font-size:10px; cursor:pointer; border-radius:5px; border:1px solid #ddd; padding: 2px; background-color: #f9f9f9;">See in 🌐 Twizzle</button></a>''', unsafe_allow_html=True)
                    
                    # El CSS de arriba hará que esto salte de línea automáticamente
                    st.code(scram_str, language=None)
                
                if item != current_scrambles[-1]:
                    st.markdown("<hr style='margin: 5px 0; opacity: 0.1;'>", unsafe_allow_html=True)

def render_personal_bests_cards(data):
    st.header("🏆 Personal Bests")
    df = data["results"].copy()
    if df.empty: return

    # Definimos la referencia temporal real (Hoy)
    today = pd.Timestamp.now().normalize() 

    # --- SECCIÓN DE FILTROS ---
    with st.expander("📅 Time period", expanded=True):
        c1, c2 = st.columns([1, 2])
        
        filter_type = c1.selectbox(
            "Select the period:", 
            ["All Time", "Past Year", "Current Year", "Custom Range"]
        )
        
        df_filtered = df.copy()

        if filter_type == "Past Year":
            # Un año exacto hacia atrás desde hoy
            start_date = today - pd.DateOffset(years=1)
            df_filtered = df[(df['CompDate'] >= start_date) & (df['CompDate'] <= today)]
            st.info(f"Mostrando resultados desde el {start_date.strftime('%d/%m/%Y')} hasta hoy.")

        elif filter_type == "Current Year":
            # Desde el 1 de enero del año actual
            start_date = pd.Timestamp(year=today.year, month=1, day=1)
            df_filtered = df[(df['CompDate'] >= start_date) & (df['CompDate'] <= today)]
            st.info(f"Showing only results from  {today.year}")

        elif filter_type == "Custom Range":
            min_comp = df['CompDate'].min().to_pydatetime()
            date_range = c2.date_input(
                "Custom Range:",
                value=(min_comp, today.to_pydatetime()),
                max_value=today.to_pydatetime()
            )
            if isinstance(date_range, tuple) and len(date_range) == 2:
                df_filtered = df[(df['CompDate'] >= pd.to_datetime(date_range[0])) & 
                                 (df['CompDate'] <= pd.to_datetime(date_range[1]))]

    # Reemplazamos el DF original por el filtrado para los cálculos de PB
    df = df_filtered

    if df.empty:
        if filter_type == "All Time":
            st.warning("No results found. Have you competed yet? 😉")
        elif filter_type == "Current Year":
            st.warning("No results this year. Time to go to a comp!! 😉")
        else:
            st.warning("No results in this period!")
        return

    # Orden de eventos estándar
    ordered_events = [k for k in event_dict.keys() if k in df['Event'].unique()]

    for event_code in ordered_events:
        event_name = event_dict.get(event_code, event_code)
        ev_df = df[df['Event'] == event_code]
        
        # Lógica mejorada para encontrar PB
        best_single_row = ev_df[ev_df['best_cs'] > 0].sort_values(by=['best_cs', 'CompDate']).iloc[0] if not ev_df[ev_df['best_cs'] > 0].empty else None
        best_avg_row = ev_df[ev_df['avg_cs'] > 0].sort_values(by=['avg_cs', 'CompDate']).iloc[0] if not ev_df[ev_df['avg_cs'] > 0].empty else None

        if best_single_row is None and best_avg_row is None: continue

        st.subheader(event_name)
        c1, c2 = st.columns(2)

        with c1:
            if best_single_row is not None:
                s_time = fn.format_wca_time(best_single_row['best_cs'], event_code=event_code)
                s_date = best_single_row['CompDate'].strftime('%d %b %Y') if pd.notnull(best_single_row['CompDate']) else "Unknown"
                render_pr_card("SINGLE", s_time, best_single_row['CompName'], s_date)
            else:
                st.info("No Single result")

        with c2:
            if best_avg_row is not None:
                a_time = fn.format_wca_time(best_avg_row['avg_cs'], event_code=event_code)
                a_date = best_avg_row['CompDate'].strftime('%d %b %Y') if pd.notnull(best_avg_row['CompDate']) else "Unknown"
                render_pr_card("AVERAGE", a_time, best_avg_row['CompName'], a_date)
            else:
                st.write("")

def render_statistics(data):
    st.header("📊 Statistics")
    df = data["results"]
    if not df.empty:
        c1, c2 = st.columns(2)
        with c1:
            with c1:
                st.subheader("Round Breakdown")
                event_counts = df['Event'].value_counts().reset_index()
                event_counts.columns = ['EventID', 'Count']
                
                event_order = list(event_dict.keys())
                event_counts['sort_order'] = event_counts['EventID'].apply(
                    lambda x: event_order.index(x) if x in event_order else 999
                )
                
                # Ordenar y limpiar
                event_counts = event_counts[event_counts['sort_order'] != 999].sort_values('sort_order')
                event_counts['Event Name'] = event_counts['EventID'].map(event_dict)
                
                # Dibujar con Plotly asegurando que no re-ordene por tamaño
                fig = px.pie(event_counts, values='Count', names='Event Name', hole=0.5)
                fig.update_traces(sort=False) # IMPORTANTE: Esto mantiene nuestro orden
                st.plotly_chart(fig, use_container_width=True)

        with c2:
            with c2:
                st.subheader("PR Count by Event")
                # 1. Obtener los PRs ignorando el total
                pr_data = data["stats_prs"].copy()
                pr_data.pop('total', None)
                
                if pr_data:
                    # 2. Crear DataFrame
                    pr_df = pd.DataFrame(list(pr_data.items()), columns=['EventID', 'Count'])
                    
                    # 3. Definir el orden estricto basado en tu event_dict
                    event_order = list(event_dict.keys())
                    
                    # 4. Crear columna de orden: si el evento no está en el dict, va al final (999)
                    pr_df['sort_order'] = pr_df['EventID'].apply(
                        lambda x: event_order.index(x) if x in event_order else 999
                    )
                    
                    # 5. Filtrar eventos "fantasma" o muy antiguos que no quieras (opcional)
                    # Si quieres que 333ft no aparezca si no está en tu dict:
                    pr_df = pr_df[pr_df['sort_order'] != 999]
                    
                    # 6. Mapear los nombres amigables (333 -> 3x3x3)
                    pr_df['Event Name'] = pr_df['EventID'].map(event_dict)
                    
                    # 7. Ordenar físicamente el DataFrame
                    pr_df = pr_df.sort_values('sort_order')
                    
                    # 8. Dibujar usando el nombre amigable
                    st.bar_chart(pr_df.set_index('Event Name')['Count'])
                else:
                    st.info("No PRs recorded yet.")

def render_activity_heatmap(data):
    st.header("🗓️ Competition Heatmap")
    df = data["results"]
    if df.empty:
        st.warning("No data available.")
        return

    # Preparar datos
    heatmap_data = fn.get_heatmap_data(df)
    pivot_df = heatmap_data.pivot(index='Year', columns='Month', values='Count').fillna(0)
    
    for m in range(1, 13):
        if m not in pivot_df.columns: pivot_df[m] = 0
    
    pivot_df = pivot_df[sorted(pivot_df.columns)]
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # 1. Selector de escala de colores
    colores_dict = {
        "Azules 🔵": "Blues",
        "Rojos 🔴": "Reds",
        "Verdes 🟢": "Greens",
        "Morados 🟣": "Purples",
        "Naranja y Sol ☀️": "YlOrRd",
        "Glaciar ❄️": "Ice",
        "Viridis (Pro) 🌈": "Viridis"
    }
    
    col_selector, _ = st.columns([1, 2])
    with col_selector:
        seleccion = st.selectbox("Elige el estilo del mapa:", list(colores_dict.keys()), index=0)
    
    escala_elegida = colores_dict[seleccion]

    # 2. Cálculo de altura dinámica
    # Base de 150px + 35px por cada año en el índice
    num_years = len(pivot_df.index)
    dynamic_height = 150 + (num_years * 35)

    # 3. Creación del gráfico
    fig = go.Figure(data=go.Heatmap(
        z=pivot_df.values,
        x=month_names,
        y=pivot_df.index.astype(str),
        colorscale=escala_elegida,
        xgap=3, 
        ygap=3,
        hovertemplate='<b>Año %{y}</b><br>Mes: %{x}<br>Competiciones: %{z}<extra></extra>'
    ))

    fig.update_layout(
        height=dynamic_height, # Aplicamos la altura calculada
        xaxis_nticks=12, 
        xaxis=dict(side="top"), # Meses arriba para mejor lectura
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=40, b=10),
    )

    st.plotly_chart(fig, use_container_width=True)

def render_competition_list(data):
    st.header("📋 Competition History")
    df = data["results"].copy()
    
    if not df.empty:
        # 1. Agrupar obteniendo eventos únicos
        comps = df.groupby(['CompName', 'CompDate', 'Country'])['Event'].unique().reset_index()
        comps = comps.sort_values(by="CompDate", ascending=False)
        
        comps['Date'] = comps['CompDate'].dt.strftime('%Y-%m-%d')
        comps['Location'] = comps['Country'].apply(lambda x: f"{fn.get_flag_emoji(x)} {fn.get_country_name(x)}")
    
        # --- PREPARAR EL ORDEN CORRECTO ---
        wca_order_keys = list(event_dict.keys())

        # 2. Generador de HTML con iconos
        def get_event_icons_html(event_list):
            html = '<div style="display: flex; flex-wrap: wrap; gap: 4px;">'
            
            # ### CORRECCIÓN DE ORDEN ###
            # Ordenamos usando el índice en la lista de claves de event_dict.
            # Si un evento no está en el dict (raro), lo mandamos al final (999).
            sorted_events = sorted(
                event_list, 
                key=lambda x: wca_order_keys.index(x) if x in wca_order_keys else 999
            )
            # ############################

            for ev in sorted_events:
                icon_url = f"https://raw.githubusercontent.com/cubing/icons/main/src/svg/event/{ev}.svg"
                html += f'<img src="{icon_url}" class="wca-icon" title="{event_dict.get(ev, ev)}">'
            html += "</div>"
            return html

        comps['Events'] = comps['Event'].apply(get_event_icons_html)
        final_view = comps[['Date', 'CompName', 'Location', 'Events']].rename(columns={'CompName': 'Competition'})
        
        # 3. Renderizar tabla HTML
        table_html = final_view.to_html(index=False, escape=False)
        
        # --- CSS PARA EL SCROLL INTERNO Y ESTILO ---
        st.markdown("""
        <style>
        .wca-scroll-container {
            width: 100%;
            overflow-x: auto; /* Permite scroll horizontal en móviles */
            max-height: 450px; 
            overflow-y: auto;
            border: 1px solid rgba(49, 51, 63, 0.2);
            border-radius: 8px;
        }

        .wca-table {
            width: 100%;
            min-width: 600px; /* Evita que las columnas se colapsen en pantallas pequeñas */
            border-collapse: collapse;
            font-family: sans-serif;
            font-size: 14px;
        }

        /* Estilo para los Cabeceros */
        .wca-table thead th {
            position: sticky;
            top: 0;
            z-index: 10;
            background-color: #e0e0e0; /* Gris claro para destacar */
            color: #000000 !important; /* Texto negro forzado */
            font-weight: bold;
            padding: 12px;
            text-align: left;
            border-bottom: 2px solid #ccc;
        }

        .wca-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid rgba(128, 128, 128, 0.2);
        }

        /* Ajuste de Iconos para Modo Oscuro */
        img.wca-icon {
            width: 22px !important;
            height: 22px !important;
            object-fit: contain;
            display: inline-block !important;
            filter: none;
        }

        @media (prefers-color-scheme: dark) {
            /* Invierte los iconos WCA de negro a blanco en modo oscuro */
            img.wca-icon {
                filter: invert(1) brightness(2);
            }
            /* Mantiene el cabecero legible en modo oscuro */
            .wca-table thead th {
                background-color: #cccccc; 
                color: #000000 !important;
            }
            .wca-table td {
                color: #ffffff;
            }
        }
        </style>
        """, unsafe_allow_html=True)

        table_html = final_view.to_html(index=False, escape=False)
        table_html = table_html.replace('<table border="1" class="dataframe">', '<table class="wca-table">')
        st.markdown(f'<div class="wca-scroll-container">{table_html}</div>', unsafe_allow_html=True)

def render_competition_map(data):
    st.header("🌍 World Map of Competitions")
    map_df = pd.DataFrame(data["map_data"])
    
    if map_df.empty:
        st.warning("No location data available to display the map.")
        return

    # --- 1. Lógica de Jitter (Mantener para evitar solapamiento visual) ---
    map_df['pos_key'] = map_df['lat'].astype(str) + map_df['lon'].astype(str)
    metres_in_degrees = 0.000045 
    
    def apply_jitter(group):
        if len(group) > 1:
            for i in range(len(group)):
                angle = 2 * np.pi * i / len(group)
                group.iloc[i, group.columns.get_loc('lat')] += metres_in_degrees * np.cos(angle)
                group.iloc[i, group.columns.get_loc('lon')] += metres_in_degrees * np.sin(angle)
        return group

    map_df = map_df.groupby('pos_key', group_keys=False).apply(apply_jitter)

    # --- 2. Lógica para encontrar el centro más denso (NUEVO) ---
    # Creamos columnas temporales redondeando las coordenadas (aprox. 1 grado ~ 111km)
    # Esto agrupa competiciones que ocurrieron en la misma región/ciudad grande.
    map_df['lat_cluster'] = map_df['lat'].round(0)
    map_df['lon_cluster'] = map_df['lon'].round(0)
    
    # Encontramos el cluster con más ocurrencias
    if not map_df.empty:
        # idxmax devuelve el índice (lat, lon) del grupo más grande
        densest_region = map_df.groupby(['lat_cluster', 'lon_cluster']).size().idxmax()
        center_lat, center_lon = densest_region
        initial_zoom = 5  # Zoom más cercano (nivel país/región)
    else:
        # Fallback por si acaso
        center_lat = map_df['lat'].mean()
        center_lon = map_df['lon'].mean()
        initial_zoom = 1.5

    view_state = pdk.ViewState(
        latitude=center_lat, 
        longitude=center_lon,
        zoom=initial_zoom, 
        pitch=0
    )
    
    # --- 3. Renderizado ---
    layer = pdk.Layer(
        "ScatterplotLayer", map_df,
        get_position='[lon, lat]', 
        get_color='[255, 75, 75, 200]',
        radius_min_pixels=5, 
        radius_max_pixels=15,
        pickable=True, 
        stroked=True,
        line_width_min_pixels=1, 
        get_line_color=[255, 255, 255]
    )
    
    st.pydeck_chart(pdk.Deck(
        map_style='https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
        initial_view_state=view_state, 
        layers=[layer],
        tooltip={"text": "{nombre}\n📅 {fecha}"}
    ))

def render_progression(data):
    st.header("📈 Personal Best Progression")
    
    # Check for data
    if 'results' not in data:
        st.warning("No results found.")
        return

    df = data["results"].copy()
    if df.empty: 
        st.warning("No data available.")
        return

    # Dictionary of available events in the user's data
    # (assuming event_dict is available globally or imported from functions)
    # If event_dict is not in scope, we define a basic one or use the keys from df
    # For safety, I will assume event_dict exists as in previous context, 
    # but I'll add a fallback just in case.
    event_dict_local = {
        '333': '3x3x3', '222': '2x2x2', '444': '4x4x4', '555': '5x5x5',
        '666': '6x6x6', '777': '7x7x7', '333bf': '3x3x3 Blindfolded',
        '333fm': '3x3x3 Fewest Moves', '333oh': '3x3x3 One-Handed',
        'clock': 'Clock', 'minx': 'Megaminx', 'pyram': 'Pyraminx',
        'skewb': 'Skewb', 'sq1': 'Square-1', '444bf': '4x4x4 Blindfolded',
        '555bf': '5x5x5 Blindfolded', '333mbf': '3x3x3 Multi-Blind'
    }
    
    # Filter available events
    available_events_codes = [e for e in event_dict_local.keys() if e in df['Event'].unique()]
    
    # Map Name -> Code
    opts = {event_dict_local.get(e, e): e for e in available_events_codes}
    
    # --- SECTION 1: EVOLUTION GRAPH (Single Selection Only) ---
    st.subheader("Evolution Graph")
    
    c1, c2 = st.columns([3, 1])
    with c1:
        # "All Events" removed here as requested
        sel_name_graph = st.selectbox("Select Event (Graph):", list(opts.keys()), key="event_graph")
    with c2:
        type_sel_graph = st.selectbox("Type (Graph):", ["Single", "Average"], key="type_graph")

    sel_code_graph = opts[sel_name_graph]
    col_target_graph = 'best_cs' if type_sel_graph == "Single" else 'avg_cs'
    
    # Filter Data
    dfe_graph = df[(df['Event'] == sel_code_graph) & (df[col_target_graph] > 0)].copy()
    
    if not dfe_graph.empty:
        dfe_graph = dfe_graph.sort_values(by='CompDate')

        # --- MULTI-BLIND LOGIC (Points) ---
        is_mbld = (sel_code_graph == "333mbf")
        
        if is_mbld:
            # WCA Modern Format: 0DDTTTTTMM -> DD is (99 - Points).
            # We calculate Points = 99 - DD.
            # Example: 97... -> 97 diff -> 2 Points.
            dfe_graph['plot_value'] = dfe_graph[col_target_graph].apply(
                lambda x: (99 - (x // 10000000)) if x > 100000000 else 0
            )
            # For Points, Higher is Better (cummax)
            dfe_graph['pr_so_far'] = dfe_graph['plot_value'].cummax()
            y_label = "Points (Solved - Missed)"
            marker_color = '#4B4BFF'
            
            # Keep rows where PB improves (Points increase)
            pr_history = dfe_graph[dfe_graph['plot_value'] == dfe_graph['pr_so_far']].drop_duplicates(subset=['plot_value'])
        
        else:
            # --- STANDARD LOGIC (Time/Moves) ---
            is_fmc = (sel_code_graph == "333fm")
            div = 1 if (is_fmc and type_sel_graph == "Single") else 100

            dfe_graph['plot_value'] = dfe_graph[col_target_graph] / div
            
            # For Time/Moves, Lower is Better (cummin)
            dfe_graph['pr_so_far'] = dfe_graph[col_target_graph].cummin()
            y_label = "Moves" if is_fmc else "Time (s)"
            marker_color = '#FF4B4B'
            
            # Keep rows where PB improves (Time decreases)
            pr_history = dfe_graph[dfe_graph[col_target_graph] == dfe_graph['pr_so_far']].drop_duplicates(subset=[col_target_graph])

        # Plot
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=pr_history['CompDate'], 
            y=pr_history['plot_value'], 
            mode='lines+markers', 
            name='Personal Best', 
            line=dict(color=marker_color, shape='hv')
        ))
        
        fig.update_layout(
            title=f"{sel_name_graph} Progression",
            yaxis_title=y_label,
            margin=dict(l=20, r=20, t=40, b=20),
            height=350
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available for this selection.")

    st.divider()

    # --- SECTION 2: YEAR-OVER-YEAR COMPARISON ---
    st.markdown("### 🗓️ Year-over-Year Comparison")
    
    cc1, cc2 = st.columns([3, 1])
    with cc1:
        # "All Events" added here
        comp_options = ["All Events"] + list(opts.keys())
        sel_name_comp = st.selectbox("Select Event (Comparison):", comp_options, key="event_comp")
    with cc2:
        type_sel_comp = st.selectbox("Type (Comparison):", ["Single", "Average"], key="type_comp")

    # Determine which events to process
    if sel_name_comp == "All Events":
        events_to_compare = available_events_codes
    else:
        events_to_compare = [opts[sel_name_comp]]

    # Select Years (Global for the loop)
    # We need to find all available years across the dataset to populate the dropdown
    df['Year'] = df['CompDate'].dt.year
    all_years = sorted(df['Year'].unique(), reverse=True)
    
    if len(all_years) < 2:
        st.info("You need results in at least two different years to compare.")
        return

    y_col1, y_col2 = st.columns(2)
    with y_col1:
        year1 = st.selectbox("Year 1 (Base):", all_years, index=min(1, len(all_years)-1), key="y1")
    with y_col2:
        year2 = st.selectbox("Year 2 (Target):", all_years, index=0, key="y2")

# --- LOOP THROUGH EVENTS ---
    found_any = False
    
    for code in events_to_compare:
        col_target = 'best_cs' if type_sel_comp == "Single" else 'avg_cs'
        
        # Filter for specific event
        sub_df = df[(df['Event'] == code) & (df[col_target] > 0)]
        
        if sub_df.empty:
            continue

        # Get best result for Year 1 and Year 2
        best_y1 = sub_df[sub_df['Year'] == year1][col_target].min()
        best_y2 = sub_df[sub_df['Year'] == year2][col_target].min()

        if pd.isna(best_y1) or pd.isna(best_y2):
            continue

        found_any = True
        event_name = event_dict_local.get(code, code)
        is_mbld_comp = (code == "333mbf")
        
        if is_mbld_comp:
            # Lógica de Puntos para MBLD
            p1 = (99 - (best_y1 // 10000000)) if best_y1 > 100000000 else 0
            p2 = (99 - (best_y2 // 10000000)) if best_y2 > 100000000 else 0
            diff = p2 - p1
            percent = ((p2 - p1) / p1 * 100) if p1 > 0 else 100.0 
            val1_str = f"{p1} pts"
            val2_str = f"{p2} pts"
            delta_val = f"{diff} pts"
        
        else:
            # Lógica para Tiempos y FMC
            is_fmc_c = (code == "333fm")
            # En WCA, los tiempos están en centésimas (cs)
            diff_cs = int(best_y1 - best_y2) 
            percent = ((best_y1 - best_y2) / best_y1) * 100
            
            val1_str = fn.format_wca_time(best_y1, event_code=code)
            val2_str = fn.format_wca_time(best_y2, event_code=code)

            # FORMATEO DE LA MEJORA (Improvement)
            if is_fmc_c:
                delta_val = f"{diff_cs} moves" if type_sel_comp == "Single" else f"{diff_cs/100:.2f} moves"
            else:
                # Si la mejora es de 60s o más, formateamos como M:SS.cc
                abs_diff = abs(diff_cs)
                if abs_diff >= 6000:
                    mins = abs_diff // 6000
                    secs = (abs_diff % 6000) // 100
                    cents = abs_diff % 100
                    # Añadimos signo negativo si empeoró (best_y2 > best_y1)
                    sign = "-" if diff_cs < 0 else ""
                    delta_val = f"{sign}{mins}:{secs:02d}.{cents:02d}s"
                else:
                    delta_val = f"{diff_cs/100:.2f}s"

        # Renderizado de métricas
        if sel_name_comp == "All Events":
            st.markdown(f"#### {event_name}")
            
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(f"PB {year1}", val1_str)
        m2.metric(f"PB {year2}", val2_str)
        
        # La delta se muestra verde si es positiva (mejora)
        # En tiempos, diff_cs es positivo si el tiempo bajó.
        m3.metric("Improvement", delta_val, delta=delta_val)
        m4.metric("Percentage", f"{percent:.1f}%", delta=f"{percent:.1f}%")
        
        if sel_name_comp == "All Events":
            st.divider()

    if not found_any and sel_name_comp == "All Events":
        st.info(f"No events found with data in both {year1} and {year2}.")
    elif not found_any and sel_name_comp != "All Events":
        st.info(f"No data for {sel_name_comp} in both selected years.")

def render_neighbours_tab(data):
    st.header("🤝 WCA Neighbours")
    st.info("Find the cubers that have attended the most competitions with you!")

    info = data.get('info', {})
    wca_id = info.get('person.wca_id') or info.get('id')
    results = data.get('results', pd.DataFrame())

    if not wca_id or results.empty:
        st.error("Insufficient data.")
        return

    # 1. Selección de año
    years = sorted(results['CompDate'].dt.year.unique().astype(int), reverse=True)
    options = ["All"] + [str(y) for y in years]
    
    col_sel, _ = st.columns([1, 2])
    selected_year_opt = col_sel.selectbox("📅 Select a year", options)

    if st.button(f"Search neighbours ({selected_year_opt})"):
        with st.spinner("Analyzing competitions..."):
            if selected_year_opt == "All":
                peopledict = {}
                for year in years:
                    # Asumiendo que fn está importado y disponible
                    df_y = fn.get_wca_neighbours(wca_id, year=str(year))
                    for _, row in df_y.iterrows():
                        name = row['Name']
                        count = row['Count']
                        peopledict[name] = peopledict.get(name, 0) + count
                
                if peopledict:
                    df_neigh = pd.DataFrame(list(peopledict.items()), columns=['Name', 'Count'])
                else:
                    df_neigh = pd.DataFrame()
            else:
                df_neigh = fn.get_wca_neighbours(wca_id, year=selected_year_opt)

        if df_neigh is not None and not df_neigh.empty:
            # 2. Limpieza de datos
            df_neigh = df_neigh.sort_values(by='Count', ascending=False).reset_index(drop=True)
            my_name = info.get('person.name') or info.get('name')
            df_neigh = df_neigh[df_neigh['Name'] != my_name]

            # --- LÓGICA DE PODIO ---
            unique_counts = sorted(df_neigh['Count'].unique(), reverse=True)
            podium_slots = []
            names_in_podium = []
            current_total_people = 0

            # Definimos medallas y colores
            tiers = [
                {"medal": "🥇", "color": "#FFD700"},
                {"medal": "🥈", "color": "#C0C0C0"},
                {"medal": "🥉", "color": "#CD7F32"}
            ]

            for count_value in unique_counts:
                if current_total_people >= 3: break
                
                people_at_this_level = df_neigh[df_neigh['Count'] == count_value]['Name'].tolist()
                tier = tiers[len(podium_slots)]
                
                podium_slots.append((people_at_this_level, tier["medal"], tier["color"], count_value))
                names_in_podium.extend(people_at_this_level)
                current_total_people += len(people_at_this_level)

            # --- RENDERIZADO DE PODIO ---
            st.subheader(f"Top companions in {selected_year_opt}")
            cols_podium = st.columns(len(podium_slots))

            for i, (names, medal, color, count) in enumerate(podium_slots):
                names_display = "<br>".join(names)
                with cols_podium[i]:
                    st.markdown(f"""
                    <div style="background-color: {color}22; padding: 15px; border-radius: 15px; 
                         border: 2px solid {color}; text-align: center; min-height: 200px; 
                         display: flex; flex-direction: column; justify-content: center;">
                        <h1 style="margin:0;">{medal}</h1>
                        <div style="font-size: 24px; font-weight: 800; margin: 10px 0;">
                            {count} <span style="font-size: 14px; font-weight: 400;">Comps</span>
                        </div>
                        <div style="font-size: 14px; line-height: 1.2;">{names_display}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
            st.markdown("---")

            # --- SECCIÓN RESTO DE LA LISTA ---
            df_others = df_neigh[~df_neigh['Name'].isin(names_in_podium)].head(20)
            
            if not df_others.empty:
                with st.expander("See rest of cubers", expanded=True):
                    current_rank = len(names_in_podium) + 1
                    max_count = df_neigh['Count'].max()
                    
                    others_grouped = df_others.groupby('Count', sort=False)
                    for count, group in others_grouped:
                        num_people_in_tie = len(group)
                        for _, row in group.iterrows():
                            c1, c2 = st.columns([3, 1])
                            c1.write(f"{current_rank}. **{row['Name']}**")
                            c2.caption(f"{row['Count']} matches")
                            st.progress(row['Count'] / max_count)
                        current_rank += num_people_in_tie

            # Botón de descarga
            st.download_button(
                "Download complete list (CSV)",
                df_neigh.to_csv(index=False),
                f"neighbours_wca_{selected_year_opt}.csv",
                "text/csv"
            )
        else:
            st.warning("No matches found.")

def render_organizer_tab(data):
    # Intentamos obtener el nombre real del usuario desde la info cargada
    info = data.get("info", {})
    # Flattened dict keys: 'person.name' suele ser la clave tras aplanar
    user_name = info.get("person.name") 
    
    if not user_name:
        st.error("Could not identify the organizer name from the WCA ID.")
        return

    st.header(f"📋 Competitions organized by {user_name}")

    # Llamamos a la función de búsqueda (esto puede tardar unos segundos, por eso el spinner)
    with st.spinner(f"Searching organized competitions for {user_name}..."):
        # Usamos cache de sesión simple para no buscar cada vez que cambias de pestaña pequeña
        if 'organized_df' not in st.session_state or st.session_state.get('org_name') != user_name:
            df_org = fn.get_organized_competitions(user_name)
            st.session_state['organized_df'] = df_org
            st.session_state['org_name'] = user_name
        else:
            df_org = st.session_state['organized_df']

    if df_org.empty:
        st.warning(f"No organized competitions found for '{user_name}'. Check if the WCA name matches exactly.")
        return

    # 1. Total arriba
    st.metric("Total Organized", len(df_org))
    st.divider()

    # 2. Mosaico por años
    # Obtenemos años únicos ordenados descendentemente
    years = sorted(df_org['Year'].unique(), reverse=True)

    # 2. Mosaico por años
    # Obtenemos años únicos ordenados descendentemente
    years = sorted(df_org['Year'].unique(), reverse=True)

    for year in years:
        # Filtramos primero para poder contar
        comps_year = df_org[df_org['Year'] == year]
        count_year = len(comps_year)
        
        # Mostramos Año y Cantidad entre paréntesis
        st.subheader(f"{year} ({count_year})")
        
        # Creamos un grid de 3 columnas para las tarjetas
        cols = st.columns(3)
        for idx, (_, row) in enumerate(comps_year.iterrows()):
            with cols[idx % 3]:
                with st.container(border=True):
                    st.markdown(f"**{row['Nombre']}**")
                    st.caption(f"📍 {row['city']}, {row['country']}")
                    
                    # --- LÓGICA DE FECHAS (Incluye la mejora de la respuesta anterior) ---
                    start = row['date_start']
                    end = row['date_end']
                    days = row['no_days']

                    if days > 1:
                        if start.month == end.month:
                            date_str = f"{start.strftime('%d')} - {end.strftime('%d %b')}"
                        else:
                            date_str = f"{start.strftime('%d %b')} - {end.strftime('%d %b')}"
                    else:
                        date_str = start.strftime('%d %b')
                    
                    st.text(f"📅 {date_str}")
                    # ---------------------------------------------------------------------
                    
                    # Link a la web de la WCA
                    wca_url = f"https://www.worldcubeassociation.org/competitions/{row['id']}"
                    st.markdown(f"[View on WCA]({wca_url})")

####### STREAMLIT APP MAIN LOGIC ###########

st.sidebar.title("🎲 MyCubing")
wca_id_input = st.sidebar.text_input("WCA ID", placeholder="2016LOPE37").upper().strip()

selection = st.sidebar.radio("Go to:", [
    "📝 Summary", 
    "🏆 Personal Bests", 
    "🌍 Competitions",      
    "📊 Statistics", 
    "📈 Progression",
    "🔀 Scrambles",
    "🤝 WCA Neighbours",
    "📋 Organized comps"
])

if wca_id_input:
    with st.spinner(f"Fetching data for {wca_id_input}... (This runs faster after the first load)"):
        data = load_all_data(wca_id_input)

    if data:
        if selection == "📝 Summary": 
            render_summary_enhanced(data, wca_id_input) 
        elif selection == "🏆 Personal Bests": 
            render_personal_bests_cards(data)  
        elif selection == "🌍 Competitions": 
            render_competitions_tab(data)   
        elif selection == "📊 Statistics": 
            render_statistics(data)
        elif selection == "📈 Progression": 
            render_progression(data)
        elif selection == "🔀 Scrambles":
            render_scrambles(data)
        elif selection == "🤝 WCA Neighbours":
            render_neighbours_tab(data)
        elif selection == "📋 Organized comps": 
            render_organizer_tab(data)
        name = data['info'].get('person.name', wca_id_input)
        st.sidebar.success(f"Loaded: {name}")
    else:
        st.sidebar.error("Profile not found or API error.")
else:
    st.title("🎲 Welcome to MyCubing!")
    st.markdown("Enter your **WCA ID** in the sidebar to see your advanced stats.")