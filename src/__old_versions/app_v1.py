import streamlit as st
import sqlite3
import os
import datetime
import json
import plotly.express as px
import pandas as pd

# --- Project and Data Configuration ---
PROJECT_NAME = "Astro Voyager"
DB_NAME = "observations.db"
UPLOAD_FOLDER = "uploads"
CELESTIAL_DATA_FILE = "celestial_data.json"

# Check and create the uploads folder
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Load celestial data from JSON
try:
    with open(CELESTIAL_DATA_FILE, 'r', encoding='utf-8') as f:
        CELESTIAL_DATA = json.load(f)
except FileNotFoundError:
    st.error(f"Error: The '{CELESTIAL_DATA_FILE}' file was not found. Please create it with the provided JSON data.")
    st.stop()

def init_db():
    """Initializes the SQLite database and creates the observations table."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            celestial_id TEXT,
            celestial_name_kr TEXT,
            catalog TEXT,
            magnitude REAL,
            type TEXT,
            constellation TEXT,
            notes TEXT,
            image_path TEXT,
            observation_date TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# --- Streamlit UI ---
st.set_page_config(page_title=PROJECT_NAME, layout="wide")
st.title(f"🌌 {PROJECT_NAME}")
st.markdown("나만의 우주 항해 일지를 기록하고 탐험하세요.")

# Database initialization
init_db()

# --- Search and Auto-fill Sidebar Form ---
st.sidebar.header("새로운 관측 기록 추가")

# The name search input
object_search_input = st.sidebar.text_input("천체 이름을 입력하세요 (예: 안드로메다 은하)")
found_object = None

# Search the JSON data for a matching object
if object_search_input:
    for obj in CELESTIAL_DATA:
        if obj.get('name_kr') == object_search_input or obj.get('name_en') == object_search_input:
            found_object = obj
            break

# Store the found object in session state to persist form data
if 'found_object' not in st.session_state:
    st.session_state.found_object = None

st.session_state.found_object = found_object

# Create the form with pre-filled data if an object was found
with st.sidebar.form("new_observation_form"):
    celestial_id = st.text_input("천체 ID", value=st.session_state.found_object['id'] if st.session_state.found_object else "", disabled=True)
    celestial_name_kr = st.text_input("한글 이름", value=st.session_state.found_object['name_kr'] if st.session_state.found_object else "", disabled=True)
    celestial_name_en = st.text_input("영문 이름", value=st.session_state.found_object['name_en'] if st.session_state.found_object else "", disabled=True)
    catalog = st.text_input("목록", value=st.session_state.found_object['catalog'] if st.session_state.found_object else "", disabled=True)
    magnitude = st.text_input("등급", value=str(st.session_state.found_object['magnitude']) if st.session_state.found_object and 'magnitude' in st.session_state.found_object else "", disabled=True)
    celestial_type = st.text_input("유형", value=st.session_state.found_object['type'] if st.session_state.found_object and 'type' in st.session_state.found_object else "", disabled=True)
    constellation = st.text_input("별자리", value=st.session_state.found_object['constellation'] if st.session_state.found_object and 'constellation' in st.session_state.found_object else "", disabled=True)
    
    notes = st.text_area("관측 느낌 및 메모", placeholder="오늘 밤 하늘이 맑아 안드로메다 은하를 쌍안경으로 관측했어요.")
    uploaded_file = st.file_uploader("사진 또는 스케치 업로드", type=["png", "jpg", "jpeg", "svg"])
    submitted = st.form_submit_button("기록 저장")

    if submitted:
        if st.session_state.found_object:
            image_path = None
            if uploaded_file is not None:
                filename = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_file.name}"
                image_path = os.path.join(UPLOAD_FOLDER, filename)
                with open(image_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute(
                "INSERT INTO observations (celestial_id, celestial_name_kr, catalog, magnitude, type, constellation, notes, image_path, observation_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    st.session_state.found_object.get('id'),
                    st.session_state.found_object.get('name_kr'),
                    st.session_state.found_object.get('catalog'),
                    st.session_state.found_object.get('magnitude'),
                    st.session_state.found_object.get('type'),
                    st.session_state.found_object.get('constellation'),
                    notes,
                    image_path,
                    datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
            )
            conn.commit()
            conn.close()
            st.sidebar.success("✅ 관측 기록이 성공적으로 저장되었습니다!")
            st.session_state.found_object = None # Reset the state after saving
            st.rerun()
        else:
            st.sidebar.error("❌ 유효한 천체 이름을 먼저 검색하세요.")

# --- 3D Visualization of Observed Objects (One-way) ---
st.header("나의 관측 은하 지도")

# Function to parse RA and Dec from strings to degrees
def parse_ra_dec(ra_str, dec_str):
    """Converts 'HH:MM:SS' and '+DD:MM:SS' strings to degrees."""
    from astropy.coordinates import SkyCoord
    import astropy.units as u
    try:
        coord = SkyCoord(ra=ra_str, dec=dec_str, unit=(u.hourangle, u.deg))
        return coord.ra.deg, coord.dec.deg
    except:
        return None, None

# Fetch all observations from the DB to visualize
conn = sqlite3.connect(DB_NAME)
c = conn.cursor()
c.execute("SELECT celestial_name_kr, notes, celestial_id, catalog FROM observations")
observed_data = c.fetchall()
conn.close()

# Prepare data for visualization
viz_data = []
for obs in observed_data:
    name_kr, notes, id, catalog = obs
    # Find RA and Dec from the JSON data for rendering
    for obj in CELESTIAL_DATA:
        if obj.get('id') == id:
            if 'ra' in obj and 'dec' in obj and obj['ra'] and obj['dec']:
                ra, dec = parse_ra_dec(obj['ra'], obj['dec'])
                if ra is not None and dec is not None:
                    viz_data.append({
                        "name": name_kr, 
                        "ra": ra, 
                        "dec": dec, 
                        "notes": notes, 
                        "id": id
                    })
            break

if viz_data:
    df = pd.DataFrame(viz_data)
    fig = px.scatter_3d(df, 
                        x='ra', 
                        y='dec', 
                        z=[0]*len(df),
                        text='name',
                        hover_name='name',
                        color='name',
                        hover_data={'ra': True, 'dec': True, 'notes': True})
    
    fig.update_traces(marker=dict(size=5, line=dict(width=2, color='DarkSlateGrey')))
    fig.update_layout(title="나의 관측 은하 지도")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("지도에 표시할 관측 기록이 없습니다.")

# --- Display Observation Log ---
st.header("나의 관측 일지")
conn = sqlite3.connect(DB_NAME)
c = conn.cursor()
c.execute("SELECT * FROM observations ORDER BY observation_date DESC")
observations = c.fetchall()
conn.close()

if not observations:
    st.info("아직 관측 기록이 없습니다. 먼저 천체를 검색하고 기록을 남겨보세요.")
else:
    for obs in observations:
        (
            obs_id, 
            celestial_id, 
            celestial_name_kr, 
            catalog, 
            magnitude, 
            celestial_type, 
            constellation, 
            notes, 
            image_path, 
            observation_date
        ) = obs
        with st.expander(f"**{celestial_name_kr}** - {observation_date}"):
            st.write(f"**ID:** {celestial_id}")
            st.write(f"**목록:** {catalog}")
            st.write(f"**등급:** {magnitude}")
            st.write(f"**유형:** {celestial_type}")
            st.write(f"**별자리:** {constellation}")
            st.write(f"**느낌 및 메모:** {notes}")
            if image_path:
                try:
                    st.image(image_path, caption=f"{celestial_name_kr} 이미지")
                except FileNotFoundError:
                    st.warning("경로에 이미지가 존재하지 않습니다.")