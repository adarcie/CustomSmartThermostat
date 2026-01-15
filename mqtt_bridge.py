import json
import paho.mqtt.client as mqtt

BROKER_IP = "192.168.4.26"
THERMO_ID = "livingroom"

class MqttBridge:
    def __init__(self):
        self.state = {
            "temperature": None,
            "setpoint": None,
            "heating": False
        }

        self.client = mqtt.Client(client_id="flask-dashboard")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(BROKER_IP, 1883, 60)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        print("Flask connected to MQTT, rc =", rc)
        client.subscribe(f"thermostat/{THERMO_ID}/#")

    def on_message(self, client, userdata, msg):
        if msg.topic.endswith("/temperature"):
            self.state["temperature"] = json.loads(msg.payload)["temperature"]

        elif msg.topic.endswith("/state"):
            data = json.loads(msg.payload)
            self.state["setpoint"] = data["setpoint"]
            self.state["heating"] = data["heating"]

    def publish_setpoint(self, value):
        self.client.publish(
            f"thermostat/{THERMO_ID}/setpoint",
            value,
            qos=1,
            retain=True
        )

    def publish_settings(self, settings):
        self.client.publish(
            f"thermostat/{THERMO_ID}/settings",
            json.dumps(settings),
            qos=1,
            retain=True
        )

    def get_state(self):
        return self.state
