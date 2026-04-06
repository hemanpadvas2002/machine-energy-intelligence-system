import streamlit as st

from ui.amtdc import apply_page_config, close_shell, inject_styles, render_shell, render_sidebar


apply_page_config("AMTDC Add Machine")
inject_styles()
render_sidebar("Add Machine")
render_shell("Registration", "System Entry", "Equipment Console", "Add Machine")

left_col, right_col = st.columns([1.8, 1], gap="large")

with left_col:
    st.markdown(
        """
        <div class="section-card">
            <div class="soft-label">System Entry</div>
            <h3 style="font-family:'Space Grotesk',sans-serif;font-size:2.2rem;margin:0.35rem 0 1.2rem 0;">Equipment Parameters</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.form("add_machine_form"):
        first_row = st.columns(2)
        machine_id = first_row[0].text_input("Machine ID", placeholder="e.g. CNC-2024-X1")
        machine_type = first_row[1].selectbox(
            "Equipment Type",
            ["CNC Machine", "Industrial Compressor", "HVAC System", "Hydraulic Press", "Robotic Arm"],
        )

        second_row = st.columns(2)
        location = second_row[0].text_input("Facility Location", placeholder="Sector 7, Bay 4")
        install_date = second_row[1].date_input("Installation Date")

        power_kw = st.slider("Power Rating (kW)", min_value=0, max_value=500, value=120, step=10)
        submitted = st.form_submit_button("Save Machine", use_container_width=True)

    if submitted:
        st.success(
            f"Machine registration captured for {machine_id or 'new asset'} as {machine_type} at {location or 'unspecified location'}."
        )

with right_col:
    st.markdown(
        f"""
        <div class="hero-band">
            <h3>Registry Guidelines</h3>
            <p style="margin:1rem 0 0 0;color:#d9f6f6;line-height:1.7;">
                Ensure all precision assets are registered with unique serial keys. Incorrect power rating input may result in inaccurate telemetry diagnostics.
            </p>
            <div style="margin-top:2rem;padding-top:1rem;border-top:1px solid rgba(255,255,255,0.2);display:flex;justify-content:space-between;">
                <span class="soft-label" style="color:#c7f1f1;">Global Tolerance</span>
                <strong style="font-size:2rem;">+- 0.002%</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="section-card" style="margin-top:1.5rem;">
            <div class="soft-label">Live Calibration</div>
            <h3 style="font-family:'Space Grotesk',sans-serif;font-size:2rem;margin:0.35rem 0 0.7rem 0;">Digital Twin Ready</h3>
            <p style="color:#61748d;line-height:1.7;margin:0;">
                Adding equipment automatically initializes a digital twin profile for telemetry baselining and stress simulation.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

footer_cols = st.columns(3)
footer_cols[0].markdown("**Database Node**  \nAMT-DB-NORTH-01")
footer_cols[1].markdown("**Status**  \nCONNECTED")
footer_cols[2].markdown("**Snapshot**  \nRegistration UI active")

close_shell()
