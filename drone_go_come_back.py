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

DRONE_ID = "drone1"
TOPIC = f"drones/{DRONE_ID}/telemetry"

# ======================
# HOME & TARGET
# ======================
HOME_LATITUDE = 28.442422
HOME_LONGITUDE = 77.037893

TARGET_LATITUDE = 28.447960
TARGET_LONGITUDE = 77.040915

# ======================
# INITIAL STATE
# ======================
current_latitude = HOME_LATITUDE
current_longitude = HOME_LONGITUDE
current_altitude = 20.0

battery_percent = 100.0
drone_speed = 6.0
sat_count = 10
gps_fix = "3D"
drone_mode = "AUTO"

status = "on AIR"

# ======================
# MOVEMENT TUNING
# ======================
STEP_FACTOR = 0.05
ALTITUDE_STEP = 0.4
ARRIVAL_THRESHOLD = 0.000001  # ≈ 0.1m

# ======================
# FLIGHT PHASE
# ======================
phase = "TO_TARGET"  # TO_TARGET → RETURN_HOME → LANDED

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

print("[MOCK] Mission started")

try:
    while True:
        # ------------------
        # Select destination
        # ------------------
        if phase == "TO_TARGET":
            dest_lat, dest_lng = TARGET_LATITUDE, TARGET_LONGITUDE
        elif phase == "RETURN_HOME":
            dest_lat, dest_lng = HOME_LATITUDE, HOME_LONGITUDE
        else:
            break

        lat_diff = dest_lat - current_latitude
        lng_diff = dest_lng - current_longitude

        # ------------------
        # Smooth movement
        # ------------------
        current_latitude += lat_diff * STEP_FACTOR
        current_longitude += lng_diff * STEP_FACTOR

        # ------------------
        # Arrival detection
        # ------------------
        if abs(lat_diff) < ARRIVAL_THRESHOLD and abs(lng_diff) < ARRIVAL_THRESHOLD:
            if phase == "TO_TARGET":
                print("[MOCK] Target reached — returning home")
                phase = "RETURN_HOME"
            elif phase == "RETURN_HOME":
                print("[MOCK] Home reached — landing")
                phase = "LANDED"
                status = "ground"
                current_altitude = 0
                drone_speed = 0
                break

        # ------------------
        # Altitude control
        # ------------------
        if phase != "LANDED" and current_altitude < 40:
            current_altitude += ALTITUDE_STEP

        # ------------------
        # Telemetry
        # ------------------
        battery_percent = max(battery_percent - 0.08, 15)
        drone_speed = round(random.uniform(5.0, 8.0), 2)

        message = {
            "event": "send_drone",
            "command": "altitudeData",

            "droneid": DRONE_ID,
            "status": status,
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
            f"[{phase}] "
            f"Lat:{message['currentLatitude']} "
            f"Lng:{message['currentLongitude']} "
            f"Alt:{message['currentAltitude']}m "
            f"Status:{status}"
        )

        time.sleep(1)

except KeyboardInterrupt:
    print("\n[MOCK] Mission aborted")

finally:
    # Final ground state publish
    message["status"] = "on GROUND"
    message["currentAltitude"] = 0
    message["droneSpeed"] = 0
    client.publish(TOPIC, json.dumps(message), qos=1)

    client.loop_stop()
    client.disconnect()
    print("[MOCK] Mission completed")
