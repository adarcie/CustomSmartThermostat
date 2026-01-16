# mqtt_bridge.py
import json
import paho.mqtt.client as mqtt
from collections import defaultdict

BROKER_IP = "192.168.4.195"

# Add more later, e.g. ["livingroom", "bedroom"]
THERMOSTATS = ["livingroom"]

DEFAULT_SETTINGS = {
    "hysteresis": 0.5,
    "steps_on": 10,
    "steps_off": 10,
    "presets": {
        "Home": 21.0,
        "Sleep": 18.0,
        "Away": 16.0,
    },
}


def _deepcopy_json(obj):
    # Simple deep copy for JSON-serializable dicts
    return json.loads(json.dumps(obj))


class MqttBridge:
    def __init__(self):
        # state[thermo_id] = {temperature, setpoint, heating, settings}
        self.state = defaultdict(
            lambda: {
                "temperature": None,
                "setpoint": None,
                "heating": False,
                "settings": _deepcopy_json(DEFAULT_SETTINGS),
            }
        )

        self.client = mqtt.Client(client_id="flask-dashboard")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(BROKER_IP, 1883, 60)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        print("Flask connected to MQTT, rc =", rc)

        # Wildcard so new thermostats just work
        client.subscribe("thermostat/+/temperature")
        client.subscribe("thermostat/+/state")
        client.subscribe("thermostat/+/settings")

    def _topic_thermo_id(self, topic: str):
        # expected: thermostat/<id>/<leaf>
        parts = topic.split("/")
        if len(parts) >= 3 and parts[0] == "thermostat":
            return parts[1]
        return None

    def _merge_settings(self, incoming: dict) -> dict:
        """
        Merge incoming settings into DEFAULT_SETTINGS.
        Presets are merged by key so missing preset names keep defaults.
        """
        merged = _deepcopy_json(DEFAULT_SETTINGS)

        if not isinstance(incoming, dict):
            return merged

        incoming = dict(incoming)

        # Merge presets dict if present
        if isinstance(incoming.get("presets"), dict):
            merged_presets = dict(merged.get("presets", {}))
            merged_presets.update(incoming["presets"])
            incoming["presets"] = merged_presets

        merged.update(incoming)
        return merged

    def on_message(self, client, userdata, msg):
        thermo_id = self._topic_thermo_id(msg.topic)
        if not thermo_id:
            return

        leaf = msg.topic.split("/")[-1]

        if leaf == "temperature":
            try:
                payload = json.loads(msg.payload)
                self.state[thermo_id]["temperature"] = payload.get("temperature")
            except Exception:
                pass

        elif leaf == "state":
            try:
                data = json.loads(msg.payload)
                self.state[thermo_id]["setpoint"] = data.get("setpoint")
                self.state[thermo_id]["heating"] = bool(data.get("heating"))
            except Exception:
                pass

        elif leaf == "settings":
            # Retained settings come back here after publish or reconnect
            try:
                data = json.loads(msg.payload)
                self.state[thermo_id]["settings"] = self._merge_settings(data)
            except Exception:
                pass

    def publish_setpoint(self, thermo_id: str, value: float):
        self.client.publish(
            f"thermostat/{thermo_id}/setpoint",
            float(value),
            qos=1,
            retain=True,
        )

    def publish_settings(self, thermo_id: str, settings: dict):
        """
        CLEAN FIX for the 'settings revert until refresh' issue:

        We optimistically update our in-memory settings cache immediately,
        then publish the retained MQTT settings. This way, after POST+redirect,
        the GET render shows the newly-saved values instantly (no waiting for MQTT roundtrip).
        """
        try:
            # Update local cache immediately (merged with defaults)
            self.state[thermo_id]["settings"] = self._merge_settings(settings)
        except Exception:
            # Don't block publishing if cache update fails
            pass

        # Publish retained settings
        self.client.publish(
            f"thermostat/{thermo_id}/settings",
            json.dumps(settings),
            qos=1,
            retain=True,
        )

    def get_dashboard_state(self):
        # Ensure a stable set of ids even before MQTT messages arrive
        ids = list(self.state.keys()) or THERMOSTATS
        return {tid: self.state[tid] for tid in ids}

    def get_thermostat(self, thermo_id: str):
        return self.state[thermo_id]
