import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import random
import os

# Seite konfigurieren
st.set_page_config(page_title="Aargau Gemeinde-Quiz", layout="centered")

@st.cache_data
def load_data():
    shp_path = "aargau_grenzen.shp"
    if not os.path.exists(shp_path):
        # Falls die Datei anders heißt, suchen wir die erste .shp Datei im Ordner
        shp_files = [f for f in os.listdir('.') if f.endswith('.shp')]
        if shp_files:
            shp_path = shp_files[0]
        else:
            raise FileNotFoundError("Keine .shp Datei auf GitHub gefunden!")

    gdf = gpd.read_file(shp_path)
    
    # Koordinaten-System (CRS) umwandeln
    if gdf.crs is None:
        gdf.crs = "epsg:2056"
    gdf = gdf.to_crs(epsg=4326)
    
    # --- INTELLIGENTE NAMENSSUCHE ---
    # Wir suchen die Spalte, die Text enthält und keine reine Zahl ist
    name_col = None
    
    # 1. Priorität: Bekannte Standardnamen
    favs = ['GMDNAME', 'NAME', 'GEMEINDE', 'GENNAME', 'GMD_NAME']
    for fav in favs:
        if fav in gdf.columns:
            # Testen, ob der Inhalt wirklich Text ist
            if not str(gdf[fav].iloc[0]).isdigit():
                name_col = fav
                break
    
    # 2. Priorität: Falls kein Favorit passt, nimm die erste Text-Spalte
    if not name_col:
        for col in gdf.columns:
            if gdf[col].dtype == 'object':
                sample = str(gdf[col].iloc[0])
                if not sample.isdigit() and len(sample) > 2:
                    name_col = col
                    break
    
    # Notfall-Fallback
    if not name_col:
        name_col = gdf.columns[0]
        
    return gdf, name_col

try:
    gdf, name_col = load_data()

    # Quiz-Logik initialisieren
    if 'target' not in st.session_state:
        st.session_state.target = random.choice(gdf[name_col].tolist())
    if 'score' not in st.session_state:
        st.session_state.score = 0

    st.title("📍 Aargau Geografie-Quiz")
    
    # Kleiner Debug-Hinweis (nur falls es immer noch Zahlen sind)
    # st.write(f"DEBUG: Spalte '{name_col}' wird verwendet.")

    st.subheader(f"Suche die Gemeinde: :blue[{st.session_state.target}]")
    st.write(f"✅ Punkte: {st.session_state.score}")

    # --- KARTEN-SETUP ---
    bounds = gdf.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=10,
        min_zoom=9,
        max_zoom=13,
        tiles="CartoDB positron",
        scrollWheelZoom=False
    )
    m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

    # Geometrien einzeichnen
    folium.GeoJson(
        gdf,
        style_function=lambda x: {
            'fillColor': '#3178c6',
            'color': 'black',
            'weight': 1,
            'fillOpacity': 0.2
        },
        highlight_function=lambda x: {'weight': 3, 'color': 'orange', 'fillOpacity': 0.5},
        tooltip=folium.GeoJsonTooltip(fields=[name_col], aliases=['Gemeinde:'])
    ).add_to(m)

    # Anzeige
    output = st_folium(m, width=700, height=500, key="quiz_map")

    # --- KLICK-LOGIK ---
    if output['last_active_drawing']:
        props = output['last_active_drawing']['properties']
        clicked_name = props[name_col]
        
        if clicked_name == st.session_state.target:
            st.success(f"Richtig! Das ist {clicked_name}!")
            st.balloons()
            st.session_state.score += 1
            # Neue Gemeinde wählen
            st.session_state.target = random.choice(gdf[name_col].tolist())
            st.button("Nächste Runde")
        else:
            # Verhindert, dass Zahlen im Fehlertext erscheinen
            st.error(f"Falsch! Das war {clicked_name}. Such weiter!")

    if st.button("Gemeinde überspringen"):
        st.session_state.target = random.choice(gdf[name_col].tolist())
        st.rerun()

except Exception as e:
    st.error("Problem beim Laden der Daten.")
    st.exception(e)
