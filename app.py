import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import random
import os

st.set_page_config(page_title="Aargau Quiz", layout="centered")

# CSS: Wir entfernen unnötige Abstände, damit die Karte Platz hat
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; padding-bottom: 0rem; }
    iframe { width: 100% !important; border-radius: 15px; }
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
    
    # Session States initialisieren
    if 'solved' not in st.session_state: st.session_state.solved = []
    if 'target' not in st.session_state: st.session_state.target = random.choice(gdf[name_col].tolist())
    if 'score' not in st.session_state: st.session_state.score = 0

    # Quiz Modus Auswahl in der Sidebar
    modus = st.sidebar.radio("Modus:", ["Klicken", "Benennen"])

    # --- HEADER (DEIN DESIGN) ---
    instruction = f"Klicke auf: <span style='background:white; color:black; padding:2px 10px; border-radius:5px;'>{st.session_state.target}</span>" if modus == "Klicken" else "Wie heisst die <span style='color:#f1c40f;'>gelbe</span> Gemeinde?"
    
    st.markdown(f"""
        <div style="background-color: #3e4a61; padding: 20px; border-radius: 15px; text-align: center; color: white; margin-bottom: 10px;">
            <h1 style="margin:0; font-size: 2.5rem;">{instruction}</h1>
            <p style="margin:10px 0 0 0; font-size: 1.2rem; opacity: 0.8;">Fortschritt: {len(st.session_state.solved)} / 201 | Punkte: {st.session_state.score}</p>
        </div>
    """, unsafe_allow_html=True)

    if modus == "Benennen":
        with st.form("input", clear_on_submit=True):
            col1, col2 = st.columns([4,1])
            with col1: ui = st.text_input("Name der Gemeinde:", label_visibility="collapsed")
            with col2: submit = st.form_submit_button("Prüfen")
            if submit and ui.strip().lower() == st.session_state.target.lower():
                st.session_state.solved.append(st.session_state.target)
                st.session_state.score += 1
                st.session_state.target = random.choice([n for n in gdf[name_col] if n not in st.session_state.solved])
                st.rerun()

    # --- DIE KARTEN-LOGIK (MANUELL ERZWUNGEN) ---
    # Wir setzen den Fokus exakt auf die Mitte des Aargaus
    # Koordinaten ca.: Lat 47.4, Lon 8.1
    m = folium.Map(
        location=[47.41, 8.12], 
        zoom_start=10, # <--- HIER EXPERIMENTIEREN: 10 ist näher als 9
        tiles=None,
        zoom_control=False,
        dragging=False,
        scrollWheelZoom=False,
        attributionControl=False
    )

    # Hintergrundfarbe
    folium.Rectangle(bounds=[[-90, -180], [90, 180]], fill=True, fill_color='#aadaff', fill_opacity=1).add_to(m)

    def style_fn(f):
        n = f['properties'][name_col]
        if n in st.session_state.solved: color = '#ffffff'
        elif modus == "Benennen" and n == st.session_state.target: color = '#f1c40f'
        else: color = '#27854d'
        return {'fillColor': color, 'color': 'white', 'weight': 1, 'fillOpacity': 1}

    folium.GeoJson(
        gdf, 
        style_function=style_fn,
        highlight_function=lambda x: {'fillColor': '#f1c40f', 'fillOpacity': 0.8} if modus == "Klicken" else {}
    ).add_to(m)

    # st_folium mit "use_container_width" sorgt für die maximale Breite
    out = st_folium(
        m, 
        use_container_width=True, 
        height=600, 
        key="aargau_map_v1",
        returned_objects=["last_active_drawing"]
    )

    # Klick-Logik
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
