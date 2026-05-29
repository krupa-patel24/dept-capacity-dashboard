
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import math

# ─── PAGE CONFIG ───────────────────────────────
st.set_page_config(
    page_title="Department Capacity Planner",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Department Capacity — Projects to Take")
st.caption("Sales team view — free hours ke hisaab se kitne projects lene hain")

# ─── DATA ──────────────────────────────────────
# Apna actual data yahan paste karo ya CSV load karo
# CSV se load karna ho toh:
# df = pd.read_csv("data.csv")

df = pd.DataFrame({
    "department":      ["Engineering", "Design", "Marketing", "Finance", "QA"],
    "available_hours": [2112, 800, 1200, 600, 900],
    "planned_hours":   [545,  300, 500,  200, 400],
    "logged_hours":    [400,  250, 450,  180, 350],
    "q1":              [28,   18,  22,   35,  20],
    "q3":              [72,   50,  58,   95,  60],
})

# ─── CALCULATE ─────────────────────────────────
df["free_hours"]      = df["available_hours"] - df["planned_hours"]
df["iqr"]             = df["q3"] - df["q1"]
df["utilization_pct"] = (df["planned_hours"] / df["available_hours"] * 100).round(1)
df["projects_to_take"]= (df["free_hours"] / df["iqr"].replace(0, float("nan"))).apply(
                            lambda x: math.floor(x) if pd.notna(x) else 0
                        )

# ─── FILTERS ───────────────────────────────────
st.sidebar.header("Filters")

all_depts = ["All"] + list(df["department"].unique())
selected_dept = st.sidebar.selectbox("Department", all_depts)

min_free = st.sidebar.slider(
    "Minimum free hours",
    min_value=0,
    max_value=int(df["free_hours"].max()),
    value=0
)

# Filter apply karo
filtered = df.copy()
if selected_dept != "All":
    filtered = filtered[filtered["department"] == selected_dept]
filtered = filtered[filtered["free_hours"] >= min_free]

# ─── KPI TILES ─────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Free Hours",     f"{filtered['free_hours'].sum():,.0f}")
col2.metric("Projects to Take",     f"{filtered['projects_to_take'].sum():,.0f}")
col3.metric("Avg IQR (hrs)",        f"{filtered['iqr'].mean():,.0f}")
col4.metric("Avg Utilization",      f"{filtered['utilization_pct'].mean():.1f}%")

st.divider()

# ─── CHARTS ────────────────────────────────────
c1, c2 = st.columns(2)

with c1:
    st.subheader("Projects to Take per Department")
    fig1 = px.bar(
        filtered.sort_values("projects_to_take", ascending=False),
        x="department",
        y="projects_to_take",
        color="projects_to_take",
        color_continuous_scale="Greens",
        labels={"projects_to_take": "Projects", "department": "Department"},
        text="projects_to_take"
    )
    fig1.update_traces(textposition="outside")
    fig1.update_layout(showlegend=False, coloraxis_showscale=False)
    st.plotly_chart(fig1, use_container_width=True)

with c2:
    st.subheader("Free vs Planned Hours")
    fig2 = px.bar(
        filtered,
        x="department",
        y=["planned_hours", "free_hours"],
        barmode="stack",
        labels={"value": "Hours", "department": "Department", "variable": "Type"},
        color_discrete_map={
            "planned_hours": "#3266AD",
            "free_hours":    "#639922"
        }
    )
    st.plotly_chart(fig2, use_container_width=True)

# ─── IQR DETAIL TABLE ──────────────────────────
st.subheader("Department Detail")
st.dataframe(
    filtered[[
        "department", "available_hours", "planned_hours",
        "free_hours", "utilization_pct", "q1", "q3", "iqr", "projects_to_take"
    ]].rename(columns={
        "department":      "Department",
        "available_hours": "Available Hrs",
        "planned_hours":   "Planned Hrs",
        "free_hours":      "Free Hrs",
        "utilization_pct": "Utilization %",
        "q1":              "Q1",
        "q3":              "Q3",
        "iqr":             "IQR",
        "projects_to_take":"Projects to Take"
    }).style.background_gradient(subset=["Projects to Take"], cmap="Greens"),
    use_container_width=True,
    hide_index=True
)
