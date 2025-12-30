import streamlit as st
import time

# 1. Setup the Page
st.set_page_config(page_title="WCA Dashboard", layout="wide")
st.title("🧩 WCA Statistics Mosaic")

# 2. Sidebar or Top Input
wca_id = st.text_input("Enter WCA ID (e.g., 2003BRAN01):", "")

if wca_id:
    with st.spinner('Calculating stats...'):
        # --- PLACEHOLDER FOR YOUR CALCULATIONS ---
        # This is where your custom Python logic goes
        time.sleep(1) # Simulating calculation time
        
        # Example dummy data
        stats = {
            "Gold Medals": 12,
            "Silver Medals": 8,
            "Bronze Medals": 5,
            "Comp Count": 42,
            "NR Count": 2,
            "Podiums": 25
        }
        # -----------------------------------------

    st.divider()
    st.subheader(f"Results for {wca_id}")

    # 3. Create the Mosaic (The "Squares")
    # We create 3 columns to make a grid/mosaic
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="🥇 Golds", value=stats["Gold Medals"])
        st.metric(label="🏅 Total Podiums", value=stats["Podiums"])

    with col2:
        st.metric(label="🥈 Silvers", value=stats["Silver Medals"], delta="Best Year!")
        st.metric(label="🗓️ Competitions", value=stats["Comp Count"])

    with col3:
        st.metric(label="🥉 Bronzes", value=stats["Bronze Medals"])
        st.metric(label="🇿🇦 National Records", value=stats["NR Count"])

    # Optional: Add a chart below the mosaic
    st.bar_chart({"Medals": [12, 8, 5]})