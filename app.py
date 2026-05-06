import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import random

# Seite konfigurieren
st.set_page_config(page_title="Aargau Quiz", layout="centered")

@st.cache_data
def load_data():
    # Versuche die Datei zu laden
    gdf = gpd.read_file("data.json")
    
    # Koordinaten ins Weltformat (WGS84) bringen, falls nötig
    if gdf.crs != "epsg:4326":
        gdf = gdf.to_crs(epsg=4326)
    
    # Finde heraus, wie die Namensspalte heißt (oft NAME, GMDNAME oder Gemeinde)
    possible_names = ['NAME', 'GMDNAME', 'Gemeinde', 'GMD_NAME', 'label']
    found_col = None
    for col in possible_names:
        if col in gdf.columns:
            found_col = col
            break
            
    if not found_col:
        # Falls nichts passt, nimm die erste Spalte mit Text
        found_col = gdf.select_dtypes(include=['object']).columns[0]
        
    return gdf, found_col

try:
    gdf, name_col = load_data()

    st.title("📍 Das Aargau-Quiz")
    st.markdown("Klicke auf die gesuchte Gemeinde auf der Karte!")

    # Spielstand initialisieren
    if 'target_name' not in st.session_state:
        st.session_state.target_name = random.choice(gdf[name_col].tolist())
    if 'feedback' not in st.session_state:
        st.session_state.feedback = ""

    st.subheader(f"Suche: :blue[{st.session_state.target_name}]")

    # Karte erstellen
    # Fokus auf die Mitte des Aargaus
    m = folium.Map(location=[47.39, 8.05], zoom_start=10, tiles="CartoDB positron")

    # Die Gemeinden als Layer hinzufügen
    geojson = folium.GeoJson(
        gdf,
        style_function=lambda x: {
            'fillColor': '#f2f2f2',
            'color': 'black',
            'weight': 0.5,
            'fillOpacity': 0.6
        },
        highlight_function=lambda x: {'weight': 3, 'color': 'orange'},
        tooltip=folium.GeoJsonTooltip(fields=[name_col], aliases=['Gemeinde:'])
    ).add_to(m)

    # Karte in Streamlit anzeigen
    map_output = st_folium(m, width=700, height=500)

    # Klick-Logik
    if map_output['last_active_drawing']:
        # Hole den Namen der geklickten Gemeinde aus den Daten
        clicked_name = map_output['last_active_drawing']['properties'][name_col]
        
        if clicked_name == st.session_state.target_name:
            st.success(f"Bravo! Das ist {clicked_name}!")
            if st.button("Nächste Runde"):
                st.session_state.target_name = random.choice(gdf[name_col].tolist())
                st.rerun()
        else:
            st.error(f"Das war {clicked_name}. Such weiter!")

except Exception as e:
    st.error("Oje, da stimmt was nicht!")
    st.write(e)
    st.info("Stelle sicher, dass 'data.json' im selben Ordner wie 'app.py' liegt.")
