# app.py
from flask import Flask, render_template, request, redirect, jsonify
from mqtt_bridge import MqttBridge, THERMOSTATS

app = Flask(__name__)
mqtt = MqttBridge()

@app.route("/")
def index():
    return render_template("index.html", thermostats=THERMOSTATS)

@app.route("/api/state")
def api_state():
    return jsonify(mqtt.get_dashboard_state())

@app.route("/thermostat/<thermo_id>/setpoint", methods=["POST"])
def set_setpoint(thermo_id):
    # IMPORTANT: do NOT redirect. Front-end uses fetch() and we want NO page reload.
    mqtt.publish_setpoint(thermo_id, float(request.form["setpoint"]))
    return ("", 204)

@app.route("/thermostat/<thermo_id>/settings", methods=["GET", "POST"])
def settings(thermo_id):
    if request.method == "POST":
        new_settings = {
            "hysteresis": float(request.form["hysteresis"]),
            "steps_on": int(request.form["steps_on"]),
            "steps_off": int(request.form["steps_off"]),
            "presets": {
                "Home": float(request.form["preset_home"]),
                "Sleep": float(request.form["preset_sleep"]),
                "Away": float(request.form["preset_away"]),
            }
        }
        mqtt.publish_settings(thermo_id, new_settings)
        return redirect(f"/thermostat/{thermo_id}/settings")

    current = mqtt.get_thermostat(thermo_id).get("settings", {})
    return render_template("settings.html", thermo_id=thermo_id, settings=current)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
