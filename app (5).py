import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="Project Cumulative Spent vs Threshold", layout="wide")

st.markdown("""
    <style>
        .block-container { padding-top: 1rem; }
        body { background-color: #0f1117; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Project Cumulative Spent vs Threshold")
st.caption("🔵 Cumulative Spent  🟣 Cumulative Planned  🟠 Threshold (Active Jobs × 8 hrs)")

# ── Load Data ──────────────────────────────────────────────────────────────────
@st.cache_data
def load_data(path="final_data.csv"):
    df_raw = pd.read_csv(path)
    df = df_raw.dropna(subset=['work_date']).copy()
    df['work_date']              = pd.to_datetime(df['work_date'])
    df['job_start_date']         = pd.to_datetime(df['job_start_date'])
    df['job_effective_end_date'] = pd.to_datetime(df['job_effective_end_date'])
    return df

try:
    df = load_data()
except FileNotFoundError:
    st.error("❌ `final_data.csv` not found. Please place it in the same folder as `app.py`.")
    st.stop()

THRESHOLD_PER_JOB = 8

# ── Project Selector ───────────────────────────────────────────────────────────
projects = sorted(df['project_name'].unique())
selected_project = st.sidebar.selectbox("📁 Select Project", projects)

# ── Build Chart for Selected Project ──────────────────────────────────────────
proj = df[df['project_name'] == selected_project].copy()

active = proj[
    (proj['work_date'] >= proj['job_start_date']) &
    (proj['work_date'] <= proj['job_effective_end_date'])
].copy()

all_days           = sorted(active['working_day_number'].dropna().astype(int).unique())
days_logged        = max(all_days)
project_total_days = int(proj['project_total_days'].iloc[0])

day_agg = (
    active.groupby('working_day_number')
    .agg(
        daily_spent   = ('spent_hours',   'sum'),
        daily_planned = ('planned_hours', 'sum'),
        active_jobs   = ('job_name',      'nunique'),
        employees     = ('employee_id',   'nunique')
    )
    .reset_index()
)
day_agg['working_day_number'] = day_agg['working_day_number'].astype(int)
day_agg = day_agg.sort_values('working_day_number')

day_agg['cum_spent']   = day_agg['daily_spent'].cumsum()
day_agg['cum_planned'] = day_agg['daily_planned'].cumsum()
day_agg['thr_day']     = day_agg['active_jobs'] * THRESHOLD_PER_JOB
day_agg['thr_cum']     = day_agg['thr_day'].cumsum()
day_agg['diff']        = day_agg['cum_spent'] - day_agg['thr_cum']
day_agg['status']      = day_agg['diff'].apply(lambda x: '🔴 Over' if x > 0 else '🟢 Under')

days     = day_agg['working_day_number'].values
cum_s    = day_agg['cum_spent'].values
cum_p    = day_agg['cum_planned'].values
thr_c    = day_agg['thr_cum'].values
daily_s  = day_agg['daily_spent'].values
daily_p  = day_agg['daily_planned'].values
act_jobs = day_agg['active_jobs'].values
emp      = day_agg['employees'].values
diff     = day_agg['diff'].values
status   = day_agg['status'].values

# Dynamic marker size
_msize = 6 if len(days) <= 100 else (4 if len(days) <= 200 else 2)

# ── Tick values ────────────────────────────────────────────────────────────────
def make_tickvals(days_logged):
    interval = max(1, round(days_logged / 15 / 5) * 5) if days_logged > 15 else 1
    tv = list(range(1, days_logged + 1, interval))
    if days_logged not in tv:
        tv.append(days_logged)
    return tv

tickvals = make_tickvals(days_logged)

# ── Summary Stats ──────────────────────────────────────────────────────────────
last      = day_agg.iloc[-1]
delta_val = last['diff']
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Days Logged",          f"{days_logged} / {project_total_days}")
col2.metric("Cumulative Spent",     f"{last['cum_spent']:.1f} hrs")
col3.metric("Cumulative Planned",   f"{last['cum_planned']:.1f} hrs")
col4.metric("Cumulative Threshold", f"{last['thr_cum']:.0f} hrs")
col5.metric("Difference (Spent vs Threshold)", f"{delta_val:+.1f} hrs",
            delta=f"{'Over' if delta_val > 0 else 'Under'} threshold",
            delta_color="inverse")

# ── Plotly Figure ──────────────────────────────────────────────────────────────
fig = go.Figure()

# Threshold line
fig.add_trace(go.Scatter(
    x=days, y=thr_c,
    mode='lines+markers',
    name='Threshold',
    line=dict(color='#ff6b35', width=2.5, dash='dash'),
    marker=dict(size=_msize, color='#ff6b35', symbol='circle'),
    hoveron='points',
    customdata=list(zip(days, thr_c, act_jobs)),
    hovertemplate=(
        '<b>🎯 Threshold</b><br>'
        '<b>📅 Day %{customdata[0]}</b><br>'
        '──────────────────────<br>'
        '📈 Cumulative Threshold: <b>%{customdata[1]:.0f} hrs</b><br>'
        '💼 Active Jobs Today   : <b>%{customdata[2]}</b><br>'
        f'⚡ Today\'s Threshold  : <b>{THRESHOLD_PER_JOB} x %{{customdata[2]}} hrs</b><br>'
        '<extra></extra>'
    )
))

# Cumulative Planned line
fig.add_trace(go.Scatter(
    x=days, y=cum_p,
    mode='lines+markers',
    name='Cumulative Planned',
    line=dict(color='#a29bfe', width=2.5, dash='dot'),
    marker=dict(size=_msize, color='#a29bfe', symbol='diamond'),
    hoveron='points',
    customdata=list(zip(days, daily_p, cum_p)),
    hovertemplate=(
        '<b>📋 Cumulative Planned</b><br>'
        '<b>📅 Day %{customdata[0]}</b><br>'
        '──────────────────────<br>'
        '⏱️ Daily Planned      : <b>%{customdata[1]:.2f} hrs</b><br>'
        '📈 Cumulative Planned : <b>%{customdata[2]:.2f} hrs</b><br>'
        '<extra></extra>'
    )
))

# Cumulative Spent line
fig.add_trace(go.Scatter(
    x=days, y=cum_s,
    mode='lines+markers',
    name='Cumulative Spent',
    line=dict(color='#4fc3f7', width=2.5),
    marker=dict(size=_msize, color='#4fc3f7'),
    hoveron='points',
    customdata=list(zip(days, daily_s, cum_s, thr_c, diff, act_jobs, emp, status)),
    hovertemplate=(
        '<b>📊 Cumulative Spent</b><br>'
        '<b>📅 Day %{customdata[0]}</b><br>'
        '──────────────────────<br>'
        '⏱️ Daily Spent        : <b>%{customdata[1]:.2f} hrs</b><br>'
        '📈 Cumulative Spent   : <b>%{customdata[2]:.2f} hrs</b><br>'
        '🎯 Cumulative Threshold: <b>%{customdata[3]:.0f} hrs</b><br>'
        '📊 Difference         : <b>%{customdata[4]:+.2f} hrs</b><br>'
        '💼 Active Jobs Today  : <b>%{customdata[5]}</b><br>'
        '👥 Employees Today    : <b>%{customdata[6]}</b><br>'
        '%{customdata[7]}'
        '<extra></extra>'
    )
))

fig.update_layout(
    title=dict(
        text=(
            f'<b>📊 {selected_project}</b><br>'
            f'<sub>Days Logged: {days_logged} / {project_total_days}  |  '
            f'🔵 Cumulative Spent  🟣 Cumulative Planned  🟠 Threshold (active jobs x 8 hrs)</sub>'
        ),
        font=dict(size=15, color='white'),
        x=0.5
    ),
    paper_bgcolor='#0f1117',
    plot_bgcolor='#1a1d27',
    font=dict(color='#aaaaaa'),
    hovermode='x',
    hoverlabel=dict(
        bgcolor='#1e2235',
        bordercolor='#555',
        font=dict(color='white', size=12),
        namelength=-1
    ),
    legend=dict(
        bgcolor='#1a1d27',
        bordercolor='#444',
        font=dict(color='white', size=11)
    ),
    xaxis=dict(
        title='Working Day Number',
        gridcolor='#2a2d3a', gridwidth=0.7,
        tickcolor='#aaaaaa', linecolor='#333344',
        title_font=dict(color='#aaaaaa'),
        tickfont=dict(color='#aaaaaa'),
        tickvals=tickvals,
        ticktext=[str(v) for v in tickvals]
    ),
    yaxis=dict(
        title='Cumulative Spent Hours',
        gridcolor='#2a2d3a', gridwidth=0.7,
        tickcolor='#aaaaaa', linecolor='#333344',
        title_font=dict(color='#aaaaaa'),
        tickfont=dict(color='#aaaaaa')
    ),
    height=560,
    margin=dict(t=140)
)

st.plotly_chart(fig, use_container_width=True)

# ── Department Breakdown ───────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🏢 Department Breakdown")

dept_col = None
for candidate in ['department_group', 'department', 'dept', 'Department', 'Dept',
                  'DEPARTMENT', 'Department_Group', 'DEPARTMENT_GROUP']:
    if candidate in proj.columns:
        dept_col = candidate
        break

if dept_col is None:
    st.info("ℹ️ No `department` column found in your data.")
else:
    dept_agg = (
        active.groupby(dept_col)['spent_hours']
        .sum()
        .reset_index()
        .rename(columns={dept_col: 'department', 'spent_hours': 'total_spent'})
        .sort_values('total_spent', ascending=False)
    )

    total_spent_all = dept_agg['total_spent'].sum()

    DEPT_CONFIG = {
        'design':      {'icon': '🎨', 'color': '#e91e8c'},
        'development': {'icon': '💻', 'color': '#2196f3'},
        'dev':         {'icon': '💻', 'color': '#2196f3'},
        'qa':          {'icon': '🧪', 'color': '#4caf50'},
        'quality':     {'icon': '🧪', 'color': '#4caf50'},
    }

    def get_dept_config(name):
        key = name.lower().strip()
        for k, v in DEPT_CONFIG.items():
            if k in key:
                return v
        return {'icon': '📁', 'color': '#9c27b0'}

    dept_cols = st.columns(len(dept_agg))
    for i, (_, row) in enumerate(dept_agg.iterrows()):
        dept_name = row['department']
        hrs       = row['total_spent']
        pct       = (hrs / total_spent_all * 100) if total_spent_all > 0 else 0
        cfg       = get_dept_config(dept_name)

        dept_cols[i].markdown(
            f"""
            <div style="
                background:#1a1d27;
                border:1px solid #2a2d3a;
                border-radius:12px;
                padding:18px 20px 14px 20px;
            ">
                <div style="font-size:28px; margin-bottom:8px;">{cfg['icon']}</div>
                <div style="font-size:11px; color:#888; letter-spacing:1px; text-transform:uppercase; margin-bottom:4px;">{dept_name}</div>
                <div style="font-size:26px; font-weight:700; color:{cfg['color']}; margin-bottom:10px;">{hrs:.2f} hrs</div>
                <div style="background:#2a2d3a; border-radius:4px; height:6px; margin-bottom:8px;">
                    <div style="background:{cfg['color']}; width:{min(pct,100):.1f}%; height:6px; border-radius:4px;"></div>
                </div>
                <div style="font-size:12px; color:#888;">{pct:.1f}% of total spent</div>
            </div>
            """,
            unsafe_allow_html=True
        )
