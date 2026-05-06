import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import random
import os

st.set_page_config(page_title="Aargau Quiz", layout="centered")

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
    
    # Namensspalte finden
    name_col = next((c for c in ['GMDNAME', 'NAME', 'GEMEINDE'] if c in gdf.columns), gdf.columns[0])
    return gdf, name_col

try:
    gdf, name_col = load_data()

    # --- SESSION STATE ---
    if 'solved' not in st.session_state: st.session_state.solved = []
    if 'target' not in st.session_state: st.session_state.target = random.choice(gdf[name_col].tolist())
    if 'score' not in st.session_state: st.session_state.score = 0

    # --- HEADER (SETERRA STYLE) ---
    st.markdown(f"""
        <div style="background-color: #3e4a61; padding: 15px; border-radius: 10px; text-align: center; color: white;">
            <h2 style="margin:0;">Klicke auf: <span style="background-color: white; color: black; padding: 2px 10px; border-radius: 5px;">{st.session_state.target}</span></h2>
            <p style="margin:5px 0 0 0;">Fortschritt: {len(st.session_state.solved)} / {len(gdf)} | Punkte: {st.session_state.score}</p>
        </div>
    """, unsafe_allow_html=True)

    # --- KARTEN LOGIK ---
    bounds = gdf.total_bounds
    # Weisser Hintergrund statt Satellit/Strassen
    m = folium.Map(
        location=[(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2],
        zoom_start=10,
        tiles=None, # Entfernt alle Standard-Karten
        scrollWheelZoom=False,
        dragging=False, # Karte fixieren
        zoom_control=False
    )
    # Hintergrund-Farbe setzen (wie das hellblaue Wasser)
    folium.Rectangle(
        bounds=[[-90, -180], [90, 180]],
        col='white',
        fill=True,
        fill_color='#aadaff', # Wasser-Blau aus deinem Screenshot
        fill_opacity=1
    ).add_to(m)

    def style_fn(feature):
        name = feature['properties'][name_col]
        if name in st.session_state.solved:
            return {'fillColor': '#ffffff', 'color': '#111', 'weight': 1, 'fillOpacity': 1} # Weiss wenn gelöst
        return {'fillColor': '#27854d', 'color': '#ffffff', 'weight': 0.8, 'fillOpacity': 1} # Seterra-Grün

    folium.GeoJson(
        gdf,
        style_function=style_fn,
        highlight_function=lambda x: {'fillColor': '#f1c40f', 'fillOpacity': 0.8} # Gelb beim Drüberfahren
    ).add_to(m)

    m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

    # Anzeige
    output = st_folium(m, width=700, height=550, key="quiz_map")

    # Auswertung
    if output['last_active_drawing']:
        clicked = output['last_active_drawing']['properties'][name_col]
        if clicked == st.session_state.target:
            st.success(f"Richtig! {clicked}")
            if clicked not in st.session_state.solved:
                st.session_state.solved.append(clicked)
                st.session_state.score += 1
            
            remaining = [n for n in gdf[name_col].tolist() if n not in st.session_state.solved]
            if remaining:
                st.session_state.target = random.choice(remaining)
                st.rerun()
        else:
            st.error(f"Falsch! Das war {clicked}.")

    if st.button("Überspringen"):
        st.session_state.target = random.choice(gdf[name_col].tolist())
        st.rerun()

except Exception as e:
    st.error("Fehler beim Laden")
    st.write(e)
