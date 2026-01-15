from flask import Flask, render_template, request, redirect, jsonify
from mqtt_bridge import MqttBridge

app = Flask(__name__)
mqtt = MqttBridge()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/state")
def api_state():
    return jsonify(mqtt.get_state())

@app.route("/setpoint", methods=["POST"])
def set_setpoint():
    mqtt.publish_setpoint(float(request.form["setpoint"]))
    return redirect("/")

@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        mqtt.publish_settings({
            "hysteresis": float(request.form["hysteresis"]),
            "steps_on": int(request.form["steps_on"]),
            "steps_off": int(request.form["steps_off"])
        })
        return redirect("/settings")

    return render_template("settings.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
