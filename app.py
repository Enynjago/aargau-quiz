import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import random

# 1. Seite konfigurieren
st.set_page_config(page_title="Aargau Quiz", layout="wide")

@st.cache_data
def load_data():
    # Lädt dein JSON
    gdf = gpd.read_file("data.json")
    
    # WICHTIG: Schweizer Koordinaten (Meter) in Welt-Koordinaten (Grad) umwandeln
    if gdf.crs != "epsg:4326":
        gdf = gdf.to_crs(epsg=4326)
    
    # Automatische Suche nach der Spalte mit den Gemeindenamen
    possible_names = ['NAME', 'GMDNAME', 'Gemeinde', 'GMD_NAME', 'label', 'GENNAME']
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

    st.title("📍 Das Aargau-Gemeinde-Quiz")
    st.write("Klicke auf die gesuchte Gemeinde auf der Karte.")

    # Spielstand in der Session speichern
    if 'target_name' not in st.session_state:
        st.session_state.target_name = random.choice(gdf[name_col].tolist())
    if 'score' not in st.session_state:
        st.session_state.score = 0

    # Anzeige der gesuchten Gemeinde
    st.info(f"Suche die Gemeinde: **{st.session_state.target_name}**")
    st.write(f"Aktueller Punktestand: {st.session_state.score}")

    # --- KARTEN-LOGIK ---
    # Berechne das Zentrum und den Rahmen (Bounds) für den automatischen Zoom
    bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
    
    # Karte initialisieren (Startpunkt ist grob Mitte Aargau)
    m = folium.Map(tiles="CartoDB positron")
    
    # Automatisch auf die Grenzen des Aargaus zoomen
    m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

    # Gemeinden einzeichnen
    folium.GeoJson(
        gdf,
        style_function=lambda x: {
            'fillColor': '#3178c6',
            'color': 'black',
            'weight': 1,
            'fillOpacity': 0.4
        },
        highlight_function=lambda x: {'weight': 3, 'color': 'orange', 'fillOpacity': 0.7},
        tooltip=folium.GeoJsonTooltip(fields=[name_col], aliases=['Gemeinde:'])
    ).add_to(m)

    # Karte in Streamlit anzeigen
    # Wir fangen den Klick ab
    map_output = st_folium(m, width=800, height=600, key="ag_map")

    # --- ÜBERPRÜFUNG ---
    if map_output['last_active_drawing']:
        properties = map_output['last_active_drawing']['properties']
        clicked_name = properties[name_col]
        
        if clicked_name == st.session_state.target_name:
            st.balloons()
            st.success(f"Richtig! Das ist {clicked_name}!")
            st.session_state.score += 1
            # Neue Gemeinde auswählen
            st.session_state.target_name = random.choice(gdf[name_col].tolist())
            st.button("Nächste Gemeinde")
        else:
            st.error(f"Falsch. Das war {clicked_name}. Versuch es nochmals!")

    if st.button("Andere Gemeinde suchen"):
        st.session_state.target_name = random.choice(gdf[name_col].tolist())
        st.rerun()

except Exception as e:
    st.error("Ein Fehler ist aufgetreten!")
    st.exception(e)
    st.info("Hinweis: Überprüfe, ob 'data.json' im GitHub-Repo liegt.")
