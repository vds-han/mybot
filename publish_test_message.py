import paho.mqtt.client as mqtt
import json
import ssl
from datetime import datetime

# MQTT Broker details
BROKER_URL = "e29b0717e75f4021aae331f800d7113d.s1.eu.hivemq.cloud"
BROKER_PORT = 8883
MQTT_USERNAME = "comebing"
MQTT_PASSWORD = "Comebingvendis9"
MQTT_TOPIC = "rubbish/disposal"

# Test MQTT message payload
payload = {
    "rubbish_type": "plastic",  # Valid options: plastic, glass, paper, metal
    "throw_time": datetime.now().isoformat()  # ISO format timestamp
}

def publish_message():
    client = mqtt.Client()
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS)
    client.tls_insecure_set(False)

    try:
        client.connect(BROKER_URL, BROKER_PORT, 60)
        print(f"Connected to {BROKER_URL}:{BROKER_PORT}")
        client.publish(MQTT_TOPIC, json.dumps(payload))
        print(f"Published message to topic '{MQTT_TOPIC}': {payload}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.disconnect()

if __name__ == "__main__":
    publish_message()
