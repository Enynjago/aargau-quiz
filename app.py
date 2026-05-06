import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import random
import os

st.set_page_config(page_title="Aargau Quiz", layout="centered")

# CSS für maximale Sichtbarkeit
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; }
    iframe { border: 2px solid #3e4a61; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_data():
    shp_files = [f for f in os.listdir('.') if f.endswith('.shp')]
    if not shp_files: return None, None
    gdf = gpd.read_file(shp_files[0])
    if gdf.crs is None: gdf.crs = "epsg:2056"
    gdf = gdf.to_crs(epsg=4326)
    gdf['geometry'] = gdf['geometry'].simplify(0.0008, preserve_topology=True)
    name_col = next((c for c in ['GMDNAME', 'NAME', 'GEMEINDE'] if c in gdf.columns), gdf.columns[0])
    return gdf, name_col

try:
    gdf, name_col = load_data()

    # --- SESSION STATE (Die "Gedächtnis"-Logik) ---
    if 'results' not in st.session_state:
        st.session_state.results = {name: 0 for name in gdf[name_col]}
    if 'target' not in st.session_state:
        st.session_state.target = random.choice(gdf[name_col].tolist())
    if 'current_attempts' not in st.session_state:
        st.session_state.current_attempts = 0
    if 'feedback' not in st.session_state:
        st.session_state.feedback = None

    # --- HEADER ---
    st.markdown(f"""
        <div style="background-color:#3e4a61; padding:20px; border-radius:12px; text-align:center; color:white;">
            <h1 style="margin:0;">Klicke auf: <span style="background:white; color:black; padding:2px 10px; border-radius:5px;">{st.session_state.target}</span></h1>
            <p style="margin:10px 0 0 0; font-size:1.2rem;">Versuch: {st.session_state.current_attempts + 1} / 3</p>
        </div>
    """, unsafe_allow_html=True)

    if st.session_state.feedback:
        st.error(st.session_state.feedback)

    # --- KARTE: ZOOM OPTIMIERT ---
    m = folium.Map(
        location=[47.41, 7.12], # Mitte leicht angepasst
        zoom_start=9.9,         # Höherer Wert = näher dran
        tiles=None,
        zoom_control=False, 
        dragging=False, 
        scrollWheelZoom=False, 
        attributionControl=False
    )
    
    folium.Rectangle(bounds=[[-90, -180], [90, 180]], fill=True, fill_color='#aadaff', fill_opacity=1).add_to(m)

    def style_fn(f):
        name = f['properties'][name_col]
        res = st.session_state.results.get(name, 0)
        if res == 1: color = '#ffffff' # Weiss (1. Versuch)
        elif res == 2: color = '#ffa500' # Orange (2. Versuch)
        elif res >= 3: color = '#ff4b4b' # Rot (3. Versuch/Hilfe)
        else: color = '#27854d' # Grün (offen)
        return {'fillColor': color, 'color': 'white', 'weight': 0.7, 'fillOpacity': 1}

    folium.GeoJson(gdf, style_function=style_fn, 
                   highlight_function=lambda x: {'fillColor': '#f1c40f'}).add_to(m)

    # WICHTIG: Die Karte muss eine feste ID haben, damit sie nicht springt
    out = st_folium(m, use_container_width=True, height=550, key="ag_quiz_map")

    # --- LOGIK BEI KLICK ---
    if out and out.get('last_active_drawing'):
        clicked = out['last_active_drawing']['properties'][name_col]
        
        # Ignorieren, wenn die Gemeinde schon gelöst wurde
        if st.session_state.results[clicked] == 0:
            
            if clicked == st.session_state.target:
                # TREFFER
                st.session_state.current_attempts += 1
                st.session_state.results[clicked] = st.session_state.current_attempts
                
                # Reset für neue Runde
                st.session_state.current_attempts = 0
                st.session_state.feedback = None
                remaining = [n for n, r in st.session_state.results.items() if r == 0]
                if remaining:
                    st.session_state.target = random.choice(remaining)
                st.rerun()
            
            else:
                # FALSCH GEKLICKT
                st.session_state.current_attempts += 1
                st.session_state.feedback = f"Das war {clicked}."
                
                # Wenn 3 Versuche erreicht sind
                if st.session_state.current_attempts >= 3:
                    st.session_state.results[st.session_state.target] = 3 # Markiere Zielgemeinde rot
                    st.session_state.current_attempts = 0 # Reset Versuche
                    st.session_state.feedback = f"Nicht gefunden! Gesucht war {st.session_state.target}."
                    
                    remaining = [n for n, r in st.session_state.results.items() if r == 0]
                    if remaining:
                        st.session_state.target = random.choice(remaining)
                
                st.rerun()

except Exception as e:
    st.write("Lade Daten...")
