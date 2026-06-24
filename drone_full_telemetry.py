import json
import time
import random
import paho.mqtt.client as mqtt

# ======================
# MQTT CONFIG
# ======================
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_USERNAME = "dro"
MQTT_PASSWORD = "gxuvimr"

DRONE_ID = "drone3"
TOPIC = f"drones/{DRONE_ID}/telemetry"

# ======================
# TARGET COORDINATES
# ======================
TARGET_LATITUDE = 28.447960
TARGET_LONGITUDE = 77.040915

# ======================
# INITIAL STATE
# ======================
current_latitude = 28.447164
current_longitude = 77.039592
current_altitude = 20.0
battery_percent = 100.0
drone_speed = 6.0
sat_count = 10
gps_fix = "3D"
drone_mode = "AUTO"

# Movement tuning (IMPORTANT)
STEP_FACTOR = 0.05     # lower = smoother & slower (0.02–0.08 recommended)
ALTITUDE_STEP = 0.4

# ======================
# MQTT CALLBACKS
# ======================
def on_connect(client, userdata, flags, rc):
    print("[MQTT] Connected" if rc == 0 else "[MQTT] Failed")

# ======================
# MQTT CLIENT
# ======================
client = mqtt.Client(client_id=f"mock-drone-{DRONE_ID}")
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.on_connect = on_connect
client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
client.loop_start()

print("[MOCK] Drone navigating toward target... CTRL+C to stop")

try:
    while True:
        # --- Smooth GPS movement ---
        lat_diff = TARGET_LATITUDE - current_latitude
        lng_diff = TARGET_LONGITUDE - current_longitude

        current_latitude += lat_diff * STEP_FACTOR
        current_longitude += lng_diff * STEP_FACTOR

        # Stop micro jitter near target
        if abs(lat_diff) < 0.000001:
            current_latitude = TARGET_LATITUDE
        if abs(lng_diff) < 0.000001:
            current_longitude = TARGET_LONGITUDE

        # --- Altitude smoothing ---
        if current_altitude < 40:
            current_altitude += ALTITUDE_STEP

        # --- Simulated telemetry ---
        battery_percent = max(battery_percent - 0.08, 15)
        drone_speed = round(random.uniform(5.0, 8.0), 2)

        message = {
            "event": "send_drone",
            "command": "altitudeData",

            "droneid": DRONE_ID,
            "status": "ground",
            "droneMode": drone_mode,

            "currentLatitude": round(current_latitude, 7),
            "currentLongitude": round(current_longitude, 7),
            "currentAltitude": round(current_altitude, 2),

            "droneSpeed": drone_speed,
            "batteryVoltage": round(battery_percent, 1),

            "GPSFix": gps_fix,
            "satelliteCount": sat_count,
            "windSpeed": str(random.randint(2, 6)),
            "targetDistance": int(
                ((lat_diff**2 + lng_diff**2) ** 0.5) * 111000
            )
        }

        client.publish(TOPIC, json.dumps(message), qos=1)

        print(
            f"[PUBLISH] Lat:{message['currentLatitude']} "
            f"Lng:{message['currentLongitude']} "
            f"Alt:{message['currentAltitude']}m"
        )

        time.sleep(1)

except KeyboardInterrupt:
    print("\n[MOCK] Navigation stopped")

finally:
    client.loop_stop()
    client.disconnect()
