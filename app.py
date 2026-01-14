from flask import Flask, render_template, request, redirect, url_for
from mqtt_bridge import MqttBridge, thermostat_state

app = Flask(__name__)

# Start MQTT bridge immediately
mqtt = MqttBridge()


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            new_setpoint = float(request.form["setpoint"])
            mqtt.publish_setpoint(new_setpoint)
        except ValueError:
            pass

        return redirect(url_for("index"))

    return render_template(
        "index.html",
        thermostat=thermostat_state
    )


if __name__ == "__main__":
    # Accessible from phone on same network
    app.run(host="0.0.0.0", port=5000, debug=True)
