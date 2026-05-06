import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import random
import os

st.set_page_config(page_title="Aargau Quiz Pro", layout="centered")

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

    # --- SESSION STATE ---
    if 'results' not in st.session_state:
        st.session_state.results = {name: 0 for name in gdf[name_col]} # 0 statt None verhindert den Fehler
    if 'attempts' not in st.session_state:
        st.session_state.attempts = 0
    if 'target' not in st.session_state:
        st.session_state.target = random.choice(gdf[name_col].tolist())
    if 'last_clicked_info' not in st.session_state:
        st.session_state.last_clicked_info = None

    # --- HEADER ---
    st.markdown(f"""
        <div style="background-color:#3e4a61; padding:20px; border-radius:12px; text-align:center; color:white; font-family:sans-serif;">
            <h1 style="margin:0; font-size: 2.8rem;">Klicke auf: <span style="background:white; color:black; padding:2px 12px; border-radius:8px;">{st.session_state.target}</span></h1>
            <p style="margin:10px 0 0 0; font-size: 1.2rem; opacity: 0.9;">Versuch: {st.session_state.attempts + 1} / 3</p>
        </div>
    """, unsafe_allow_html=True)

    # Kurze Info bei falschem Klick
    if st.session_state.last_clicked_info:
        st.error(st.session_state.last_clicked_info)

    # --- KARTEN-STYLING (FEHLERSICHER) ---
    def get_color(name):
        res = st.session_state.results.get(name, 0)
        if res == 1: return '#ffffff' # Weiss (1. Versuch)
        if res == 2: return '#ffa500' # Orange (2. Versuch)
        if res >= 3: return '#ff4b4b' # Rot (3.+ Versuche)
        return '#27854d' # Grün (noch offen)

    m = folium.Map(location=[47.41, 8.12], zoom_start=10, tiles=None, 
                   zoom_control=False, dragging=False, scrollWheelZoom=False, attributionControl=False)
    
    folium.Rectangle(bounds=[[-90, -180], [90, 180]], fill=True, fill_color='#aadaff', fill_opacity=1).add_to(m)

    folium.GeoJson(
        gdf,
        style_function=lambda f: {
            'fillColor': get_color(f['properties'][name_col]),
            'color': 'white', 'weight': 0.6, 'fillOpacity': 1
        },
        highlight_function=lambda x: {'fillColor': '#f1c40f', 'fillOpacity': 0.8}
    ).add_to(m)

    out = st_folium(m, use_container_width=True, height=520, key="quiz_map_v2", returned_objects=["last_active_drawing"])

    # --- LOGIK ---
    if out and out.get('last_active_drawing'):
        clicked = out['last_active_drawing']['properties'][name_col]
        
        # Nur reagieren, wenn die angeklickte Gemeinde noch nicht gelöst ist
        if st.session_state.results[clicked] == 0:
            
            if clicked == st.session_state.target:
                # Treffer!
                st.session_state.attempts += 1
                st.session_state.results[clicked] = st.session_state.attempts
                st.session_state.attempts = 0
                st.session_state.last_clicked_info = None
                
                remaining = [n for n, r in st.session_state.results.items() if r == 0]
                if remaining:
                    st.session_state.target = random.choice(remaining)
                st.rerun()
            else:
                # Daneben!
                st.session_state.attempts += 1
                st.session_state.last_clicked_info = f"Falsch! Das war {clicked}"
                
                if st.session_state.attempts >= 3:
                    # Nach 3 Fehlern: Zielgemeinde rot markieren
                    st.session_state.results[st.session_state.target] = 3
                    st.session_state.attempts = 0
                    st.session_state.last_clicked_info = f"Nicht gefunden! Gesucht war {st.session_state.target} (jetzt rot)."
                    
                    remaining = [n for n, r in st.session_state.results.items() if r == 0]
                    if remaining:
                        st.session_state.target = random.choice(remaining)
                
                st.rerun()

except Exception as e:
    st.error(f"Ein Fehler ist aufgetreten: {e}")
