"""
VERA - Verification Engine for Results & Accountability
Streamlit Web Application for H-EDU
"""

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import re
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# =============================================================================
# Configuration
# =============================================================================

st.set_page_config(
    page_title="VERA | H-EDU",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# H-EDU Brand Colors
NAVY = "#1B2A4A"
GOLD = "#B8902A"
CREAM = "#F8F4EE"
RED = "#8B2A2A"
GREEN = "#1A5C38"

# Custom CSS for H-EDU branding
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Lora:wght@400;600;700&family=Source+Sans+3:wght@400;600&display=swap');

    /* Main app background */
    .stApp {{
        background-color: {CREAM};
    }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background-color: {NAVY};
    }}
    section[data-testid="stSidebar"] .stMarkdown {{
        color: white;
    }}
    section[data-testid="stSidebar"] label {{
        color: white !important;
    }}
    section[data-testid="stSidebar"] .stSelectbox label {{
        color: white !important;
    }}
    section[data-testid="stSidebar"] .stRadio > div {{
        display: flex;
        flex-direction: column;
        gap: 8px;
    }}
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stRadio label span,
    section[data-testid="stSidebar"] .stRadio label p,
    section[data-testid="stSidebar"] .stRadio label div,
    section[data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"],
    section[data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p {{
        color: white !important;
        font-size: 1rem;
        position: relative;
        z-index: 1;
    }}
    section[data-testid="stSidebar"] .stRadio label {{
        padding: 8px 12px;
        border-radius: 6px;
        cursor: pointer;
        transition: background-color 0.2s;
    }}
    section[data-testid="stSidebar"] .stRadio label:hover {{
        background-color: rgba(255,255,255,0.1);
    }}
    section[data-testid="stSidebar"] .stRadio input[type="radio"]:checked + div,
    section[data-testid="stSidebar"] .stRadio input[type="radio"]:checked + div p,
    section[data-testid="stSidebar"] .stRadio input[type="radio"]:checked ~ div,
    section[data-testid="stSidebar"] .stRadio input[type="radio"]:checked ~ div p {{
        color: {GOLD} !important;
        font-weight: 600;
    }}

    /* Headers */
    h1, h2, h3 {{
        font-family: 'Lora', serif;
        color: {NAVY};
    }}
    h1 {{
        border-bottom: 3px solid {GOLD};
        padding-bottom: 10px;
    }}

    /* Body text */
    p, li, span {{
        font-family: 'Source Sans 3', sans-serif;
    }}

    /* Stat cards */
    .stat-card {{
        background: white;
        border-left: 4px solid {GOLD};
        padding: 20px;
        border-radius: 4px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 16px;
    }}
    .stat-card .number {{
        font-size: 2.5rem;
        font-weight: 700;
        color: {GOLD};
        font-family: 'Lora', serif;
    }}
    .stat-card .label {{
        font-size: 0.9rem;
        color: #666;
        margin-top: 4px;
    }}

    /* Type 4 flag highlight */
    .type4-flag {{
        background-color: {RED};
        color: white;
        padding: 4px 12px;
        border-radius: 4px;
        font-weight: 600;
    }}

    /* Section headers */
    .section-header {{
        background: {NAVY};
        color: white;
        padding: 12px 20px;
        margin: 24px 0 16px 0;
        font-family: 'Lora', serif;
        font-size: 1.1rem;
    }}

    /* Navigation header */
    .nav-header {{
        background: {NAVY};
        padding: 16px 24px;
        margin: -1rem -1rem 2rem -1rem;
        display: flex;
        align-items: center;
        gap: 40px;
    }}
    .nav-logo {{
        color: {GOLD};
        font-size: 1.8rem;
        font-weight: 700;
        font-family: 'Lora', serif;
    }}
    .nav-logo span {{
        color: white;
    }}

    /* Hide Streamlit branding */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# Authentication System
# =============================================================================

# Password from environment variable (fallback for local dev)
VERA_PASSWORD = os.environ.get("VERA_PASSWORD", "forever vera")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "brian@h-edu.solutions")

# School board email domain patterns
SCHOOL_DOMAIN_PATTERNS = [
    r'.*\.k12\.[a-z]{2}\.us$',      # *.k12.CA.us, etc.
    r'.*\.edu$',                     # *.edu
    r'.*school.*\.[a-z]+$',          # *school*.com, etc.
    r'.*district.*\.[a-z]+$',        # *district*.org, etc.
    r'.*unified.*\.[a-z]+$',         # *unified*.org, etc.
    r'.*usd\.[a-z]+$',               # *usd.org, etc.
    r'.*isd\.[a-z]+$',               # *isd.org (independent school district)
    r'.*coe\.[a-z]+$',               # county office of education
    r'.*schools\.[a-z]+$',           # *schools.org
]

def is_school_email(email):
    """Check if email domain matches school board patterns."""
    if not email or '@' not in email:
        return False
    domain = email.lower().split('@')[1]
    for pattern in SCHOOL_DOMAIN_PATTERNS:
        if re.match(pattern, domain):
            return True
    return False

def init_auth_db():
    """Create access_requests table if it doesn't exist."""
    db_path = Path(__file__).parent / "vera_demo.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS access_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            organization TEXT,
            requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending'
        )
    """)
    conn.commit()
    conn.close()

def save_access_request(email, phone, organization=""):
    """Save a new access request to the database."""
    db_path = Path(__file__).parent / "vera_demo.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO access_requests (email, phone, organization) VALUES (?, ?, ?)",
        (email, phone, organization)
    )
    conn.commit()
    conn.close()

def send_notification_email(email, phone, organization):
    """Send email notification about new access request."""
    try:
        # Email configuration from environment variables
        smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        smtp_user = os.environ.get("SMTP_USER", "")
        smtp_pass = os.environ.get("SMTP_PASS", "")

        if not smtp_user or not smtp_pass:
            # If no email configured, just log it
            print(f"Access request: {email}, {phone}, {organization}")
            return False

        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = ADMIN_EMAIL
        msg['Subject'] = f"VERA Access Request: {email}"

        body = f"""
New VERA access request:

Email: {email}
Phone: {phone}
Organization: {organization}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

