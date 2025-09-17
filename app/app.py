import streamlit as st
import sqlite3
import os
import datetime
import json
import pandas as pd
import plotly.express as px
from astropy.coordinates import SkyCoord
import astropy.units as u
from lang import translations

# --- Project and Data Configuration ---
PROJECT_NAME = "Astro Notebook 2025"
DB_NAME = "observations.db"
UPLOAD_FOLDER = "uploads"
CELESTIAL_DATA_FILE = "data/celestial_data.json"

# Initialize session state variables
if 'editing' not in st.session_state:
    st.session_state.editing = None
if 'found_object' not in st.session_state:
    st.session_state.found_object = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = 0
if 'selected_date' not in st.session_state:
    st.session_state.selected_date = None
if 'language' not in st.session_state:
    st.session_state.language = 'en'

# Get the translation dictionary for the selected language
lang = translations[st.session_state.language]

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
            celestial_name_en TEXT,
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
    """Deletes an observation record with the specified ID from the database."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT image_path FROM observations WHERE id=?", (record_id,))
    image_path = c.fetchone()[0]
    
    c.execute("DELETE FROM observations WHERE id=?", (record_id,))
    conn.commit()
    conn.close()
    
    if image_path and os.path.exists(image_path):
        os.remove(image_path)
    
    st.success(lang["success_delete"])
    st.session_state.editing = None
    st.rerun()

def update_record(record_id, new_notes, new_image_file):
    """Updates an observation record with the specified ID."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    new_image_path = st.session_state.editing['image_path']
    if new_image_file:
        if new_image_path and os.path.exists(new_image_path):
            os.remove(new_image_path)
        
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
    st.success(lang["success_update"])
    st.session_state.editing = None
    st.rerun()

def set_edit_mode(record_data):
    """Switches to edit mode and stores the record data in session state."""
    st.session_state.editing = record_data

def set_selected_date():
    """Saves the date from the calendar widget to the session state."""
    st.session_state.selected_date = st.session_state.date_picker
    st.session_state.current_page = 0
    st.rerun()

def set_today_date():
    """Sets the selected date to today's date and re-runs."""
    st.session_state.selected_date = datetime.date.today()
    st.session_state.current_page = 0
    st.rerun()

# --- Streamlit UI ---
st.set_page_config(page_title=PROJECT_NAME, layout="wide")
st.title(f"🌌 {lang['project_name']}")
st.markdown(lang['app_description'])

init_db()

# --- Language selector in sidebar ---
with st.sidebar:
    st.selectbox(
        label=lang["language_selector"],
        options=['en', 'ko'],
        index=['en', 'ko'].index(st.session_state.language),
        key='language_selector',
        on_change=lambda: st.session_state.update(language=st.session_state.language_selector)
    )
    st.markdown("---")

# --- Tab Configuration ---
tab1, tab2 = st.tabs([lang['tab_log'], lang['tab_data']])

