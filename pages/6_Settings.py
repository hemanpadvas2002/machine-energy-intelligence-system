import streamlit as st

from ui.amtdc import apply_page_config, close_shell, inject_styles, render_shell, render_sidebar


apply_page_config("AMTDC Settings")
inject_styles()
render_sidebar("Settings")
render_shell("System Settings", "Configuration", "Configuration Console", "Settings")

left_col, right_col = st.columns([1, 2], gap="large")

with left_col:
    st.markdown(
        """
        <div class="section-card">
            <div class="soft-label">User Profile</div>
            <h3 style="font-family:'Space Grotesk',sans-serif;font-size:2rem;margin:0.6rem 0 0.35rem 0;">Marcus Vance</h3>
            <p style="margin:0;color:#61748d;">Senior Systems Engineer</p>
            <div style="margin-top:1.8rem;">
                <div class="soft-label">Email Address</div>
                <p style="font-size:1.2rem;margin:0.6rem 0 1.2rem 0;">m.vance@amtdc.industrial</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.button("Edit Profile", use_container_width=True)

    st.markdown(
        """
        <div class="section-card" style="margin-top:1.5rem;">
            <div class="soft-label">Interface Theme</div>
            <h3 style="font-family:'Space Grotesk',sans-serif;font-size:1.7rem;margin:0.6rem 0 1rem 0;">Light Graphite</h3>
            <p style="margin:0;color:#61748d;">The current UI follows the light industrial shell you attached.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with right_col:
    st.markdown(
        """
        <div class="section-card">
            <div class="soft-label">Telemetry Tolerances</div>
            <h3 style="font-family:'Space Grotesk',sans-serif;font-size:2.3rem;margin:0.35rem 0 1rem 0;">System Thresholds</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )
    threshold_cols = st.columns(3)
    labels = [("Normal State", 45), ("Warning Trigger", 75), ("Critical Load", 90)]
    for col, (label, value) in zip(threshold_cols, labels):
        with col:
            st.markdown(f'<div class="soft-label">{label}</div>', unsafe_allow_html=True)
            st.slider(label, min_value=0, max_value=100, value=value, label_visibility="collapsed")

    bottom_cols = st.columns(2, gap="large")
    with bottom_cols[0]:
        st.markdown(
            """
            <div class="section-card">
                <div class="soft-label">Dispatch Rules</div>
                <h3 style="font-family:'Space Grotesk',sans-serif;font-size:2rem;margin:0.35rem 0 1rem 0;">Notifications</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.toggle("Email Alerts", value=True)
        st.toggle("SMS Push", value=False)
    with bottom_cols[1]:
        st.markdown(
            """
            <div class="section-card">
                <div class="soft-label">External Integrations</div>
                <h3 style="font-family:'Space Grotesk',sans-serif;font-size:2rem;margin:0.35rem 0 1rem 0;">API Keys</h3>
                <p style="color:#61748d;">Provision and manage access tokens for third-party telemetry software.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.code("AK-882-XXXX-XXXX")
        action_cols = st.columns(2)
        action_cols[0].button("Revoke", use_container_width=True)
        action_cols[1].button("Generate New Key", use_container_width=True)

footer_cols = st.columns([1, 1, 1.2])
footer_cols[0].markdown("Last synced: Today, 08:42 AM")
footer_cols[1].button("Discard Changes", use_container_width=True)
footer_cols[2].button("Commit Configuration", use_container_width=True)

close_shell()
