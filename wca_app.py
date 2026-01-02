### IMPORTS ###

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import functions as fn
import numpy as np
import pydeck as pdk
import subprocess 
import os          


st.set_page_config(page_title="MyCubing Dashboard", layout="wide", page_icon="🎲")

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
    </style>
    """, unsafe_allow_html=True)

st.markdown("""
<style>
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

### HELPER FUNCTIONS ###
def render_metric(label, value):
    with st.container(border=True):
        st.metric(label=label, value=value)

# --- CONFIGURACIÓN TNOODLE (AJUSTA TU RUTA AQUÍ) ---
# current working directory
cd = os.getcwd()
CLI_BIN_PATH = os.path.join(cd, "tnoodle", "bin")
OUTPUT_FOLDER = os.path.join(os.getcwd(), "scramble_images")

# Asegurar que existe la carpeta
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

def generate_scramble_image(puzzle_id, scramble_string, unique_filename):
    """
    Genera la imagen usando tnoodle localmente.
    Devuelve la ruta completa de la imagen.
    """
    full_output_path = os.path.join(OUTPUT_FOLDER, unique_filename)
    
    # OPTIMIZACIÓN: Si la imagen ya existe, no la regeneramos para no bloquear la app
    if os.path.exists(full_output_path):
        return full_output_path

    # Mapeo básico de ids de WCA a tnoodle si fuera necesario
    # (tnoodle suele usar '333', '222', etc., igual que tu app, pero 'pyram' -> 'minx' a veces varía)
    # Por ahora pasamos el id directo.
    
    command = [
        "tnoodle", 
        "draw",
        "--puzzle", puzzle_id,
        "--scramble", scramble_string,
        "--output", full_output_path
    ]
    
    try:
        result = subprocess.run(
            command, 
            capture_output=True, 
            text=True, 
            shell=True, 
            cwd=CLI_BIN_PATH
        )
        
        if result.returncode == 0:
            return full_output_path
        else:
            st.error(f"Error tnoodle: {result.stderr}")
            return None
    except Exception as e:
        st.error(f"Error ejecutando subproceso: {e}")
        return None

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
def render_summary(data, wca_id): # legacy version
    info = data["info"]
    iso_code = info.get('person.country.iso2', 'N/A')
    flag = fn.get_flag_emoji(iso_code)
    
    st.header(f"{flag} {info.get('person.name', wca_id)}")
    st.caption(f"WCA ID: {wca_id}")
    st.divider()

    st.subheader("Activity")
    c1, c2 = st.columns(2)
    with c1: render_metric("🗓️ Competitions", info.get('competition_count', len(data['results']['Competition'].unique())))
    
    last_comp = "N/A"
    if not data['results'].empty:
        last_comp = data['results'].iloc[0]['CompName']
        
    with c2: render_metric("🏟️ Last Comp", last_comp)

    st.subheader("Medals")
    m1, m2, m3 = st.columns(3)
    with m1: render_metric("🥇 Gold", info.get('medals.gold', 0))
    with m2: render_metric("🥈 Silver", info.get('medals.silver', 0))
    with m3: render_metric("🥉 Bronze", info.get('medals.bronze', 0))

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
    st.header("🧩 Scrambles Viewer (Tnoodle Local)")
    
    df = data["results"]
    if df.empty: return

    # --- 1. Selectores ---
    comps_df = df[['CompName', 'CompDate', 'Competition']].drop_duplicates().sort_values(by='CompDate', ascending=False)
    selected_comp_name = st.selectbox("Select Competition:", comps_df['CompName'])
    
    if not selected_comp_name: return

    comp_specific_df = df[df['CompName'] == selected_comp_name]
    # get events of that competition get_comp_data(compid)['events']
    comp_events_codes = fn.get_comp_data(comp_specific_df.iloc[0]['Competition'])['events']
    
    event_options = {event_dict.get(code, code): code for code in comp_events_codes}
    
    selected_event_name = st.selectbox("Select Event:", list(event_options.keys()))
    selected_event_code = event_options[selected_event_name] # ej: '333', '222'

    # valid names for events two, three, four, four_fast, five, six, seven, three_ni, four_ni, five_ni, three_fm, pyra, sq1, mega, clock, skewb
    # do a dict and change the selected_event_code
    event_code_mapping = {
        '333': 'three',
        '222': 'two',
        '444': 'four',
        '555': 'five',
        '666': 'six',
        '333oh': 'three',
        '777': 'seven',
        '333bf': 'three_ni',
        '444bf': 'four_ni',
        '555bf': 'five_ni',
        '333fm': 'three_fm',
        'pyram': 'pyra',
        'sq1': 'sq1',
        'minx': 'mega',
        'clock': 'clock',
        'skewb': 'skewb'
    }
    
    selected_event_code = event_code_mapping.get(selected_event_code, selected_event_code)

    st.divider()

    # we load the wcif of the competition
    wcif_url = f'https://worldcubeassociation.org/api/v0/competitions/{comp_specific_df.iloc[0]["Competition"]}/wcif/public'
    wcif_data = fn.fetch_json(wcif_url)

    # now we cry because scrambles are not in the public wcif
    

    # --- 2. Datos Dummy para Sets A y B ---
    # En el futuro, esto vendrá de una base de datos o lógica real
    dummy_scrambles = ["D' R' U' R B2 U2 L D' F' R2 F2 B R2 D2 F R2 B' R2 D2 L ",
                        "F2 B R D' R' U2 L' F2 L2 F' D2 R2 B' U2 F2 U2 D2 L2 B L",
                        "F D' L' U' F2 R D' B' L U' L2 U' B2 R2 U L2 D2 R2 U L2 ",
                        "B' D' L2 U' L2 U' R2 D U B2 U B2 F2 L' R2 D R2 D' B U' R2 ",
                        "U' F' D2 R2 B2 U' L2 R2 U R2 U2 F2 R2 U2 F' L' B' D R U2 B2 "] 

    # --- 3. Función de renderizado por filas ---
    def render_set_rows(set_label, scrambles_list):
        with st.container(border=True):
            st.subheader(f"📂 {set_label}")
            
            for i, scram in enumerate(scrambles_list):
                # Crear nombre de archivo único para evitar colisiones
                # ej: 333_SetA_1.svg
                filename = f"{selected_event_code}_{set_label}_{i+1}.svg"
                
                # Generar imagen
                img_path = generate_scramble_image(selected_event_code, scram, filename)
                
                # --- DISEÑO EN FILA (ROW) ---
                # Columna 1 pequeña (Imagen), Columna 2 grande (Texto)
                c_img, c_text = st.columns([1, 4]) 
                
                with c_img:
                    if img_path and os.path.exists(img_path):
                        st.image(img_path, width=150)
                    else:
                        st.warning("Img fail")
                
                with c_text:
                    st.markdown(f"**{i+1}.**")
                    # Usamos st.code para que sea fácil de copiar y leer
                    st.code(scram, language=None)
                
                # Separador sutil entre mezclas
                if i < len(scrambles_list) - 1:
                    st.markdown("<hr style='margin: 5px 0; opacity: 0.3;'>", unsafe_allow_html=True)

    # Renderizamos los sets
    render_set_rows("Set A", dummy_scrambles)
    render_set_rows("Set B", dummy_scrambles)

