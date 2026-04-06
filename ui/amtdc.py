import streamlit as st


NAV_ITEMS = [
    ("Dashboard", "/", "Main Navigation"),
    ("Live Data", "/Live_Data", None),
    ("Past Data", "/Machine_Data", None),
    ("Add Machine", "/Add_Machine", None),
]

OPS_ITEMS = [
    ("Settings", "/Settings", "Support & Ops"),
    ("Support", "/Support", None),
    ("Logs", "/Logs", None),
]


def apply_page_config(page_title: str) -> None:
    st.set_page_config(
        page_title=page_title,
        page_icon="A",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Inter:wght@400;500;600;700&display=swap');

        :root {
            --bg: #eef2f4;
            --panel: #ffffff;
            --panel-soft: #f6f8f9;
            --panel-muted: #e8edef;
            --ink: #11181c;
            --muted: #7f90a3;
            --line: #d9e1e5;
            --teal: #0b7171;
            --teal-soft: #5fd1d1;
            --blue-soft: #d8edf7;
            --warn: #a47400;
            --danger: #cf2e2e;
        }

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            background: var(--bg);
            color: var(--ink);
        }

        p, span, label, div, h1, h2, h3, h4, h5, h6 {
            color: inherit;
        }

        .stApp {
            background: linear-gradient(180deg, #f3f6f8 0%, #eef2f4 100%);
        }

        #MainMenu, footer, header[data-testid="stHeader"] {
            display: none !important;
        }

        [data-testid="stSidebarNav"] {
            display: none !important;
        }

        [data-testid="stSidebar"] {
            display: none !important;
        }

        .block-container {
            padding: 0 !important;
            max-width: 100% !important; 
            margin: 0 !important;
            padding-left: 215px !important; /* Increased for wider rail + gap */
            position: relative !important;
        }

        .amtdc-shell {
            padding: 0 1.25rem 1rem 1.25rem;
        }

        .amtdc-topbar {
            height: 72px; /* Bigger appropriate size */
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(217, 225, 229, 0.6);
            border-radius: 20px; /* Rounded pill style */
            display: flex;
            align-items: center;
            justify-content: flex-start;
            margin: -1.35rem 1rem 0.5rem 0rem; /* Flushed with Rail, moved UI up */
            padding: 0 2rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.03);
        }

        .amtdc-topbar-left {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .amtdc-orb {
            width: 28px;
            height: 28px;
            border-radius: 999px;
            border: 2px solid #0f1820;
            box-shadow: inset 0 0 0 6px rgba(11, 113, 113, 0.08);
        }

        .amtdc-brand {
            font-family: 'Space Grotesk', sans-serif;
            font-weight: 700;
            font-size: 2rem;
            color: var(--teal);
        }

        .amtdc-subbrand {
            color: #203038;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            font-size: 0.82rem;
            border-left: 1px solid #dde5e8;
            padding-left: 1rem;
        }

        .amtdc-page-title {
            display: flex;
            align-items: baseline;
            gap: 1rem;
            margin: 0px !important; 
            padding: 0px !important;
            margin-bottom: -1.2rem !important; /* Force content upwards */
        }

        .amtdc-page-title h1 {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 2.25rem; 
            line-height: 1;
            letter-spacing: -0.02em;
            margin: 0;
            color: var(--ink);
        }

        .amtdc-page-title .accent {
            flex: 1;
            height: 2px;
            background: linear-gradient(90deg, #e4eaee 0%, rgba(228, 234, 238, 0) 100%);
        }

        .amtdc-page-title .tag {
            color: var(--teal);
            font-weight: 700;
            font-size: 0.82rem;
            letter-spacing: 0.22em;
            text-transform: uppercase;
        }

        .section-card {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(4px);
            border: 1px solid rgba(217, 225, 229, 0.8);
            box-shadow: 0 6px 20px rgba(0,0,0,0.06);
            border-radius: 16px;
            padding: 1.5rem; /* Responsive padding */
            transition: transform 250ms ease-in-out, box-shadow 250ms ease-in-out;
            margin-bottom: 1rem;
            height: 100%;
            overflow: hidden; /* Prevent cramping overflow */
        }
        .section-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 32px rgba(0,0,0,0.1);
        }

        .section-card,
        .section-card *,
        .metric-card,
        .metric-card *,
        .panel-muted,
        .panel-muted * {
            color: var(--ink) !important;
        }

        .metric-card {
            background: rgba(255, 255, 255, 0.96);
            border: 1px solid rgba(224, 232, 236, 0.95);
            min-height: 130px;
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            border-radius: 16px;
            box-shadow: 0 6px 20px rgba(0,0,0,0.06);
            transition: transform 250ms ease-in-out, box-shadow 250ms ease-in-out;
            margin-bottom: 1rem;
            height: 100%;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 24px rgba(0,0,0,0.08);
        }

        .metric-label {
            color: #93a2b6 !important;
            text-transform: uppercase;
            letter-spacing: 0.16em;
            font-size: 0.8rem;
            font-weight: 700;
        }

        .metric-value {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 2.75rem;
            line-height: 1;
            font-weight: 700;
            color: var(--ink);
        }

        .metric-foot {
            color: #8ba0b8 !important;
            font-size: 0.9rem;
            font-weight: 600;
        }

        .rank-row {
            margin-bottom: 1rem;
        }

        .rank-row:last-child {
            margin-bottom: 0;
        }

        .rank-head {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-weight: 700;
            font-size: 0.92rem;
            margin-bottom: 0.5rem;
        }

        .rank-track {
            height: 7px;
            background: #e7edf0;
            border-radius: 999px;
            overflow: hidden;
        }

        .rank-fill {
            height: 100%;
            background: var(--teal);
            border-radius: 999px;
        }

        .soft-label {
            color: #93a2b6 !important;
            text-transform: uppercase;
            letter-spacing: 0.18em;
            font-size: 0.72rem;
            font-weight: 700;
        }

        .hero-band {
            background: linear-gradient(135deg, #0b7171 0%, #10a8a8 100%);
            color: white !important;
            padding: 1.8rem;
            box-shadow: 0 12px 30px rgba(11, 113, 113, 0.2);
            border-radius: 14px;
        }

        .hero-band * {
            color: white !important;
        }

        .hero-band h3 {
            margin: 0;
            font-family: 'Space Grotesk', sans-serif;
            font-size: 2rem;
        }

        .panel-muted {
            background: #f8fafc;
            border: 1px solid #e0e7eb;
            padding: 1.4rem;
            border-radius: 12px;
        }

        .status-pill {
            display: inline-block;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            padding: 0.25rem 0.65rem;
            border-radius: 9999px; /* Pill shaped */
        }

        .status-ok { background: rgba(11, 113, 113, 0.14); color: var(--teal) !important; }
        .status-warn { background: rgba(164, 116, 0, 0.14); color: var(--warn) !important; }
        .status-danger { background: rgba(207, 46, 46, 0.14); color: var(--danger) !important; }
        .status-info { background: rgba(72, 132, 176, 0.14); color: #4b6e90 !important; }

        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li,
        [data-testid="stMarkdownContainer"] strong,
        [data-testid="stMarkdownContainer"] span {
            color: var(--ink) !important;
        }

        .amtdc-right-rail {
            position: fixed;
            top: 12px;
            bottom: 12px;
            left: 12px;
            width: 190px; /* Widened to 190px to prevent text wrap */
            background: linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(240,245,247,0.98) 100%);
            border: 1px solid #dce6ea;
            border-radius: 24px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.05);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            padding: 1.5rem 1rem;
            z-index: 999;
        }

        .amtdc-rail-top, .amtdc-rail-bottom {
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }

        .amtdc-rail-brand {
            font-family: 'Space Grotesk', sans-serif;
            color: var(--teal) !important;
            font-size: 1.55rem;
            font-weight: 700;
            margin: 0 0 0.3rem 0;
        }

        .amtdc-rail-label {
            color: #8fa0b3 !important;
            text-transform: uppercase;
            letter-spacing: 0.18em;
            font-size: 0.68rem;
            font-weight: 700;
            margin: 0.7rem 0 0.25rem 0;
        }

        .amtdc-rail-link {
            display: block;
            color: #27465d !important;
            text-decoration: none;
            padding: 0.75rem 1rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            text-decoration: none !important; /* No underlines as requested */
            white-space: nowrap; /* Single word display */
            font-size: 0.72rem;
            border-right: 4px solid transparent;
            border-radius: 0 40px 40px 0; 
            margin-right: 0.5rem;
            background: transparent;
        }

        .amtdc-rail-link:hover {
            background: rgba(11, 113, 113, 0.08);
            color: var(--teal) !important;
        }

        .amtdc-rail-link.active {
            background: rgba(255, 255, 255, 0.95);
            color: var(--teal) !important;
            border-right-color: var(--teal);
            box-shadow: 0 10px 20px rgba(32, 48, 56, 0.05);
        }

        div[data-baseweb="select"] > div,
        .stDateInput > div > div,
        .stTimeInput > div > div,
        .stTextInput > div > div,
        .stTextArea textarea,
        .stNumberInput > div > div {
            background: rgba(255, 255, 255, 0.95) !important;
            border: 1px solid #dde5e8 !important;
            border-radius: 8px !important;
            color: var(--ink) !important;
            transition: border-color 200ms ease, box-shadow 200ms ease !important;
        }

        div[data-baseweb="select"] > div:focus-within,
        .stDateInput > div > div:focus-within,
        .stTimeInput > div > div:focus-within,
        .stTextInput > div > div:focus-within,
        .stTextArea textarea:focus,
        .stNumberInput > div > div:focus-within {
            border-color: var(--teal) !important;
            box-shadow: 0 0 0 3px rgba(11, 113, 113, 0.15) !important;
        }

        input,
        textarea,
        [data-baseweb="select"] input,
        [data-baseweb="select"] span,
        [data-baseweb="select"] div {
            color: var(--ink) !important;
        }

        input::placeholder,
        textarea::placeholder {
            color: #a1afbf !important;
            opacity: 1 !important;
        }

        [data-testid="stWidgetLabel"],
        [data-testid="stWidgetLabel"] *,
        .stSelectbox label,
        .stTextInput label,
        .stTextArea label,
        .stDateInput label,
        .stTimeInput label,
        .stSlider label {
            color: var(--ink) !important;
        }

        .stButton > button {
            border-radius: 8px !important;
            border: none !important;
            background: linear-gradient(135deg, #0b7171 0%, #10a8a8 100%) !important;
            color: white !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.12em !important;
            box-shadow: 0 6px 16px rgba(11, 113, 113, 0.15) !important;
            transition: transform 250ms ease, box-shadow 250ms ease !important;
        }

        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 22px rgba(11, 113, 113, 0.25) !important;
        }

        .stSlider [data-baseweb="slider"] > div > div > div {
            background: var(--teal) !important;
        }

        [data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.96);
            border: 1px solid rgba(224, 232, 236, 0.95);
            padding: 1rem 1.2rem;
        }

        .stDataFrame, div[data-testid="stTable"] {
            border: 1px solid #dde5e8;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 16px rgba(0,0,0,0.03);
        }

        [data-testid="stPlotlyChart"] {
            background: transparent !important;
            border-radius: 18px !important;
            overflow: hidden !important;
        }

        [data-testid="stPlotlyChart"] > div {
            border-radius: 18px !important;
            overflow: hidden !important;
        }
        
        /* Table Zebra subtle shading */
        .stDataFrame tr:nth-child(even) {
            background-color: #f8fafc !important;
        }

        /* --- PROPORTIONAL INPUT STRUCTURING --- */
        [data-testid="stSelectbox"] {
            max-width: 300px !important;
        }

        [data-testid="stDateInput"], 
        [data-testid="stTimeInput"] {
            max-width: 220px !important;
        }
        
        [data-testid="stHorizontalBlock"] > div[data-testid="column"] > div > [data-testid="stSelectbox"],
        [data-testid="stHorizontalBlock"] > div[data-testid="column"] > div > [data-testid="stDateInput"],
        [data-testid="stHorizontalBlock"] > div[data-testid="column"] > div > [data-testid="stTimeInput"] {
            margin-right: auto;
        }

        [data-testid="stHorizontalBlock"] {
            gap: 1.5rem !important; /* Full width tracking gap */
        }
        
        [data-testid="stVerticalBlock"] {
            gap: 1.25rem !important;
        }

        @media (max-width: 960px) {
            .amtdc-topbar {
                padding: 0 1rem;
                margin-left: -1rem;
                margin-right: -1rem;
            }

            .amtdc-page-title h1 {
                font-size: 2rem;
            }

            .amtdc-shell {
                padding: 0 1rem 1rem 1rem;
            }

            .amtdc-right-rail {
                width: 60px;
                padding: 1rem 0.5rem;
                left: 0 !important;
            }
            
            .amtdc-rail-brand {
                display: none;
            }

            .amtdc-rail-link {
                font-size: 0;
                padding: 0.5rem;
                text-align: center;
            }

            .amtdc-rail-link::before {
                content: "•";
                font-size: 1.2rem;
            }

            .block-container {
                padding-left: 60px !important;
                width: 100% !important;
                max-width: 100% !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(active_page: str) -> None:
    return None


def render_shell(title: str, tag: str, subtitle: str, active_page: str) -> None:
    st.markdown('<div class="amtdc-shell">', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="amtdc-topbar">
            <div class="amtdc-topbar-left">
                <div class="amtdc-orb"></div>
                <div class="amtdc-brand">AMTDC</div>
                <div class="amtdc-subbrand">{subtitle}</div>
            </div>
        </div>
        <div class="amtdc-page-title">
            <h1>{title}</h1>
            <div class="accent"></div>
            <div class="tag">{tag}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(_right_rail_markup(active_page), unsafe_allow_html=True)


def close_shell() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def metric_card(label: str, value: str, foot: str = "") -> str:
    foot_markup = f'<div class="metric-foot">{foot}</div>' if foot else ""
    return (
        '<div class="metric-card">'
        f'<div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div>'
        f"{foot_markup}"
        "</div>"
    )


def badge(text: str, tone: str = "ok") -> str:
    return f'<span class="status-pill status-{tone}">{text}</span>'


def _right_rail_markup(active_page: str) -> str:
    parts = [
        '<div class="amtdc-right-rail">',
        # Top Group
        '<div class="amtdc-rail-top">',
    ]

    group_label = None
    for label, path, section in NAV_ITEMS:
        if section and section != group_label:
            parts.append(f'<div class="amtdc-rail-label">{section}</div>')
            group_label = section
        active_class = " active" if label == active_page else ""
        parts.append(f'<a class="amtdc-rail-link{active_class}" href="{path}" target="_self">{label}</a>')

    # Close Top Group, Open Bottom Group
    parts.append('</div><div class="amtdc-rail-bottom">')

    parts.append('<div class="amtdc-rail-label">Support & Ops</div>')
    for label, path, _ in OPS_ITEMS:
        active_class = " active" if label == active_page else ""
        parts.append(f'<a class="amtdc-rail-link{active_class}" href="{path}" target="_self">{label}</a>')

    parts.append("</div></div>")
    return "".join(parts)
