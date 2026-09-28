import json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from utils.machine_registry import get_all_machines
from services.matlab_analytics import get_matlab_analytics_service
from ui.amtdc import apply_page_config, close_shell, inject_styles, render_shell, render_sidebar
from utils.db_handler import fetch_data_by_date_range


apply_page_config("AMTDC Past Data")
inject_styles()
render_sidebar("Past Data")
render_shell("Past Data", "Historical", "Telemetry Archive", "Past Data")


METRIC_OPTIONS = {
    "Total kW": {"column": "total_kw", "unit": "kW", "title": "Load Frequency"},
    "Total Net kWh": {"column": "total_net_kwh", "unit": "kWh", "title": "Energy Trend"},
    "Avg Voltage LN": {"column": "avg_voltage_ln", "unit": "V", "title": "Voltage Trend"},
    "Avg Voltage LL": {"column": "avg_voltage_ll", "unit": "V", "title": "Voltage Trend"},
    "Avg Current": {"column": "avg_current", "unit": "A", "title": "Current Trend"},
}

MODE_TONES = ["#0b7171", "#1191a0", "#4b6e90", "#a47400", "#cf2e2e"]
TELEMETRY_COLUMNS = ["avg_voltage_ln", "avg_voltage_ll", "avg_current", "total_kw", "total_net_kwh"]