def render_personal_bests_cards(data):
    st.header("🏆 Personal Bests")

    df = data["results"].copy()
    if df.empty: return

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

def render_competitions(data): # Legacy
    st.header("🌍 Competitions History")

    df = data["results"].copy()
    if not df.empty:
        # 1. Agrupar datos (Igual que antes)
        comps = df.groupby(['CompName', 'CompDate', 'Country'])['Event'].unique().reset_index()
        comps = comps.sort_values(by="CompDate", ascending=False)
        
        comps['Date'] = comps['CompDate'].dt.strftime('%Y-%m-%d')
        comps['Location'] = comps['Country'].apply(lambda x: f"{fn.get_flag_emoji(x)} {fn.get_country_name(x)}")
        
        # 2. Generar HTML de iconos (Con el arreglo de tamaño incluido)
        def get_event_icons_html(event_list):
            # Orden personalizado: 333 primero, luego 222, etc. o alfabético
            # Aquí usamos el orden que viene del groupby, o puedes hacer sorted(event_list)
            sorted_events = sorted(event_list) 
            
            html = '<div style="display: flex; flex-wrap: wrap; gap: 4px; align-items: center;">'
            for ev in sorted_events:
                icon_url = f"https://raw.githubusercontent.com/cubing/icons/main/src/svg/event/{ev}.svg"
                # Iconos ligeramente más pequeños (20px) para que la fila no sea gigante
                html += f'<img src="{icon_url}" class="wca-icon" title="{event_dict.get(ev, ev)}">'
            html += "</div>"
            return html

        comps['Events'] = comps['Event'].apply(get_event_icons_html)

        # Seleccionar columnas
        final_view = comps[['Date', 'CompName', 'Location', 'Events']].rename(columns={'CompName': 'Competition', 'Events': 'Events Participated', 'Location': 'Region'})
        
        # 3. Convertir a HTML
        table_html = final_view.to_html(index=False, escape=False)
        
        # 4. CSS "Nativo" de Streamlit
        # Este CSS imita los colores, fuentes y bordes de st.dataframe
        st.markdown("""
        <style>
        /* Contenedor con bordes redondeados como los widgets de Streamlit */
        .wca-table-container {
            border: 1px solid rgba(49, 51, 63, 0.2);
            border-radius: 0.5rem;
            overflow: hidden; /* Para que las esquinas redondeadas recorten la tabla */
            margin-bottom: 1rem;
        }

        .wca-table {
            width: 100%;
            border-collapse: collapse;
            font-family: "Source Sans Pro", sans-serif; /* Fuente nativa de Streamlit */
            font-size: 14px;
            color: rgb(49, 51, 63); /* Color texto oscuro estándar */
        }
        
        /* Ajustes para modo oscuro (automáticos si el navegador lo soporta, 
           pero Streamlit inyecta sus variables. Usamos transparencia para compatibilidad) */
        @media (prefers-color-scheme: dark) {
            .wca-table { color: #fafafa; }
            .wca-table-container { border-color: rgba(250, 250, 250, 0.2); }
        }

        .wca-table th {
            text-align: left;
            background-color: rgba(150, 150, 150, 0.1); /* Fondo gris sutil para cabecera */
            padding: 12px 16px;
            font-weight: 600;
            border-bottom: 1px solid rgba(49, 51, 63, 0.2);
        }

        .wca-table td {
            padding: 12px 16px;
            border-bottom: 1px solid rgba(49, 51, 63, 0.1);
            vertical-align: middle;
        }

        /* Hover effect en las filas */
        .wca-table tr:hover td {
            background-color: rgba(150, 150, 150, 0.05);
        }

        /* Control estricto de iconos */
        img.wca-icon {
            width: 22px !important;
            height: 22px !important;
            object-fit: contain;
            vertical-align: middle;
            margin: 0 !important;
        }
        
        /* Ocultar bordes de la tabla generada por pandas por defecto */
        .dataframe { border: none !important; }
        </style>
        """, unsafe_allow_html=True)

        # Renderizamos la tabla dentro del contenedor estilizado
        table_html = table_html.replace('<table border="1" class="dataframe">', '<table class="wca-table">')
        st.markdown(f'<div class="wca-table-container">{table_html}</div>', unsafe_allow_html=True)

    st.divider()

    # --- A. MAPA (Sin cambios) ---
    map_df = pd.DataFrame(data["map_data"])
    if not map_df.empty:
        # ... (Mantén el código del mapa aquí igual que antes) ...
        # (Para ahorrar espacio no lo copio de nuevo, pero asegúrate de dejarlo aquí)
        with st.expander("🗺️ View Map", expanded=True):
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

            view_state = pdk.ViewState(
                latitude=map_df['lat'].mean(), longitude=map_df['lon'].mean(),
                zoom=2, pitch=0
            )
            layer = pdk.Layer(
                "ScatterplotLayer", map_df,
                get_position='[lon, lat]', get_color='[255, 75, 75, 200]',
                radius_min_pixels=5, radius_max_pixels=15,
                pickable=True, stroked=True,
                line_width_min_pixels=1, get_line_color=[255, 255, 255]
            )
            st.pydeck_chart(pdk.Deck(
                map_style='https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
                initial_view_state=view_state, layers=[layer],
                tooltip={"text": "{nombre}\n📅 {fecha}"}
            ))

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
    df = data["results"].copy()
    if df.empty: return

    # Obtener eventos disponibles pero ordenarlos según event_dict
    available_events = [e for e in event_dict.keys() if e in df['Event'].unique()]
    opts = {event_dict[e]: e for e in available_events}
    
    c1, c2 = st.columns([3, 1])
    with c1:
        # El orden aquí será ahora siempre el de event_dict
        sel_name = st.selectbox("Select Event:", list(opts.keys()))
    with c2:
        type_sel = st.selectbox("Type:", ["Single", "Average"])

    sel_code = opts[sel_name]
    col_target = 'best_cs' if type_sel == "Single" else 'avg_cs'
    
    # Filtrar datos válidos
    dfe = df[(df['Event'] == sel_code) & (df[col_target] > 0) & (df['CompDate'].notnull())].copy()
    
    if dfe.empty:
        st.warning(f"No valid {type_sel} results found for this event.")
        return

    dfe = dfe.sort_values(by='CompDate', ascending=True)

    is_fmc = sel_code == "333fm"
    divisor = 1 if (is_fmc and type_sel == "Single") else 100
    unit = "moves" if is_fmc else "seconds"

    # Lógica de PB acumulado
    dfe['pr_so_far'] = dfe[col_target].cummin()
    pr_history = dfe[dfe[col_target] == dfe['pr_so_far']].drop_duplicates(subset=[col_target], keep='first')

    fig = go.Figure()

    # 1. Línea de PB
    fig.add_trace(go.Scatter(
        x=pr_history['CompDate'], 
        y=pr_history[col_target] / divisor,
        mode='lines+markers',
        name=f'PB {type_sel}',
        line=dict(color='#FF4B4B', width=3, shape='hv'),
        marker=dict(size=8, color='#FF4B4B')
    ))

    # 2. Todos los resultados
    fig.add_trace(go.Scatter(
        x=dfe['CompDate'],
        y=dfe[col_target] / divisor,
        mode='markers',
        name='All Results',
        marker=dict(size=4, color='rgba(0,0,0,0.1)'),
        hoverinfo='skip'
    ))

    # 3. Media Móvil (MA5)
    dfe['MA_5'] = dfe[col_target].rolling(window=5, min_periods=1).mean()
    fig.add_trace(go.Scatter(
        x=dfe['CompDate'],
        y=dfe['MA_5'] / divisor,
        mode='lines',
        name='Avg (Last 5)',
        line=dict(color='rgba(100, 100, 100, 0.4)', width=2, dash='dot')
    ))

    fig.update_layout(
        title=f"Evolution of {sel_name} ({type_sel})",
        xaxis_title="Date",
        yaxis_title=unit,
        hovermode="x unified",
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"🔴 Red line: Your {type_sel} personal record history. ⚫ Grey dots: All official results.")

