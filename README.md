# Custom Smart Thermostat

A scalable, self-hosted smart thermostat system built with **Python**, **Flask**, and **Raspberry Pi**.  
Designed to retrofit existing “dumb” thermostats by mechanically turning their knobs, while providing a modern mobile-friendly web interface.

---

## Architecture Overview

```
iPhone / Browser
        |
        |  WireGuard VPN
        |
Flask Dashboard (PC / Raspberry Pi 4)
        |
        |  REST API
        |
Multiple Raspberry Pi Zero Thermostats
```

---

## Components

### Central Controller
- Flask web application
- SQLite database
- Mobile-first UI (iPhone Safari friendly)
- Runs on Windows/macOS (development) or Raspberry Pi 4 (production)

### Thermostat Nodes (Raspberry Pi Zero W)
- Read temperature sensors
- Control heater motor/relay
- Report temperature and state
- Pull setpoints and settings from server

### Networking
- Secure remote access via WireGuard VPN
- No public internet exposure

---

## Features

### Thermostat Control
- Set temperature setpoint
- View on/off state
- Eco / Away mode

### Per-Thermostat Settings
- Hysteresis (on/off tolerance)
- Minimum and maximum allowed temperatures
- Eco (away) setpoint
- Safety clamping of values

### Planned
- Scheduling
- Temperature and state graphs
- Google Home / Home Assistant integration

---

## Technology Stack

- Python 3.10+
- Flask
- Flask-SQLAlchemy
- SQLite
- Bootstrap 5
- WireGuard VPN

---

## Running Locally (Windows / macOS)

### 1. Clone repository

```bash
git clone https://github.com/yourname/CustomSmartThermostat.git
cd CustomSmartThermostat
```

### 2. Create virtual environment

```bash
python -m venv venv
```

Activate:

**Windows (cmd)**
```cmd
venv\Scripts\activate
```

**Linux / macOS**
```bash
source venv/bin/activate
```

---

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

---

### 4. Initialize database

⚠️ Development only — this recreates the database.

```bash
python schema_init.py
```

---

### 5. Run the server

```bash
python app.py
```

Open in browser:

```
http://127.0.0.1:5000
```

---

## Using the Web Interface

- Home page shows all thermostats
- Each thermostat card allows:
  - Setpoint adjustment
  - Viewing current state
  - Opening **Settings**
- Settings page allows:
  - Hysteresis configuration
  - Min/max temperature limits
  - Eco / Away mode

UI is optimized for mobile use.

---

## Running on Raspberry Pi (Production)

### 1. Install OS
- Raspberry Pi OS Lite
- Enable SSH

### 2. Install system dependencies

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip git
```

### 3. Clone and setup

```bash
git clone https://github.com/yourname/CustomSmartThermostat.git
cd CustomSmartThermostat
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Initialize DB and run

```bash
python schema_init.py
python app.py
```

Access from LAN or VPN:

```
http://<pi-ip>:5000
```

---

## Control Logic

```
target = eco_setpoint if away_mode else setpoint

Heater ON  if temperature <= target - hysteresis_down
Heater OFF if temperature >= target + hysteresis_up
```

Minimum and maximum temperature limits are always enforced.

---

## Security

- Remote access via WireGuard VPN
- No exposed public ports
- API currently unauthenticated (VPN required)

---

## Future Improvements

- Graphing (Chart.js)
- Scheduler engine
- Presence detection
- Authentication
- OTA updates for thermostat nodes

---

## Disclaimer

This project controls heating equipment.  
Always implement hardware failsafes and manual overrides.