To grant access, share the password with this user.
        """
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def check_authentication():
    """Display login page and check authentication."""

    # Initialize auth database table
    init_auth_db()

    # Check if already authenticated
    if st.session_state.get('authenticated', False):
        return True

    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.image("vera_logo.png", use_container_width=True)
        st.markdown(f"""
            <h2 style="text-align: center; color: {NAVY}; margin-top: 20px;">
                Welcome to VERA
            </h2>
            <p style="text-align: center; color: #666; margin-bottom: 30px;">
                Verification Engine for Results & Accountability
            </p>
        """, unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["🔐 I Have Access", "📝 Request Access"])

        with tab1:
            st.markdown("Enter your password to access VERA.")
            password = st.text_input("Password", type="password", key="login_password")

            if st.button("Sign In", type="primary", use_container_width=True):
                if password.lower().strip() == VERA_PASSWORD.lower():
                    st.session_state['authenticated'] = True
                    st.rerun()
                else:
                    st.error("Incorrect password. Please try again or request access.")

        with tab2:
            st.markdown("Request access to VERA. You must have a school board or educational institution email.")

            with st.form("access_request_form"):
                req_email = st.text_input("Email Address *", placeholder="you@yourdistrict.k12.ca.us")
                req_phone = st.text_input("Phone Number *", placeholder="(555) 123-4567")
                req_org = st.text_input("Organization/District", placeholder="Your School District")

                submitted = st.form_submit_button("Request Access", type="primary", use_container_width=True)

                if submitted:
                    # Validate fields
                    if not req_email or not req_phone:
                        st.error("Please fill in all required fields.")
                    elif not is_school_email(req_email):
                        st.error("Please use an email address from a school board, district, or educational institution (.k12.ca.us, .edu, etc.)")
                    else:
                        # Save request and send notification
                        save_access_request(req_email, req_phone, req_org)
                        send_notification_email(req_email, req_phone, req_org)
                        st.success("✅ Access request submitted! You will receive the password via email once approved.")

        st.markdown(f"""
            <div style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd;">
                <a href="https://h-edu.solutions" style="color: {GOLD}; text-decoration: none;">
                    ← Return to H-EDU.solutions
                </a>
            </div>
        """, unsafe_allow_html=True)

    return False

# Check authentication before showing main app
if not check_authentication():
    st.stop()

# =============================================================================
# Database Connection
# =============================================================================

DB_PATH = Path(__file__).parent / "vera_demo.db"

@st.cache_resource
def get_connection():
    return sqlite3.connect(str(DB_PATH), check_same_thread=False)

def run_query(query, params=None):
    conn = get_connection()
    if params:
        return pd.read_sql_query(query, conn, params=params)
    return pd.read_sql_query(query, conn)

# =============================================================================
# Data Functions
# =============================================================================

@st.cache_data
def get_districts():
    query = """
        SELECT DISTINCT district_name, district_id, county
        FROM caaspp_results
        ORDER BY district_name
    """
    return run_query(query)

@st.cache_data
def get_caaspp_data(district_name, grade=None, subgroup=None):
    query = "SELECT * FROM caaspp_results WHERE district_name = ?"
    params = [district_name]

    if grade:
        query += " AND grade = ?"
        params.append(grade)
    if subgroup:
        query += " AND subgroup = ?"
        params.append(subgroup)

    query += " ORDER BY grade, subgroup"
    return run_query(query, params)

@st.cache_data
def compute_owd(district_name, subgroup=None):
    query = """
        SELECT c.district_name, c.district_id, c.grade, c.subgroup,
               c.ela_claim2_score as writing_score,
               e.speaking_score,
               (e.speaking_score - c.ela_claim2_score) as delta
        FROM caaspp_results c
        LEFT JOIN elpac_results e ON c.district_id = e.district_id
            AND c.grade = e.grade AND c.subgroup = e.subgroup
        WHERE c.district_name = ?
    """
    params = [district_name]

    if subgroup:
        query += " AND c.subgroup = ?"
        params.append(subgroup)

    query += " ORDER BY c.grade"
    return run_query(query, params)

@st.cache_data
def get_all_type4_flags(threshold=8.0):
    query = """
        SELECT c.district_name, c.district_id, c.county, c.grade, c.subgroup,
               c.ela_claim2_score as writing_score,
               e.speaking_score,
               (e.speaking_score - c.ela_claim2_score) as delta
        FROM caaspp_results c
        JOIN elpac_results e ON c.district_id = e.district_id
            AND c.grade = e.grade AND c.subgroup = e.subgroup
        WHERE (e.speaking_score - c.ela_claim2_score) > ?
        ORDER BY delta DESC
    """
    return run_query(query, [threshold])

# =============================================================================
# Sidebar
# =============================================================================

with st.sidebar:
    # VERA Logo
    st.image("vera_logo.png", use_container_width=True)

    # Return to H-EDU link
    st.markdown(f"""
        <div style="text-align: center; margin: 10px 0;">
            <a href="https://h-edu.solutions" target="_blank" style="
                display: inline-block;
                color: {GOLD};
                text-decoration: none;
                font-size: 0.85rem;
                padding: 8px 16px;
                border: 1px solid {GOLD};
                border-radius: 4px;
                transition: all 0.2s;
            ">← Return to H-EDU</a>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Navigation
    st.markdown("""
        <p style="color: rgba(255,255,255,0.7); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">
            Navigate
        </p>
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigate",
        ["📊 District Dashboard", "🔍 Cross-District Scan", "📋 LCAP Report", "📝 Student Record", "📅 Daily Observations", "ℹ️ About VERA"],
        label_visibility="collapsed",
        format_func=lambda x: x
    )

    st.markdown("---")

    # District selector (for relevant pages)
    if page in ["📊 District Dashboard", "📋 LCAP Report"]:
        districts = get_districts()
        selected_district = st.selectbox(
            "Select District",
            districts['district_name'].tolist()
        )

        # Get district data for filters
        district_data = get_caaspp_data(selected_district)

        # Grade filter
        grades = ["All"] + sorted(district_data['grade'].unique().tolist())
        selected_grade = st.selectbox("Grade", grades)

        # Subgroup filter
        subgroups = ["All"] + sorted(district_data['subgroup'].unique().tolist())
        selected_subgroup = st.selectbox("Subgroup", subgroups)

    st.markdown("---")
    st.markdown(f"""
        <p style="color: rgba(255,255,255,0.5); font-size: 0.8rem; text-align: center;">
            VERA v1.0<br>
            <a href="https://h-edu.solutions" style="color: {GOLD};">h-edu.solutions</a>
        </p>
    """, unsafe_allow_html=True)

# =============================================================================
# Page: District Dashboard
# =============================================================================

if page == "📊 District Dashboard":
    st.title(f"District Dashboard: {selected_district}")

    # Get district info
    district_info = districts[districts['district_name'] == selected_district].iloc[0]
    st.markdown(f"**{district_info['county']} County** | District ID: `{district_info['district_id']}`")

    # Compute OWD
    subgroup_filter = None if selected_subgroup == "All" else selected_subgroup
    owd_data = compute_owd(selected_district, subgroup_filter)

    if selected_grade != "All":
        owd_data = owd_data[owd_data['grade'] == int(selected_grade)]

    # Stat cards
    col1, col2, col3, col4 = st.columns(4)

    type4_count = len(owd_data[owd_data['delta'] > 8])
    max_delta = owd_data['delta'].max() if len(owd_data) > 0 else 0
    avg_delta = owd_data['delta'].mean() if len(owd_data) > 0 else 0

    with col1:
        st.markdown(f"""
            <div class="stat-card">
                <div class="number">{len(owd_data)}</div>
                <div class="label">Populations Analyzed</div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
            <div class="stat-card">
                <div class="number" style="color: {RED if type4_count > 0 else GOLD};">{type4_count}</div>
                <div class="label">Type 4 Flags</div>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
            <div class="stat-card">
                <div class="number">{max_delta:+.1f}</div>
                <div class="label">Max Delta</div>
            </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
            <div class="stat-card">
                <div class="number">{avg_delta:+.1f}</div>
                <div class="label">Avg Delta</div>
            </div>
        """, unsafe_allow_html=True)

    # OWD Table
    st.markdown('<div class="section-header">Oral-Written Delta Analysis</div>', unsafe_allow_html=True)

    if len(owd_data) > 0:
        display_df = owd_data[['grade', 'subgroup', 'writing_score', 'speaking_score', 'delta']].copy()
        display_df.columns = ['Grade', 'Subgroup', 'Writing (ELA Claim 2)', 'Speaking (ELPAC)', 'Delta']
        display_df['Delta'] = display_df['Delta'].apply(lambda x: f"{x:+.1f}" if pd.notna(x) else "N/A")

        # Highlight Type 4 rows
        def highlight_type4(row):
            delta_val = float(row['Delta'].replace('+', '')) if row['Delta'] != 'N/A' else 0
            if delta_val > 8:
                return ['background-color: #FADBD8'] * len(row)
            return [''] * len(row)

        st.dataframe(
            display_df.style.apply(highlight_type4, axis=1),
            use_container_width=True,
            hide_index=True
        )

        # Chart
        st.markdown('<div class="section-header">Oral vs. Written Scores by Grade</div>', unsafe_allow_html=True)

        chart_data = owd_data[owd_data['speaking_score'].notna()].copy()
        if len(chart_data) > 0:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name='Writing (ELA Claim 2)',
                x=chart_data['grade'].astype(str) + ' - ' + chart_data['subgroup'],
                y=chart_data['writing_score'],
                marker_color=NAVY
            ))
            fig.add_trace(go.Bar(
                name='Speaking (ELPAC)',
                x=chart_data['grade'].astype(str) + ' - ' + chart_data['subgroup'],
                y=chart_data['speaking_score'],
                marker_color=GOLD
            ))
            fig.update_layout(
                barmode='group',
                xaxis_title='Grade - Subgroup',
                yaxis_title='Score',
                plot_bgcolor='white',
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)

        # Download
        csv = owd_data.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"vera_owd_{selected_district.replace(' ', '_')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No data available for the selected filters.")

# =============================================================================
# Page: Cross-District Scan
# =============================================================================

elif page == "🔍 Cross-District Scan":
    st.title("Cross-District Type 4 Scan")
    st.markdown("Identifies oral-written delta flags across all districts in the database.")

    # Threshold selector
    threshold = st.slider("Delta Threshold", min_value=5.0, max_value=15.0, value=8.0, step=0.5)

    # Get all flags
    flags_df = get_all_type4_flags(threshold)

    # Stats
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
            <div class="stat-card">
                <div class="number" style="color: {RED};">{len(flags_df)}</div>
                <div class="label">Total Flags</div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        districts_flagged = flags_df['district_name'].nunique() if len(flags_df) > 0 else 0
        st.markdown(f"""
            <div class="stat-card">
                <div class="number">{districts_flagged}</div>
                <div class="label">Districts Flagged</div>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        max_delta = flags_df['delta'].max() if len(flags_df) > 0 else 0
        st.markdown(f"""
            <div class="stat-card">
                <div class="number">{max_delta:+.1f}</div>
                <div class="label">Max Delta</div>
            </div>
        """, unsafe_allow_html=True)

    # Flags table
    st.markdown('<div class="section-header">Flagged Populations</div>', unsafe_allow_html=True)

    if len(flags_df) > 0:
        display_df = flags_df[['district_name', 'county', 'grade', 'subgroup', 'writing_score', 'speaking_score', 'delta']].copy()
        display_df.columns = ['District', 'County', 'Grade', 'Subgroup', 'Writing', 'Speaking', 'Delta']
        display_df['Delta'] = display_df['Delta'].apply(lambda x: f"{x:+.1f}")

        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # Chart: Flags by district
        st.markdown('<div class="section-header">Type 4 Flags by District</div>', unsafe_allow_html=True)

        flag_counts = flags_df.groupby('district_name').size().reset_index(name='flags')
        flag_counts = flag_counts.sort_values('flags', ascending=True)

        fig = px.bar(
            flag_counts,
            x='flags',
            y='district_name',
            orientation='h',
            color_discrete_sequence=[RED]
        )
        fig.update_layout(
            xaxis_title='Number of Flags',
            yaxis_title='',
            plot_bgcolor='white',
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)

        # Download
        csv = flags_df.to_csv(index=False)
        st.download_button(
            label="Download All Flags CSV",
            data=csv,
            file_name="vera_type4_flags_all_districts.csv",
            mime="text/csv"
        )
    else:
        st.success(f"No Type 4 flags found at threshold {threshold}")

# =============================================================================
# Page: LCAP Report
# =============================================================================

elif page == "📋 LCAP Report":
    st.title(f"LCAP Match-Rate Report")
    st.markdown(f"**District:** {selected_district}")

    # Get district info
    district_info = districts[districts['district_name'] == selected_district].iloc[0]
    district_id = district_info['district_id']

    # Compute data
    owd_data = compute_owd(selected_district)
    type4_count = len(owd_data[owd_data['delta'] > 8])
    total_populations = len(owd_data)

    # Calculate match rate (simplified)
    match_rate = max(0, 100 - (type4_count * 15))

    # Pull observation data (Document 2)
    db_path = Path(__file__).parent / "vera_demo.db"
    obs_data = None
    init_data = None

    try:
        conn = sqlite3.connect(str(db_path))

        # Get observation aggregates
        obs_df = pd.read_sql_query("""
            SELECT
                COUNT(DISTINCT ssid) as students_observed,
                COUNT(DISTINCT observation_date) as observation_days,
                COUNT(*) as total_observations,
                SUM(present) as total_present,
                SUM(oral_participation) as total_oral,
                SUM(written_output) as total_written,
                SUM(concern_flag) as total_concerns,
                SUM(CASE WHEN elaboration = 'Intervention responding' THEN 1 ELSE 0 END) as intervention_responding,
                SUM(CASE WHEN elaboration = 'Intervention not responding' THEN 1 ELSE 0 END) as intervention_not_responding,
                SUM(CASE WHEN elaboration = 'VERA hypothesis confirmed' THEN 1 ELSE 0 END) as vera_confirmed,
                SUM(CASE WHEN elaboration = 'VERA hypothesis challenged' THEN 1 ELSE 0 END) as vera_challenged
            FROM observations
        """, conn)
        if len(obs_df) > 0:
            obs_data = obs_df.iloc[0].to_dict()

        # Get initialization record summary
        init_df = pd.read_sql_query("""
            SELECT
                COUNT(*) as total_records,
                SUM(CASE WHEN locked_at IS NOT NULL THEN 1 ELSE 0 END) as locked_records,
                SUM(CASE WHEN teacher_response = 'confirmed' THEN 1 ELSE 0 END) as hypothesis_confirmed,
                SUM(CASE WHEN teacher_response = 'challenged' THEN 1 ELSE 0 END) as hypothesis_challenged
            FROM initialization_records
        """, conn)
        if len(init_df) > 0:
            init_data = init_df.iloc[0].to_dict()

        conn.close()
    except Exception:
        pass

    # Gauge chart
    col1, col2 = st.columns([1, 1])

    with col1:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=match_rate,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "LCAP Match Rate", 'font': {'size': 20}},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': GOLD},
                'steps': [
                    {'range': [0, 50], 'color': '#FADBD8'},
                    {'range': [50, 75], 'color': '#FCF3CF'},
                    {'range': [75, 100], 'color': '#D5F5E3'}
                ],
                'threshold': {
                    'line': {'color': RED, 'width': 4},
                    'thickness': 0.75,
                    'value': 70
                }
            }
        ))
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Summary stats
        st.markdown(f"""
            <div class="stat-card">
                <div class="number">{total_populations}</div>
                <div class="label">Grade-Subgroup Combinations Analyzed</div>
            </div>
        """, unsafe_allow_html=True)

        color = RED if type4_count > 2 else (GOLD if type4_count > 0 else GREEN)
        st.markdown(f"""
            <div class="stat-card">
                <div class="number" style="color: {color};">{type4_count}</div>
                <div class="label">Type 4 Gaps Detected (oral > written by 8+ pts)</div>
            </div>
        """, unsafe_allow_html=True)

    # Finding
    st.markdown('<div class="section-header">Finding</div>', unsafe_allow_html=True)

    if match_rate >= 75:
        st.success(f"**MATCH RATE: {match_rate}%** — LCAP interventions appear well-aligned with student needs.")
    elif match_rate >= 50:
        st.warning(f"**MATCH RATE: {match_rate}%** — Some misalignment detected. Review ELD intervention targeting.")
    else:
        st.error(f"**MATCH RATE: {match_rate}%** — Significant misalignment. Immediate review of LCAP spending recommended.")

    # NEW: Document 1 & 2 Status
    st.markdown("---")
    st.markdown('<div class="section-header">Observation System Status</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        init_count = init_data.get('locked_records', 0) if init_data else 0
        st.metric("Student Records Locked", init_count, help="Document 1 - Initialization records signed off")

    with col2:
        obs_students = obs_data.get('students_observed', 0) if obs_data else 0
        st.metric("Students Observed", int(obs_students) if obs_students else 0, help="Document 2 - Daily observations")

    with col3:
        obs_days = obs_data.get('observation_days', 0) if obs_data else 0
        st.metric("Observation Days", int(obs_days) if obs_days else 0)

    with col4:
        concerns = obs_data.get('total_concerns', 0) if obs_data else 0
        st.metric("Concern Flags", int(concerns) if concerns else 0, delta="review" if concerns and concerns > 0 else None, delta_color="inverse")

    # Oral vs Written Pattern
    if obs_data and obs_data.get('total_present') and obs_data['total_present'] > 0:
        oral_rate = (obs_data.get('total_oral', 0) / obs_data['total_present']) * 100
        written_rate = (obs_data.get('total_written', 0) / obs_data['total_present']) * 100

        st.markdown("**Participation Patterns (from daily observations):**")
        pattern_cols = st.columns(2)
        with pattern_cols[0]:
            st.metric("Oral Participation Rate", f"{oral_rate:.0f}%")
        with pattern_cols[1]:
            st.metric("Written Output Rate", f"{written_rate:.0f}%")

        if oral_rate > written_rate + 15:
            st.warning("⚠️ **Pattern Alert:** Oral participation exceeds written output by >15% — confirms Type 4 indicators at classroom level.")

    # Intervention Effectiveness
    if obs_data:
        responding = obs_data.get('intervention_responding', 0) or 0
        not_responding = obs_data.get('intervention_not_responding', 0) or 0
        if responding + not_responding > 0:
            effectiveness = (responding / (responding + not_responding)) * 100
            st.markdown("**Intervention Effectiveness (from teacher elaborations):**")
            st.metric("Interventions Responding", f"{effectiveness:.0f}%", delta="good" if effectiveness >= 50 else "needs review", delta_color="normal" if effectiveness >= 50 else "inverse")

    # Report text
    st.markdown("---")
    st.markdown('<div class="section-header">COE Submission Report</div>', unsafe_allow_html=True)

    # Build enhanced report
    report_text = f"""
======================================================================
LCAP VERIFICATION REPORT - H-EDU/VERA
======================================================================

District: {selected_district}
County: {district_info['county']}
District ID: {district_id}
Report Date: {pd.Timestamp.now().strftime('%Y-%m-%d')}
----------------------------------------------------------------------

SECTION 1: ASSESSMENT-BASED GAP PROFILE
  Total grade-subgroup combinations analyzed: {total_populations}
  Type 4 gaps detected (oral > written by 8+ pts): {type4_count}
  Assessment-based match rate: {match_rate}%

{"ATTENTION REQUIRED:" if type4_count > 0 else ""}
{"  " + str(type4_count) + " grade-subgroup combinations show significant" if type4_count > 0 else ""}
{"  oral-written divergence. Review ELD intervention alignment." if type4_count > 0 else ""}

SECTION 2: STUDENT INITIALIZATION RECORDS (Document 1)
  Total records locked: {init_data.get('locked_records', 0) if init_data else 'N/A'}
  VERA hypothesis confirmed: {init_data.get('hypothesis_confirmed', 0) if init_data else 'N/A'}
  VERA hypothesis challenged: {init_data.get('hypothesis_challenged', 0) if init_data else 'N/A'}
  SB 1288 Section C compliance: {'ACTIVE' if init_data and init_data.get('locked_records') else 'NOT STARTED'}

SECTION 3: CLASSROOM OBSERVATIONS (Document 2)
  Students observed: {int(obs_data.get('students_observed', 0)) if obs_data else 'N/A'}
  Observation days: {int(obs_data.get('observation_days', 0)) if obs_data else 'N/A'}
  Total observations: {int(obs_data.get('total_observations', 0)) if obs_data else 'N/A'}
  Concern flags raised: {int(obs_data.get('total_concerns', 0)) if obs_data else 'N/A'}

SECTION 4: INTERVENTION EFFECTIVENESS
  Interventions responding: {int(obs_data.get('intervention_responding', 0)) if obs_data else 'N/A'}
  Interventions not responding: {int(obs_data.get('intervention_not_responding', 0)) if obs_data else 'N/A'}

NON-EVALUATION GUARANTEE:
  No teacher identity is attached to any result in this report.
  Match-rate data is aggregate only.

----------------------------------------------------------------------
The working group reports once and disbands.
VERA reports continuously.
The working group built the policy. VERA measures whether it works.
----------------------------------------------------------------------
Generated by VERA - H-EDU Verification Engine
    """

    st.code(report_text, language=None)

    st.download_button(
        label="Download Report",
        data=report_text,
        file_name=f"vera_lcap_report_{district_id}.txt",
        mime="text/plain"
    )

# =============================================================================
# Page: About VERA
# =============================================================================

elif page == "ℹ️ About VERA":
    st.title("About VERA")

    st.markdown("""
    ## Verification Engine for Results & Accountability

    VERA is H-EDU's core analytical tool for identifying achievement gaps in California's K-12 education system. It connects Claude to California education assessment data, enabling plain-English queries against CAASPP, ELPAC, and other data sources.

    ### The Type 4 Gap

    H-EDU's differentiator is identifying students who **speak well but write poorly** — the "oral-written delta." This computation runs on:

    - **CAASPP ELA Claim 2** (writing scores)
    - **ELPAC Speaking** scores

    A large positive delta (speaking > writing by 8+ points) flags students who may be:
    - Misclassified in language programs
    - Receiving inappropriate interventions
    - At risk of falling through the cracks

    ### Data Sources

    - **CAASPP** — California Assessment of Student Performance and Progress
    - **ELPAC** — English Language Proficiency Assessments for California

    ### The Five VERA Tools

    1. **list_districts()** — List all districts in the database
    2. **fetch_caaspp_results()** — Get CAASPP data for a district
    3. **compute_oral_written_delta()** — Identify Type 4 gaps
    4. **flag_type4_candidates()** — Statewide scan for flags
    5. **get_lcap_match_summary()** — LCAP verification for COE

    ### Non-Evaluation Guarantee

    No teacher identity is attached to any result in VERA reports. Match-rate data is aggregate only.

    ---

    **Contact:** [brian@h-edu.solutions](mailto:brian@h-edu.solutions)

    **Website:** [h-edu.solutions](https://h-edu.solutions)
    """)

    st.markdown(f"""
        <div style="background: {NAVY}; color: white; padding: 24px; text-align: center; margin-top: 40px; border-radius: 4px;">
            <p style="color: {GOLD}; font-size: 1.2rem; font-weight: 600; margin: 0;">
                VERA: The verification layer California education accountability has been missing.
            </p>
        </div>
    """, unsafe_allow_html=True)

# =============================================================================
# Page: Student Initialization Record (Document 1)
# =============================================================================

elif page == "📝 Student Record":
    st.title("Student Initialization Record")
    st.markdown("*Document 1 — Day-One Student Record*")

    # Initialize database tables if needed
    def init_observation_tables():
        db_path = Path(__file__).parent / "vera_demo.db"
        conn = sqlite3.connect(str(db_path))

        conn.execute("""
            CREATE TABLE IF NOT EXISTS initialization_records (
                record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ssid TEXT NOT NULL,
                teacher_id TEXT NOT NULL,
                district_id TEXT NOT NULL,
                school_id TEXT,
                school_year TEXT NOT NULL,
                vera_hypothesis TEXT,
                teacher_response TEXT,
                teacher_notes TEXT,
                intervention_assigned TEXT,
                section_a_complete INTEGER DEFAULT 0,
                section_b_complete INTEGER DEFAULT 0,
                section_c_complete INTEGER DEFAULT 0,
                section_d_complete INTEGER DEFAULT 0,
                section_e_complete INTEGER DEFAULT 0,
                locked_at TIMESTAMP,
                locked_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ssid, school_year)
            )
        """)
        conn.commit()
        conn.close()

    init_observation_tables()

    # Session state for form
    if 'init_record' not in st.session_state:
        st.session_state.init_record = {
            'section_a': {},
            'section_b': {},
            'section_c': {},
            'section_d': {},
            'section_e': {}
        }

    # Student selector
    st.markdown("---")
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        student_ssid = st.text_input("Student SSID", placeholder="Enter State Student ID")
    with col2:
        teacher_id = st.text_input("Teacher ID", value="demo_teacher")
    with col3:
        school_year = st.selectbox("School Year", ["2025-2026", "2024-2025", "2026-2027"])

    if not student_ssid:
        st.info("Enter a Student SSID to begin the initialization record.")
        st.stop()

    # Check if record exists and is locked
    db_path = Path(__file__).parent / "vera_demo.db"
    conn = sqlite3.connect(str(db_path))
    existing = conn.execute(
        "SELECT * FROM initialization_records WHERE ssid = ? AND school_year = ?",
        (student_ssid, school_year)
    ).fetchone()
    conn.close()

    if existing and existing[16]:  # locked_at field
        st.warning(f"This record was locked on {existing[16]} and cannot be edited.")
        st.markdown("**Document 2 (Daily Observations)** is now active for this student.")
        st.stop()

    st.markdown("---")

    # Five-Section Checklist
    st.markdown(f"""
        <div style="background: {NAVY}; color: white; padding: 16px; border-radius: 4px; margin-bottom: 20px;">
            <h3 style="color: {GOLD}; margin: 0;">Five-Section Initialization Checklist</h3>
            <p style="margin: 8px 0 0 0; opacity: 0.8;">All sections must be completed before this record can be locked.</p>
        </div>
    """, unsafe_allow_html=True)

    # SECTION A: Record Verification
    with st.expander("**Section A: Record Verification**", expanded=True):
        st.markdown("*Verify student identity and administrative records*")

        a1 = st.checkbox("Student name and SSID confirmed against roster", key="a1")
        a2 = st.checkbox("Emergency contact and parent/guardian verified (Day 1 required)", key="a2")
        a3 = st.checkbox("Home language survey reviewed (EL students)", key="a3")
        a4 = st.checkbox("Immunization record on file (health office confirms)", key="a4")
        a5 = st.checkbox("Special population flags reviewed and acknowledged", key="a5")

        # Population flags display
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.checkbox("English Learner (EL)", key="flag_el")
        with col2:
            st.checkbox("IEP/504", key="flag_iep")
        with col3:
            st.checkbox("Foster Youth", key="flag_foster")
        with col4:
            st.checkbox("Socioeconomically Disadvantaged", key="flag_sed")

        section_a_complete = all([a1, a2, a3, a4, a5])
        if section_a_complete:
            st.success("Section A complete")

    # SECTION B: Assessment Data Review
    with st.expander("**Section B: Assessment Data Review**", expanded=False):
        st.markdown("*Review baseline assessment scores and VERA hypothesis*")

        # Simulated VERA data pull (in production, this would come from CAASPP/ELPAC)
        st.markdown("**CAASPP Scores (Auto-populated)**")
        col1, col2 = st.columns(2)
        with col1:
            caaspp_ela = st.number_input("ELA Scale Score", value=2485, disabled=True)
            ela_claim2 = st.number_input("ELA Claim 2 (Writing)", value=2470, disabled=True)
        with col2:
            caaspp_math = st.number_input("Math Scale Score", value=2510, disabled=True)

        st.markdown("**ELPAC Scores (Auto-populated)**")
        col1, col2, col3 = st.columns(3)
        with col1:
            elpac_oral = st.number_input("ELPAC Oral", value=2502, disabled=True)
        with col2:
            elpac_written = st.number_input("ELPAC Written", value=2465, disabled=True)
        with col3:
            delta = elpac_oral - ela_claim2
            st.metric("Oral-Written Delta", f"{delta:+d}")
            if delta > 8:
                st.error("TYPE 4 FLAG")

        st.markdown("---")
        st.markdown("**VERA Starting Hypothesis**")
        vera_hypothesis = "Type 4 candidate - oral language proficiency exceeds written. Consider writing-focused intervention rather than oral ELD." if delta > 8 else "No significant oral-written gap detected. Standard ELD pathway recommended."
        st.info(vera_hypothesis)

        b1 = st.checkbox("CAASPP ELA score reviewed", key="b1")
        b2 = st.checkbox("ELPAC oral and written scores reviewed — delta confirmed", key="b2")
        b3 = st.checkbox("CAASPP Math score reviewed", key="b3")
        b4 = st.checkbox("Teacher acknowledges VERA finding and starting hypothesis (SB 1288 §C)", key="b4")

        section_b_complete = all([b1, b2, b3, b4])
        if section_b_complete:
            st.success("Section B complete")

    # SECTION C: Prior Intervention History
    with st.expander("**Section C: Prior Intervention History**", expanded=False):
        st.markdown("*Review what has been tried before*")

        st.markdown("**Prior Teacher Summary (Auto-populated)**")
        st.text_area(
            "Previous teacher notes",
            value="Student shows strong verbal participation in class discussions. Written work often incomplete or below grade level. Responded well to graphic organizers and sentence frames. Parent engaged and supportive.",
            height=100,
            disabled=True,
            key="prior_summary"
        )

        st.markdown("**Prior Interventions**")
        intervention_data = {
            "Intervention": ["Small group ELD", "After-school tutoring", "Graphic organizers"],
            "Duration": ["12 weeks", "8 weeks", "Ongoing"],
            "Outcome": ["Partially effective", "Ineffective", "Effective"]
        }
        st.dataframe(intervention_data, use_container_width=True)

        c1 = st.checkbox("Prior teacher summary read and acknowledged", key="c1")
        c2 = st.checkbox("Prior intervention outcomes reviewed — effective interventions flagged", key="c2")

        st.markdown("**LCAP Intervention Assignment**")
        intervention_options = [
            "Writing-focused ELD (VERA recommended)",
            "Standard oral ELD",
            "Integrated ELD",
            "Designated ELD",
            "After-school tutoring",
            "Push-in support",
            "Other"
        ]
        assigned_intervention = st.selectbox("Confirm or modify intervention assignment", intervention_options, key="intervention")
        c3 = st.checkbox("LCAP intervention assignment confirmed or modified (human approval required)", key="c3")

        section_c_complete = all([c1, c2, c3])
        if section_c_complete:
            st.success("Section C complete")

    # SECTION D: Equity and Access
    with st.expander("**Section D: Equity and Access**", expanded=False):
        st.markdown("*Verify equitable access to resources (SB 1288 Section E)*")

        d1 = st.checkbox("Device access confirmed (1:1 device or daily access verified)", key="d1")

        st.markdown("**AI Literacy Status (New 2026 — SB 1288 §E)**")
        ai_literacy = st.selectbox(
            "AI literacy instruction received",
            ["Not yet started", "In progress", "Completed - basic", "Completed - advanced"],
            key="ai_literacy"
        )
        d2 = st.checkbox("AI literacy instruction status reviewed", key="d2")

        d3 = st.checkbox("Free/Reduced meal eligibility confirmed", key="d3")

        section_d_complete = all([d1, d2, d3])
        if section_d_complete:
            st.success("Section D complete")

    # SECTION E: Day-One Starting Plan
    with st.expander("**Section E: Day-One Starting Plan**", expanded=False):
        st.markdown("*Final review and sign-off — THIS LOCKS THE RECORD*")

        st.markdown("**VERA Starting Hypothesis**")
        st.info(vera_hypothesis)

        teacher_response = st.radio(
            "Teacher response to VERA hypothesis",
            ["Confirmed — I agree with VERA's assessment",
             "Challenged — I disagree based on my observation",
             "Modified — I accept with adjustments"],
            key="teacher_response"
        )

        if "Challenged" in teacher_response or "Modified" in teacher_response:
            teacher_notes = st.text_area(
                "Explain your challenge or modification",
                placeholder="Provide rationale for disagreeing with or modifying VERA's hypothesis...",
                key="teacher_notes"
            )
        else:
            teacher_notes = ""

        e1 = st.checkbox("VERA starting hypothesis accepted or challenged", key="e1")
        e2 = st.checkbox("I understand this record will be LOCKED permanently upon submission", key="e2")

        section_e_complete = all([e1, e2])
        if section_e_complete:
            st.success("Section E complete — Ready to lock")

    # Summary and Submit
    st.markdown("---")
    st.markdown("### Checklist Summary")

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        if section_a_complete:
            st.success("A ✓")
        else:
            st.error("A ○")
    with col2:
        if section_b_complete:
            st.success("B ✓")
        else:
            st.error("B ○")
    with col3:
        if section_c_complete:
            st.success("C ✓")
        else:
            st.error("C ○")
    with col4:
        if section_d_complete:
            st.success("D ✓")
        else:
            st.error("D ○")
    with col5:
        if section_e_complete:
            st.success("E ✓")
        else:
            st.error("E ○")

    all_complete = all([section_a_complete, section_b_complete, section_c_complete,
                        section_d_complete, section_e_complete])

    if all_complete:
        st.markdown(f"""
            <div style="background: {GREEN}; color: white; padding: 16px; border-radius: 4px; margin: 20px 0;">
                <strong>All sections complete.</strong> This record is ready to be locked.
            </div>
        """, unsafe_allow_html=True)

        if st.button("🔒 LOCK RECORD & OPEN DOCUMENT 2", type="primary", use_container_width=True):
            # Save to database
            db_path = Path(__file__).parent / "vera_demo.db"
            conn = sqlite3.connect(str(db_path))

            # Map teacher response
            response_map = {
                "Confirmed — I agree with VERA's assessment": "confirmed",
                "Challenged — I disagree based on my observation": "challenged",
                "Modified — I accept with adjustments": "modified"
            }

            conn.execute("""
                INSERT INTO initialization_records
                (ssid, teacher_id, district_id, school_year, vera_hypothesis, teacher_response,
                 teacher_notes, intervention_assigned, section_a_complete, section_b_complete,
                 section_c_complete, section_d_complete, section_e_complete, locked_at, locked_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 1, 1, 1, 1, datetime('now'), ?)
                ON CONFLICT(ssid, school_year) DO UPDATE SET
                    vera_hypothesis = excluded.vera_hypothesis,
                    teacher_response = excluded.teacher_response,
                    teacher_notes = excluded.teacher_notes,
                    intervention_assigned = excluded.intervention_assigned,
                    section_a_complete = 1,
                    section_b_complete = 1,
                    section_c_complete = 1,
                    section_d_complete = 1,
                    section_e_complete = 1,
                    locked_at = datetime('now'),
                    locked_by = excluded.locked_by,
                    updated_at = datetime('now')
            """, (
                student_ssid,
                teacher_id,
                "demo_district",
                school_year,
                vera_hypothesis,
                response_map.get(teacher_response, "confirmed"),
                teacher_notes,
                assigned_intervention,
                teacher_id
            ))
            conn.commit()
            conn.close()

            st.success("✅ Record LOCKED. Document 2 (Daily Observations) is now active.")
            st.balloons()
            st.info("Navigate to **📅 Daily Observations** to begin recording daily observations for this student.")
    else:
        st.warning("Complete all five sections to lock this record.")
        st.markdown("*Nothing in VERA activates until the teacher signs off on Section E. This is the human approval gate required by SB 1288 Section C.*")

# =============================================================================
# Page: Daily Observations (Document 2)
# =============================================================================

elif page == "📅 Daily Observations":
    st.title("Daily Classroom Observations")
    st.markdown("*Document 2 — Ongoing Observation Log*")

    # Initialize observations table
    def init_observations_table():
        db_path = Path(__file__).parent / "vera_demo.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS observations (
                record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id TEXT NOT NULL,
                district_id TEXT NOT NULL,
                school_id TEXT,
                class_period TEXT,
                observation_date DATE NOT NULL,
                ssid TEXT NOT NULL,
                present INTEGER DEFAULT 0,
                oral_participation INTEGER DEFAULT 0,
                written_output INTEGER DEFAULT 0,
                engaged INTEGER DEFAULT 0,
                concern_flag INTEGER DEFAULT 0,
                absent INTEGER DEFAULT 0,
                elaboration TEXT,
                oral_quality TEXT,
                written_quality TEXT,
                intervention_response TEXT,
                note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(teacher_id, observation_date, ssid, class_period)
            )
        """)
        conn.commit()
        conn.close()

    init_observations_table()

    # Demo student roster (in production, pulled from initialization_records)
    DEMO_ROSTER = [
        {"ssid": "1001", "name": "Garcia, Maria", "flag": "EL", "type4": True},
        {"ssid": "1002", "name": "Johnson, Michael", "flag": None, "type4": False},
        {"ssid": "1003", "name": "Chen, David", "flag": "EL", "type4": True},
        {"ssid": "1004", "name": "Williams, Jasmine", "flag": "IEP", "type4": False},
        {"ssid": "1005", "name": "Martinez, Carlos", "flag": "EL", "type4": False},
        {"ssid": "1006", "name": "Brown, Ashley", "flag": None, "type4": False},
        {"ssid": "1007", "name": "Nguyen, Tommy", "flag": "EL", "type4": True},
        {"ssid": "1008", "name": "Davis, Brandon", "flag": "SED", "type4": False},
        {"ssid": "1009", "name": "Lopez, Sofia", "flag": "EL", "type4": False},
        {"ssid": "1010", "name": "Wilson, Tyler", "flag": "IEP", "type4": False},
    ]

    # Elaboration options
    ELABORATION_OPTIONS = [
        "",
        "Strong oral response",
        "Oral prompting needed",
        "Written output strong",
        "Written output emerging",
        "Oral exceeds written",
        "Written exceeds oral",
        "Off task redirected",
        "VERA hypothesis confirmed",
        "VERA hypothesis challenged",
        "Intervention responding",
        "Intervention not responding",
        "Parent contact needed",
        "Referral recommended",
        "Academic vocabulary used",
        "Peer collaboration strong",
        "Peer collaboration needed",
        "Assessment accommodation used",
        "Other"
    ]

    # Header controls
    st.markdown("---")
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

    with col1:
        teacher_id = st.text_input("Teacher ID", value="demo_teacher", key="obs_teacher")
    with col2:
        class_period = st.selectbox("Class Period", ["Period 1", "Period 2", "Period 3", "Period 4", "Period 5", "Period 6"], key="obs_period")
    with col3:
        observation_date = st.date_input("Date", value=datetime.now(), key="obs_date")
    with col4:
        if st.button("Mark All Present", use_container_width=True):
            for i, student in enumerate(DEMO_ROSTER):
                st.session_state[f"present_{student['ssid']}"] = True
                st.session_state[f"absent_{student['ssid']}"] = False

    st.markdown("---")

    # Legend
    st.markdown(f"""
        <div style="display: flex; gap: 20px; margin-bottom: 16px; font-size: 0.85rem;">
            <span><span style="color: #FFA500; font-weight: bold;">●</span> Type 4 (Oral > Written)</span>
            <span><span style="color: #4CAF50; font-weight: bold;">●</span> EL</span>
            <span><span style="color: #2196F3; font-weight: bold;">●</span> IEP</span>
            <span><span style="color: #9C27B0; font-weight: bold;">●</span> SED</span>
        </div>
    """, unsafe_allow_html=True)

    # Column headers
    header_cols = st.columns([3, 1, 1, 1, 1, 1, 1, 3, 3])
    with header_cols[0]:
        st.markdown("**Student**")
    with header_cols[1]:
        st.markdown("**P**")
    with header_cols[2]:
        st.markdown("**Or**")
    with header_cols[3]:
        st.markdown("**Wr**")
    with header_cols[4]:
        st.markdown("**En**")
    with header_cols[5]:
        st.markdown("**!**")
    with header_cols[6]:
        st.markdown("**Ab**")
    with header_cols[7]:
        st.markdown("**Elaboration**")
    with header_cols[8]:
        st.markdown("**Note**")

    st.markdown("---")

    # Student roster rows
    observations_data = []

    for student in DEMO_ROSTER:
        ssid = student['ssid']

        # Color dot based on flags
        if student['type4']:
            dot = '<span style="color: #FFA500; font-weight: bold;">●</span>'
        elif student['flag'] == 'EL':
            dot = '<span style="color: #4CAF50; font-weight: bold;">●</span>'
        elif student['flag'] == 'IEP':
            dot = '<span style="color: #2196F3; font-weight: bold;">●</span>'
        elif student['flag'] == 'SED':
            dot = '<span style="color: #9C27B0; font-weight: bold;">●</span>'
        else:
            dot = '<span style="color: #888;">○</span>'

        cols = st.columns([3, 1, 1, 1, 1, 1, 1, 3, 3])

        with cols[0]:
            st.markdown(f"{dot} {student['name']}", unsafe_allow_html=True)

        with cols[1]:
            present = st.checkbox("P", key=f"present_{ssid}", label_visibility="collapsed")

        with cols[2]:
            oral = st.checkbox("Or", key=f"oral_{ssid}", label_visibility="collapsed")

        with cols[3]:
            written = st.checkbox("Wr", key=f"written_{ssid}", label_visibility="collapsed")

        with cols[4]:
            engaged = st.checkbox("En", key=f"engaged_{ssid}", label_visibility="collapsed")

        with cols[5]:
            concern = st.checkbox("!", key=f"concern_{ssid}", label_visibility="collapsed")

        with cols[6]:
            absent = st.checkbox("Ab", key=f"absent_{ssid}", label_visibility="collapsed")

        with cols[7]:
            elaboration = st.selectbox(
                "Elab",
                ELABORATION_OPTIONS,
                key=f"elab_{ssid}",
                label_visibility="collapsed"
            )

        with cols[8]:
            note = st.text_input("Note", key=f"note_{ssid}", label_visibility="collapsed", placeholder="...")

        # Concern flag expansion
        if concern:
            with st.expander(f"⚠️ Concern details for {student['name']}", expanded=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    oral_quality = st.selectbox(
                        "Oral language quality",
                        ["", "Sentence-level", "Paragraph-level", "Academic vocabulary", "Single words only"],
                        key=f"oral_qual_{ssid}"
                    )
                with c2:
                    written_quality = st.selectbox(
                        "Written output quality",
                        ["", "Full sentences", "Sentence fragments", "Key words only", "No written output"],
                        key=f"written_qual_{ssid}"
                    )
                with c3:
                    intervention_resp = st.selectbox(
                        "Intervention response",
                        ["", "Responding well", "Partially responding", "Not responding", "Not yet active"],
                        key=f"interv_resp_{ssid}"
                    )
        else:
            oral_quality = ""
            written_quality = ""
            intervention_resp = ""

        # Collect data
        observations_data.append({
            "ssid": ssid,
            "present": 1 if present and not absent else 0,
            "oral_participation": 1 if oral else 0,
            "written_output": 1 if written else 0,
            "engaged": 1 if engaged else 0,
            "concern_flag": 1 if concern else 0,
            "absent": 1 if absent else 0,
            "elaboration": elaboration if elaboration else None,
            "oral_quality": oral_quality if oral_quality else None,
            "written_quality": written_quality if written_quality else None,
            "intervention_response": intervention_resp if intervention_resp else None,
            "note": note if note else None
        })

    # Aggregation bar
    st.markdown("---")
    st.markdown(f"""
        <div style="background: {NAVY}; color: white; padding: 16px; border-radius: 4px;">
            <h4 style="color: {GOLD}; margin: 0 0 12px 0;">Today's Aggregation</h4>
        </div>
    """, unsafe_allow_html=True)

    total_students = len(DEMO_ROSTER)
    present_count = sum(1 for o in observations_data if o['present'])
    absent_count = sum(1 for o in observations_data if o['absent'])
    oral_count = sum(1 for o in observations_data if o['oral_participation'])
    written_count = sum(1 for o in observations_data if o['written_output'])
    engaged_count = sum(1 for o in observations_data if o['engaged'])
    concern_count = sum(1 for o in observations_data if o['concern_flag'])

    agg_cols = st.columns(6)
    with agg_cols[0]:
        st.metric("Present", f"{present_count}/{total_students}")
    with agg_cols[1]:
        st.metric("Absent", absent_count)
    with agg_cols[2]:
        st.metric("Oral", oral_count)
    with agg_cols[3]:
        st.metric("Written", written_count)
    with agg_cols[4]:
        st.metric("Engaged", engaged_count)
    with agg_cols[5]:
        st.metric("Concerns", concern_count, delta=None if concern_count == 0 else "flag", delta_color="inverse")

    # Oral vs Written pattern detection
    if present_count > 0:
        oral_rate = (oral_count / present_count) * 100
        written_rate = (written_count / present_count) * 100

        if oral_rate > written_rate + 15:
            st.warning(f"⚠️ **Pattern detected:** Oral participation ({oral_rate:.0f}%) exceeds written output ({written_rate:.0f}%) by >15%. This may indicate Type 4 characteristics at class level.")

    # Submit button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("💾 SUBMIT OBSERVATIONS", type="primary", use_container_width=True):
            db_path = Path(__file__).parent / "vera_demo.db"
            conn = sqlite3.connect(str(db_path))

            records_saved = 0
            for obs in observations_data:
                try:
                    conn.execute("""
                        INSERT INTO observations
                        (teacher_id, district_id, class_period, observation_date, ssid,
                         present, oral_participation, written_output, engaged,
                         concern_flag, absent, elaboration, oral_quality, written_quality,
                         intervention_response, note)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(teacher_id, observation_date, ssid, class_period)
                        DO UPDATE SET
                            present = excluded.present,
                            oral_participation = excluded.oral_participation,
                            written_output = excluded.written_output,
                            engaged = excluded.engaged,
                            concern_flag = excluded.concern_flag,
                            absent = excluded.absent,
                            elaboration = excluded.elaboration,
                            oral_quality = excluded.oral_quality,
                            written_quality = excluded.written_quality,
                            intervention_response = excluded.intervention_response,
                            note = excluded.note
                    """, (
                        teacher_id,
                        "demo_district",
                        class_period,
                        observation_date.strftime("%Y-%m-%d"),
                        obs['ssid'],
                        obs['present'],
                        obs['oral_participation'],
                        obs['written_output'],
                        obs['engaged'],
                        obs['concern_flag'],
                        obs['absent'],
                        obs['elaboration'],
                        obs['oral_quality'],
                        obs['written_quality'],
                        obs['intervention_response'],
                        obs['note']
                    ))
                    records_saved += 1
                except Exception as e:
                    st.error(f"Error saving {obs['ssid']}: {e}")

            conn.commit()
            conn.close()

            st.success(f"✅ {records_saved} observations saved for {observation_date.strftime('%Y-%m-%d')} - {class_period}")
            st.balloons()

    # Show recent observations summary
    st.markdown("---")
    st.markdown("### Recent Observation History")

    db_path = Path(__file__).parent / "vera_demo.db"
    conn = sqlite3.connect(str(db_path))
    try:
        history_df = pd.read_sql_query("""
            SELECT observation_date, class_period,
                   COUNT(*) as students,
                   SUM(present) as present,
                   SUM(oral_participation) as oral,
                   SUM(written_output) as written,
                   SUM(concern_flag) as concerns
            FROM observations
            WHERE teacher_id = ?
            GROUP BY observation_date, class_period
            ORDER BY observation_date DESC, class_period
            LIMIT 10
        """, conn, params=[teacher_id])

        if len(history_df) > 0:
            st.dataframe(history_df, use_container_width=True)
        else:
            st.info("No observation history yet. Submit your first observations above.")
    except Exception as e:
        st.info("No observation history yet.")
    finally:
        conn.close()
