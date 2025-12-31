import streamlit as st
import pandas as pd
import plotly.express as px
import functions as fn
import numpy as np
import pydeck as pdk # Necesario para tu mapa original

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="MyCubing Dashboard", layout="wide", page_icon="🎲")

# --- RESTAURACIÓN DE ESTILOS EXACTOS ---
st.markdown("""
    <style>
    /* Estilo para el valor de las métricas */
    [data-testid="stMetricValue"] { font-size: 24px; font-weight: bold; }
    
    /* Estilo para los contenedores (las "tarjetas" grises) */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 15px;
        background-color: #f8f9fa;
        padding: 15px;
    }
    
    /* TU CSS ORIGINAL para forzar columnas en móvil */
    [data-testid="column"] {
        min-width: 45% !important;
        flex: 1 1 45% !important;
    }

    @media (min-width: 768px) {
        [data-testid="column"] {
            min-width: 20% !important;
            flex: 1 1 20% !important;
        }
    }
    
    /* Ajuste extra para tablas */
    .stDataFrame { width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# Diccionario de Eventos
event_dict = {
    "333": "3x3x3", "222": "2x2x2", "444": "4x4x4", "555": "5x5x5", "666": "6x6x6", "777": "7x7x7",
    "333bf": "3x3 BF", "333oh": "3x3 OH", "333fm": "3x3 FMC", "minx": "Megaminx", 
    "pyram": "Pyraminx", "skewb": "Skewb", "sq1": "Square-1", "clock": "Clock", 
    "444bf": "4x4 BF", "555bf": "5x5 BF", "333mbf": "3x3 Multi-BF"
}

# --- 2. HELPERS VISUALES (RESTAURADOS) ---
def render_metric(label, value):
    """Muestra la métrica dentro de un contenedor con borde (estilo tarjeta original)"""
    with st.container(border=True):
        st.metric(label=label, value=value)

# --- 3. GESTIÓN DE DATOS (CACHÉ) ---
@st.cache_data(ttl=3600)
def load_all_data(wca_id):
    try:
        info = fn.get_wcaid_info(wca_id)
        results = fn.get_wca_results(wca_id)
        prs_dict = fn.prs_info(wca_id)
        stats_prs = fn.number_of_prs(wca_id)
        oldest, newest = fn.oldest_and_newest_pr(wca_id)
        map_data = list(fn.generate_map_data(wca_id))
        return {
            "info": info,
            "results": results,
            "prs_dict": prs_dict,
            "stats_prs": stats_prs,
            "oldest": oldest,
            "newest": newest,
            "map_data": map_data
        }
    except Exception as e:
        st.error(f"No se pudo cargar el perfil: {e}")
        return None

# --- 4. FUNCIONES DE PÁGINAS ---

def render_summary(data, wca_id):
    """Página: Resumen (Dashboard Principal)"""
    info = data["info"]
    iso_code = info.get('person.country.iso2', 'N/A')
    flag = fn.get_flag_emoji(iso_code)
    
    st.header(f"{flag} {info.get('person.name')}")
    st.caption(f"WCA ID: {wca_id} | Country: {iso_code}")
    st.divider()

    # SECTION 1: Activity
    st.subheader("Activity")
    act1, act2 = st.columns(2)
    with act1: render_metric("🗓️ Total Competitions", info.get('competition_count', 0))
    # Para Last Comp necesitamos un pequeño cálculo extra si no viene directo
    last_comp = data['results']['Competition'].iloc[0] if not data['results'].empty else "N/A"
    with act2: render_metric("🏟️ Last Competition", last_comp)

    # SECTION 2: Medals
    st.subheader("Medals & Podiums")
    m1, m2, m3 = st.columns(3)
    with m1: render_metric("🥇 Gold", info.get('medals.gold', 0))
    with m2: render_metric("🥈 Silver", info.get('medals.silver', 0))
    with m3: render_metric("🥉 Bronze", info.get('medals.bronze', 0))

    st.divider()
    
    # PRs Highlights (Usando tu estilo de tarjetas)
    col_old, col_new = st.columns(2)
    with col_old:
        if data["oldest"]:
            st.write("🕒 **Oldest PR (Still standing)**")
            cat_raw, details = data["oldest"]
            comp_name, fecha, tiempo, ev_name = details[1], details[2], details[3], event_dict.get(cat_raw.split('_')[0], cat_raw)
            with st.container(border=True):
                st.markdown(f"**{ev_name}**")
                st.markdown(f"## {tiempo}s")
                st.caption(f"🏆 {comp_name}")
                st.caption(f"📅 {fecha}")
                
    with col_new:
        if data["newest"]:
            st.write("✨ **Newest Personal Record**")
            cat_raw, details = data["newest"]
            comp_name, fecha, tiempo, ev_name = details[1], details[2], details[3], event_dict.get(cat_raw.split('_')[0], cat_raw)
            with st.container(border=True):
                st.markdown(f"**{ev_name}**")
                st.markdown(f"## {tiempo}s")
                st.caption(f"🏆 {comp_name}")
                st.caption(f"📅 {fecha}")

    # --- MAPA RESTAURADO (Pydeck) ---
    st.divider()
    st.subheader("📍 Competition map")
    
    map_df = pd.DataFrame(data["map_data"])
    
    if not map_df.empty:
        # Lógica de Jitter original restaurada
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
            latitude=map_df['lat'].mean(),
            longitude=map_df['lon'].mean(),
            zoom=3,
            pitch=0,
        )

        layer = pdk.Layer(
            "ScatterplotLayer",
            map_df,
            get_position='[lon, lat]',
            get_color='[255, 75, 75, 200]', # Rojo WCA
            radius_min_pixels=6, 
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
    else:
        st.info("No location data available.")

def render_personal_bests(data):
    st.header("🏆 Personal Bests")
    info = data["info"]
    pb_rows = []
    
    for code, name in event_dict.items():
        s_path = f"personal_records.{code}.single.best"
        a_path = f"personal_records.{code}.average.best"

        if s_path in info or a_path in info:
            s_val = info.get(s_path, 0)
            s_str = fn.format_wca_time(s_val) if s_val > 0 else "-"
            s_wr = info.get(f"personal_records.{code}.single.world_rank", "-")
            
            a_val = info.get(a_path, 0)
            a_str = fn.format_wca_time(a_val) if a_val > 0 else "-"
            a_wr = info.get(f"personal_records.{code}.average.world_rank", "-")

            pb_rows.append({"Event": name, "Single": s_str, "WR (S)": s_wr, "Average": a_str, "WR (A)": a_wr})
    
    if pb_rows:
        st.dataframe(pd.DataFrame(pb_rows), use_container_width=True, hide_index=True)

def render_competitions(data):
    st.header("🌍 Competitions History")
    df = data["results"].copy()
    if not df.empty:
        comps = df.groupby(['CompName', 'CompDate', 'Country']).size().reset_index(name='Events')
        comps = comps.sort_values(by="CompDate", ascending=False)
        st.dataframe(comps, use_container_width=True, hide_index=True)

def render_statistics(data):
    st.header("📊 Statistics")
    df = data["results"]
    if not df.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Events Breakdown")
            event_counts = df['Event'].value_counts().reset_index()
            event_counts.columns = ['Event', 'Count']
            event_counts['Event'] = event_counts['Event'].map(event_dict).fillna(event_counts['Event'])
            st.plotly_chart(px.pie(event_counts, values='Count', names='Event', hole=0.5), use_container_width=True)
        with c2:
            st.subheader("PR Count by Event")
            pr_clean = {k: v for k,v in data["stats_prs"].items() if k != 'total'}
            if pr_clean:
                pr_df = pd.DataFrame(list(pr_clean.items()), columns=['Event', 'Count'])
                pr_df['Event'] = pr_df['Event'].map(event_dict).fillna(pr_df['Event'])
                st.bar_chart(pr_df.set_index('Event'))

def render_progression(data):
    st.header("📈 Progression")
    df = data["results"].copy()
    if not df.empty:
        # Selector
        opts = {event_dict.get(e, e): e for e in df['Event'].unique()}
        sel_name = st.selectbox("Select Event:", list(opts.keys()))
        sel_code = opts[sel_name]
        
        # Filtros
        dfe = df[(df['Event'] == sel_code) & (df['best_cs'] > 0)].copy()
        dfe['Date'] = pd.to_datetime(dfe['CompDate'])
        dfe = dfe.sort_values('Date')
        dfe['Single'] = dfe['best_cs'] / 100
        
        fig = px.line(dfe, x='Date', y='Single', title=f"{sel_name} Single Progression", markers=True)
        
        if dfe['avg_cs'].max() > 0:
            dfe_avg = dfe[dfe['avg_cs'] > 0].copy()
            dfe_avg['Average'] = dfe_avg['avg_cs'] / 100
            fig.add_scatter(x=dfe_avg['Date'], y=dfe_avg['Average'], mode='lines+markers', name='Average')
            
        st.plotly_chart(fig, use_container_width=True)

# --- 5. LAYOUT PRINCIPAL ---

st.sidebar.title("🎲 MyCubing")
wca_id_input = st.sidebar.text_input("WCA ID", placeholder="2016LOPE37").upper().strip()
selection = st.sidebar.radio("Go to:", ["Summary", "Personal Bests", "Competitions", "Statistics", "Progression"])

if wca_id_input:
    with st.spinner("Fetching data..."):
        data = load_all_data(wca_id_input)
    
    if data:
        if selection == "Summary": render_summary(data, wca_id_input)
        elif selection == "Personal Bests": render_personal_bests(data)
        elif selection == "Competitions": render_competitions(data)
        elif selection == "Statistics": render_statistics(data)
        elif selection == "Progression": render_progression(data)
        
        st.sidebar.success(f"Loaded: {data['info'].get('person.name')}")
else:
    st.title("🎲 Welcome to MyCubing")
    st.info("Please enter a WCA ID in the sidebar to start.")