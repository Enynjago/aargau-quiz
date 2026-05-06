import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import random
import os
import time

st.set_page_config(page_title="Aargau Quiz Pro", layout="centered")

@st.cache_data
def load_data():
    shp_files = [f for f in os.listdir('.') if f.endswith('.shp')]
    if not shp_files: return None, None
    gdf = gpd.read_file(shp_files[0])
    if gdf.crs is None: gdf.crs = "epsg:2056"
    gdf = gdf.to_crs(epsg=4326)
    # Performance-Optimierung
    gdf['geometry'] = gdf['geometry'].simplify(0.0008, preserve_topology=True)
    name_col = next((c for c in ['GMDNAME', 'NAME', 'GEMEINDE'] if c in gdf.columns), gdf.columns[0])
    return gdf, name_col

try:
    gdf, name_col = load_data()

    # --- SESSION STATE INITIALISIERUNG ---
    if 'results' not in st.session_state:
        # Speichert pro Gemeinde: None (ungelöst), 1 (weiss), 2 (orange), 3+ (rot)
        st.session_state.results = {name: None for name in gdf[name_col]}
    if 'attempts' not in st.session_state:
        st.session_state.attempts = 0 # Versuche für die AKTUELL gesuchte Gemeinde
    if 'target' not in st.session_state:
        st.session_state.target = random.choice(gdf[name_col].tolist())
    if 'last_clicked_name' not in st.session_state:
        st.session_state.last_clicked_name = None

    # --- HEADER ---
    st.markdown(f"""
        <div style="background-color:#3e4a61; padding:15px; border-radius:10px; text-align:center; color:white; font-family:sans-serif;">
            <h2 style="margin:0;">Klicke auf: <span style="background:white; color:black; padding:2px 10px; border-radius:5px;">{st.session_state.target}</span></h2>
            <p style="margin:5px 0 0 0; opacity:0.8;">Versuch: {st.session_state.attempts + 1} / 3</p>
        </div>
    """, unsafe_allow_html=True)

    # Kurzes Feedback, wenn man daneben klickt
    if st.session_state.last_clicked_name:
        st.info(f"Das war: {st.session_state.last_clicked_name}")
        # Wir löschen den Namen nach dem Anzeigen nicht sofort, damit er kurz stehen bleibt
    
    # --- KARTEN-LOGIK ---
    m = folium.Map(location=[47.41, 8.12], zoom_start=10, tiles=None, 
                   zoom_control=False, dragging=False, scrollWheelZoom=False, attributionControl=False)
    
    folium.Rectangle(bounds=[[-90, -180], [90, 180]], fill=True, fill_color='#aadaff', fill_opacity=1).add_to(m)

    def get_color(name):
        res = st.session_state.results.get(name)
        if res == 1: return '#ffffff' # 1. Versuch -> Weiss
        if res == 2: return '#ffa500' # 2. Versuch -> Orange
        if res >= 3: return '#ff4b4b' # 3. Versuch / nicht gefunden -> Rot
        return '#27854d' # Standard -> Grün

    folium.GeoJson(
        gdf,
        style_function=lambda f: {
            'fillColor': get_color(f['properties'][name_col]),
            'color': 'white', 'weight': 0.5, 'fillOpacity': 1
        },
        highlight_function=lambda x: {'fillColor': '#f1c40f', 'fillOpacity': 0.7}
    ).add_to(m)

    out = st_folium(m, use_container_width=True, height=500, key="quiz_map", returned_objects=["last_active_drawing"])

    # --- LOGIK BEI KLICK ---
    if out and out.get('last_active_drawing'):
        clicked = out['last_active_drawing']['properties'][name_col]
        
        # Schon gelöste Gemeinden ignorieren
        if st.session_state.results[clicked] is None:
            
            if clicked == st.session_state.target:
                # TREFFER
                st.session_state.attempts += 1
                st.session_state.results[clicked] = st.session_state.attempts
                
                # Reset für nächste Gemeinde
                st.session_state.attempts = 0
                st.session_state.last_clicked_name = None
                remaining = [n for n, res in st.session_state.results.items() if res is None]
                if remaining:
                    st.session_state.target = random.choice(remaining)
                st.rerun()
            
            else:
                # FALSCH GEKLICKT
                st.session_state.attempts += 1
                st.session_state.last_clicked_name = clicked
                
                # Nach 3 Fehlversuchen: Automatisch lösen (Rot markieren)
                if st.session_state.attempts >= 3:
                    st.session_state.results[st.session_state.target] = 3
                    st.session_state.attempts = 0
                    st.session_state.last_clicked_name = f"Nicht gefunden! {st.session_state.target} wurde rot markiert."
                    remaining = [n for n, res in st.session_state.results.items() if res is None]
                    if remaining:
                        st.session_state.target = random.choice(remaining)
                
                st.rerun()

except Exception as e:
    st.error(f"Fehler: {e}")