# En wca_app.py

# En wca_app.py

def render_neighbours_tab(data):
    st.header("🤝 WCA Neighbours")
    st.info("Descubre con quién has compartido más competiciones.")

    info = data.get('info', {})
    wca_id = info.get('person.wca_id') or info.get('id')
    my_name = info.get('person.name') or info.get('name')
    results = data.get('results', pd.DataFrame())

    if not wca_id or results.empty:
        st.error("No hay datos suficientes para calcular vecinos.")
        return

    # --- NUEVO: Selector de Año ---
    # Extraemos los años únicos de las competiciones
    if 'CompDate' in results.columns and pd.api.types.is_datetime64_any_dtype(results['CompDate']):
        years = sorted(results['CompDate'].dt.year.unique().astype(int), reverse=True)
    else:
        years = []
    
    col1, col2 = st.columns([1, 3])
    with col1:
        # Añadimos la opción "Todos" al principio
        options = ["Todos"] + years
        selected_year_opt = st.selectbox("📅 Selecciona año", options)
    
    # Preparamos el valor para enviar a la función (None si es "Todos")
    selected_year = None if selected_year_opt == "Todos" else selected_year_opt

    # Botón de acción
    if st.button(f"Buscar Vecinos ({selected_year_opt})"):
        with st.spinner(f"Analizando competiciones de {selected_year_opt}..."):
            # Pasamos 'results' y el 'year' a la función
            df_neigh = fn.get_wca_neighbours(wca_id, year=selected_year)

        if df_neigh.empty:
            st.warning("No se encontraron coincidencias o hubo un error.")
            return

        if my_name:
            df_neigh = df_neigh[df_neigh['Name'] != my_name]

        st.subheader(f"Top coincidencia en {selected_year_opt}")
        
        # Gráfico
        fig = px.bar(
            df_neigh.head(15), 
            x='Count', 
            y='Name', 
            orientation='h',
            text='Count',
            title=f"Coincidencias ({selected_year_opt})",
            color='Count',
            color_continuous_scale='Viridis'
        )
        fig.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("Ver lista completa"):
            st.dataframe(df_neigh, use_container_width=True)


