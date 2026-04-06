import streamlit as st

from ui.amtdc import apply_page_config, close_shell, inject_styles, render_shell, render_sidebar


apply_page_config("AMTDC Support")
inject_styles()
render_sidebar("Support")
render_shell("Precision Support", "Operational", "Engineering Hub", "Support")

top_cols = st.columns([2, 1], gap="large")
with top_cols[0]:
    st.markdown(
        """
        <div class="section-card">
            <div class="soft-label">Support Search</div>
            <h3 style="font-family:'Space Grotesk',sans-serif;font-size:2.3rem;margin:0.35rem 0 0.8rem 0;">Engineering Assistance</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.text_input("Search technical documentation, error codes, or schematics", placeholder="Search technical documentation, error codes, or schematics...")
with top_cols[1]:
    st.markdown(
        """
        <div class="hero-band">
            <div class="soft-label" style="color:#c7f1f1;">System Status</div>
            <h3>Operational</h3>
            <p style="margin:0.8rem 0 0 0;color:#d9f6f6;">Latency 14ms | Uptime 99.98%</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

content_cols = st.columns([1.6, 1], gap="large")
with content_cols[0]:
    st.markdown(
        """
        <div class="section-card">
            <div class="soft-label">Open Support Ticket</div>
            <h3 style="font-family:'Space Grotesk',sans-serif;font-size:2rem;margin:0.35rem 0 1rem 0;">Contact Engineering</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.form("support_ticket_form"):
        row = st.columns(2)
        subject = row[0].text_input("Subject Line", placeholder="Component Failure - Axis B")
        priority = row[1].selectbox("Priority Level", ["Standard (P4)", "Urgent (P2)", "Critical Shutdown (P1)"])
        message = st.text_area(
            "Detailed Message / Telemetry Data",
            placeholder="Provide machine ID and a detailed description of the incident...",
            height=180,
        )
        submitted = st.form_submit_button("Dispatch Ticket", use_container_width=True)

    if submitted:
        st.success(f"Support ticket submitted with priority {priority}: {subject or 'Untitled issue'}")

with content_cols[1]:
    st.markdown(
        """
        <div class="section-card">
            <div class="soft-label">Technical Resources</div>
            <h3 style="font-family:'Space Grotesk',sans-serif;font-size:2rem;margin:0.35rem 0 1rem 0;">Documentation</h3>
            <div class="panel-muted" style="margin-bottom:0.8rem;"><strong>API Documentation</strong><br><span style="color:#61748d;">Version 4.2.0 stable</span></div>
            <div class="panel-muted" style="margin-bottom:0.8rem;"><strong>Installation Schematics</strong><br><span style="color:#61748d;">CAD and PDF blueprints</span></div>
            <div class="panel-muted"><strong>Safety Protocol Manual</strong><br><span style="color:#61748d;">Updated 48h ago</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

faq_cols = st.columns(3, gap="large")
faq_items = [
    ("Thermal Calibration", "If axis deviation exceeds 0.002 mm, initiate a thermal reset before opening a hardware ticket."),
    ("API Key Rotation", "Security tokens expire every 90 days. Refresh the handshake from Settings when telemetry sync fails."),
    ("Latency Spikes", "Confirm the local edge node is not saturated by high-frequency logging before escalating cloud diagnostics."),
]
for col, item in zip(faq_cols, faq_items):
    with col:
        st.markdown(
            f"""
            <div class="section-card">
                <div class="soft-label">Resolution</div>
                <h3 style="font-family:'Space Grotesk',sans-serif;font-size:1.6rem;margin:0.35rem 0 0.8rem 0;">{item[0]}</h3>
                <p style="color:#61748d;line-height:1.7;margin:0;">{item[1]}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

close_shell()
