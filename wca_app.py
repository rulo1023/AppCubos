import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import functions as fn
import numpy as np
import pydeck as pdk

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="MyCubing Dashboard", layout="wide", page_icon="🎲")

# --- ESTILOS CSS (Mantenemos los tuyos) ---
st.markdown("""
    <style>
    /* Estilo para el valor de las métricas */
    [data-testid="stMetricValue"] { font-size: 24px; font-weight: bold; }
    
    /* Estilo para los contenedores (las "tarjetas" grises) */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 15px;
        background-color: #f8f9fa;
        padding: 15px;
        margin-bottom: 10px;
    }
    
    /* Títulos de las tarjetas de PR */
    .pr-card-title {
        font-size: 14px;
        color: #666;
        margin-bottom: 0px;
    }
    .pr-card-time {
        font-size: 26px;
        font-weight: 800;
        color: #31333F;
        margin: 5px 0;
    }
    .pr-card-sub {
        font-size: 12px;
        color: #888;
    }
    
    /* Ajuste responsive */
    [data-testid="column"] { min-width: 45% !important; flex: 1 1 45% !important; }
    @media (min-width: 768px) {
        [data-testid="column"] { min-width: 20% !important; flex: 1 1 20% !important; }
    }
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

# --- 2. HELPERS ---
def render_metric(label, value):
    with st.container(border=True):
        st.metric(label=label, value=value)

def render_pr_card(title, time_str, comp_name, date_str):
    """Renderiza una tarjeta HTML personalizada para los PRs"""
    with st.container(border=True):
        st.markdown(f"""
        <div class="pr-card-title">{title}</div>
        <div class="pr-card-time">{time_str}</div>
        <div class="pr-card-sub">📍 {comp_name}</div>
        <div class="pr-card-sub">📅 {date_str}</div>
        """, unsafe_allow_html=True)

# --- 3. CARGA DE DATOS ---
@st.cache_data(ttl=3600, show_spinner=False)  # <-- Añadimos show_spinner=False aquí
def load_all_data(wca_id):
    try:
        # El resto del código se queda igual...
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

# --- 4. VISTAS ---

def render_summary(data, wca_id):
    info = data["info"]
    iso_code = info.get('person.country.iso2', 'N/A')
    flag = fn.get_flag_emoji(iso_code)
    
    st.header(f"{flag} {info.get('person.name')}")
    st.caption(f"WCA ID: {wca_id}")
    st.divider()

    st.subheader("Activity")
    c1, c2 = st.columns(2)
    with c1: render_metric("🗓️ Competitions", info.get('competition_count', 0))
    last_comp = data['results']['Competition'].iloc[0] if not data['results'].empty else "N/A"
    with c2: render_metric("🏟️ Last Comp", last_comp)

    st.subheader("Medals")
    m1, m2, m3 = st.columns(3)
    with m1: render_metric("🥇 Gold", info.get('medals.gold', 0))
    with m2: render_metric("🥈 Silver", info.get('medals.silver', 0))
    with m3: render_metric("🥉 Bronze", info.get('medals.bronze', 0))

    # --- MAPA (Original Restaurado) ---
    st.divider()
    st.subheader("📍 Competition Map")
    map_df = pd.DataFrame(data["map_data"])
    
    if not map_df.empty:
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
            zoom=3, pitch=0
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

def render_personal_bests_cards(data):
    st.header("🏆 Personal Bests")
    df = data["results"].copy()
    if df.empty: return

    # Asegurar formato fecha
    df['CompDate'] = pd.to_datetime(df['CompDate'])
    
    # Orden de eventos estándar
    ordered_events = [k for k in event_dict.keys() if k in df['Event'].unique()]

    for event_code in ordered_events:
        event_name = event_dict.get(event_code, event_code)
        
        # Filtramos datos del evento
        ev_df = df[df['Event'] == event_code]
        
        # Buscamos la fila del mejor Single
        # Ordenamos por tiempo (asc) y luego fecha (asc) para coger el primero cronológicamente en caso de empate
        best_single_row = ev_df[ev_df['best_cs'] > 0].sort_values(by=['best_cs', 'CompDate']).iloc[0] if not ev_df[ev_df['best_cs'] > 0].empty else None
        
        # Buscamos la fila de la mejor Media
        best_avg_row = ev_df[ev_df['avg_cs'] > 0].sort_values(by=['avg_cs', 'CompDate']).iloc[0] if not ev_df[ev_df['avg_cs'] > 0].empty else None

        # Si no tiene ni single ni media (raro), saltamos
        if best_single_row is None and best_avg_row is None:
            continue

        st.subheader(event_name)
        c1, c2 = st.columns(2)

        # Tarjeta SINGLE
        with c1:
            if best_single_row is not None:
                s_time = s_time = fn.format_wca_time(best_single_row['best_cs'], event_code=event_code)
                s_comp = best_single_row['Competition'] # O CompName si prefieres corto
                s_date = best_single_row['CompDate'].strftime('%d %b %Y')
                render_pr_card("SINGLE", s_time, s_comp, s_date)
            else:
                st.info("No Single result")

        # Tarjeta AVERAGE
        with c2:
            if best_avg_row is not None:
                a_time = fn.format_wca_time(best_avg_row['avg_cs'], event_code=event_code)
                a_comp = best_avg_row['Competition']
                a_date = best_avg_row['CompDate'].strftime('%d %b %Y')
                render_pr_card("AVERAGE", a_time, a_comp, a_date)
            else:
                # Espacio vacío o mensaje discreto si no hay media (ej. 3x3 Blindfolded antiguo)
                st.write("") 

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
    st.header("📈 Progression (PR History)")
    df = data["results"].copy()
    if df.empty: return

    # Selector
    opts = {event_dict.get(e, e): e for e in df['Event'].unique()}
    sel_name = st.selectbox("Select Event:", list(opts.keys()))
    sel_code = opts[sel_name]
    
    # Preparar datos
    dfe = df[(df['Event'] == sel_code) & (df['best_cs'] > 0)].copy()
    dfe['Date'] = pd.to_datetime(dfe['CompDate'])
    dfe = dfe.sort_values('Date')

    # AJUSTE PARA FMC
    if sel_code == "333fm":
        dfe['Single_Val'] = dfe['best_cs']
        # La media en FMC se guarda multiplicada por 100 (ej: 33.67 moves es 3367)
        dfe['Average_Val'] = dfe['avg_cs'] / 100 
        unit = "moves"
    else:
        dfe['Single_Val'] = dfe['best_cs'] / 100
        dfe['Average_Val'] = dfe['avg_cs'] / 100
        unit = "seconds"
    
    # --- Lógica de PRs ---
    dfe['pr_so_far'] = dfe['best_cs'].cummin()
    pr_history = dfe[dfe['best_cs'] == dfe['pr_so_far']].drop_duplicates(subset=['best_cs'])
    
    # En FMC el PR de la columna Single_Val ya es correcto, en otros se divide
    pr_history_display = pr_history['Single_Val']

    # GRÁFICO (Actualizar yaxis_title)
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=pr_history['Date'], 
        y=pr_history_display,
        mode='lines+markers',
        name=f'PR ({unit})',
        line=dict(color='firebrick', width=3, shape='hv'),
        marker=dict(size=8)
    ))

    # --- LOGICA Media Móvil (Trend) ---
    # Usamos todos los datos (dfe) para la media móvil
    # Window = 5 competiciones (ajustable)
    dfe['MA_5'] = dfe['Single'].rolling(window=5, min_periods=1).mean()

    # GRÁFICO
    fig = go.Figure()

    # 1. Línea de PRs (Escalonada)
    fig.add_trace(go.Scatter(
        x=pr_history['Date'], 
        y=pr_history['Single_Sec'],
        mode='lines+markers',
        name='Personal Record (PR)',
        line=dict(color='firebrick', width=3, shape='hv'), # 'hv' hace el efecto escalón
        marker=dict(size=8)
    ))

    # 2. Línea de Tendencia (Media Móvil)
    fig.add_trace(go.Scatter(
        x=dfe['Date'],
        y=dfe['MA_5'],
        mode='lines',
        name='Moving Avg (5 comps)',
        line=dict(color='royalblue', width=2, dash='dot'),
        opacity=0.7
    ))

    # Average si existe (Opcional: Agregar lógica similar para Avg PRs)
    
    fig.update_layout(
        title=f"Evolution of {sel_name}",
        xaxis_title="Date",
        yaxis_title=unit,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    st.caption("🔴 Red line: The moments you broke your PR. | 🔵 Blue dotted line: Your average performance (Moving Avg of last 5 comps).")


# --- 5. LAYOUT PRINCIPAL ---

st.sidebar.title("🎲 MyCubing")
wca_id_input = st.sidebar.text_input("WCA ID", placeholder="2016LOPE37").upper().strip()
selection = st.sidebar.radio("Go to:", ["Summary", "Personal Bests", "Competitions", "Statistics", "Progression"])

if wca_id_input:
    # Este spinner manual es el único que verá el usuario
    with st.spinner("Loading WCA profile and results. This might take some time, you've done too many solves!"):
        data = load_all_data(wca_id_input)

    if data:
        if selection == "Summary": render_summary(data, wca_id_input)
        elif selection == "Personal Bests": render_personal_bests_cards(data)
        elif selection == "Competitions": render_competitions(data)
        elif selection == "Statistics": render_statistics(data)
        elif selection == "Progression": render_progression(data)
        
        st.sidebar.success(f"User: {data['info'].get('person.name')}")
else:
    st.title("🎲 Welcome to MyCubing")
    st.markdown("Enter your **WCA ID** in the sidebar to see your advanced stats.")