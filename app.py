import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import random
import os

st.set_page_config(page_title="Aargau Geografie-Trainer", layout="centered")

@st.cache_data
def load_data():
    shp_path = "aargau_grenzen.shp"
    if not os.path.exists(shp_path):
        shp_files = [f for f in os.listdir('.') if f.endswith('.shp')]
        shp_path = shp_files[0] if shp_files else None
    
    if not shp_path: return None, None
    gdf = gpd.read_file(shp_path)
    if gdf.crs is None: gdf.crs = "epsg:2056"
    gdf = gdf.to_crs(epsg=4326)
    gdf['geometry'] = gdf['geometry'].simplify(0.0001, preserve_topology=True)
    
    name_col = next((c for c in ['GMDNAME', 'NAME', 'GEMEINDE'] if c in gdf.columns), gdf.columns[0])
    return gdf, name_col

try:
    gdf, name_col = load_data()

    if 'solved' not in st.session_state: st.session_state.solved = []
    if 'target' not in st.session_state: st.session_state.target = random.choice(gdf[name_col].tolist())
    if 'score' not in st.session_state: st.session_state.score = 0

    # --- SIDEBAR ---
    st.sidebar.title("Quiz-Optionen")
    modus = st.sidebar.radio("Modus wählen:", ["Klicken", "Benennen"])
    if st.sidebar.button("Quiz neu starten"):
        st.session_state.solved = []
        st.session_state.score = 0
        st.session_state.target = random.choice(gdf[name_col].tolist())
        st.rerun()

    # --- HEADER ---
    header_color = "#3e4a61"
    if modus == "Klicken":
        instruction = f"Klicke auf: <span style='background-color: white; color: black; padding: 2px 8px; border-radius: 4px; font-weight: bold;'>{st.session_state.target}</span>"
    else:
        instruction = "Wie heisst die <span style='background-color: #f1c40f; color: black; padding: 2px 8px; border-radius: 4px; font-weight: bold;'>gelbe</span> Gemeinde?"

    st.markdown(f"""
        <div style="background-color: {header_color}; padding: 15px; border-radius: 10px; text-align: center; color: white; font-family: sans-serif;">
            <h2 style="margin:0;">{instruction}</h2>
            <p style="margin:8px 0 0 0; opacity: 0.8;">Fortschritt: {len(st.session_state.solved)} / {len(gdf)} | Punkte: {st.session_state.score}</p>
        </div>
    """, unsafe_allow_html=True)

    if modus == "Benennen":
        st.write("")
        with st.form("input_form", clear_on_submit=True):
            user_input = st.text_input("Name der Gemeinde:", placeholder="Tippe hier...")
            if st.form_submit_button("Prüfen"):
                if user_input.strip().lower() == st.session_state.target.lower():
                    st.success("Richtig!")
                    if st.session_state.target not in st.session_state.solved:
                        st.session_state.solved.append(st.session_state.target)
                        st.session_state.score += 1
                    remaining = [n for n in gdf[name_col].tolist() if n not in st.session_state.solved]
                    if remaining: st.session_state.target = random.choice(remaining)
                    st.rerun()
                else:
                    st.error("Leider falsch!")

    # --- KARTEN-STYLING ---
    def style_fn(feature):
        name = feature['properties'][name_col]
        if name in st.session_state.solved:
            return {'fillColor': '#ffffff', 'color': '#555', 'weight': 1, 'fillOpacity': 1}
        if modus == "Benennen" and name == st.session_state.target:
            return {'fillColor': '#f1c40f', 'color': '#000', 'weight': 2, 'fillOpacity': 1}
        return {'fillColor': '#27854d', 'color': '#ffffff', 'weight': 0.7, 'fillOpacity': 1}

    # --- MANUELLE BERECHNUNG ---
    bounds = gdf.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2
    
    # Wir setzen einen fixen Zoom-Level, der für den Aargau bei dieser Fenstergröße passt.
    # 9.4 oder 9.5 ist oft ideal, um den Rand zu füllen.
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=9.4, 
        tiles=None,
        scrollWheelZoom=False, 
        dragging=False, 
        zoom_control=False,
        attributionControl=False
    )
    
    folium.Rectangle(
        bounds=[[-90, -180], [90, 180]],
        fill=True, fill_color='#aadaff', fill_opacity=1
    ).add_to(m)

    folium.GeoJson(
        gdf,
        style_function=style_fn,
        highlight_function=lambda x: {'fillColor': '#f1c40f', 'fillOpacity': 0.8} if modus == "Klicken" else {}
    ).add_to(m)

    # st_folium mit festen Dimensionen erzwingt das Layout
    output = st_folium(m, width=700, height=500, key="ag_quiz_final", returned_objects=["last_active_drawing"])

    if modus == "Klicken" and output and output.get('last_active_drawing'):
        clicked = output['last_active_drawing']['properties'][name_col]
        if clicked == st.session_state.target:
            if clicked not in st.session_state.solved:
                st.session_state.solved.append(clicked)
                st.session_state.score += 1
            remaining = [n for n in gdf[name_col].tolist() if n not in st.session_state.solved]
            if remaining: st.session_state.target = random.choice(remaining)
            st.rerun()

except Exception as e:
    st.error("Fehler beim Laden")
    st.write(e)
