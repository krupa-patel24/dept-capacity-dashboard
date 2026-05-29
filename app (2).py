
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import math

st.set_page_config(
    page_title="Project Hours Analysis",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Project Wise Hours Analysis")
st.caption("Available vs Spent Hours — Project wise cumulative view")

# ─── LOAD DATA ─────────────────────────────────
df = pd.read_csv("Dedication_prediction.csv")

# NO RENAME NEEDED — job_effective_end_date already exists

# ─── DATE CONVERSION ───────────────────────────
df['project_start_date']     = pd.to_datetime(df['project_start_date'])
df['project_end_date']       = pd.to_datetime(df['project_end_date'])
df['job_start_date']         = pd.to_datetime(df['job_start_date'])
df['job_effective_end_date'] = pd.to_datetime(df['job_effective_end_date'])

# ─── SIDEBAR FILTER ────────────────────────────
st.sidebar.header("Filter")
all_projects = sorted(df['project_name'].unique())
selected_project = st.sidebar.selectbox("Select Project", all_projects)

# ─── DAY WISE DATA ─────────────────────────────
project_df    = df[df['project_name'] == selected_project]
project_start = project_df['project_start_date'].min()
project_end   = project_df['project_end_date'].max()
all_days      = pd.date_range(project_start, project_end)

all_rows = []
for single_day in all_days:
    active_jobs = project_df[
        (project_df['job_start_date']         <= single_day) &
        (project_df['job_effective_end_date'] >= single_day)
    ]
    all_rows.append({
        'date':            single_day,
        'available_hours': active_jobs['available_hours'].sum(),
        'spent_hours':     active_jobs['spent_hours'].sum()
    })

final_df = pd.DataFrame(all_rows).sort_values('date')
final_df['cum_available_hours'] = final_df['available_hours'].cumsum()
final_df['cum_spent_hours']     = final_df['spent_hours'].cumsum()
final_df['project_day']         = range(1, len(final_df) + 1)

# ─── KPI TILES ─────────────────────────────────
total_available = final_df['cum_available_hours'].iloc[-1]
total_spent     = final_df['cum_spent_hours'].iloc[-1]
utilization     = (total_spent / total_available * 100) if total_available > 0 else 0

col1, col2, col3 = st.columns(3)
col1.metric("Total Available Hours", f"{total_available:,.0f}")
col2.metric("Total Spent Hours",     f"{total_spent:,.0f}")
col3.metric("Utilization %",         f"{utilization:.1f}%",
    delta="Healthy" if 75 <= utilization <= 85 else
          "Under" if utilization < 75 else "Over")

st.divider()

# ─── CHART ─────────────────────────────────────
total_days = len(final_df)
interval   = max(1, math.ceil(total_days / 5))

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=final_df['project_day'],
    y=final_df['cum_available_hours'],
    mode='lines+markers',
    name='Available Hours',
    line=dict(color='blue'),
    hovertemplate=(
        '<b>Available Hours</b><br>'
        'Project Day: %{x}<br>'
        'Hours: %{y}<br><br>'
        'Total available working capacity.<extra></extra>'
    )
))

fig.add_trace(go.Scatter(
    x=final_df['project_day'],
    y=final_df['cum_spent_hours'],
    mode='lines+markers',
    name='Spent Hours',
    line=dict(color='red'),
    hovertemplate=(
        '<b>Spent Hours</b><br>'
        'Project Day: %{x}<br>'
        'Hours: %{y}<br><br>'
        'Actual consumed effort.<extra></extra>'
    )
))

fig.update_layout(
    title=f'{selected_project} : Available vs Spent Hours',
    xaxis=dict(title='Project Days', dtick=interval),
    yaxis=dict(title='Hours'),
    hovermode='x unified',
    height=550,
    annotations=[dict(
        x=0, y=-0.35,
        xref='paper', yref='paper',
        showarrow=False,
        align='left',
        text=(
            '<b>Graph Explanation:</b><br><br>'
            '🔵 <b>Available Hours:</b> Total working capacity based on active jobs.<br><br>'
            '🔴 <b>Spent Hours:</b> Actual effort consumed over project duration.<br><br>'
            '<b>Interpretation:</b><br>'
            '• Spent below Available → Under-utilization<br>'
            '• Spent near Available → Healthy utilization<br>'
            '• Spent above Available → Over-utilization'
        )
    )]
)

st.plotly_chart(fig, use_container_width=True)

# ─── RAW DATA ──────────────────────────────────
with st.expander("View Raw Data"):
    st.dataframe(final_df[[
        'project_day', 'date',
        'available_hours', 'spent_hours',
        'cum_available_hours', 'cum_spent_hours'
    ]], use_container_width=True, hide_index=True)
