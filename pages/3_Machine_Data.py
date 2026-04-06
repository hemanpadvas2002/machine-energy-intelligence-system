import json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from config.settings import MACHINE_TABLE_MAPPING
from services.matlab_analytics import get_matlab_analytics_service
from ui.amtdc import apply_page_config, close_shell, inject_styles, render_shell, render_sidebar
from utils.db_handler import fetch_data_from_postgres


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
          background: rgba(164, 116, 0, 0.12);
          color: #805b00;
          font-weight: 600;
          display: none;
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

        document.getElementById('zeroWarning').style.display = payload.zero_only_signal ? 'block' : 'none';
        document.getElementById('zeroWarning').textContent = payload.zero_only_signal
          ? 'Only zero telemetry is available in this historical range, so the MATLAB trace is flat.'
          : '';

        renderCharts();
        setVariant('all');
      </script>
    </body>
    </html>
    """


selector_cols = st.columns(2)
with selector_cols[0]:
    machine = st.selectbox("Select Machine", list(MACHINE_TABLE_MAPPING.keys()), index=0)
with selector_cols[1]:
    metric_label = st.selectbox("Select Data View", list(METRIC_OPTIONS.keys()), index=0)

metric_config = METRIC_OPTIONS[metric_label]
metric_column = metric_config["column"]
metric_unit = metric_config["unit"]

df = fetch_data_from_postgres(MACHINE_TABLE_MAPPING[machine])

if df.empty:
    st.warning(f"No PostgreSQL data is available for {machine}.")
    close_shell()
    st.stop()

date_cols = st.columns(2)
with date_cols[0]:
    start_date = st.date_input("From Date", value=df["timestamp"].min().date())
with date_cols[1]:
    end_date = st.date_input("To Date", value=df["timestamp"].max().date())

filtered_df = df[
    (df["timestamp"].dt.date >= start_date)
    & (df["timestamp"].dt.date <= end_date)
].copy()

if filtered_df.empty:
    st.warning("No data found for the selected timeline.")
    close_shell()
    st.stop()

if metric_column not in filtered_df.columns:
    st.warning(f"{metric_label} is not available for {machine}.")
    close_shell()
    st.stop()

series_df = filtered_df[["timestamp", metric_column]].copy()
series_df[metric_column] = pd.to_numeric(series_df[metric_column], errors="coerce").fillna(0.0)

timestamps = series_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S").tolist()
values = series_df[metric_column].astype(float).tolist()
result = get_matlab_analytics_service().process_series(
    timestamps,
    values,
    sample_interval=1.0,
    cache_key=("historical", machine, metric_column, timestamps[-1] if timestamps else "empty", len(values)),
)

modes = compute_modes(result.filtered or result.raw)
zero_only_signal = bool(values) and all(abs(float(value)) < 1e-9 for value in values)

metric_cols = st.columns(3)
with metric_cols[0]:
    render_metric_card(
        f"{metric_label} Average",
        f'{series_df[metric_column].mean():.2f}{f" {metric_unit}" if metric_unit else ""}',
    )
with metric_cols[1]:
    render_metric_card(
        f"{metric_label} Peak",
        f'{series_df[metric_column].max():.2f}{f" {metric_unit}" if metric_unit else ""}',
    )
with metric_cols[2]:
    render_metric_card("Samples Loaded", str(len(series_df)))

components.html(
    build_historical_dashboard_html(
        metric_title=metric_config["title"],
        unit=metric_unit,
        engine=result.engine,
        payload={
            "timestamps": result.timestamps,
            "values": result.raw,
            "filtered": result.filtered,
            "smoothed": result.smoothed,
            "fft_frequency": result.fft_frequency,
            "fft": result.fft_magnitude,
            "modes": modes,
            "zero_only_signal": zero_only_signal,
        },
    ),
    height=760,
        scrolling=False,
)

table_df = filtered_df.tail(50).copy()
table_df["timestamp"] = table_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
st.dataframe(table_df, use_container_width=True, hide_index=True)

close_shell()
