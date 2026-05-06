import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import random
import os

# Seite konfigurieren
st.set_page_config(page_title="Aargau Profi-Quiz", layout="wide")

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
    
    # Namensspalte finden
    name_col = None
    for col in ['GMDNAME', 'NAME', 'GEMEINDE', 'GMD_NAME']:
        if col in gdf.columns and not str(gdf[col].iloc[0]).isdigit():
            name_col = col
            break
    return gdf, name_col

try:
    gdf, name_col = load_data()

    # --- SESSION STATE INITIALISIERUNG ---
    if 'solved_gemeinden' not in st.session_state:
        st.session_state.solved_gemeinden = []
    if 'target' not in st.session_state:
        st.session_state.target = random.choice(gdf[name_col].tolist())
    if 'score' not in st.session_state:
        st.session_state.score = 0

    # --- SIDEBAR MODUS WAHL ---
    st.sidebar.title("Einstellungen")
    modus = st.sidebar.radio("Wähle den Modus:", ["Gemeinde anklicken", "Gemeinde benennen"])
    
    if st.sidebar.button("Quiz zurücksetzen"):
        st.session_state.solved_gemeinden = []
        st.session_state.score = 0
        st.session_state.target = random.choice(gdf[name_col].tolist())
        st.rerun()

    st.title("📍 Aargau Geografie-Trainer")

    # --- LOGIK: WELCHE GEMEINDE WIRD GEZEIGT? ---
    # Im Modus "Benennen" müssen wir die gesuchte Gemeinde auf der Karte hervorheben
    highlight_target = st.session_state.target if modus == "Gemeinde benennen" else None

    col1, col2 = st.columns([3, 1])

    with col1:
        if modus == "Gemeinde anklicken":
            st.subheader(f"Gesucht: :blue[{st.session_state.target}]")
        else:
            st.subheader("Wie heisst die gelb markierte Gemeinde?")
            user_input = st.text_input("Name hier eingeben:", key="input_text")
            if st.button("Prüfen"):
                if user_input.strip().lower() == st.session_state.target.lower():
                    st.success("Richtig!")
                    if st.session_state.target not in st.session_state.solved_gemeinden:
                        st.session_state.solved_gemeinden.append(st.session_state.target)
                        st.session_state.score += 1
                    st.session_state.target = random.choice(gdf[~gdf[name_col].isin(st.session_state.solved_gemeinden)][name_col].tolist())
                    st.rerun()
                else:
                    st.error("Leider falsch, versuch es nochmal!")

    with col2:
        st.metric("Punkte", st.session_state.score)
        st.write(f"Gelöst: {len(st.session_state.solved_gemeinden)} / {len(gdf)}")

    # --- KARTEN-STYLING ---
    def get_style(feature):
        gmd_name = feature['properties'][name_col]
        # Falls bereits gelöst -> Grün
        if gmd_name in st.session_state.solved_gemeinden:
            return {'fillColor': '#2ecc71', 'color': 'black', 'weight': 1, 'fillOpacity': 0.7}
        # Falls aktuell gesucht im Schreib-Modus -> Gelb
        elif gmd_name == highlight_target:
            return {'fillColor': '#f1c40f', 'color': 'black', 'weight': 2, 'fillOpacity': 0.8}
        # Standard
        else:
            return {'fillColor': '#3178c6', 'color': 'black', 'weight': 0.5, 'fillOpacity': 0.2}

    # Karte erstellen
    bounds = gdf.total_bounds
    m = folium.Map(
        location=[(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2],
        zoom_start=10, tiles="CartoDB positron", scrollWheelZoom=False
    )
    m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

    folium.GeoJson(
        gdf,
        style_function=get_style,
        highlight_function=lambda x: {'weight': 3, 'color': 'orange'} if modus == "Gemeinde anklicken" else None
    ).add_to(m)

    # Karte anzeigen
    output = st_folium(m, width=800, height=550, key="quiz_map")

    # --- KLICK-LOGIK (Nur im Klick-Modus) ---
    if modus == "Gemeinde anklicken" and output['last_active_drawing']:
        clicked_name = output['last_active_drawing']['properties'][name_col]
        if clicked_name == st.session_state.target:
            st.success(f"Richtig! Das ist {clicked_name}!")
            if clicked_name not in st.session_state.solved_gemeinden:
                st.session_state.solved_gemeinden.append(clicked_name)
                st.session_state.score += 1
            st.session_state.target = random.choice(gdf[~gdf[name_col].isin(st.session_state.solved_gemeinden)][name_col].tolist())
            st.button("Nächste Gemeinde")
        else:
            st.error(f"Falsch! Das war {clicked_name}.")

except Exception as e:
    st.error("Fehler beim Laden der App.")
    st.write(e)
