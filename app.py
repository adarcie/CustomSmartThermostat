# app.py (full — replace existing)
from flask import Flask, jsonify, request, render_template, abort
from flask_cors import CORS
from models import db, Thermostat, Reading, Schedule
from datetime import datetime, timedelta
import random
from mqtt_bridge import MqttBridge

mqtt = MqttBridge()

def _normalize_name_key(name):
    if not name:
        return ""
    return "".join(name.lower().split())

def find_db_for_tid(tid):
    """Try to map an MQTT thermostat id (string or numeric) to a DB thermostat.
    Returns (db_id or None, Thermostat instance or None)
    """
    # try numeric id
    try:
        nid = int(tid)
        tdb = Thermostat.query.get(nid)
        if tdb:
            return nid, tdb
    except Exception:
        pass

    # try exact name match
    all_ts = Thermostat.query.all()
    tid_norm = _normalize_name_key(tid)
    for t in all_ts:
        if t.name and _normalize_name_key(t.name) == tid_norm:
            return t.id, t

    # try substring match
    for t in all_ts:
        if t.name and tid_norm in _normalize_name_key(t.name):
            return t.id, t

    return None, None

def create_app(db_path="sqlite:///thermo.db"):
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config['SQLALCHEMY_DATABASE_URI'] = db_path
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    CORS(app)
    db.init_app(app)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/thermostats")
    def list_thermostats():
        result = []

        # If we have MQTT data, include it first (scales to many devices)
        if getattr(mqtt, "temps", None):
            for tid, temp in mqtt.temps.items():
                state = mqtt.states.get(tid, {})
                db_id, db_obj = find_db_for_tid(tid)
                result.append({
                    # id is the MQTT id (string); db_id is numeric DB id when available
                    "id": tid,
                    "db_id": db_id,
                    "name": db_obj.name if db_obj else f"Thermostat {tid}",
                    "location": db_obj.location if db_obj else "Unknown",
                    "temperature": temp,
                    "setpoint": state.get("setpoint", db_obj.current_setpoint if db_obj else 20.0),
                    "heating": state.get("heating", False)
                })

        # If no MQTT data (or as fallback), include DB thermostats
        if not result:
            db_thermostats = Thermostat.query.all()
            for t in db_thermostats:
                simulated_temp = t.current_setpoint + random.uniform(-2, 2)
                result.append({
                    "id": str(t.id),          # keep id as string for consistency
                    "db_id": t.id,
                    "name": t.name,
                    "location": t.location,
                    "temperature": simulated_temp,
                    "setpoint": t.current_setpoint,
                    "heating": t.is_on and simulated_temp < t.current_setpoint
                })

        return jsonify(result)

    # Flexible history endpoint: supports numeric DB id or MQTT id
    @app.route("/api/thermostats/<path:tid>/history", methods=["GET"])
    def history_by_tid(tid):
        # allow ?n= parameter
        n = int(request.args.get("n", 48))
        # try map to DB id
        db_id, db_obj = find_db_for_tid(tid)
        if db_id:
            rows = Reading.query.filter_by(thermostat_id=db_id).order_by(Reading.timestamp.desc()).limit(n).all()
            rows.reverse()
            return jsonify([{
                "timestamp": r.timestamp.isoformat(),
                "temperature": r.temperature,
                "setpoint": r.setpoint,
                "is_on": r.is_on
            } for r in rows])
        # no DB history available for this MQTT-only thermostat -> return empty or synthetic
        return jsonify([])

    # --- API: single thermostat (DB) ---
    @app.route("/api/thermostats/<int:t_id>", methods=["GET"])
    def get_thermostat(t_id):
        t = Thermostat.query.get_or_404(t_id)
        return jsonify({
            "id": t.id,
            "name": t.name,
            "location": t.location,
            "setpoint": t.current_setpoint,
            "is_on": t.is_on
        })

    # --- API: set setpoint (flexible tid; tid may be MQTT id string or numeric) ---
    @app.route("/api/thermostats/<path:tid>/setpoint", methods=["POST"])
    def set_setpoint(tid):
        body = request.json or {}
        if "setpoint" not in body:
            return abort(400, "setpoint required")
        try:
            value = float(body["setpoint"])
        except Exception:
            return abort(400, "invalid setpoint")
        # publish via MQTT; mqtt.set_setpoint should publish to thermostat/<tid>/setpoint
        mqtt.set_setpoint(tid, value)
        return jsonify({"ok": True})

    # --- API: toggle on/off (DB) ---
    @app.route("/api/thermostats/<int:t_id>/toggle", methods=["POST"])
    def toggle(t_id):
        t = Thermostat.query.get_or_404(t_id)
        body = request.json or {}
        if "is_on" in body:
            t.is_on = bool(body["is_on"])
        else:
            t.is_on = not t.is_on
        db.session.add(t)
        r = Reading(thermostat_id=t.id, temperature= t.current_setpoint + random.uniform(-2,2),
                    setpoint=t.current_setpoint, is_on=t.is_on)
        db.session.add(r)
        db.session.commit()
        return jsonify({"ok": True, "is_on": t.is_on})

    # --- API: get settings for a thermostat (DB) ---
    @app.route("/api/thermostats/<int:t_id>/settings", methods=["GET"])
    def get_settings(t_id):
        t = Thermostat.query.get_or_404(t_id)
        return jsonify({
            "hysteresis_up": t.hysteresis_up,
            "hysteresis_down": t.hysteresis_down,
            "min_temp": t.min_temp,
            "max_temp": t.max_temp,
            "eco_setpoint": t.eco_setpoint,
            "away_mode": t.away_mode
        })

    # --- API: update settings (DB) ---
    @app.route("/api/thermostats/<int:t_id>/settings", methods=["POST"])
    def update_settings(t_id):
        t = Thermostat.query.get_or_404(t_id)
        body = request.json or {}

        def getf(key, current):
            if key in body:
                try:
                    return float(body[key])
                except Exception:
                    abort(400, f"{key} must be a number")
            return current

        t.hysteresis_up = getf("hysteresis_up", t.hysteresis_up)
        t.hysteresis_down = getf("hysteresis_down", t.hysteresis_down)
        t.min_temp = getf("min_temp", t.min_temp)
        t.max_temp = getf("max_temp", t.max_temp)
        t.eco_setpoint = getf("eco_setpoint", t.eco_setpoint)

        if "away_mode" in body:
            t.away_mode = bool(body["away_mode"])

        if t.min_temp >= t.max_temp:
            abort(400, "min_temp must be less than max_temp")
        if not (-50.0 <= t.min_temp <= 100.0 and -50.0 <= t.max_temp <= 100.0):
            abort(400, "temperatures must be in a reasonable range")

        if t.current_setpoint < t.min_temp:
            t.current_setpoint = t.min_temp
        if t.current_setpoint > t.max_temp:
            t.current_setpoint = t.max_temp

        db.session.add(t)
        db.session.commit()
        return jsonify({"ok": True})

    @app.route("/settings/<int:t_id>")
    def settings_page(t_id):
        return render_template("settings.html")

    return app


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
        if Thermostat.query.count() == 0:
            default_thermo = Thermostat(
                name="Living Room",
                location="Main Floor",
                current_setpoint=20.0,
                is_on=True,
                hysteresis_up=0.5,
                hysteresis_down=0.5,
                min_temp=16.0,
                max_temp=26.0,
                eco_setpoint=18.0,
                away_mode=False
            )
            db.session.add(default_thermo)
            for i in range(48):
                reading = Reading(
                    thermostat_id=1,
                    temperature=20.0 + random.uniform(-1, 1),
                    setpoint=20.0,
                    is_on=True,
                    timestamp=datetime.now() - timedelta(minutes=i*30)
                )
                db.session.add(reading)
            db.session.commit()
            print("Created default thermostat with sample data")
    app.run(host="0.0.0.0", port=5000, debug=True)
