from flask import Flask, jsonify, request, render_template, abort
from flask_cors import CORS
from models import db, Thermostat, Reading, Schedule
from datetime import datetime, timedelta
import random

def create_app(db_path="sqlite:///thermo.db"):
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config['SQLALCHEMY_DATABASE_URI'] = db_path
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    CORS(app)
    db.init_app(app)

    @app.route("/")
    def index():
        return render_template("index.html")

    # --- API: thermostats list ---
    @app.route("/api/thermostats", methods=["GET"])
    def list_thermostats():
        ts = Thermostat.query.all()
        out = []
        for t in ts:
            out.append({
                "id": t.id,
                "name": t.name,
                "location": t.location,
                "setpoint": t.current_setpoint,
                "is_on": t.is_on
            })
        return jsonify(out)

    # --- API: single thermostat ---
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

    # --- API: set setpoint ---
    @app.route("/api/thermostats/<int:t_id>/setpoint", methods=["POST"])
    def set_setpoint(t_id):
        t = Thermostat.query.get_or_404(t_id)
        body = request.json or {}
        try:
            sp = float(body.get("setpoint"))
        except Exception:
            return abort(400, "setpoint required")
        t.current_setpoint = sp
        db.session.add(t)
        # log a reading (placeholder temperature random)
        r = Reading(thermostat_id=t.id, temperature=sp + random.uniform(-1.5, 1.5), setpoint=sp, is_on=t.is_on)
        db.session.add(r)
        db.session.commit()
        return jsonify({"ok": True, "setpoint": sp})

    # --- API: toggle on/off ---
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

    # --- API: get history for chart (returns last N points) ---
    @app.route("/api/thermostats/<int:t_id>/history", methods=["GET"])
    def history(t_id):
        t = Thermostat.query.get_or_404(t_id)
        # number of points
        n = int(request.args.get("n", 48))
        rows = Reading.query.filter_by(thermostat_id=t.id).order_by(Reading.timestamp.desc()).limit(n).all()
        rows.reverse()
        return jsonify([{
            "timestamp": r.timestamp.isoformat(),
            "temperature": r.temperature,
            "setpoint": r.setpoint,
            "is_on": r.is_on
        } for r in rows])

    # --- API: schedules (basic CRUD) ---
    @app.route("/api/thermostats/<int:t_id>/schedules", methods=["GET","POST"])
    def schedules(t_id):
        t = Thermostat.query.get_or_404(t_id)
        if request.method == "GET":
            s = Schedule.query.filter_by(thermostat_id=t.id).all()
            return jsonify([{
                "id": sch.id,
                "weekday_mask": sch.weekday_mask,
                "time_h": sch.time_h,
                "time_m": sch.time_m,
                "setpoint": sch.setpoint,
                "enabled": sch.enabled
            } for sch in s])
        else:
            body = request.json or {}
            sch = Schedule(
                thermostat_id = t.id,
                weekday_mask = int(body.get("weekday_mask", 127)),
                time_h = int(body.get("time_h", 7)),
                time_m = int(body.get("time_m", 0)),
                setpoint = float(body.get("setpoint", t.current_setpoint)),
                enabled = bool(body.get("enabled", True))
            )
            db.session.add(sch)
            db.session.commit()
            return jsonify({"ok": True, "id": sch.id})

        # --- API: get settings for a thermostat ---
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

    # --- API: update settings (partial allowed) ---
    @app.route("/api/thermostats/<int:t_id>/settings", methods=["POST"])
    def update_settings(t_id):
        t = Thermostat.query.get_or_404(t_id)
        body = request.json or {}

        # Helper to parse floats safely
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

        # boolean
        if "away_mode" in body:
            t.away_mode = bool(body["away_mode"])

        # validation: sensible ranges
        if t.min_temp >= t.max_temp:
            abort(400, "min_temp must be less than max_temp")
        if not ( -50.0 <= t.min_temp <= 100.0 and -50.0 <= t.max_temp <= 100.0):
            abort(400, "temperatures must be in a reasonable range")

        # clamp current setpoint into allowed range
        if t.current_setpoint < t.min_temp:
            t.current_setpoint = t.min_temp
        if t.current_setpoint > t.max_temp:
            t.current_setpoint = t.max_temp

        db.session.add(t)
        db.session.commit()
        return jsonify({"ok": True})

    @app.route("/settings/<int:t_id>")
    def settings_page(t_id):
        # render template — the page will call the API to load/save
        return render_template("settings.html")


    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