# ======================================================================================================
#                                          Observation Log Tab
# ======================================================================================================
with tab1:
    # --- Add New Observation Section (Sidebar) ---
    st.sidebar.header(lang['sidebar_header'])

    # Display current date and time
    now = datetime.datetime.now()
    st.sidebar.markdown(f"**{lang['current_time']}:** {now.strftime('%Y-%m-%d %H:%M:%S')}")

    object_search_input = st.sidebar.text_input(lang['search_label'], placeholder=lang['search_placeholder'])
    found_object = None

    # --- UPDATED SEARCH LOGIC ---
    if object_search_input:
        search_query = object_search_input.lower().replace(" ", "")
        
        # 1. Exact match search across all relevant fields
        for obj in CELESTIAL_DATA:
            obj_id = obj.get('id', '').lower().replace(" ", "")
            obj_name_en = obj.get('name_en', '').lower().replace(" ", "")
            try:
                obj_name_kr = obj.get('name_kr', '').lower().replace(" ", "")
            except:
                obj_name_kr = ''
                
            # Check aliases
            aliases_en = [a.lower().replace(" ", "") for a in obj.get('aliases_en', []) if a]
            aliases_kr = [a.lower().replace(" ", "") for a in obj.get('aliases_kr', []) if a]
            
            if obj_id == search_query or \
               obj_name_en == search_query or \
               obj_name_kr == search_query or \
               search_query in aliases_en or \
               search_query in aliases_kr:
                found_object = obj
                break
        
        # 2. If no exact match, perform a more flexible "starts with" search
        if not found_object:
            for obj in CELESTIAL_DATA:
                obj_id = obj.get('id', '').lower().replace(" ", "")
                obj_name_en = obj.get('name_en', '').lower().replace(" ", "")
                try:
                    obj_name_kr = obj.get('name_kr', '').lower().replace(" ", "")
                except:
                    obj_name_kr = ''
                    
                aliases_en = [a.lower().replace(" ", "") for a in obj.get('aliases_en', []) if a]
                aliases_kr = [a.lower().replace(" ", "") for a in obj.get('aliases_kr', []) if a]

                if obj_id.startswith(search_query) or \
                   obj_name_en.startswith(search_query) or \
                   obj_name_kr.startswith(search_query) or \
                   any(alias.startswith(search_query) for alias in aliases_en) or \
                   any(alias.startswith(search_query) for alias in aliases_kr):
                    found_object = obj
                    break

    st.session_state.found_object = found_object

    with st.sidebar.form("new_observation_form"):
        celestial_id = st.text_input(lang['celestial_id'], value=st.session_state.found_object['id'] if st.session_state.found_object else "", disabled=True)
        celestial_name_en = st.text_input(lang['celestial_name_en'], value=st.session_state.found_object['name_en'] if st.session_state.found_object else "", disabled=True)
        celestial_name_kr = st.text_input(lang['celestial_name_kr'], value=st.session_state.found_object['name_kr'] if st.session_state.found_object else "", disabled=True)
        ra = st.text_input(lang['ra_label'], value=st.session_state.found_object['ra'] if st.session_state.found_object and 'ra' in st.session_state.found_object else "", disabled=True)
        dec = st.text_input(lang['dec_label'], value=st.session_state.found_object['dec'] if st.session_state.found_object and 'dec' in st.session_state.found_object else "", disabled=True)
        magnitude = st.text_input(lang['magnitude'], value=st.session_state.found_object['magnitude'] if st.session_state.found_object and 'magnitude' in st.session_state.found_object else "", disabled=True)
        notes = st.text_area(lang['notes_label'], placeholder=lang['notes_placeholder'])
        uploaded_file = st.file_uploader(lang['upload_file'], type=["png", "jpg", "jpeg", "svg"])
        submitted = st.form_submit_button(lang['save_record'])

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
                    "INSERT INTO observations (celestial_id, celestial_name_en, celestial_name_kr, catalog, ra, dec, magnitude, type, constellation, notes, image_path, observation_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        st.session_state.found_object.get('id'), 
                        st.session_state.found_object.get('name_en'), 
                        st.session_state.found_object.get('name_kr'), 
                        st.session_state.found_object.get('catalog'),
                        st.session_state.found_object.get('ra'), 
                        st.session_state.found_object.get('dec'), 
                        st.session_state.found_object.get('magnitude'),
                        st.session_state.found_object.get('type'), 
                        st.session_state.found_object.get('constellation'),
                        notes, image_path, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    )
                )
                conn.commit()
                conn.close()
                st.sidebar.success(lang['success_save'])
                st.session_state.found_object = None
                st.rerun()
            else:
                st.sidebar.error(lang['error_search'])

    # --- Observation Log List Section ---
    st.header(lang['log_header'])
    col1, col2 = st.columns([0.7, 0.3])
    with col1:
        st.date_input(lang['select_date'], key="date_picker", on_change=set_selected_date)
    with col2:
        st.markdown(" ") # Spacer
        st.button(lang['today'], on_click=set_today_date)

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    if st.session_state.selected_date:
        query = "SELECT * FROM observations WHERE observation_date LIKE ? ORDER BY observation_date DESC"
        c.execute(query, (f"{st.session_state.selected_date.strftime('%Y-%m-%d')}%",))
    else:
        query = "SELECT * FROM observations ORDER BY observation_date DESC"
        c.execute(query)

    all_observations = c.fetchall()
    conn.close()

    ITEMS_PER_PAGE = 10
    total_records = len(all_observations)
    total_pages = (total_records + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    if not st.session_state.selected_date and total_records > ITEMS_PER_PAGE:
        start_idx = st.session_state.current_page * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        paginated_observations = all_observations[start_idx:end_idx]

        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.session_state.current_page > 0:
                if st.button(lang['previous']):
                    st.session_state.current_page -= 1
                    st.rerun()
        with col2:
            st.write(f"{lang['page']} {st.session_state.current_page + 1}/{total_pages}")
        with col3:
            if st.session_state.current_page < total_pages - 1:
                if st.button(lang['next']):
                    st.session_state.current_page += 1
                    st.rerun()
        st.markdown("---")
    else:
        paginated_observations = all_observations

    if not paginated_observations:
        st.info(lang['no_records'])
    else:
        for obs in paginated_observations:
            (
                obs_id, celestial_id, celestial_name_en, celestial_name_kr, catalog,
                ra, dec, magnitude, celestial_type, constellation,
                notes, image_path, observation_date
            ) = obs

            if st.session_state.language == 'en':
                celestial_name = celestial_name_en
            else:
                celestial_name = celestial_name_kr
                
            if st.session_state.editing and st.session_state.editing['id'] == obs_id:
                with st.expander(f"**{celestial_name}** - {observation_date}", expanded=True):
                    st.markdown(f"### {lang['editing_record']}")
                    st.markdown(f"**{lang['celestial_id']}:** {celestial_id}, **{lang['ra_label']}:** `{ra}`, **{lang['dec_label']}:** `{dec}`")
                    st.markdown(f"**Catalog:** {catalog}, **Magnitude:** {magnitude}, **Type:** {celestial_type}, **Constellation:** {constellation}")

                    new_notes = st.text_area(lang['new_notes'], value=notes)
                    if image_path:
                        st.image(image_path, caption=lang['image_caption'], width=200)
                    new_image_file = st.file_uploader(lang['new_image'], type=["png", "jpg", "jpeg", "svg"], key=f"edit_file_{obs_id}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(lang['save_changes'], key=f"edit_complete_{obs_id}"):
                            update_record(obs_id, new_notes, new_image_file)
                    with col2:
                        if st.button(lang['cancel'], key=f"edit_cancel_{obs_id}"):
                            st.session_state.editing = None
                            st.rerun()
            else:
                with st.expander(f"**{celestial_name}** - {observation_date}"):
                    st.write(f"**{lang['celestial_id']}:** {celestial_id}, **{lang['ra_label']}:** `{ra}`, **{lang['dec_label']}:** `{dec}`")
                    st.write(f"**Catalog:** {catalog}, **Magnitude:** {magnitude}")
                    st.write(f"**Type:** {celestial_type}, **Constellation:** {constellation}")
                    st.write(f"**{lang['notes_label']}:** {notes}")
                    if image_path:
                        try:
                            st.image(image_path, caption=f"{celestial_name} Image")
                        except FileNotFoundError:
                            st.warning(lang['file_not_found'])
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(lang['delete'], key=f"delete_{obs_id}"):
                            delete_record(obs_id)
                    with col2:
                        if st.button(lang['edit'], key=f"edit_{obs_id}"):
                            record_data = {
                                "id": obs_id,
                                "celestial_name_en": celestial_name_en,
                                "celestial_name_kr": celestial_name_kr,
                                "notes": notes,
                                "image_path": image_path
                            }
                            set_edit_mode(record_data)
                            st.rerun()

# ======================================================================================================
#                                    Data Management & Visualization Tab
# ======================================================================================================
with tab2:
    st.header(lang['export_data_header'])
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM observations ORDER BY observation_date DESC")
    db_rows = c.fetchall()
    conn.close()
    
    column_names = [description[0] for description in c.description]
    df = pd.DataFrame(db_rows, columns=column_names)

    json_data = df.to_json(orient='records', force_ascii=False)
    st.download_button(
        label=lang['export_json'],
        data=json_data,
        file_name="astro_notebook_observations.json",
        mime="application/json"
    )

    csv_data = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label=lang['export_csv'],
        data=csv_data,
        file_name="astro_notebook_observations.csv",
        mime="text/csv"
    )

    html_data = df.to_html().encode('utf-8')
    st.download_button(
        label=lang['export_html'],
        data=html_data,
        file_name="astro_notebook_observations.html",
        mime="text/html"
    )

    with open(DB_NAME, "rb") as f:
        db_file_bytes = f.read()
    st.download_button(
        label=lang['export_db'],
        data=db_file_bytes,
        file_name=DB_NAME,
        mime="application/octet-stream"
    )
    
    st.markdown("---")
    
    st.header(lang['map_header'])
    
    def parse_ra_dec(ra_str, dec_str):
        try:
            if ra_str and dec_str:
                coord = SkyCoord(ra=ra_str, dec=dec_str, unit=(u.hourangle, u.deg))
                return coord.ra.deg, coord.dec.deg
        except:
            return None, None
        return None, None

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT celestial_name_en, celestial_name_kr, notes, celestial_id, ra, dec FROM observations")
    all_observations = c.fetchall()
    conn.close()

    viz_data = []
    for obs in all_observations:
        name_en, name_kr, notes, id, ra, dec = obs
        parsed_ra, parsed_dec = parse_ra_dec(ra, dec)
        if parsed_ra is not None and parsed_dec is not None:
            viz_data.append({
                "name": name_en,
                "name_kr": name_kr, 
                "ra": parsed_ra, 
                "dec": parsed_dec, 
                "notes": notes, 
                "id": id
            })
    
    if viz_data:
        df_viz = pd.DataFrame(viz_data)
        
        counts = df_viz['name'].value_counts().reset_index()
        counts.columns = ['name', 'count']
        
        df_viz = df_viz.merge(counts, on='name')
        
        fig = px.scatter_3d(df_viz, 
                            x='ra', 
                            y='dec', 
                            z=[0]*len(df_viz), 
                            text='name',
                            hover_name='name',
                            color='count', 
                            size='count',  
                            hover_data={'ra': True, 'dec': True, 'notes': True, 'count': True})
        
        fig.update_traces(marker=dict(line=dict(width=2, color='DarkSlateGrey')))
        fig.update_layout(title=lang['map_title'], scene_camera=dict(eye=dict(x=1.2, y=1.2, z=0.6)))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(lang['no_map_data'])