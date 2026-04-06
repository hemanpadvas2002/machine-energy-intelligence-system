from config.settings import MACHINE_TABLE_MAPPING


def build_streaming_dashboard_html(default_machine: str, api_base_url: str, view_mode: str = "dashboard") -> str:
    machine_options = "".join(
        f'<option value="{machine}" {"selected" if machine == default_machine else ""}>{machine}</option>'
        for machine in MACHINE_TABLE_MAPPING.keys()
    )
    live_kpi_markup = """
        <section class="kpi-grid">
          <div class="panel"><div id="kpi-label-1" class="metric-label">Live Raw Value</div><div id="kpi-total-energy" class="metric-value">0.00</div><div id="kpi-foot-1" class="metric-foot">Current sample</div></div>
          <div class="panel"><div id="kpi-label-2" class="metric-label">Filtered Signal</div><div id="kpi-active-machines" class="metric-value">0.00</div><div id="kpi-foot-2" class="metric-foot">Savitzky-Golay output</div></div>
          <div class="panel"><div id="kpi-label-3" class="metric-label">Smoothed Signal</div><div id="kpi-average-load" class="metric-value">0.00</div><div id="kpi-foot-3" class="metric-foot">Gaussian smooth</div></div>
          <div class="panel"><div id="kpi-label-4" class="metric-label">Peak Signal</div><div id="kpi-peak-demand" class="metric-value">0.00</div><div id="kpi-foot-4" class="metric-foot">Within displayed window</div></div>
        </section>
    """
    dashboard_kpi_markup = """
        <section class="kpi-grid">
          <div class="panel"><div id="kpi-label-1" class="metric-label">Total Energy Consumption</div><div id="kpi-total-energy" class="metric-value">0</div><div id="kpi-foot-1" class="metric-foot">MWh equivalent snapshot</div></div>
          <div class="panel"><div id="kpi-label-2" class="metric-label">Active Machines</div><div id="kpi-active-machines" class="metric-value">0/0</div><div id="kpi-foot-2" class="metric-foot">Connected now</div></div>
          <div class="panel"><div id="kpi-label-3" class="metric-label">Average Load</div><div id="kpi-average-load" class="metric-value">0.0%</div><div id="kpi-foot-3" class="metric-foot">Across active units</div></div>
          <div class="panel"><div id="kpi-label-4" class="metric-label">Peak Demand</div><div id="kpi-peak-demand" class="metric-value">0.0 kW</div><div id="kpi-foot-4" class="metric-foot">Latest machine peak</div></div>
        </section>
    """
    legend_markup = """
            <div class="legend-row" id="variantButtons">
              <button class="variant-pill active" data-variant="all"><span class="legend-swatch" style="background:#0b7171;"></span>All</button>
              <button class="variant-pill" data-variant="raw"><span class="legend-swatch" style="background:#4b6e90;"></span>Raw</button>
              <button class="variant-pill" data-variant="filtered"><span class="legend-swatch" style="background:#0b7171;"></span>Filtered</button>
              <button class="variant-pill" data-variant="smoothed"><span class="legend-swatch" style="background:#5fd1d1;"></span>Smoothed</button>
            </div>
    """
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
        .dashboard {{
          display: grid;
          gap: 20px;
        }}
        .controls {{
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 16px;
          flex-wrap: wrap;
        }}
        .control-group {{
          display: flex;
          gap: 12px;
          flex-wrap: wrap;
        }}
        .control-select {{
          padding: 10px 14px;
          border-radius: 10px;
          border: 1px solid var(--line);
          background: var(--panel);
          color: var(--ink);
          font-weight: 600;
        }}
        .engine-badge {{
          background: rgba(11, 113, 113, 0.12);
          color: var(--teal);
          border-radius: 999px;
          font-size: 12px;
          padding: 8px 12px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.08em;
        }}
        .kpi-grid {{
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 18px;
        }}
        .panel {{
          background: var(--panel);
          border: 1px solid rgba(217, 225, 229, 0.9);
          border-radius: 16px;
          box-shadow: 0 6px 20px rgba(0,0,0,0.06);
          padding: 22px;
        }}
        .metric-label, .section-label {{
          color: var(--muted);
          text-transform: uppercase;
          letter-spacing: 0.18em;
          font-size: 11px;
          font-weight: 700;
        }}
        .metric-value {{
          font-family: "Space Grotesk", sans-serif;
          font-size: 44px;
          font-weight: 700;
          line-height: 1;
          margin-top: 14px;
        }}
        .metric-foot {{
          color: var(--muted);
          font-size: 14px;
          font-weight: 600;
          margin-top: 12px;
        }}
        .main-grid {{
          display: grid;
          grid-template-columns: minmax(0, 2.2fr) minmax(320px, 1fr);
          gap: 20px;
          align-items: stretch;
        }}
        .chart-panel {{
          min-height: 620px;
          display: flex;
          flex-direction: column;
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
        .variant-pill:hover {{
          transform: translateY(-1px);
        }}
        .legend-item {{
          display: inline-flex;
          align-items: center;
          gap: 8px;
          color: #526273;
          font-size: 13px;
          font-weight: 600;
        }}
        .legend-swatch {{
          width: 12px;
          height: 12px;
          border-radius: 999px;
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
        .status-table {{
          width: 100%;
          border-collapse: collapse;
        }}
        .status-table th {{
          text-align: left;
          color: var(--muted);
          text-transform: uppercase;
          letter-spacing: 0.14em;
          font-size: 11px;
          padding: 14px 0;
        }}
        .status-table td {{
          padding: 16px 0;
          border-top: 1px solid #edf2f5;
          font-size: 14px;
        }}
        .state-badge {{
          display: inline-block;
          border-radius: 999px;
          padding: 4px 10px;
          font-size: 11px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.08em;
        }}
        .state-optimal {{ background: rgba(11, 113, 113, 0.12); color: var(--teal); }}
        .state-idle {{ background: rgba(127, 144, 163, 0.16); color: #506273; }}
        @media (max-width: 900px) {{
          .kpi-grid, .main-grid {{ grid-template-columns: 1fr; }}
          .controls {{ justify-content: stretch; }}
          .control-group {{ width: 100%; }}
          .control-select {{ width: 100%; }}
        }}
      </style>
    </head>
    <body>
      <div class="dashboard">
        <div class="controls">
          <div class="control-group">
            <select id="machineSelect" class="control-select">{machine_options}</select>
            <select id="parameterSelect" class="control-select">
              <option value="total_kw" selected>Total KW</option>
              <option value="avg_current">Avg Current</option>
              <option value="avg_voltage_ln">Avg Voltage LN</option>
              <option value="avg_voltage_ll">Avg Voltage LL</option>
              <option value="total_net_kwh">Total Net KWh</option>
            </select>
          </div>
          <div id="engineBadge" class="engine-badge">Analytics Engine</div>
        </div>
        {live_kpi_markup if view_mode == "live" else dashboard_kpi_markup}
        <section class="main-grid">
          <div class="panel chart-panel">
            <div class="section-label">MATLAB Time-Series</div>
            <h3>Real-Time Load Frequency</h3>
            {legend_markup}
            <div class="chart-wrap"><canvas id="powerChart"></canvas></div>
            <div id="zeroWarning" class="warning"></div>
            <div class="fft-wrap">
              <div class="section-label">FFT Spectrum</div>
              <canvas id="fftChart"></canvas>
            </div>
          </div>
          <div class="panel">
            <div class="section-label">Operation Modules</div>
            <h3>Live Units</h3>
            <div id="modeList" class="mode-list"></div>
          </div>
        </section>
        <section class="panel">
          <div class="section-label">Unit Operational Status</div>
          <h3>Live Machine State</h3>
          <table class="status-table">
            <thead>
              <tr>
                <th>Machine ID</th>
                <th>Operational State</th>
                <th>Load (kW)</th>
                <th>Last Sync</th>
              </tr>
            </thead>
            <tbody id="statusRows"></tbody>
          </table>
        </section>
      </div>
      <script>
        Chart.register(window['chartjs-plugin-annotation']);

        const apiBaseUrl = "{api_base_url}";
        const state = {{
          machine: "{default_machine}",
          parameter: "total_kw",
          viewMode: "{view_mode}",
          variant: "all",
          chart: null,
          fftChart: null,
          kpiPolling: null,
          analyticsPolling: null,
          yMin: null,
          yMax: null,
        }};

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
                pointRadius: 0,
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
            animation: {{
              duration: 450,
              easing: 'easeOutCubic'
            }},
            interaction: {{ intersect: false, mode: 'index' }},
            plugins: {{
              legend: {{ display: false }},
              annotation: {{ annotations: {{}} }}
            }},
            scales: {{
              x: {{ grid: {{ display: false }}, ticks: {{ color: '#8ca0b6', maxTicksLimit: 6 }} }},
              y: {{ beginAtZero: true, grid: {{ color: 'rgba(217,225,229,0.5)' }}, ticks: {{ color: '#8ca0b6' }} }}
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
              pointRadius: 0,
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

        state.chart = timeseriesChart;
        state.fftChart = fftChart;

        function formatTime(iso) {{
          const date = new Date(iso);
          return date.toLocaleTimeString([], {{ hour: '2-digit', minute: '2-digit', second: '2-digit' }});
        }}

        function parameterMeta() {{
          const mapping = {{
            total_kw: {{ label: 'Load', unit: 'kW' }},
            avg_current: {{ label: 'Current', unit: 'A' }},
            avg_voltage_ln: {{ label: 'Voltage LN', unit: 'V' }},
            avg_voltage_ll: {{ label: 'Voltage LL', unit: 'V' }},
            total_net_kwh: {{ label: 'Net Energy', unit: 'kWh' }}
          }};
          return mapping[state.parameter] || {{ label: 'Signal', unit: '' }};
        }}

        function updateKpis(kpis) {{
          if (state.viewMode === 'live') return;
          document.getElementById('kpi-total-energy').textContent = Number(kpis.total_energy || 0).toFixed(0);
          document.getElementById('kpi-active-machines').textContent = `${{kpis.active_machines || 0}}/${{kpis.machine_count || 0}}`;
          document.getElementById('kpi-average-load').textContent = `${{Number(kpis.average_load || 0).toFixed(1)}}%`;
          document.getElementById('kpi-peak-demand').textContent = `${{Number(kpis.peak_demand || 0).toFixed(1)}} kW`;
        }}

        function updateRealtimeKpis(payload) {{
          if (state.viewMode !== 'live') return;
          const meta = parameterMeta();
          const rawValues = payload.values || [];
          const filteredValues = payload.filtered || [];
          const smoothedValues = payload.smoothed || [];
          const latestRaw = rawValues.length ? rawValues[rawValues.length - 1] : 0;
          const latestFiltered = filteredValues.length ? filteredValues[filteredValues.length - 1] : 0;
          const latestSmoothed = smoothedValues.length ? smoothedValues[smoothedValues.length - 1] : 0;
          const peakSignal = rawValues.length ? Math.max(...rawValues) : 0;

          document.getElementById('kpi-label-1').textContent = `Live ${{meta.label}} Raw`;
          document.getElementById('kpi-label-2').textContent = `Live ${{meta.label}} Filtered`;
          document.getElementById('kpi-label-3').textContent = `Live ${{meta.label}} Smoothed`;
          document.getElementById('kpi-label-4').textContent = `Peak ${{meta.label}}`;

          const unitSuffix = meta.unit ? ` ${{meta.unit}}` : '';
          document.getElementById('kpi-total-energy').textContent = `${{Number(latestRaw).toFixed(2)}}${{unitSuffix}}`;
          document.getElementById('kpi-active-machines').textContent = `${{Number(latestFiltered).toFixed(2)}}${{unitSuffix}}`;
          document.getElementById('kpi-average-load').textContent = `${{Number(latestSmoothed).toFixed(2)}}${{unitSuffix}}`;
          document.getElementById('kpi-peak-demand').textContent = `${{Number(peakSignal).toFixed(2)}}${{unitSuffix}}`;

          document.getElementById('kpi-foot-1').textContent = 'Current sample';
          document.getElementById('kpi-foot-2').textContent = 'Savitzky-Golay output';
          document.getElementById('kpi-foot-3').textContent = 'Gaussian smoothing';
          document.getElementById('kpi-foot-4').textContent = 'Within displayed window';
        }}

        function updateEngine(engine) {{
          const el = document.getElementById('engineBadge');
          el.textContent = engine === 'matlab' ? 'MATLAB Engine' : engine === 'scipy-fallback' ? 'SciPy Fallback' : 'Analytics Engine';
        }}

        function updateModes(modes, zeroOnlySignal) {{
          const list = document.getElementById('modeList');
          list.innerHTML = '';
          if (!modes.length) {{
            const note = document.createElement('div');
            note.className = 'warning';
            note.style.display = 'block';
            note.style.marginTop = '8px';
            note.textContent = zeroOnlySignal
              ? 'Only zero telemetry is available right now, so no valid MOD values can be computed.'
              : 'No mode values available for the selected range.';
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

        function updateStatusRows(rows) {{
          const tbody = document.getElementById('statusRows');
          tbody.innerHTML = '';
          rows.forEach((row) => {{
            const tr = document.createElement('tr');
            const badgeClass = row.state === 'Optimal' ? 'state-optimal' : 'state-idle';
            tr.innerHTML = `
              <td><strong>${{row.machine}}</strong></td>
              <td><span class="state-badge ${{badgeClass}}">${{row.state}}</span></td>
              <td>${{Number(row.load_kw || 0).toFixed(2)}}</td>
              <td>${{formatTime(row.last_sync)}}</td>
            `;
            tbody.appendChild(tr);
          }});
        }}

        function renderWarning(zeroOnlySignal) {{
          const warning = document.getElementById('zeroWarning');
          if (zeroOnlySignal) {{
            warning.style.display = 'block';
            warning.textContent = `${{state.machine}} is currently returning only 0.0 values for ${{state.parameter}}. MATLAB analytics will become meaningful once non-zero telemetry arrives.`;
          }} else {{
            warning.style.display = 'none';
            warning.textContent = '';
          }}
        }}

        function smoothAxis(allValues) {{
          if (!allValues.length) return;
          const localMin = Math.min(...allValues);
          const localMax = Math.max(...allValues);
          const span = Math.max(localMax - localMin, 0.05);
          const padding = Math.max(span * 0.18, 0.02);
          const targetMin = Math.max(0, localMin - padding);
          const targetMax = localMax + padding;

          if (state.yMin === null || state.yMax === null) {{
            state.yMin = targetMin;
            state.yMax = targetMax;
          }} else {{
            state.yMin = state.yMin * 0.84 + targetMin * 0.16;
            state.yMax = state.yMax * 0.84 + targetMax * 0.16;
          }}

          if (state.yMax - state.yMin < 0.05) {{
            state.yMax = state.yMin + 0.05;
          }}

          state.chart.options.scales.y.min = Number(state.yMin.toFixed(2));
          state.chart.options.scales.y.max = Number(state.yMax.toFixed(2));
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
          state.chart.options.plugins.annotation.annotations = annotations;
        }}

        function setVariant(variant) {{
          state.variant = variant;
          const datasetVisibility = {{
            all: [false, false, false],
            raw: [false, true, true],
            filtered: [true, false, true],
            smoothed: [true, true, false]
          }};
          const hiddenFlags = datasetVisibility[variant] || datasetVisibility.all;
          state.chart.data.datasets.forEach((dataset, index) => {{
            dataset.hidden = hiddenFlags[index];
          }});
          document.querySelectorAll('.variant-pill').forEach((button) => {{
            button.classList.toggle('active', button.dataset.variant === variant);
          }});
          state.chart.update('active');
        }}

        function updateTimeseries(payload) {{
          const labels = payload.timestamps.map(formatTime);
          state.chart.data.labels = labels;
          state.chart.data.datasets[0].data = payload.values || [];
          state.chart.data.datasets[1].data = payload.filtered || [];
          state.chart.data.datasets[2].data = payload.smoothed || [];
          updateAnnotations(payload.modes || []);
          smoothAxis([...(payload.values || []), ...(payload.filtered || []), ...(payload.smoothed || []), ...((payload.modes || []).map(mode => Number(mode.value || 0)))]);
          updateRealtimeKpis(payload);
          state.chart.update('active');
          updateModes(payload.modes || [], payload.zero_only_signal);
          renderWarning(payload.zero_only_signal);
          updateEngine(payload.engine);
          setVariant(state.variant);
        }}

        function updateFft(payload) {{
          state.fftChart.data.labels = (payload.fft_frequency || []).map((value) => Number(value).toFixed(2));
          state.fftChart.data.datasets[0].data = payload.fft || [];
          state.fftChart.update('active');
          updateEngine(payload.engine);
        }}

        async function fetchJson(path, params = {{}}) {{
          const url = new URL(`${{apiBaseUrl}}${{path}}`);
          Object.entries(params).forEach(([key, value]) => {{
            if (value !== undefined && value !== null) {{
              url.searchParams.set(key, value);
            }}
          }});
          const response = await fetch(url.toString(), {{ cache: 'no-store' }});
          if (!response.ok) throw new Error(`HTTP ${{response.status}}`);
          return response.json();
        }}

        async function refreshDashboard() {{
          try {{
            const payload = await fetchJson('/api/telemetry/dashboard', {{
              machine: state.machine,
              parameter: state.parameter
            }});
            updateKpis(payload.kpis || {{}});
            updateStatusRows(payload.machines || []);
          }} catch (error) {{
            console.error('Dashboard fetch failed', error);
          }}
        }}

        async function refreshAnalytics() {{
          try {{
            const [timeseriesPayload, fftPayload] = await Promise.all([
              fetchJson('/api/matlab/timeseries', {{ machine: state.machine, parameter: state.parameter, window: 60 }}),
              fetchJson('/api/matlab/fft', {{ machine: state.machine, parameter: state.parameter, window: 60 }})
            ]);
            updateTimeseries(timeseriesPayload);
            updateFft(fftPayload);
          }} catch (error) {{
            console.error('MATLAB analytics fetch failed', error);
          }}
        }}

        function schedulePolling() {{
          if (state.kpiPolling) window.clearInterval(state.kpiPolling);
          if (state.analyticsPolling) window.clearInterval(state.analyticsPolling);
          state.kpiPolling = window.setInterval(refreshDashboard, 1500);
          state.analyticsPolling = window.setInterval(refreshAnalytics, 3000);
        }}

        function resetCharts() {{
          state.yMin = null;
          state.yMax = null;
          state.chart.data.labels = [];
          state.chart.data.datasets.forEach((dataset) => dataset.data = []);
          state.fftChart.data.labels = [];
          state.fftChart.data.datasets[0].data = [];
          state.chart.update('none');
          state.fftChart.update('none');
        }}

        document.getElementById('machineSelect').addEventListener('change', (event) => {{
          state.machine = event.target.value;
          resetCharts();
          refreshDashboard();
          refreshAnalytics();
        }});

        document.getElementById('parameterSelect').addEventListener('change', (event) => {{
          state.parameter = event.target.value;
          resetCharts();
          refreshAnalytics();
        }});

        document.querySelectorAll('.variant-pill').forEach((button) => {{
          button.addEventListener('click', () => setVariant(button.dataset.variant));
        }});

        refreshDashboard();
        refreshAnalytics();
        schedulePolling();
      </script>
    </body>
    </html>
    """
