import json
import os
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from logger import setup_logger

logger = setup_logger(__name__)

MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_PREFIX = os.getenv("MQTT_PREFIX", "shellyazplug-powerout")

INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "")
INFLUX_ORG = os.getenv("INFLUX_ORG", "powerout")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "outages")


def utc_now():
    return datetime.now(timezone.utc)


class Tracker:
    def __init__(self, write_api, bucket, org, device_tag):
        self.write_api = write_api
        self.bucket = bucket
        self.org = org
        self.device_tag = device_tag
        self.state = None

    def write_metrics(self, state, metrics, raw_payload):
        p = Point("power_metrics").tag("device", self.device_tag)
        p = p.field("state", 1 if state == "ON" else 0)
        for k, v in metrics.items():
            if v is None:
                continue
            try:
                p = p.field(k, float(v))
            except:
                logger.warning(f"Failed to convert metric {k}={v} to float")
                continue
        p = p.field("raw", raw_payload)
        p = p.time(utc_now(), WritePrecision.S)
        try:
            self.write_api.write(bucket=self.bucket, org=self.org, record=p)
            logger.debug(f"Wrote metrics: state={state}, metrics={metrics}")
        except Exception as e:
            logger.error(f"Failed to write to InfluxDB: {e}")

    def set_state(self, new_state, metrics, raw_payload):
        if self.state != new_state:
            logger.info(f"State changed: {self.state} -> {new_state}")
        self.state = new_state
        self.write_metrics(new_state, metrics, raw_payload)


def main():
    logger.info("Starting pi_agent listener")
    if not INFLUX_TOKEN:
        logger.critical("INFLUX_TOKEN is required")
        raise RuntimeError("INFLUX_TOKEN is required")

    influx = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    write_api = influx.write_api(write_options=SYNCHRONOUS)

    prefix = MQTT_PREFIX
    device_tag = prefix

    online_t = f"{prefix}/online"
    status_t = f"{prefix}/status/switch:0"

    tracker = Tracker(write_api, INFLUX_BUCKET, INFLUX_ORG, device_tag)

    def on_connect(client, userdata, flags, rc, properties=None):
        logger.info(f"Connected to MQTT broker with result code {rc}")
        client.subscribe(online_t)
        client.subscribe(status_t)

    def on_message(client, userdata, msg):
        raw = msg.payload.decode("utf-8", errors="ignore").strip()
        logger.debug(f"Received message on {msg.topic}: {raw}")

        if msg.topic == online_t:
            state = "ON" if raw.lower() == "true" else "OFF"
            tracker.set_state(state, {}, raw)
            return

        if msg.topic == status_t:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from {msg.topic}: {e}")
                return

            voltage = data.get("voltage")
            apower = data.get("apower") or data.get("apower", 0.0)
            current = data.get("current")
            freq = data.get("freq")
            temp_c = None
            t = data.get("temperature")
            if isinstance(t, dict):
                temp_c = t.get("tC")

            state = "ON" if data.get("output") else "OFF"

            metrics = {
                "voltage": voltage,
                "apower": apower,
                "current": current,
                "freq": freq,
                "temperature_c": temp_c,
                "output": 1 if data.get("output") else 0,
            }

            tracker.set_state(state, metrics, raw)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_HOST, MQTT_PORT, 60)
        client.loop_forever()
    except Exception as e:
        logger.critical(f"MQTT connection failed: {e}")
        raise

if __name__ == "__main__":
    main()