def render_metric_card(label: str, value: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def compute_modes(values: list[float]) -> list[dict]:
    series = pd.Series(values, dtype="float64").round(2)
    series = series[series != 0]
    if series.empty:
        return []
    counts = series.value_counts().head(5)
    modes = []
    for index, (value, hits) in enumerate(counts.items()):
        modes.append(
            {
                "label": f"MOD-{index + 1:02d}",
                "value": float(value),
                "hits": int(hits),
                "tone": MODE_TONES[index % len(MODE_TONES)],
            }
        )
    return modes


def filter_valid_meter_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Drop synthetic/offline all-zero packets from historical graphs."""
    if df.empty:
        return df
    available_columns = [column for column in TELEMETRY_COLUMNS if column in df.columns]
    if not available_columns:
        return df
    numeric = df[available_columns].fillna(0).astype(float).abs()
    return df[numeric.sum(axis=1) > 0].copy()


def build_historical_dashboard_html(metric_title: str, unit: str, engine: str, payload: dict) -> str:
    payload_json = json.dumps(payload)
    display_title = f"Historical {metric_title}"
    unit_label = unit or "signal"
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
      <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js"></script>
      <style>
        :root {{
          --panel: rgba(255,255,255,0.96);
          --line: #d9e1e5;
          --ink: #11181c;
          --muted: #8ba0b8;
          --teal: #0b7171;
          --teal-soft: #5fd1d1;
          --blue: #4b6e90;
          --warn: #a47400;
          --danger: #cf2e2e;
        }}
        * {{ box-sizing: border-box; }}
        body {{
          margin: 0;
          font-family: Inter, sans-serif;
          color: var(--ink);
          background: transparent;
        }}
        .main-grid {{
          display: grid;
          grid-template-columns: minmax(0, 2.2fr) minmax(320px, 1fr);
          gap: 20px;
          align-items: stretch;
        }}
        .panel {{
          background: var(--panel);
          border: 1px solid rgba(217, 225, 229, 0.9);
          border-radius: 16px;
          box-shadow: 0 6px 20px rgba(0,0,0,0.06);
          padding: 22px;
        }}
        .chart-panel {{
          min-height: 620px;
          display: flex;
          flex-direction: column;
        }}
        .section-label {{
          color: var(--muted);
          text-transform: uppercase;
          letter-spacing: 0.18em;
          font-size: 11px;
          font-weight: 700;
        }}
        h3 {{
          font-family: "Space Grotesk", sans-serif;
          font-size: 30px;
          margin: 8px 0 0 0;
        }}
        .legend-row {{
          display: flex;
          gap: 16px;
          margin-top: 14px;
          flex-wrap: wrap;
        }}
        .variant-pill {{
          display: inline-flex;
          align-items: center;
          gap: 8px;
          border: 1px solid #d8e1e6;
          background: #f8fbfc;
          color: #526273;
          border-radius: 999px;
          font-size: 13px;
          font-weight: 700;
          padding: 8px 14px;
          cursor: pointer;
          transition: all 180ms ease;
        }}
        .variant-pill.active {{
          background: rgba(11, 113, 113, 0.12);
          color: var(--teal);
          border-color: rgba(11, 113, 113, 0.28);
          box-shadow: 0 4px 12px rgba(11, 113, 113, 0.08);
        }}
        .legend-swatch {{
          width: 12px;
          height: 12px;
          border-radius: 999px;
        }}
        .chart-wrap {{
          position: relative;
          height: 360px;
          margin-top: 20px;
        }}
        .fft-wrap {{
          position: relative;
          height: 220px;
          margin-top: 18px;
          border-top: 1px solid #edf2f5;
          padding-top: 18px;
        }}
        .mode-list {{
          display: grid;
          gap: 14px;
          margin-top: 18px;
        }}
        .mode-row {{
          background: #f8fafc;
          border: 1px solid #e0e7eb;
          border-left-width: 4px;
          border-radius: 12px;
          padding: 16px;
        }}
        .mode-head {{
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-top: 8px;
          font-weight: 700;
          gap: 10px;
        }}
        .mode-pill {{
          background: rgba(11, 113, 113, 0.12);
          color: var(--teal);
          border-radius: 999px;
          font-size: 11px;
          padding: 4px 10px;
          text-transform: uppercase;
          letter-spacing: 0.08em;
        }}
        .warning {{
          margin-top: 16px;
          border-radius: 12px;
          padding: 14px 16px;
          background: rgba(127, 144, 163, 0.08);
          color: #526273;
          font-weight: 600;
          display: none;
          border-left: 4px solid #7f90a3;
        }}
        @media (max-width: 900px) {{
          .main-grid {{ grid-template-columns: 1fr; }}
        }}
      </style>
    </head>
    <body>
      <section class="main-grid">
        <div class="panel chart-panel">
          <div class="section-label">MATLAB TIME-SERIES</div>
          <h3>{display_title}</h3>
          <div class="legend-row" id="variantButtons">
            <button class="variant-pill active" data-variant="all"><span class="legend-swatch" style="background:#0b7171;"></span>All</button>
            <button class="variant-pill" data-variant="raw"><span class="legend-swatch" style="background:#4b6e90;"></span>Raw</button>
            <button class="variant-pill" data-variant="filtered"><span class="legend-swatch" style="background:#0b7171;"></span>Filtered</button>
            <button class="variant-pill" data-variant="smoothed"><span class="legend-swatch" style="background:#5fd1d1;"></span>Smoothed</button>
          </div>
          <div class="chart-wrap"><canvas id="powerChart"></canvas></div>
          <div id="zeroWarning" class="warning"></div>
          <div class="fft-wrap">
            <div class="section-label">FFT SPECTRUM</div>
            <canvas id="fftChart"></canvas>
          </div>
        </div>
        <div class="panel">
          <div class="section-label">Operation Modules</div>
          <h3>Historical Units</h3>
          <div id="modeList" class="mode-list"></div>
        </div>
      </section>
      <script>
        Chart.register(window['chartjs-plugin-annotation']);
        const payload = {payload_json};

        const timeseriesChart = new Chart(document.getElementById('powerChart'), {{
          type: 'line',
          data: {{
            labels: [],
            datasets: [
              {{
                label: 'Raw',
                data: [],
                borderColor: '#4b6e90',
                borderWidth: 2,
                fill: false,
                pointRadius: 2,
                tension: 0.24
              }},
              {{
                label: 'Filtered',
                data: [],
                borderColor: '#0b7171',
                borderWidth: 3,
                backgroundColor: 'rgba(95, 209, 209, 0.14)',
                fill: true,
                pointRadius: 0,
                tension: 0.34
              }},
              {{
                label: 'Smoothed',
                data: [],
                borderColor: '#5fd1d1',
                borderWidth: 2,
                fill: false,
                pointRadius: 0,
                tension: 0.4
              }}
            ]
          }},
          options: {{
            responsive: true,
            maintainAspectRatio: false,
            animation: {{ duration: 450, easing: 'easeOutCubic' }},
            interaction: {{ intersect: false, mode: 'index' }},
            plugins: {{
              legend: {{ display: false }},
              annotation: {{ annotations: {{}} }}
            }},
            scales: {{
              x: {{ grid: {{ display: false }}, ticks: {{ color: '#8ca0b6', maxTicksLimit: 6 }} }},
              y: {{
                grid: {{ color: 'rgba(217,225,229,0.5)' }},
                ticks: {{ color: '#8ca0b6' }},
                title: {{ display: true, text: '{unit_label}', color: '#8ca0b6' }}
              }}
            }}
          }}
        }});

        const fftChart = new Chart(document.getElementById('fftChart'), {{
          type: 'line',
          data: {{
            labels: [],
            datasets: [{{
              label: 'FFT',
              data: [],
              borderColor: '#a47400',
              backgroundColor: 'rgba(164, 116, 0, 0.10)',
              fill: true,
              borderWidth: 2,
              pointRadius: 2,
              tension: 0.2
            }}]
          }},
          options: {{
            responsive: true,
            maintainAspectRatio: false,
            animation: {{ duration: 450, easing: 'easeOutCubic' }},
            plugins: {{ legend: {{ display: false }} }},
            scales: {{
              x: {{ grid: {{ display: false }}, ticks: {{ color: '#8ca0b6', maxTicksLimit: 5 }} }},
              y: {{ grid: {{ color: 'rgba(217,225,229,0.35)' }}, ticks: {{ color: '#8ca0b6', maxTicksLimit: 4 }} }}
            }}
          }}
        }});

        function formatTime(iso) {{
          const date = new Date(iso);
          return date.toLocaleString([], {{
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
          }});
        }}

        function updateAnnotations(modes) {{
          const annotations = {{}};
          modes.forEach((mode, index) => {{
            annotations[`mode_${{index}}`] = {{
              type: 'line',
              yMin: mode.value,
              yMax: mode.value,
              borderColor: mode.tone,
              borderWidth: 2,
              borderDash: [4, 4],
              label: {{
                display: true,
                content: `${{mode.label}} ${{Number(mode.value).toFixed(2)}}`,
                position: 'start',
                backgroundColor: 'rgba(255,255,255,0.88)',
                color: '#1b2530',
                font: {{ size: 12, weight: '700' }},
                yAdjust: -6
              }}
            }};
          }});
          timeseriesChart.options.plugins.annotation.annotations = annotations;
        }}

        function updateModes(modes) {{
          const list = document.getElementById('modeList');
          list.innerHTML = '';
          if (!modes.length) {{
            const note = document.createElement('div');
            note.className = 'warning';
            note.style.display = 'block';
            note.style.marginTop = '8px';
            note.textContent = 'No mode values are available for the selected historical range.';
            list.appendChild(note);
            return;
          }}

          modes.forEach((mode) => {{
            const row = document.createElement('div');
            row.className = 'mode-row';
            row.style.borderLeftColor = mode.tone;
            row.innerHTML = `
              <div class="section-label">${{mode.label}}</div>
              <div class="mode-head">
                <strong>${{Number(mode.value).toFixed(2)}}</strong>
                <span class="mode-pill">${{mode.hits}} hits</span>
              </div>
            `;
            list.appendChild(row);
          }});
        }}

        function setVariant(variant) {{
          const datasetVisibility = {{
            all: [false, false, false],
            raw: [false, true, true],
            filtered: [true, false, true],
            smoothed: [true, true, false]
          }};
          const hiddenFlags = datasetVisibility[variant] || datasetVisibility.all;
          timeseriesChart.data.datasets.forEach((dataset, index) => {{
            dataset.hidden = hiddenFlags[index];
          }});
          document.querySelectorAll('.variant-pill').forEach((button) => {{
            button.classList.toggle('active', button.dataset.variant === variant);
          }});
          timeseriesChart.update('active');
        }}

        function renderCharts() {{
          timeseriesChart.data.labels = (payload.timestamps || []).map(formatTime);
          timeseriesChart.data.datasets[0].data = payload.values || [];
          timeseriesChart.data.datasets[1].data = payload.filtered || [];
          timeseriesChart.data.datasets[2].data = payload.smoothed || [];

          const allValues = [
            ...(payload.values || []),
            ...(payload.filtered || []),
            ...(payload.smoothed || []),
            ...((payload.modes || []).map((mode) => Number(mode.value || 0)))
          ];
          if (allValues.length) {{
            const localMin = Math.min(...allValues);
            const localMax = Math.max(...allValues);
            const span = Math.max(localMax - localMin, 0.05);
            const padding = Math.max(span * 0.18, 0.02);
            timeseriesChart.options.scales.y.min = Number((localMin - padding).toFixed(2));
            timeseriesChart.options.scales.y.max = Number((localMax + padding).toFixed(2));
          }}

          updateAnnotations(payload.modes || []);
          updateModes(payload.modes || []);
          timeseriesChart.update('active');

          fftChart.data.labels = (payload.fft_frequency || []).map((value) => Number(value).toFixed(2));
          fftChart.data.datasets[0].data = payload.fft || [];
          fftChart.update('active');
        }}

        document.querySelectorAll('.variant-pill').forEach((button) => {{
          button.addEventListener('click', () => setVariant(button.dataset.variant));
        }});
        const warningElement = document.getElementById('zeroWarning');
        warningElement.style.display = payload.zero_only_signal ? 'block' : 'none';
        if (payload.zero_only_signal) {{
            warningElement.textContent = 'Signal is currently flat (0.0). Valid mode analytics require dynamic telemetry.';
        }} else {{
            warningElement.textContent = '';
        }}
        renderCharts();
        setVariant('all');
      </script>
    </body>
    </html>
    """


# ── session-state defaults ────────────────────────────────────────────────────
_MACHINE_KEYS = list(get_all_machines().keys())
_METRIC_KEYS = list(METRIC_OPTIONS.keys())
if "pd_machine" not in st.session_state:
    st.session_state["pd_machine"] = _MACHINE_KEYS[0]
if "pd_metric" not in st.session_state:
    st.session_state["pd_metric"] = _METRIC_KEYS[0]
if "pd_start" not in st.session_state:
    st.session_state["pd_start"] = (pd.Timestamp.now() - pd.Timedelta(days=1)).date()
if "pd_end" not in st.session_state:
    st.session_state["pd_end"] = pd.Timestamp.now().date()
if "pd_results" not in st.session_state:
    st.session_state["pd_results"] = None

# ── controls ──────────────────────────────────────────────────────────────────
ctrl_cols = st.columns([1.5, 1.5, 1.2, 1.2, 1.0])
with ctrl_cols[0]:
    st.selectbox("Select Machine", _MACHINE_KEYS, key="pd_machine")
with ctrl_cols[1]:
    st.selectbox("Select Data View", _METRIC_KEYS, key="pd_metric")
with ctrl_cols[2]:
    st.date_input("From Date", key="pd_start")
with ctrl_cols[3]:
    st.date_input("To Date", key="pd_end")
with ctrl_cols[4]:
    st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
    apply_clicked = st.button("Apply", type="primary")

# ── query (only on Apply click) ───────────────────────────────────────────────
if apply_clicked:
    _machine = st.session_state["pd_machine"]
    _metric_label = st.session_state["pd_metric"]
    _start_date = st.session_state["pd_start"]
    _end_date = st.session_state["pd_end"]
    _metric_config = METRIC_OPTIONS[_metric_label]
    _metric_column = _metric_config["column"]
    _metric_unit = _metric_config["unit"]

    with st.spinner(f"Querying {_machine}…"):
        df = fetch_data_by_date_range(get_all_machines()[_machine], _start_date, _end_date)

    if df.empty:
        st.session_state["pd_results"] = {
            "error": f"No historical telemetry found for {_machine} within the selected date range."
        }
    else:
        filtered_df = filter_valid_meter_rows(df)
        if filtered_df.empty:
            st.session_state["pd_results"] = {
                "error": "No valid meter packets found. All-zero/offline packets are ignored."
            }
        elif _metric_column not in filtered_df.columns:
            st.session_state["pd_results"] = {
                "error": f"{_metric_label} is not available for {_machine}."
            }
        else:
            series_df = filtered_df[["timestamp", _metric_column]].copy()
            series_df[_metric_column] = pd.to_numeric(series_df[_metric_column], errors="coerce").fillna(0.0)
            timestamps = series_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S").tolist()
            values = series_df[_metric_column].astype(float).tolist()
            result = get_matlab_analytics_service().process_series(
                timestamps, values, sample_interval=1.0,
                cache_key=("historical", _machine, _metric_column,
                           timestamps[-1] if timestamps else "empty", len(values)),
            )

            MAX_VISUAL_POINTS = 3000
            vis_ts = result.timestamps
            vis_raw = result.raw
            vis_filt = result.filtered
            vis_smooth = result.smoothed
            if len(vis_raw) > MAX_VISUAL_POINTS:
                step = len(vis_raw) // MAX_VISUAL_POINTS
                vis_ts = vis_ts[::step][:MAX_VISUAL_POINTS]
                vis_raw = vis_raw[::step][:MAX_VISUAL_POINTS]
                vis_filt = vis_filt[::step][:MAX_VISUAL_POINTS]
                vis_smooth = vis_smooth[::step][:MAX_VISUAL_POINTS]

            vis_fft_freq = result.fft_frequency
            vis_fft_mag = result.fft_magnitude
            if len(vis_fft_mag) > MAX_VISUAL_POINTS:
                fft_step = len(vis_fft_mag) // MAX_VISUAL_POINTS
                vis_fft_freq = vis_fft_freq[::fft_step][:MAX_VISUAL_POINTS]
                vis_fft_mag = vis_fft_mag[::fft_step][:MAX_VISUAL_POINTS]

            modes = compute_modes(result.filtered or result.raw)
            zero_only = bool(values) and all(abs(float(v)) < 1e-9 for v in values)

            table_snap = filtered_df.tail(50).copy()
            table_snap["timestamp"] = table_snap["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

            st.session_state["pd_results"] = {
                "metric_label": _metric_label,
                "metric_config": _metric_config,
                "metric_unit": _metric_unit,
                "avg": series_df[_metric_column].mean(),
                "peak": series_df[_metric_column].max(),
                "count": len(series_df),
                "table_df": table_snap,
                "html_payload": {
                    "timestamps": vis_ts,
                    "values": vis_raw,
                    "filtered": vis_filt,
                    "smoothed": vis_smooth,
                    "fft_frequency": vis_fft_freq,
                    "fft": vis_fft_mag,
                    "modes": modes,
                    "zero_only_signal": zero_only,
                },
            }

# ── render stored results ─────────────────────────────────────────────────────
res = st.session_state.get("pd_results")
if res is None:
    st.info("Select your machine, metric, and date range, then click **Apply**.")
elif "error" in res:
    st.warning(res["error"])
else:
    _unit_suffix = (" " + res["metric_unit"]) if res["metric_unit"] else ""
    metric_cols = st.columns(3)
    with metric_cols[0]:
        render_metric_card(
            f"{res['metric_label']} Average",
            f'{res["avg"]:.2f}{_unit_suffix}',
        )
    with metric_cols[1]:
        render_metric_card(
            f"{res['metric_label']} Peak",
            f'{res["peak"]:.2f}{_unit_suffix}',
        )
    with metric_cols[2]:
        render_metric_card("Samples Loaded", str(res["count"]))

    components.html(
        build_historical_dashboard_html(
            metric_title=res["metric_config"]["title"],
            unit=res["metric_unit"],
            engine="",
            payload=res["html_payload"],
        ),
        height=760,
        scrolling=False,
    )

    st.dataframe(res["table_df"], use_container_width=True, hide_index=True)

close_shell()
