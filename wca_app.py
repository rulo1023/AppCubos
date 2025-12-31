import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import functions as fn
import numpy as np
import pydeck as pdk

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="MyCubing Dashboard", layout="wide", page_icon="🎲")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 24px; font-weight: bold; }
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 15px;
        background-color: #f8f9fa;
        padding: 15px;
        margin-bottom: 10px;
    }
    .pr-card-title { font-size: 14px; color: #666; margin-bottom: 0px; }
    .pr-card-time { font-size: 26px; font-weight: 800; color: #31333F; margin: 5px 0; }
    
    /* Clase para el nombre de la competición con espacio extra debajo */
    .pr-card-comp { 
        font-size: 12px; 
        color: #888; 
        margin-bottom: 12px; /* Aquí controlas el "aire" o espacio vacío */
        line-height: 1.2;
    }
    
    /* Clase para la fecha */
    .pr-card-date { 
        font-size: 11px; 
        color: #aaa; 
        font-style: italic;
    }

    [data-testid="column"] { min-width: 45% !important; flex: 1 1 45% !important; }
    @media (min-width: 768px) {
        [data-testid="column"] { min-width: 20% !important; flex: 1 1 20% !important; }
    }
    </style>
    """, unsafe_allow_html=True)

# Diccionario de Eventos
event_dict = {
    "333": "3x3x3", "222": "2x2x2", "444": "4x4x4", "555": "5x5x5", "666": "6x6x6", "777": "7x7x7",
    "333bf": "3x3x3 Blind", "333oh": "3x3x3 OH", "333fm": "3x3x3 FM", "minx": "Megaminx", 
    "pyram": "Pyraminx", "skewb": "Skewb", "sq1": "Square-1", "clock": "Clock", 
    "444bf": "4x4x4 Blind", "555bf": "5x5x5 Blind", "333mbf": "3x3x3 Multi-Blind"
}

# --- 2. HELPERS ---
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

# --- 3. CARGA DE DATOS ---
@st.cache_data(ttl=3600, show_spinner=False)
def load_all_data(wca_id):
    try:
        results = fn.get_wca_results(wca_id)
        if results.empty: return None

        info = fn.get_wcaid_info(wca_id)
        prs_dict = fn.prs_info(wca_id, results_df=results)
        stats_prs = fn.number_of_prs(wca_id, results_df=results)
        oldest, newest = fn.oldest_and_newest_pr(wca_id, prs_data=prs_dict)
        map_data = list(fn.generate_map_data(wca_id, results_df=results))
        
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
        st.error(f"Error loading profile: {e}")
        return None

# --- 4. VISTAS ---

def render_summary(data, wca_id):
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
            st.subheader("Round Breakdown")
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

def render_competitions(data):
    st.header("🌍 Competitions History")

    # --- B. TABLA ---
    df = data["results"].copy()
    if not df.empty:
        # Agrupamos por competición para no repetir filas por cada ronda
        comps = df.groupby(['CompName', 'CompDate', 'Country']).size().reset_index(name='Rounds')
        comps = comps.sort_values(by="CompDate", ascending=False)
        
        # Formatear localización y fecha
        comps['Location'] = comps['Country'].apply(lambda x: f"{fn.get_flag_emoji(x)} {fn.get_country_name(x)}")
        comps['Date'] = comps['CompDate'].dt.strftime('%Y-%m-%d')
        
        st.dataframe(
            comps[['Date', 'CompName', 'Location']], 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Date": st.column_config.TextColumn("Date", width="small"),
                "CompName": st.column_config.TextColumn("Competition", width="large"),
                "Location": st.column_config.TextColumn("Location", width="medium")
            }
        )

    st.divider()

    # --- A. MAPA ---
    map_df = pd.DataFrame(data["map_data"])
    if not map_df.empty:
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
    
def render_progression(data):
    st.header("📈 Personal Best Progression")
    df = data["results"].copy()
    if df.empty: return

    # Selectores
    available_events = df['Event'].unique()
    opts = {event_dict.get(e, e): e for e in available_events}
    
    c1, c2 = st.columns([3, 1])
    with c1:
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
# --- 5. LAYOUT PRINCIPAL ---

st.sidebar.title("🎲 MyCubing")
wca_id_input = st.sidebar.text_input("WCA ID", placeholder="2016LOPE37").upper().strip()
selection = st.sidebar.radio("Go to:", ["Summary", "Personal Bests", "Competitions", "Statistics", "Progression"])

if wca_id_input:
    # Spinner informativo
    with st.spinner(f"Fetching data for {wca_id_input}... (This runs faster after the first load)"):
        data = load_all_data(wca_id_input)

    if data:
        if selection == "Summary": render_summary(data, wca_id_input)
        elif selection == "Personal Bests": render_personal_bests_cards(data)
        elif selection == "Competitions": render_competitions(data)
        elif selection == "Statistics": render_statistics(data)
        elif selection == "Progression": render_progression(data)
        
        name = data['info'].get('person.name', wca_id_input)
        st.sidebar.success(f"Loaded: {name}")
    else:
        st.sidebar.error("Profile not found or API error.")
else:
    st.title("🎲 Welcome to MyCubing")
    st.markdown("Enter your **WCA ID** in the sidebar to see your advanced stats.")