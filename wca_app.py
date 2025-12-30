import streamlit as st
import time
import functions as fn

# 1. Configuración de la página
st.set_page_config(page_title="WCA Dashboard", layout="wide")

# Estilo CSS personalizado para que las métricas parezcan más un "mosaico"
st.markdown("""
    <style>
    /* Cambia el tamaño del número */
    [data-testid="stMetricValue"] { font-size: 35px; font-weight: bold; }
    /* Personaliza el borde de los contenedores */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 15px;
        background-color: #f8f9fa;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🧩 WCA Statistics Mosaic")

wca_id = st.text_input("Enter WCA ID (e.g., 2003BRAN01):", "")

if wca_id:
    try:
        with st.spinner('Fetching WCA data...'):
            info = fn.get_wcaid_info(wca_id)
            
            # Extraemos el código del país
            iso_code = info.get('person.country.iso2', 'N/A')
            flag = fn.get_flag_emoji(iso_code) # <-- Convertimos a emoji

            s333 = info.get('personal_records.333.single.best', 0) / 100
            a333 = info.get('personal_records.333.average.best', 0) / 100

            stats = {
                "Name": info.get('person.name'),
                "Gold": info.get('medals.gold', 0),
                "Silver": info.get('medals.silver', 0),
                "Bronze": info.get('medals.bronze', 0),
                "Comps": info.get('competition_count', 0),
                "Country": iso_code,
                "Flag": flag, # <-- Guardamos la bandera
                "Single333": f"{s333:.2f}s",
                "Avg333": f"{a333:.2f}s"
            }
            podiums = stats["Gold"] + stats["Silver"] + stats["Bronze"]

        st.divider()
        # Título con la bandera al lado del nombre
        st.header(f"{stats['Flag']} {stats['Name']}'s Dashboard")

        # 3. El Mosaico con Bordes Redondeados (Grid de 4 columnas)
        # Primera fila: Medallas
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            with st.container(border=True):
                st.metric(label="🥇 Golds", value=stats["Gold"])
        with col2:
            with st.container(border=True):
                st.metric(label="🥈 Silvers", value=stats["Silver"])
        with col3:
            with st.container(border=True):
                st.metric(label="🥉 Bronzes", value=stats["Bronze"])
        with col4:
            with st.container(border=True):
                st.metric(label="🗓️ Total Opens", value=stats["Comps"])

        # Segunda fila: Récords y Totales
        col5, col6, col7, col8 = st.columns(4)

        with col5:
            with st.container(border=True):
                st.metric(label="🏅 Total Podiums", value=podiums)
        with col6:
            with st.container(border=True):
                st.metric(label="⏱️ 3x3 Single", value=stats["Single333"])
        with col7:
            with st.container(border=True):
                st.metric(label="📊 3x3 Average", value=stats["Avg333"])
        with col8:
            with st.container(border=True):
                # Mostramos la bandera grande en el mosaico
                st.metric(label="Country", value=f"{stats['Flag']} {stats['Country']}")

        # Gráfico decorativo
        st.write("")
        st.bar_chart({"Medals": [stats["Gold"], stats["Silver"], stats["Bronze"]]}, color="#FFD700")

    except Exception as e:
        st.error(f"Error al obtener datos: {e}. Revisa si el WCA ID es correcto.")