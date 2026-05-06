import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import random
import os

# Seite konfigurieren - 'wide' kann die Performance bei Karten verbessern
st.set_page_config(page_title="Aargau Quiz", layout="wide")

@st.cache_data
def load_data():
    shp_path = "aargau_grenzen.shp"
    if not os.path.exists(shp_path):
        shp_files = [f for f in os.listdir('.') if f.endswith('.shp')]
        shp_path = shp_files[0] if shp_files else None
    
    if not shp_path:
        return None, None

    gdf = gpd.read_file(shp_path)
    if gdf.crs is None:
        gdf.crs = "epsg:2056"
    gdf = gdf.to_crs(epsg=4326)
    
    # Vereinfachung der Geometrie für mehr Speed (Toleranz in Grad)
    # 0.0001 reduziert die Datenpunkte, ohne dass man es optisch stark merkt
    gdf['geometry'] = gdf['geometry'].simplify(0.0001, preserve_topology=True)
    
    # Namensspalte finden
    name_col = None
    favs = ['GMDNAME', 'NAME', 'GEMEINDE', 'GMD_NAME']
    for fav in favs:
        if fav in gdf.columns and not str(gdf[fav].iloc[0]).isdigit():
            name_col = fav
            break
    
    if not name_col:
        name_col = gdf.select_dtypes(include=['object']).columns[0]
        
    return gdf, name_col

try:
    gdf, name_col = load_data()

    if 'target' not in st.session_state:
        st.session_state.target = random.choice(gdf[name_col].tolist())
    if 'score' not in st.session_state:
        st.session_state.score = 0

    st.title("📍 Aargau Quiz")
    
    # Layout für Text
    c1, c2 = st.columns([3, 1])
    with c1:
        st.subheader(f"Gesucht: :blue[{st.session_state.target}]")
    with c2:
        st.metric("Punkte", st.session_state.score)

    # --- KARTEN-SETUP (OPTIMIERT) ---
    bounds = gdf.total_bounds
    m = folium.Map(
        location=[(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2],
        zoom_start=10,
        tiles="CartoDB positron",
        scrollWheelZoom=False,
        zoom_control=True
    )
    m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

    # Geometrien OHNE Tooltip (damit man die Lösung nicht sieht)
    folium.GeoJson(
        gdf,
        style_function=lambda x: {
            'fillColor': '#3178c6',
            'color': 'black',
            'weight': 0.5, # Dünnere Linien sparen Rechenleistung
            'fillOpacity': 0.2
        },
        highlight_function=lambda x: {'weight': 2, 'color': 'orange', 'fillOpacity': 0.4}
    ).add_to(m)

    # Anzeige der Karte
    # use_container_width=True sorgt für bessere Anpassung
    output = st_folium(m, width=800, height=500, key="quiz_map")

    # Logik
    if output['last_active_drawing']:
        clicked_name = output['last_active_drawing']['properties'][name_col]
        
        if clicked_name == st.session_state.target:
            st.success(f"Richtig! Das ist {clicked_name}!")
            st.balloons()
            st.session_state.score += 1
            st.session_state.target = random.choice(gdf[name_col].tolist())
            st.button("Nächste Gemeinde")
        else:
            # Falls es eine Zahl ist, zeigen wir nichts an, sonst den Namen
            if not str(clicked_name).isdigit():
                st.error(f"Falsch! Das war {clicked_name}. Such weiter!")
            else:
                st.error("Falsch! Versuch es noch einmal.")

    if st.button("Überspringen"):
        st.session_state.target = random.choice(gdf[name_col].tolist())
        st.rerun()

except Exception as e:
    st.error("Fehler beim Starten der App.")
    st.write(e)
