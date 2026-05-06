import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import random

st.set_page_config(page_title="Aargau Quiz", layout="centered")

@st.cache_data
def load_data():
    gdf = gpd.read_file("data.json")
    
    # 1. VERSUCH: Koordinaten-Check und Umrechnung
    # Falls das CRS nicht gesetzt ist, setzen wir es auf das Schweizer System (MN95)
    if gdf.crs is None:
        gdf.crs = "epsg:2056" 
    
    # Umwandeln in das Web-Format (WGS84)
    gdf = gdf.to_crs(epsg=4326)
    
    # 2. Namensspalte finden
    possible_names = ['NAME', 'GMDNAME', 'Gemeinde', 'GMD_NAME', 'GENNAME', 'label']
    name_col = next((c for c in possible_names if c in gdf.columns), gdf.columns[0])
    
    return gdf, name_col

try:
    gdf, name_col = load_data()

    if 'target_name' not in st.session_state:
        st.session_state.target_name = random.choice(gdf[name_col].tolist())

    st.title("📍 Aargau Quiz")
    st.subheader(f"Suche: {st.session_state.target_name}")

    # --- MANUELLE KARTE (AARGAU FIXIERT) ---
    # Wir setzen die Koordinaten fix auf die Mitte des Aargaus (Aarau/Lenzburg)
    # Damit wir sicher etwas sehen.
    m = folium.Map(
        location=[47.40, 8.10], 
        zoom_start=10, 
        tiles="OpenStreetMap", # "OpenStreetMap" ist oft stabiler zum Testen
        scrollWheelZoom=False
    )

    # Gemeinden hinzufügen
    folium.GeoJson(
        gdf,
        style_function=lambda x: {
            'fillColor': 'blue',
            'color': 'black',
            'weight': 1,
            'fillOpacity': 0.2
        },
        tooltip=folium.GeoJsonTooltip(fields=[name_col])
    ).add_to(m)

    # Anzeige
    map_output = st_folium(m, width=700, height=500)

    # --- DEBUG INFO (Nur für dich zum Testen) ---
    with st.expander("Daten-Check (Klick hier falls Karte leer)"):
        st.write(f"Anzahl Gemeinden gefunden: {len(gdf)}")
        st.write("Spalten in deiner Datei:", list(gdf.columns))
        st.write("Erste Koordinaten:", gdf.geometry.iloc[0].centroid.coords[0] if not gdf.empty else "Keine")

except Exception as e:
    st.error(f"Fehler: {e}")
