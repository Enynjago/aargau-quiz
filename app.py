import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import random
import os

st.set_page_config(page_title="Aargau Quiz", layout="centered")

# CSS um die Karte im Container zu zentrieren und Ränder zu minimieren
st.markdown("""
    <style>
    .stMainContainer { padding-top: 2rem; }
    iframe { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

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
    st.sidebar.title("Einstellungen")
    modus = st.sidebar.radio("Modus:", ["Klicken", "Benennen"])
    if st.sidebar.button("Reset"):
        st.session_state.solved = []
        st.session_state.score = 0
        st.session_state.target = random.choice(gdf[name_col].tolist())
        st.rerun()

    # --- HEADER ---
    header_html = f"""
        <div style="background-color: #3e4a61; padding: 15px; border-radius: 10px; text-align: center; color: white; margin-bottom: 20px;">
            <h2 style="margin:0;">{f"Klicke auf: <b style='color:black; background:white; padding:0 5px;'>{st.session_state.target}</b>" if modus == "Klicken" else "Benenne die gelbe Gemeinde"}</h2>
            <p style="margin:5px 0 0 0;">Gelöst: {len(st.session_state.solved)}/201 | Punkte: {st.session_state.score}</p>
        </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)

    if modus == "Benennen":
        with st.form("quiz_form", clear_on_submit=True):
            ui = st.text_input("Name:")
            if st.form_submit_button("Prüfen") and ui.strip().lower() == st.session_state.target.lower():
                st.session_state.solved.append(st.session_state.target)
                st.session_state.score += 1
                st.session_state.target = random.choice([n for n in gdf[name_col] if n not in st.session_state.solved])
                st.rerun()

    # --- KARTEN-TRICK ---
    bounds = gdf.total_bounds
    cx, cy = (bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2
    
    # Wir erstellen die Map OHNE Zoom-Vorgabe, damit fit_bounds Priorität hat
    m = folium.Map(
        location=[cy, cx],
        tiles=None,
        zoom_control=False, dragging=False, scrollWheelZoom=False, attributionControl=False
    )
    
    folium.Rectangle(bounds=[[-90, -180], [90, 180]], fill=True, fill_color='#aadaff', fill_opacity=1).add_to(m)

    def style_fn(f):
        n = f['properties'][name_col]
        if n in st.session_state.solved: color = '#ffffff'
        elif modus == "Benennen" and n == st.session_state.target: color = '#f1c40f'
        else: color = '#27854d'
        return {'fillColor': color, 'color': '#fff', 'weight': 0.5, 'fillOpacity': 1}

    folium.GeoJson(gdf, style_function=style_fn, 
                   highlight_function=lambda x: {'fillColor': '#f1c40f'} if modus == "Klicken" else {}).add_to(m)

    # Hier setzen wir fit_bounds extrem aggressiv
    m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

    # st_folium mit 'use_container_width=True' füllt den Platz besser aus
    out = st_folium(m, use_container_width=True, height=500, key="ag_final")

    if modus == "Klicken" and out and out.get('last_active_drawing'):
        clicked = out['last_active_drawing']['properties'][name_col]
        if clicked == st.session_state.target:
            if clicked not in st.session_state.solved:
                st.session_state.solved.append(clicked)
                st.session_state.score += 1
            st.session_state.target = random.choice([n for n in gdf[name_col] if n not in st.session_state.solved])
            st.rerun()

except Exception as e:
    st.error(f"Fehler: {e}")
