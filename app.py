import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import random
import os

st.set_page_config(page_title="Aargau Shapefile Quiz", layout="centered")

@st.cache_data
def load_shapefile():
    # Suche die .shp Datei im Ordner
    shp_file = [f for f in os.listdir('.') if f.endswith('.shp')][0]
    gdf = gpd.read_file(shp_file)
    
    # 1. Koordinaten-System (CRS)
    # Schweizer Shapefiles sind fast immer in Meter (EPSG:2056 oder 21781)
    # Wir wandeln sie für die Webkarte in Grad um.
    if gdf.crs is None:
        gdf.crs = "epsg:2056"
    gdf = gdf.to_crs(epsg=4326)
    
    # 2. Die richtige Spalte für Namen finden (BFS-Nummern ignorieren)
    # Wir suchen Spalten mit Text, die mehr als nur Ziffern enthalten
    potential_cols = []
    for col in gdf.columns:
        if gdf[col].dtype == 'object':
            # Checken, ob der Inhalt wirklich Text ist und keine versteckte Zahl
            sample = str(gdf[col].iloc[0])
            if not sample.isdigit():
                potential_cols.append(col)
    
    # Favoriten-Liste für Spaltennamen
    favs = ['GMDNAME', 'NAME', 'GEMEINDE', 'GENNAME']
    name_col = next((c for c in favs if c in potential_cols), potential_cols[0])
    
    return gdf, name_col

try:
    gdf, name_col = load_shapefile()

    if 'target' not in st.session_state:
        st.session_state.target = random.choice(gdf[name_col].tolist())
    if 'counter' not in st.session_state:
        st.session_state.counter = 0

    st.title("📍 Aargau Quiz (Shapefile)")
    st.subheader(f"Suche die Gemeinde: :blue[{st.session_state.target}]")

    # Karte erstellen (Zentrum Aargau)
    m = folium.Map(
        location=[47.40, 8.10], 
        zoom_start=10, 
        tiles="CartoDB positron",
        scrollWheelZoom=False
    )

    # Grenzen einzeichnen
    folium.GeoJson(
        gdf,
        style_function=lambda x: {
            'fillColor': '#3178c6',
            'color': 'black',
            'weight': 1,
            'fillOpacity': 0.3
        },
        highlight_function=lambda x: {'weight': 3, 'color': 'red'},
        tooltip=folium.GeoJsonTooltip(fields=[name_col], aliases=['Gemeinde:'])
    ).add_to(m)

    # Karte anzeigen
    output = st_folium(m, width=700, height=500)

    # Klick-Logik
    if output['last_active_drawing']:
        clicked = output['last_active_drawing']['properties'][name_col]
        if clicked == st.session_state.target:
            st.success(f"Richtig! Das ist {clicked}!")
            if st.button("Nächste Gemeinde"):
                st.session_state.target = random.choice(gdf[name_col].tolist())
                st.session_state.counter += 1
                st.rerun()
        else:
            st.error(f"Das ist {clicked}. Such weiter nach {st.session_state.target}!")

except Exception as e:
    st.error(f"Fehler beim Laden: {e}")
    st.info("Stelle sicher, dass alle Shapefile-Teile (.shp, .shx, .dbf, .prj) hochgeladen sind.")
