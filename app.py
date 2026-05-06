import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import random
import os

st.set_page_config(page_title="Aargau Quiz", layout="centered")

@st.cache_data
def load_data():
    shp_files = [f for f in os.listdir('.') if f.endswith('.shp')]
    if not shp_files: return None, None
    gdf = gpd.read_file(shp_files[0])
    if gdf.crs is None: gdf.crs = "epsg:2056"
    gdf = gdf.to_crs(epsg=4326)
    
    # TURBO: Geometrie vereinfachen (0.001 ist ein guter Kompromiss für Performance)
    # Das reduziert die Dateigröße im Speicher massiv
    gdf['geometry'] = gdf['geometry'].simplify(0.0008, preserve_topology=True)
    
    name_col = next((c for c in ['GMDNAME', 'NAME', 'GEMEINDE'] if c in gdf.columns), gdf.columns[0])
    return gdf, name_col

try:
    gdf, name_col = load_data()

    if 'solved' not in st.session_state: st.session_state.solved = []
    if 'target' not in st.session_state: st.session_state.target = random.choice(gdf[name_col].tolist())
    if 'score' not in st.session_state: st.session_state.score = 0
    if 'last_feedback' not in st.session_state: st.session_state.last_feedback = None

    modus = st.sidebar.radio("Modus:", ["Klicken", "Benennen"])

    # Header & Feedback
    st.markdown(f"""
        <div style="background-color:#3e4a61; padding:15px; border-radius:10px; text-align:center; color:white; font-family:sans-serif;">
            <h2 style="margin:0;">{f"Klicke auf: <span style='background:white; color:black; padding:0 5px; border-radius:3px;'>{st.session_state.target}</span>" if modus == "Klicken" else "Wie heisst die gelbe Gemeinde?"}</h2>
            <p style="margin:5px 0 0 0; opacity:0.8;">Fortschritt: {len(st.session_state.solved)}/201 | Punkte: {st.session_state.score}</p>
        </div>
    """, unsafe_allow_html=True)

    if st.session_state.last_feedback:
        msg, color = st.session_state.last_feedback
        st.markdown(f"<div style='background:{color}; color:white; padding:10px; border-radius:5px; text-align:center; margin-top:10px; font-weight:bold;'>{msg}</div>", unsafe_allow_html=True)

    if modus == "Benennen":
        with st.form("f", clear_on_submit=True):
            ui = st.text_input("Name:")
            if st.form_submit_button("Prüfen"):
                if ui.strip().lower() == st.session_state.target.lower():
                    st.session_state.solved.append(st.session_state.target)
                    st.session_state.score += 1
                    st.session_state.last_feedback = ("Richtig!", "#27854d")
                    st.session_state.target = random.choice([n for n in gdf[name_col] if n not in st.session_state.solved])
                else:
                    st.session_state.last_feedback = ("Falsch!", "#e74c3c")
                st.rerun()

    # KARTEN-LOGIK (PERFORMANCE OPTIMIERT)
    m = folium.Map(location=[47.41, 8.12], zoom_start=10, tiles=None, 
                   zoom_control=False, dragging=False, scrollWheelZoom=False, attributionControl=False)
    
    folium.Rectangle(bounds=[[-90, -180], [90, 180]], fill=True, fill_color='#aadaff', fill_opacity=1).add_to(m)

    # Style-Funktion direkt im GeoJson (vermeidet Overheads)
    folium.GeoJson(
        gdf,
        style_function=lambda f: {
            'fillColor': '#ffffff' if f['properties'][name_col] in st.session_state.solved 
                         else ('#f1c40f' if modus == "Benennen" and f['properties'][name_col] == st.session_state.target 
                         else '#27854d'),
            'color': 'white', 'weight': 0.5, 'fillOpacity': 1
        },
        highlight_function=lambda x: {'fillColor': '#f1c40f', 'fillOpacity': 0.8} if modus == "Klicken" else {}
    ).add_to(m)

    # WICHTIG: 'returned_objects' auf das absolute Minimum reduzieren
    out = st_folium(
        m, 
        use_container_width=True, 
        height=500, 
        key="fast_map",
        returned_objects=["last_active_drawing"] 
    )

    if modus == "Klicken" and out and out.get('last_active_drawing'):
        clicked = out['last_active_drawing']['properties'][name_col]
        if clicked == st.session_state.target:
            st.session_state.solved.append(clicked)
            st.session_state.score += 1
            st.session_state.last_feedback = (f"Richtig! {clicked}", "#27854d")
            st.session_state.target = random.choice([n for n in gdf[name_col] if n not in st.session_state.solved])
        else:
            st.session_state.last_feedback = (f"Falsch! Das war {clicked}", "#e74c3c")
        st.rerun()

except Exception as e:
    st.error("Lade...")
