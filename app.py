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
    gdf['geometry'] = gdf['geometry'].simplify(0.0008, preserve_topology=True)
    name_col = next((c for c in ['GMDNAME', 'NAME', 'GEMEINDE'] if c in gdf.columns), gdf.columns[0])
    return gdf, name_col

try:
    gdf, name_col = load_data()

    # --- SESSION STATE INITIALISIERUNG (SICHER) ---
    if 'results' not in st.session_state:
        st.session_state.results = {name: 0 for name in gdf[name_col]}
    if 'target' not in st.session_state:
        st.session_state.target = random.choice(gdf[name_col].tolist())
    if 'current_attempts' not in st.session_state:
        st.session_state.current_attempts = 0
    if 'last_processed_click' not in st.session_state:
        st.session_state.last_processed_click = None
    if 'feedback' not in st.session_state:
        st.session_state.feedback = None

    # --- SIDEBAR ---
    if st.sidebar.button("Reset"):
        for key in ['results', 'target', 'current_attempts', 'last_processed_click', 'feedback']:
            if key in st.session_state: del st.session_state[key]
        st.rerun()

    # --- HEADER ---
    st.markdown(f"""
        <div style="background-color:#3e4a61; padding:20px; border-radius:12px; text-align:center; color:white;">
            <h1 style="margin:0;">Klicke auf: <span style="background:white; color:black; padding:2px 10px; border-radius:5px;">{st.session_state.target}</span></h1>
            <p style="margin:10px 0 0 0; font-size:1.2rem;">Versuch: {st.session_state.current_attempts + 1} / 3</p>
        </div>
    """, unsafe_allow_html=True)

    if st.session_state.feedback:
        st.info(st.session_state.feedback)

    # --- KARTE ---
    m = folium.Map(location=[47.38, 8.12], zoom_start=10.0, tiles=None, # Zoom auf 10.0 für dich
                   zoom_control=False, dragging=False, scrollWheelZoom=False, attributionControl=False)
    
    folium.Rectangle(bounds=[[-90, -180], [90, 180]], fill=True, fill_color='#aadaff', fill_opacity=1).add_to(m)

    def style_fn(f):
        res = st.session_state.results.get(f['properties'][name_col], 0)
        color = '#ffffff' if res == 1 else '#ffa500' if res == 2 else '#ff4b4b' if res >= 3 else '#27854d'
        return {'fillColor': color, 'color': 'white', 'weight': 0.7, 'fillOpacity': 1}

    folium.GeoJson(gdf, style_function=style_fn, highlight_function=lambda x: {'fillColor': '#f1c40f'}).add_to(m)

    # st_folium Ausgabe
    out = st_folium(m, use_container_width=True, height=550, key="fixed_map")

    # --- DIE NEUE, SICHERE LOGIK ---
    if out and out.get('last_active_drawing'):
        current_click = out['last_active_drawing']['properties'][name_col]
        
        # Sicherheits-Check: Nur verarbeiten, wenn der Klick neu ist ODER kein Feedback existiert
        if out['last_active_drawing'] != st.session_state.last_processed_click:
            st.session_state.last_processed_click = out['last_active_drawing']
            
            # Nur reagieren, wenn Gemeinde noch nicht gelöst
            if st.session_state.results[current_click] == 0:
                
                if current_click == st.session_state.target:
                    # RICHTIG GEKLICKT
                    st.session_state.current_attempts += 1
                    st.session_state.results[current_click] = st.session_state.current_attempts
                    st.session_state.current_attempts = 0
                    st.session_state.feedback = f"Richtig! Das war {current_click}."
                    st.session_state.target = random.choice([n for n, r in st.session_state.results.items() if r == 0])
                    st.rerun()
                
                else:
                    # FALSCH GEKLICKT
                    st.session_state.current_attempts += 1
                    
                    if st.session_state.current_attempts >= 3:
                        # 3 Fehler voll
                        st.session_state.results[st.session_state.target] = 3
                        st.session_state.current_attempts = 0
                        st.session_state.feedback = f"Leider nein. Gesucht war {st.session_state.target} (jetzt rot)."
                        st.session_state.target = random.choice([n for n, r in st.session_state.results.items() if r == 0])
                    else:
                        # 1. oder 2. Fehler
                        st.session_state.feedback = f"Falsch, das war {current_click}! Du hast noch {3 - st.session_state.current_attempts} Versuche."
                    
                    st.rerun()

except Exception as e:
    st.error(f"Fehler im Quiz: {e}")
