import streamlit as st
import pandas as pd
import plotly.express as px
from config.settings import MACHINE_TABLE_MAPPING
from utils.db_handler import fetch_data_from_postgres

def render_machine_dashboard():
    st.title("🏭 Machine Data Dashboard")

    # Sidebar Controls
    st.sidebar.header("Controls")
    machine_display_name = st.sidebar.selectbox("Select Machine", list(MACHINE_TABLE_MAPPING.keys()))
    table = MACHINE_TABLE_MAPPING[machine_display_name]

    df = fetch_data_from_postgres(table)

    if df.empty:
        st.warning(f"No data available for {machine_display_name}")
        return

    # Date and Time Filters
    st.sidebar.subheader("Filter Timeline")
    with st.sidebar.form("filter_form"):
        start_date = st.date_input("From Date", df["timestamp"].min().date())
        start_time = st.time_input("From Time", value=pd.to_datetime("00:00:00").time())
        
        end_date = st.date_input("To Date", df["timestamp"].max().date())
        end_time = st.time_input("To Time", value=pd.to_datetime("23:59:59").time())
        
        submitted = st.form_submit_button("🚀 Go")

    # Combine to datetime
    start_ts = pd.to_datetime(f"{start_date} {start_time}")
    end_ts   = pd.to_datetime(f"{end_date} {end_time}")

    # Use session state to keep filtered data
    if "filtered_df" not in st.session_state or submitted or "last_machine" not in st.session_state or st.session_state.last_machine != machine_display_name:
        st.session_state.filtered_df = df[
            (df["timestamp"] >= start_ts) &
            (df["timestamp"] <= end_ts)
        ]
        st.session_state.last_machine = machine_display_name

    filtered_df = st.session_state.filtered_df

    if filtered_df.empty:
        st.warning("No data found for the selected timeline. Adjust and click **Go**.")
        return

    # Metrics Row
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Avg Voltage LN", f"{filtered_df['avg_voltage_ln'].mean():.2f}")
    with col2:
        st.metric("Avg Current", f"{filtered_df['avg_current'].mean():.2f}")
    with col3:
        st.metric("Total KW", f"{filtered_df['total_kw'].max():.2f}")

    # Graph
    st.subheader(f"{machine_display_name} - Power (kW)")
    fig = px.line(
        filtered_df,
        x="timestamp",
        y="total_kw",
        title="Power Consumption Over Time",
        template="plotly_dark",
        color_discrete_sequence=['#00D4FF']
    )
    st.plotly_chart(fig, use_container_width=True)

    # Data Table
    st.subheader("Raw Data (Latest 50 rows)")
    st.dataframe(filtered_df.tail(50), use_container_width=True)
