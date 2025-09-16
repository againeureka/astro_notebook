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

if 'editing' not in st.session_state:
    st.session_state.editing = None
if 'found_object' not in st.session_state:
    st.session_state.found_object = None

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
            ra TEXT,
            dec TEXT,
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

def delete_record(record_id):
    """지정된 ID의 관측 기록을 데이터베이스에서 삭제합니다."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT image_path FROM observations WHERE id=?", (record_id,))
    image_path = c.fetchone()[0]
    
    c.execute("DELETE FROM observations WHERE id=?", (record_id,))
    conn.commit()
    conn.close()
    
    if image_path and os.path.exists(image_path):
        os.remove(image_path)
    
    st.success("✅ 기록이 성공적으로 삭제되었습니다.")
    st.session_state.editing = None
    st.rerun()

def update_record(record_id, new_notes, new_image_file):
    """지정된 ID의 관측 기록을 업데이트합니다."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    new_image_path = st.session_state.editing['image_path']
    if new_image_file:
        # 기존 파일 삭제
        if new_image_path and os.path.exists(new_image_path):
            os.remove(new_image_path)
        
        # 새 파일 저장
        filename = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{new_image_file.name}"
        new_image_path = os.path.join(UPLOAD_FOLDER, filename)
        with open(new_image_path, "wb") as f:
            f.write(new_image_file.getbuffer())

    c.execute(
        "UPDATE observations SET notes=?, image_path=? WHERE id=?",
        (new_notes, new_image_path, record_id)
    )
    conn.commit()
    conn.close()
    st.success("✅ 기록이 성공적으로 업데이트되었습니다.")
    st.session_state.editing = None
    st.rerun()

def set_edit_mode(record_data):
    """편집 모드로 전환하고, 편집할 기록 데이터를 session_state에 저장합니다."""
    st.session_state.editing = record_data
    
# --- Streamlit UI ---
st.set_page_config(page_title=PROJECT_NAME, layout="wide")
st.title(f"🌌 {PROJECT_NAME}")
st.markdown("나만의 우주 항해 일지를 기록하고 탐험하세요.")

init_db()

# 사이드바에 기록 폼 생성
st.sidebar.header("새로운 관측 기록 추가")

object_search_input = st.sidebar.text_input("천체 이름을 입력하세요 (예: 안드로메다 은하)")
found_object = None

if object_search_input:
    for obj in CELESTIAL_DATA:
        if obj.get('name_kr') == object_search_input or obj.get('name_en') == object_search_input:
            found_object = obj
            break

st.session_state.found_object = found_object

with st.sidebar.form("new_observation_form"):
    celestial_id = st.text_input("천체 ID", value=st.session_state.found_object['id'] if st.session_state.found_object else "", disabled=True)
    celestial_name_kr = st.text_input("한글 이름", value=st.session_state.found_object['name_kr'] if st.session_state.found_object else "", disabled=True)
    
    # 추가된 정보: 적경, 적위
    ra = st.text_input("적경 (RA)", value=st.session_state.found_object['ra'] if st.session_state.found_object and 'ra' in st.session_state.found_object else "", disabled=True)
    dec = st.text_input("적위 (Dec)", value=st.session_state.found_object['dec'] if st.session_state.found_object and 'dec' in st.session_state.found_object else "", disabled=True)

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
                "INSERT INTO observations (celestial_id, celestial_name_kr, catalog, ra, dec, magnitude, type, constellation, notes, image_path, observation_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    st.session_state.found_object.get('id'),
                    st.session_state.found_object.get('name_kr'),
                    st.session_state.found_object.get('catalog'),
                    st.session_state.found_object.get('ra'),
                    st.session_state.found_object.get('dec'),
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
            st.session_state.found_object = None
            st.rerun()
        else:
            st.sidebar.error("❌ 유효한 천체 이름을 먼저 검색하세요.")

# --- 3D Visualization of Observed Objects (One-way) ---
st.header("나의 관측 은하 지도")

def parse_ra_dec(ra_str, dec_str):
    from astropy.coordinates import SkyCoord
    import astropy.units as u
    try:
        if ra_str and dec_str:
            coord = SkyCoord(ra=ra_str, dec=dec_str, unit=(u.hourangle, u.deg))
            return coord.ra.deg, coord.dec.deg
    except:
        return None, None

    return None, None

conn = sqlite3.connect(DB_NAME)
c = conn.cursor()
c.execute("SELECT celestial_name_kr, notes, celestial_id, ra, dec FROM observations")
observed_data = c.fetchall()
conn.close()

viz_data = []
for obs in observed_data:
    name_kr, notes, id, ra, dec = obs
    parsed_ra, parsed_dec = parse_ra_dec(ra, dec)
    if parsed_ra is not None and parsed_dec is not None:
        viz_data.append({
            "name": name_kr, 
            "ra": parsed_ra, 
            "dec": parsed_dec, 
            "notes": notes, 
            "id": id
        })

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

# --- Display Observation Log and Interaction ---
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
            ra,
            dec,
            magnitude, 
            celestial_type, 
            constellation, 
            notes, 
            image_path, 
            observation_date
        ) = obs

        if st.session_state.editing and st.session_state.editing['id'] == obs_id:
            with st.expander(f"**{celestial_name_kr}** - {observation_date}", expanded=True):
                st.markdown("### 기록 편집 중")
                st.markdown(f"**천체 ID:** {celestial_id}")
                st.markdown(f"**적경(RA):** `{ra}`")
                st.markdown(f"**적위(Dec):** `{dec}`")
                st.markdown(f"**목록:** {catalog}, **등급:** {magnitude}")
                st.markdown(f"**유형:** {celestial_type}, **별자리:** {constellation}")

                new_notes = st.text_area("새로운 메모를 입력하세요", value=notes)

                # 사진 변경 UI
                if image_path:
                    st.image(image_path, caption="현재 사진", width=200)
                new_image_file = st.file_uploader("새로운 사진 업로드", type=["png", "jpg", "jpeg", "svg"], key=f"edit_file_{obs_id}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("수정 완료", key=f"edit_complete_{obs_id}"):
                        update_record(obs_id, new_notes, new_image_file)
                with col2:
                    if st.button("취소", key=f"edit_cancel_{obs_id}"):
                        st.session_state.editing = None
                        st.rerun()

        else:
            # 일반 보기 모드 UI
            with st.expander(f"**{celestial_name_kr}** - {observation_date}"):
                st.write(f"**ID:** {celestial_id}")
                st.write(f"**적경(RA):** `{ra}`")
                st.write(f"**적위(Dec):** `{dec}`")
                st.write(f"**목록:** {catalog}, **등급:** {magnitude}")
                st.write(f"**유형:** {celestial_type}, **별자리:** {constellation}")
                st.write(f"**느낌 및 메모:** {notes}")
                if image_path:
                    try:
                        st.image(image_path, caption=f"{celestial_name_kr} 이미지")
                    except FileNotFoundError:
                        st.warning("경로에 이미지가 존재하지 않습니다.")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("삭제", key=f"delete_{obs_id}"):
                        delete_record(obs_id)
                with col2:
                    if st.button("편집", key=f"edit_{obs_id}"):
                        record_data = {
                            "id": obs_id,
                            "celestial_name_kr": celestial_name_kr,
                            "notes": notes,
                            "image_path": image_path
                        }
                        set_edit_mode(record_data)
                        st.rerun()