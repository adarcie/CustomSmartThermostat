import json
import paho.mqtt.client as mqtt

class ThermostatMQTT:
    def __init__(self, broker, thermostat_id, on_setpoint):
        self.id = thermostat_id
        self.on_setpoint = on_setpoint

        self.client = mqtt.Client(client_id=f"thermo-{thermostat_id}")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

        self.client.connect(broker, 1883, 60)
        self.client.loop_start()

    def _on_connect(self, client, userdata, flags, rc):
        print("MQTT connected:", rc)
        client.subscribe(f"thermostat/{self.id}/setpoint")
        client.subscribe(f"thermostat/{self.id}/command")

    def _on_message(self, client, userdata, msg):
        payload = msg.payload.decode()
        topic = msg.topic

        if topic.endswith("/setpoint"):
            try:
                value = float(payload)
                print("New setpoint:", value)
                self.on_setpoint(value)
            except ValueError:
                print("Invalid setpoint")

        elif topic.endswith("/command"):
            print("Command received:", payload)
            # future: calibration, emergency stop, etc.

    def publish_temperature(self, temp):
        self.client.publish(
            f"thermostat/{self.id}/temperature",
            json.dumps({"temperature": temp})
        )

    def publish_state(self, state):
        self.client.publish(
            f"thermostat/{self.id}/state",
            json.dumps(state)
        )