####### STREAMLIT APP MAIN LOGIC ###########

st.sidebar.title("🎲 MyCubing")
wca_id_input = st.sidebar.text_input("WCA ID", placeholder="2016LOPE37").upper().strip()

selection = st.sidebar.radio("Go to:", [
    "Summary", 
    "Personal Bests", 
    "Competitions",      
    "Statistics", 
    "Progression",
    "Scrambles",
    "WCA Neighbours"
])

if wca_id_input:
    with st.spinner(f"Fetching data for {wca_id_input}... (This runs faster after the first load)"):
        data = load_all_data(wca_id_input)

    if data:
        if selection == "Summary": 
            render_summary_enhanced(data, wca_id_input)
            
        elif selection == "Personal Bests": 
            render_personal_bests_cards(data)
            
        elif selection == "Competitions": 
            render_competitions_tab(data) 
            
        elif selection == "Statistics": 
            render_statistics(data)
            
        elif selection == "Progression": 
            render_progression(data)

        elif selection == "Scrambles":
            render_scrambles(data)

        elif selection == "WCA Neighbours":
            render_neighbours_tab(data)

        # Footer sidebar con nombre
        name = data['info'].get('person.name', wca_id_input)
        st.sidebar.success(f"Loaded: {name}")
    else:
        st.sidebar.error("Profile not found or API error.")
else:
    st.title("🎲 Welcome to MyCubing")
    st.markdown("Enter your **WCA ID** in the sidebar to see your advanced stats.")