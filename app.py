import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import random
import os

st.set_page_config(page_title="Aargau Quiz", layout="centered")

# CSS für das Seterra-Feeling
st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; }
    iframe { border-radius: 10px; border: 2px solid #3e4a61; }
    .feedback-box { padding: 10px; border-radius: 5px; margin-bottom: 10px; text-align: center; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_data():
    shp_files = [f for f in os.listdir('.') if f.endswith('.shp')]
    if not shp_files: return None, None
    gdf = gpd.read_file(shp_files[0])
    if gdf.crs is None: gdf.crs = "epsg:2056"
    gdf = gdf.to_crs(epsg=4326)
    name_col = next((c for c in ['GMDNAME', 'NAME', 'GEMEINDE'] if c in gdf.columns), gdf.columns[0])
    return gdf, name_col

try:
    gdf, name_col = load_data()

    # --- SESSION STATE ---
    if 'solved' not in st.session_state: st.session_state.solved = []
    if 'target' not in st.session_state: st.session_state.target = random.choice(gdf[name_col].tolist())
    if 'score' not in st.session_state: st.session_state.score = 0
    if 'last_feedback' not in st.session_state: st.session_state.last_feedback = None

    # Modus-Wahl
    modus = st.sidebar.radio("Modus:", ["Klicken", "Benennen"])

    # --- HEADER ---
    instr = f"Klicke auf: <span style='background:white; color:black; padding:2px 8px; border-radius:4px;'>{st.session_state.target}</span>" if modus == "Klicken" else "Wie heisst die <span style='color:#f1c40f;'>gelbe</span> Gemeinde?"
    
    st.markdown(f"""
        <div style="background-color: #3e4a61; padding: 15px; border-radius: 10px; text-align: center; color: white;">
            <h2 style="margin:0;">{instr}</h2>
            <p style="margin:5px 0 0 0;">Fortschritt: {len(st.session_state.solved)} / {len(gdf)} | Punkte: {st.session_state.score}</p>
        </div>
    """, unsafe_allow_html=True)

    # --- FEEDBACK ANZEIGE (Neu) ---
    if st.session_state.last_feedback:
        fb_text, fb_color = st.session_state.last_feedback
        st.markdown(f'<div class="feedback-box" style="background-color:{fb_color}; color:white;">{fb_text}</div>', unsafe_allow_html=True)

    # --- INPUT FÜR BENENNEN ---
    if modus == "Benennen":
        with st.form("input_form", clear_on_submit=True):
            ui = st.text_input("Gemeindename eingeben:")
            if st.form_submit_button("Prüfen"):
                if ui.strip().lower() == st.session_state.target.lower():
                    st.session_state.last_feedback = (f"Richtig! Das ist {st.session_state.target}", "#27854d")
                    st.session_state.solved.append(st.session_state.target)
                    st.session_state.score += 1
                    remaining = [n for n in gdf[name_col] if n not in st.session_state.solved]
                    if remaining: st.session_state.target = random.choice(remaining)
                else:
                    st.session_state.last_feedback = (f"Falsch! Versuch es nochmal.", "#e74c3c")
                st.rerun()

    # --- KARTE ---
    m = folium.Map(location=[47.41, 8.12], zoom_start=10, tiles=None, 
                   zoom_control=False, dragging=False, scrollWheelZoom=False, attributionControl=False)
    
    folium.Rectangle(bounds=[[-90, -180], [90, 180]], fill=True, fill_color='#aadaff', fill_opacity=1).add_to(m)

    def style_fn(f):
        n = f['properties'][name_col]
        if n in st.session_state.solved: color = '#ffffff'
        elif modus == "Benennen" and n == st.session_state.target: color = '#f1c40f'
        else: color = '#27854d'
        return {'fillColor': color, 'color': 'white', 'weight': 1, 'fillOpacity': 1}

    folium.GeoJson(gdf, style_function=style_fn, 
                   highlight_function=lambda x: {'fillColor': '#f1c40f'} if modus == "Klicken" else {}).add_to(m)

    out = st_folium(m, use_container_width=True, height=500, key="map", returned_objects=["last_active_drawing"])

    # --- KLICK LOGIK ---
    if modus == "Klicken" and out and out.get('last_active_drawing'):
        clicked = out['last_active_drawing']['properties'][name_col]
        if clicked == st.session_state.target:
            st.session_state.last_feedback = (f"Richtig! {clicked} gefunden.", "#27854d")
            st.session_state.solved.append(clicked)
            st.session_state.score += 1
            remaining = [n for n in gdf[name_col] if n not in st.session_state.solved]
            if remaining: st.session_state.target = random.choice(remaining)
        else:
            st.session_state.last_feedback = (f"Falsch! Das war {clicked}.", "#e74c3c")
        st.rerun()

except Exception as e:
    st.error(f"Error: {e}")
