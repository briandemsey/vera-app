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
    st.markdown(f"""
        <div style="text-align: center; padding: 20px 0;">
            <span style="color: {GOLD}; font-size: 2rem; font-weight: 700; font-family: 'Lora', serif;">H-</span>
            <span style="color: white; font-size: 2rem; font-weight: 700; font-family: 'Lora', serif;">EDU</span>
            <p style="color: {GOLD}; font-size: 0.9rem; margin-top: 8px;">VERA Dashboard</p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Navigation
    page = st.radio(
        "Navigate",
        ["District Dashboard", "Cross-District Scan", "LCAP Report", "About VERA"],
        label_visibility="collapsed"
    )

    st.markdown("---")

    # District selector (for relevant pages)
    if page in ["District Dashboard", "LCAP Report"]:
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

if page == "District Dashboard":
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

elif page == "Cross-District Scan":
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

elif page == "LCAP Report":
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

    # Report text
    st.markdown('<div class="section-header">COE Submission Report</div>', unsafe_allow_html=True)

    report_text = f"""
======================================================================
LCAP VERIFICATION REPORT - H-EDU/VERA
======================================================================

District: {selected_district}
County: {district_info['county']}
District ID: {district_id}
Report Date: {pd.Timestamp.now().strftime('%Y-%m-%d')}
----------------------------------------------------------------------

GAP PROFILE SUMMARY
  Total grade-subgroup combinations analyzed: {total_populations}
  Type 4 gaps detected (oral > written by 8+ pts): {type4_count}
  Estimated LCAP-to-Need Match Rate: {match_rate}%

{"ATTENTION REQUIRED:" if type4_count > 0 else ""}
{"  " + str(type4_count) + " grade-subgroup combinations show significant" if type4_count > 0 else ""}
{"  oral-written divergence. Review ELD intervention alignment." if type4_count > 0 else ""}

NON-EVALUATION GUARANTEE:
  No teacher identity is attached to any result in this report.
  Match-rate data is aggregate only.
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

elif page == "About VERA":
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
