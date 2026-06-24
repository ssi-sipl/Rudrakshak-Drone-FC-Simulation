import time
import json
import random
import math
import threading
import paho.mqtt.client as mqtt

# ===== MQTT CONFIG =====
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_USERNAME = "dro"
MQTT_PASSWORD = "gxuvimr"

DRONE_IDS = ["drone1", "drone2", "drone3"]

# ===== MAP BOUNDS (Sector 32) =====
NORTH = 28.4570
SOUTH = 28.4390
EAST = 77.0488
WEST = 77.0340

# ===== TARGET LOCATION =====
TARGET_LAT = 28.44796
TARGET_LNG = 77.04091

# ===== MOTION CONFIG =====
PUBLISH_INTERVAL = 0.3   # seconds
STEP_SIZE = 0.00005     # degrees (~5m)

ALT_MIN = 30
ALT_MAX = 50


def random_start():
    lat = random.uniform(SOUTH, NORTH)
    lng = random.uniform(WEST, EAST)
    return lat, lng


def move_towards(lat, lng, target_lat, target_lng, step):
    dlat = target_lat - lat
    dlng = target_lng - lng
    dist = math.sqrt(dlat**2 + dlng**2)

    if dist == 0:
        return lat, lng, True

    if dist <= step:
        return target_lat, target_lng, True

    lat += (dlat / dist) * step
    lng += (dlng / dist) * step
    return lat, lng, False


def simulate_drone(drone_id: str):
    topic = f"drones/{drone_id}/telemetry"

    client = mqtt.Client(client_id=f"sim-{drone_id}")
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    print(f"[{drone_id}] Connecting to MQTT...")
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    client.loop_start()

    lat, lng = random_start()
    alt = random.randint(ALT_MIN, ALT_MAX)

    print(f"[{drone_id}] Start at lat={lat:.5f}, lng={lng:.5f}")

    try:
        while True:
            lat, lng, reached = move_towards(
                lat, lng, TARGET_LAT, TARGET_LNG, STEP_SIZE
            )

            payload = {
                "droneId": drone_id,
                "lat": round(lat, 6),
                "lng": round(lng, 6),
                "alt": alt
            }

            client.publish(topic, json.dumps(payload), qos=1)
            print(f"[{drone_id}] → {topic} {payload}")

            if reached:
                print(f"[{drone_id}] 🎯 Target reached. Holding...")
                time.sleep(5)
            else:
                time.sleep(PUBLISH_INTERVAL)

    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()
        print(f"[{drone_id}] Disconnected.")


def main():
    threads = []

    for drone_id in DRONE_IDS:
        t = threading.Thread(target=simulate_drone, args=(drone_id,), daemon=True)
        t.start()
        threads.append(t)

    print("[SIM] 🚀 Multi-drone simulator running (Ctrl+C to stop)")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[SIM] Stopping all drones...")


if __name__ == "__main__":
    main()
