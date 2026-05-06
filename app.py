import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import random

# 1. Seite konfigurieren
st.set_page_config(page_title="Aargau Quiz", layout="centered")

@st.cache_data
def load_data():
    # Lädt dein JSON (Stelle sicher, dass die Datei auf GitHub 'data.json' heißt)
    gdf = gpd.read_file("data.json")
    
    # Schweizer Koordinaten in Welt-Koordinaten (Grad) umwandeln
    if gdf.crs != "epsg:4326":
        gdf = gdf.to_crs(epsg=4326)
    
    # Suche nach der Spalte mit den Gemeindenamen
    possible_names = ['NAME', 'GMDNAME', 'Gemeinde', 'GMD_NAME', 'GENNAME']
    name_col = None
    for col in possible_names:
        if col in gdf.columns:
            name_col = col
            break
    
    if not name_col:
        name_col = gdf.select_dtypes(include=['object']).columns[0]
        
    return gdf, name_col

# --- App Start ---
try:
    gdf, name_col = load_data()

    st.title("📍 Aargau Geografie-Trainer")
    
    # Spielstand in der Session speichern
    if 'target_name' not in st.session_state:
        st.session_state.target_name = random.choice(gdf[name_col].tolist())
    if 'score' not in st.session_state:
        st.session_state.score = 0

    # UI Layout
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader(f"Suche: :blue[{st.session_state.target_name}]")
    with col2:
        st.write(f"✅ Punkte: {st.session_state.score}")

    # --- KARTEN-LOGIK (STANDBILD-MODUS) ---
    bounds = gdf.total_bounds # [minx, miny, maxx, maxy]
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2

    # Erstelle die Karte mit eingeschränktem Zoom und Bewegung
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=10,
        min_zoom=9,           # Verhindert zu weites Rauszoomen
        max_zoom=12,          # Erlaubt nur wenig Reinzoomen
        tiles="CartoDB positron",
        scrollWheelZoom=False, # Verhindert versehentliches Zoomen beim Scrollen der Webseite
        dragging=True          # Erlaubt das Verschieben der Karte
    )

    # Fixiert die Ansicht auf den Aargau
    m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

    # Die Gemeinden einzeichnen
    geojson = folium.GeoJson(
        gdf,
        style_function=lambda x: {
            'fillColor': '#3178c6',
            'color': 'black',
            'weight': 1,
            'fillOpacity': 0.2  # Dezent, damit man Namen darunter lesen kann
        },
        highlight_function=lambda x: {'weight': 3, 'color': 'orange', 'fillOpacity': 0.5},
        tooltip=folium.GeoJsonTooltip(fields=[name_col], aliases=['Gemeinde:'])
    ).add_to(m)

    # Anzeige in Streamlit
    map_output = st_folium(m, width=700, height=550, key="ag_quiz_map")

    # --- LOGIK BEI KLICK ---
    if map_output['last_active_drawing']:
        properties = map_output['last_active_drawing']['properties']
        clicked_name = properties[name_col]
        
        if clicked_name == st.session_state.target_name:
            st.success(f"Richtig! Das ist {clicked_name}!")
            st.balloons()
            st.session_state.score += 1
            # Neue Gemeinde auswählen
            st.session_state.target_name = random.choice(gdf[name_col].tolist())
            st.button("Nächste Gemeinde")
        else:
            st.error(f"Das war {clicked_name}. Such weiter!")

    if st.button("Gemeinde überspringen"):
        st.session_state.target_name = random.choice(gdf[name_col].tolist())
        st.rerun()

except Exception as e:
    st.error("Datei 'data.json' konnte nicht korrekt geladen werden.")
    st.info("Stelle sicher, dass du die JSON-Datei im GitHub-Repo hochgeladen hast.")
    st.write(e)
