# Machine Energy Intelligence System

## Quick Start

```bash
# 1. Create virtual environment and install dependencies
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / Mac

pip install -r requirements.txt

# 2. (Windows) Double-click START.bat
#    OR run directly:
python START.py
```

The dashboard opens at **http://localhost:8501**

### Galaxy_CNC Network Mode

To switch Galaxy_CNC between LAN and direct-link mode, edit `config/settings.py`:

- **Office LAN:** `"host": "192.168.1.182"` and `"port": 522`  
- **Direct cable (APIPA):** `"host": "169.254.92.218"` and `"port": 520`

### Modbus Reads Returning Zeros?

Open the **SELC AC-S2E web configurator** at the device IP → **Serial Port** tab:
- Set Baud Rate: **9600**
- Parity: **Even**
- Stop bits: **1**
- Mode: **RTU**

These must match the power meter's RS-485 configuration.

---

## Overview

This project focuses on monitoring and analysing machine-level power consumption to build intelligent insights around energy usage.

The system is designed to track voltage, current, and power consumption of machines in real-time, and use that data to predict future energy usage, detect anomalies, and enable predictive maintenance.

It also helps estimate the operational cost of running machines — from simple appliances like air conditioners to heavy industrial machinery used in manufacturing.

---

## Problem Statement

In most systems today, electricity cost is estimated roughly rather than measured precisely at the machine level.

This leads to:

* Inaccurate cost estimation in manufacturing
* Inefficient energy usage
* Unexpected machine failures
* Poor visibility into operational expenses

---

## Solution

This system introduces a data-driven approach to:

* Monitor real-time machine energy consumption
* Analyse usage patterns
* Predict future consumption trends
* Enable predictive maintenance
* Calculate accurate electricity costs per operation

---

## Key Features

* Real-time voltage and power monitoring
* Machine-level energy tracking
* Predictive analytics for consumption
* Cost estimation for operations
* Scalable for both small and industrial use cases

---

## Use Cases

* Cost estimation for manufacturing processes
* Monitoring AC or equipment usage in buildings
* Industrial energy optimisation
* Predictive maintenance for machinery
* Smart energy auditing

---

## Future Scope

* Integration with IoT sensors
* Machine learning models for prediction
* Automated alerts for anomalies
* Dashboard for real-time analytics
* Integration with ERP / industrial systems

---

## Status

Work in progress — actively being developed and expanded.

---

## LAN HTTPS hosting

This project is a Streamlit portal with a Python telemetry API, so the LAN setup maps the usual frontend/backend checklist to:

* Portal: `https://<server-ip>:8501/Live_Data`
* Telemetry API: `https://<server-ip>:8765/api/telemetry/dashboard`
* PM2 process: `digital-transformation-portal`

### Setup steps

1. Verify the server tools:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check_lan_https_prereqs.ps1
   ```

2. Install PM2 if it is missing:

   ```powershell
   npm install -g pm2
   ```

3. Generate or refresh the self-signed LAN certificate:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\create_streamlit_https_cert.ps1
   ```

4. If Windows Firewall blocks access from another computer, run PowerShell as Administrator and allow LAN-only access to ports `8501` and `8765`:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\enable_streamlit_firewall.ps1
   ```

5. Start with PM2:

   ```powershell
   pm2 start ecosystem.config.js
   pm2 save
   ```

6. Reload safely after code changes:

   ```powershell
   pm2 reload digital-transformation-portal
   ```

7. Open from another computer on the same Wi-Fi:

   ```text
   https://192.168.1.37:8501/Live_Data
   ```

### Config snippets

Streamlit HTTPS is configured in `.streamlit/config.toml`:

```toml
[server]
address = "0.0.0.0"
port = 8501
sslCertFile = "certs/server.crt"
sslKeyFile = "certs/server.key"
```

PM2 starts the existing Python entrypoint without changing the app framework:

```javascript
module.exports = {
  apps: [
    {
      name: "digital-transformation-portal",
      script: "launch.py",
      interpreter: "python",
    },
  ],
};
```

### Security checks

* HTTPS is enforced on the portal and telemetry API; plain HTTP connections on those ports are rejected.
* TLS 1.3 is enforced for the telemetry API, and the portal negotiates TLS 1.3 with modern clients.
* The generated certificate includes `localhost`, `127.0.0.1`, the computer name, and the LAN IPv4 address as certificate SANs.
* `certs/server.key` is private. Do not share it.
* Share only `certs/server.crt` with client devices. Import it into Trusted Root Certification Authorities to avoid browser warnings.
* Firewall rules are restricted to the Private network profile and `LocalSubnet`.

If this computer gets a different Wi-Fi IP address later, rerun `scripts\create_streamlit_https_cert.ps1`, restart PM2, and use the new URL printed by the script.

---

## Vision

To build a system where energy is not just consumed, but understood, optimised, and predicted.
