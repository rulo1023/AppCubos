import streamlit as st
import time
import functions as fn
from datetime import datetime
import pandas as pd


event_dict = {"333": "3x3x3", "222": "2x2x2", "444": "4x4x4", "555": "5x5x5", "666": "6x6x6", "777": "7x7x7",
                    "333bf": "3x3x3 Blindfolded", "333oh": "3x3x3 One-Handed", "333fm": "3x3x3 Fewest Moves",
                    "minx": "Megaminx", "pyram": "Pyraminx", "skewb": "Skewb", "sq1": "Square-1",
                    "clock": "Clock", "444bf": "4x4x4 Blindfolded", "555bf": "5x5x5 Blindfolded", "333mbf": "3x3x3 Multi-Blind"}


# 1. Page Configuration
st.set_page_config(page_title="MyCubing Dashboard", layout="wide", page_icon="🎲")

# 2. Custom CSS Style
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 24px; font-weight: bold; }
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 15px;
        background-color: #f8f9fa;
        padding: 15px;
    }
    
    /* Force 2 columns on mobile */
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
    </style>
    """, unsafe_allow_html=True)

# 3. UI Helper Functions
def render_metric(label, value):
    with st.container(border=True):
        st.metric(label=label, value=value)

def render_pr_card(label_icon, pr_data):
    """Renders a compact cell with Title, Time, and small Competition info"""
    if not pr_data or not isinstance(pr_data, tuple):
        st.warning("No PR data available")
        return

    
    # Structure: ('333_single', ('ID', 'Name', 'Date', 'Time', 'Event', 'Type'))
    categoria_raw, details = pr_data
    comp_name = details[1]
    fecha = details[2]
    tiempo = details[3]
    event_name = details[4].replace(categoria_raw.split('_')[0], event_dict.get(categoria_raw.split('_')[0], categoria_raw.split('_')[0]))
    kind_type = details[5]

    st.write(label_icon)
    with st.container(border=True):
        st.markdown(f"**{event_name} {kind_type}**")
        st.markdown(f"## {tiempo}s")
        st.caption(f"🏆 {comp_name}")
        st.caption(f"📅 {fecha}")

# 4. Main App Logic
st.title("🎲 MyCubing")

wca_id = st.text_input("Enter WCA ID:", placeholder="e.g., 2016LOPE37").upper()

if wca_id:
    try:
        with st.spinner('Fetching WCA Data...'):
            # 1. Recuperación de datos
            info = fn.get_wcaid_info(wca_id)
            results = fn.get_wca_results(wca_id)
            prs_dict = fn.prs_info(wca_id) 
            oldest, newest = fn.oldest_and_newest_pr(wca_id)
            
            # 2. Procesamiento de estadísticas de PRs (Llamada única para optimizar)
            stats_prs = fn.number_of_prs(wca_id)
            total_prs = stats_prs.get('total', 0)
            
            # Cálculo del evento con más PRs
            pr_counts = {k: v for k, v in stats_prs.items() if k != 'total'}
            if pr_counts:
                max_event = max(pr_counts, key=pr_counts.get)
                max_event_count = pr_counts[max_event]
                display_max_event = f"{event_dict[max_event]} ({max_event_count})"
            else:
                display_max_event = "N/A"

            # 3. Otros datos básicos
            iso_code = info.get('person.country.iso2', 'N/A')
            flag = fn.get_flag_emoji(iso_code)
            comp_count = info.get('competition_count', 0)
            last_comp = results['Competition'].iloc[0] if not results.empty else "N/A"
            
            gold = info.get('medals.gold', 0)
            silver = info.get('medals.silver', 0)
            bronze = info.get('medals.bronze', 0)

        # --- Dashboard Layout ---
        st.header(f"{flag} {info.get('person.name')}")
        st.caption(f"WCA ID: {wca_id} | Country: {iso_code}")
        st.divider()

        # SECTION 1: Activity
        st.subheader("Activity")
        act1, act2 = st.columns(2)
        with act1:
            render_metric("🗓️ Total Competitions", comp_count)
        with act2:
            render_metric("🏟️ Last Competition", last_comp)

        # SECTION 2: Medals
        st.subheader("Medals & Podiums")
        m1, m2, m3 = st.columns(3)
        with m1: render_metric("🥇 Gold", gold)
        with m2: render_metric("🥈 Silver", silver)
        with m3: render_metric("🥉 Bronze", bronze)

        # SECTION 3: Personal Records
        st.divider()
        st.subheader("Personal Records Summary")
        
        # Creamos dos columnas para mostrar las métricas generales de PRs
        pr_col1, pr_col2 = st.columns(2)
        
        with pr_col1:
            render_metric("📊 Total PRs Achieved", total_prs)
            
        with pr_col2:
            # AQUÍ HEMOS MOVIDO EL RECUADRO
            render_metric("🔥 Event with most PRs", display_max_event)
        
        st.write("") # Spacer
        
        # Oldest and Newest PR Cards
        col_old, col_new = st.columns(2)
        with col_old:
            render_pr_card("🕒 **Oldest PR (Still standing)**", oldest)
        
        with col_new:
            render_pr_card("✨ **Newest Personal Record**", newest)

        # --- SECCIÓN NUEVA: MAPA ---
       
        st.divider()
        st.subheader("📍 Competition map")

        # Convertimos el generador en un DataFrame
        with st.spinner("Cargando ubicaciones..."):
            raw_map_data = list(fn.generate_map_data(wca_id))
            map_df = pd.DataFrame(raw_map_data)

        if not map_df.empty:
            import pydeck as pdk
            import numpy as np

            # 1. Identificar posiciones duplicadas
            # Creamos una clave única por coordenada
            map_df['pos_key'] = map_df['lat'].astype(str) + map_df['lon'].astype(str)
            
            # 2. Aplicar desplazamiento de 5 metros SOLO a los duplicados
            # 0.000009 grados latitud aprox = 1 metro
            metres_in_degrees = 0.000045 # 5 metros aprox
            
            def apply_jitter(group):
                if len(group) > 1:
                    for i in range(len(group)):
                        # Ángulo aleatorio para dispersar en círculo
                        angle = 2 * np.pi * i / len(group)
                        group.iloc[i, group.columns.get_loc('lat')] += metres_in_degrees * np.cos(angle)
                        group.iloc[i, group.columns.get_loc('lon')] += metres_in_degrees * np.sin(angle)
                return group

            map_df = map_df.groupby('pos_key', group_keys=False).apply(apply_jitter)

            # --- Configuración del Mapa (Pydeck) ---
            view_state = pdk.ViewState(
                latitude=map_df['lat'].mean(),
                longitude=map_df['lon'].mean(),
                zoom=4,
                pitch=0,
            )

            layer = pdk.Layer(
                "ScatterplotLayer",
                map_df,
                get_position='[lon, lat]',
                get_color='[255, 75, 75, 200]',
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
            st.info("No se encontraron coordenadas para las competiciones de este usuario.")
            
    except Exception as e:
        st.error(f"Error loading data: {e}")

else:
    st.info("Enter a WCA ID to see the profile statistics.")