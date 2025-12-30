import streamlit as st
import time
import functions as fn

# 1. Configuración de la página
st.set_page_config(page_title="WCA Dashboard", layout="wide")

# Estilo CSS personalizado para el mosaico y FORZAR visualización horizontal en móvil
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; font-weight: bold; }
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 15px;
        background-color: #f8f9fa;
        padding: 10px;
    }
    
    /* TRUCO PARA MÓVIL: Evita que las columnas se apilen */
    [data-testid="column"] {
        min-width: 45% !important; /* Permite 2 columnas por fila en móviles */
        flex: 1 1 45% !important;
    }
    
    /* Ajuste para tablets o pantallas medianas */
    @media (min-width: 768px) {
        [data-testid="column"] {
            min-width: 20% !important;
            flex: 1 1 20% !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🎲 MyCubing")

wca_id = st.text_input("Enter WCA ID (e.g., 2003BRUC01):", "")

if wca_id:
    try:
        with st.spinner('Fetching WCA data...'):
            info = fn.get_wcaid_info(wca_id)
            
            iso_code = info.get('person.country.iso2', 'N/A')
            flag = fn.get_flag_emoji(iso_code)

            s333 = info.get('personal_records.333.single.best', 0) / 100
            a333 = info.get('personal_records.333.average.best', 0) / 100

            stats = {
                "Name": info.get('person.name'),
                "Gold": info.get('medals.gold', 0),
                "Silver": info.get('medals.silver', 0),
                "Bronze": info.get('medals.bronze', 0),
                "Comps": info.get('competition_count', 0),
                "Country": iso_code,
                "Flag": flag,
                "Single333": f"{s333:.2f}s",
                "Avg333": f"{a333:.2f}s"
            }
            podiums = stats["Gold"] + stats["Silver"] + stats["Bronze"]

        st.divider()
        st.header(f"{stats['Flag']} {stats['Name']}")

        # Agrupamos los elementos para que se vean bien en cuadrícula
        # Usamos 2 columnas principales que dentro tendrán sus métricas
        # O definimos filas de 2 en 2 para asegurar orden en móvil
        
        def render_metric(label, value):
            with st.container(border=True):
                st.metric(label=label, value=value)

        # Fila 1
        col1, col2 = st.columns(2)
        with col1: render_metric("🥇 Golds", stats["Gold"])
        with col2: render_metric("🥈 Silvers", stats["Silver"])

        # Fila 2
        col3, col4 = st.columns(2)
        with col3: render_metric("🥉 Bronzes", stats["Bronze"])
        with col4: render_metric("🗓️ Total Opens", stats["Comps"])

        # Fila 3
        col5, col6 = st.columns(2)
        with col5: render_metric("🏅 Podiums", podiums)
        with col6: render_metric("⏱️ 3x3 Single", stats["Single333"])

        # Fila 4
        col7, col8 = st.columns(2)
        with col7: render_metric("📊 3x3 Average", stats["Avg333"])
        with col8: render_metric("Country", f"{stats['Flag']} {stats['Country']}")

        st.write("")
        st.bar_chart({"Medals": [stats["Gold"], stats["Silver"], stats["Bronze"]]}, color="#FFD700")

    except Exception as e:
        st.error(f"Error: {e}")
        