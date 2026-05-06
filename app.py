import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import random
import os

# Seite konfigurieren
st.set_page_config(page_title="Aargau Gemeinde-Quiz", layout="centered")

@st.cache_data
def load_shapefile():
    # Wir nutzen den exakten Namen aus deinem Screenshot
    shp_path = "aargau_grenzen.shp"
    
    if not os.path.exists(shp_path):
        raise FileNotFoundError(f"Die Datei {shp_path} wurde nicht gefunden. Bitte prüfe die Schreibweise auf GitHub.")

    # Shapefile laden
    gdf = gpd.read_file(shp_path)
    
    # Koordinaten-System (CRS) von Schweizer Meter in Welt-Grad umwandeln
    if gdf.crs is None:
        gdf.crs = "epsg:2056"
    gdf = gdf.to_crs(epsg=4326)
    
    # Die richtige Spalte für Namen finden (BFS-Nummern ignorieren)
    potential_cols = []
    for col in gdf.columns:
        if gdf[col].dtype == 'object':
            # Wir prüfen, ob der Inhalt wirklich Text ist (keine reine Zahl)
            sample = str(gdf[col].iloc[0])
            if not sample.isdigit():
                potential_cols.append(col)
    
    # Favoriten-Liste für Spaltennamen (GMDNAME ist im Aargau oft der Standard)
    favs = ['GMDNAME', 'NAME', 'GEMEINDE', 'GENNAME']
    name_col = next((c for c in favs if c in potential_cols), potential_cols[0] if potential_cols else gdf.columns[0])
    
    return gdf, name_col

# --- Hauptprogramm ---
try:
    gdf, name_col = load_shapefile()

    # Initialisierung der Quiz-Logik
    if 'target' not in st.session_state:
        st.session_state.target = random.choice(gdf[name_col].tolist())
    if 'score' not in st.session_state:
        st.session_state.score = 0

    st.title("📍 Aargau Geografie-Quiz")
    st.markdown(f"Suche die Gemeinde: **{st.session_state.target}**")
    st.write(f"Aktueller Punktestand: {st.session_state.score}")

    # --- KARTEN-EINSTELLUNGEN ---
    # Zentrum berechnen
    bounds = gdf.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2

    # Karte erstellen (Standbild-Modus)
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=10,
        min_zoom=9,
        max_zoom=12,
        tiles="CartoDB positron",
        scrollWheelZoom=False
    )

    # Automatisch auf den Aargau zoomen
    m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

    # Geometrien hinzufügen
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

    # Karte anzeigen
    output = st_folium(m, width=700, height=500, key="quiz_map")

    # --- AUSWERTUNG ---
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
            st.error(f"Falsch! Das war {clicked_name}. Such weiter nach {st.session_state.target}!")

    if st.button("Gemeinde überspringen"):
        st.session_state.target = random.choice(gdf[name_col].tolist())
        st.rerun()

except Exception as e:
    st.error("Es gab ein Problem beim Laden der Daten.")
    st.exception(e)
