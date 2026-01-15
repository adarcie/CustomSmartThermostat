# Custom Smart Thermostat

A DIY smart thermostat system that clips onto existing “dumb” thermostats and turns the physical knob using a stepper motor.

The system is designed to be:
- modular (many thermostats, one dashboard),
- LAN-first (no cloud required),
- iPhone-friendly (mobile web UI),
- safe to iterate (motor calibration and limits come later).

---

## High-level Architecture

```
┌───────────────┐        MQTT         ┌─────────────────────┐
│ Flask Dashboard│  ◀──────────────▶  │  Thermostat Node(s) │
│ (Windows PC)   │                   │  (Pi 4 / Pi Zero)   │
│                │                   │                     │
│ - Web UI       │                   │ - Temperature read  │
│ - Graphs       │                   │ - Stepper motor     │
│ - Scheduling   │                   │ - Control logic     │
└───────────────┘                   └─────────────────────┘
                     ▲
                     │
              Mosquitto Broker
               (running on Pi 4)
```

- **PC (Windows)** runs Flask + database + MQTT client
- **Pi 4 (initially)** runs:
  - Mosquitto MQTT broker
  - Thermostat node (motor + temperature)
- **Pi Zero / Pi Nano (later)** will replace the Pi 4 thermostat node
- Communication is **MQTT over LAN**
- Control is via **mobile web app** (Safari on iPhone)

---

## Repository Structure (important)

```
CustomSmartThermostat/
├── app.py                  # Flask app (dashboard + API)
├── mqtt_bridge.py          # Flask ↔ MQTT bridge
├── models.py               # SQLAlchemy models
├── schema_init.py          # DB init helper
├── templates/
│   ├── index.html          # Main dashboard UI
│   └── settings.html       # Settings page
├── static/
│   └── (optional assets)
├── thermostat/
│   ├── thermostat_node.py  # Runs on Pi (main loop)
│   ├── stepper.py          # Stepper motor control
│   ├── temperature.py      # Temperature sensor abstraction
│   └── requirements.txt    # Pi-side Python deps (pip)
└── README.md
```

---

# PART 1 — Windows PC (Flask Dashboard)

## Requirements
- Windows 10/11
- Python **3.10 – 3.12** (recommended)
- Git

> ⚠️ Python 3.14 is very new — if you hit odd issues, downgrade to 3.12.

---

## 1. Clone the repo

```powershell
git clone https://github.com/yourname/CustomSmartThermostat.git
cd CustomSmartThermostat
```

---

## 2. Create and activate a virtual environment

```powershell
python -m venv venv
venv\Scripts\activate
```

You should see:
```
(venv)
```

---

## 3. Install PC-side dependencies

```powershell
pip install flask flask-cors flask-sqlalchemy paho-mqtt
```

---

## 4. Configure MQTT broker IP

Edit `mqtt_bridge.py` and set:

```python
BROKER_IP = "192.168.x.x"  # IP address of the Pi running Mosquitto
```

---

## 5. Initialize the database (first run only)

```powershell
python schema_init.py
```

This creates:
- `thermo.db`
- a default thermostat
- sample historical data

---

## 6. Run the Flask app

```powershell
python app.py
```

Visit from:
- PC: `http://127.0.0.1:5000`
- Phone (same LAN): `http://<PC_IP>:5000`

---

# PART 2 — Pi 4 (MQTT Broker + Thermostat Node)

These instructions assume **Raspberry Pi OS Bookworm**.

---

## A. System setup (Pi 4)

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip \
                    mosquitto mosquitto-clients \
                    python3-rpi.gpio
```

---

## B. Configure Mosquitto (CRITICAL)

### 1. Create listener config

```bash
sudo nano /etc/mosquitto/conf.d/listener.conf
```

Paste:

```
listener 1883 0.0.0.0
allow_anonymous true
```

Save and exit.

---

### 2. Restart and verify

```bash
sudo systemctl restart mosquitto
ss -lntp | grep 1883
```

You **must** see:

```
0.0.0.0:1883
```

---

## C. Thermostat node setup (Pi 4)

### 1. Copy thermostat code

```bash
mkdir ~/thermostat
cd ~/thermostat
# copy thermostat_node.py, stepper.py, temperature.py here
```

---

### 2. Create virtual environment (IMPORTANT)

Because Bookworm blocks system pip installs:

```bash
python3 -m venv venv --system-site-packages
source venv/bin/activate
```

> `--system-site-packages` is REQUIRED so the venv can see `RPi.GPIO`

---

### 3. Install Python deps

```bash
pip install paho-mqtt
```

Do **NOT** install `RPi.GPIO` via pip — it comes from apt.

---

### 4. Run the thermostat node

```bash
python3 thermostat_node.py
```

You should see:
- MQTT connected
- temperature publishing
- setpoint updates logged when changed from the dashboard

---

## D. Testing MQTT manually (recommended)

On Pi:
```bash
mosquitto_sub -t "thermostat/#" -v
```

On PC:
```powershell
mosquitto_pub -h <PI_IP> -t thermostat/test/setpoint -m 22.5
```

---

# PART 3 — Stepper Motor Notes

- Controlled via `stepper.py`
- Supports:
  - discrete steps (forward/backward),
  - continuous motion,
  - safe coil release.
- Direction bugs were fixed by using explicit reversed step sequences.
- GPIO pin mapping is **BCM-based** and identical on Pi 4 and Pi Zero.

---

# PART 4 — Pi Zero / Pi Nano Migration (Later)

When moving from Pi 4 → Pi Zero / Nano:

What stays the same:
- Python code
- MQTT topics
- Flask dashboard
- Motor logic

What changes:
- Physical wiring
- Possibly power supply
- GPIO headers (may need soldering)

Steps:
1. Install Raspberry Pi OS
2. Install:
   ```bash
   sudo apt install python3-venv python3-rpi.gpio
   ```
3. Copy thermostat folder
4. Recreate venv with `--system-site-packages`
5. Run `thermostat_node.py`

---

## Common Pitfalls (Read This)

- ❌ `pip install` fails on Pi → use a venv
- ❌ `RPi.GPIO` not found → recreate venv with `--system-site-packages`
- ❌ MQTT connection refused → Mosquitto not listening on `0.0.0.0`
- ❌ Temperature not shown → MQTT ID mismatch (string vs DB id)
- ❌ Setpoint unreliable → dashboard sending duplicate requests (fixed)

---

## Roadmap / Next Steps

- Motor calibration with limit switches
- Setpoint → motor position mapping
- Acknowledged MQTT commands (ACK/NACK)
- Offline detection / heartbeat
- Scheduling engine
- Auto-start services on boot

---

## License

DIY / personal use.  
Use at your own risk — especially when controlling heating equipment.
