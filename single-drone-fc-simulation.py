import json
import time
import math
import random
import threading
import paho.mqtt.client as mqtt

# =====================
# CONFIG
# =====================
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_USERNAME = "dro"
MQTT_PASSWORD = "gxuvimr"

DRONE_ID = "drone1"
COMMAND_TOPIC = "drone"
TELEMETRY_TOPIC = f"drones/{DRONE_ID}/telemetry"

TICK_RATE = 1  # seconds

# =====================
# DRONE STATE (FC MEMORY)
# =====================
state = {
    # Flight
    "status": "ground",      # ground | on_air | reached | returning
    "mode": "STABILIZE",

    # Position
    "lat": 28.442422,
    "lng": 77.037893,
    "alt": 0.0,

    # Motion
    "speed": 0.0,
    "verticalSpeed": 0.0,
    "heading": 0,

    # Power & link
    "battery": 100.0,
    "signalStrength": -60,
    "linkQuality": 100,

    # Target
    "targetLat": None,
    "targetLng": None,

    # Home
    "homeLat": 28.442422,
    "homeLng": 77.037893,
}

LOCK = threading.Lock()

# =====================
# HELPERS
# =====================
def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)

    a = math.sin(Δφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def move_towards(current, target, factor=0.05):
    return current + (target - current) * factor

# =====================
# MQTT CALLBACKS
# =====================
def on_connect(client, userdata, flags, rc):
    print("[MQTT] Connected")
    client.subscribe(COMMAND_TOPIC)

def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode())
    if payload.get("droneId") != DRONE_ID:
        return

    event = payload.get("event")

    with LOCK:
        # 🚫 HARD BLOCK trajectory change mid-flight
        if state["status"] == "on_air" and event == "send_drone":
            print("[BLOCKED] Drone already in air")
            return

        if event == "send_drone":
            state["targetLat"] = float(payload["latitude"])
            state["targetLng"] = float(payload["longitude"])
            state["status"] = "on_air"
            state["mode"] = "AUTO"
            print(f"[CMD] SEND → {state['targetLat']}, {state['targetLng']}")

        elif event == "recall_drone":
            state["targetLat"] = state["homeLat"]
            state["targetLng"] = state["homeLng"]
            state["status"] = "on_air"
            state["mode"] = "RTL"
            print("[CMD] RECALL")

        elif event == "patrol":
            print("[CMD] PATROL (ignored in mock)")

# =====================
# TELEMETRY LOOP (FC OUTPUT)
# =====================
def telemetry_loop(client):
    while True:
        with LOCK:
            # =====================
            # FLIGHT STATE MACHINE
            # =====================
            if state["status"] in ("on_air", "returning"):
                state["alt"] = min(40, state["alt"] + 0.6)
                state["speed"] = random.uniform(5.0, 8.0)
                state["verticalSpeed"] = 0.6
                state["heading"] = random.randint(0, 359)

                dist = haversine_m(
                    state["lat"], state["lng"],
                    state["targetLat"], state["targetLng"]
                )

                if dist > 6:
                    state["lat"] = move_towards(state["lat"], state["targetLat"])
                    state["lng"] = move_towards(state["lng"], state["targetLng"])
                else:
                    if state["status"] == "on_air":
                        state["status"] = "reached"
                        state["speed"] = 0.0
                        state["verticalSpeed"] = 0.0
                        print("[STATE] TARGET REACHED")
                    else:
                        state["status"] = "ground"
                        state["alt"] = 0.0
                        state["speed"] = 0.0
                        state["verticalSpeed"] = 0.0
                        state["mode"] = "STABILIZE"
                        state["targetLat"] = None
                        state["targetLng"] = None
                        print("[STATE] LANDED")

            elif state["status"] == "reached":
                state["speed"] = 0.0
                state["verticalSpeed"] = 0.0

            # =====================
            # POWER & LINK
            # =====================
            state["battery"] = max(state["battery"] - 0.05, 15)
            state["signalStrength"] = random.randint(-70, -55)
            state["linkQuality"] = random.randint(90, 100)

            # =====================
            # TARGET DISTANCE
            # =====================
            targetDistance = None
            if state["targetLat"] is not None:
                targetDistance = int(
                    haversine_m(
                        state["lat"], state["lng"],
                        state["targetLat"], state["targetLng"]
                    )
                )

            # =====================
            # TELEMETRY PACKET (FINAL)
            # =====================
            telemetry = {
                "droneDbId": DRONE_ID,
                "droneId": DRONE_ID,

                "status": state["status"],
                "mode": state["mode"],

                "lat": round(state["lat"], 7),
                "lng": round(state["lng"], 7),
                "alt": round(state["alt"], 2),

                "speed": round(state["speed"], 2),
                "verticalSpeed": round(state["verticalSpeed"], 2),
                "heading": state["heading"],

                "battery": round(state["battery"], 1),

                "gpsFix": "3D",
                "satellites": 10,
                "windSpeed": random.randint(2, 6),

                "signalStrength": state["signalStrength"],
                "linkQuality": state["linkQuality"],

                "targetLatitude": state["targetLat"],
                "targetLongitude": state["targetLng"],
                "targetDistance": targetDistance,

                "ts": int(time.time() * 1000),
            }

        client.publish(TELEMETRY_TOPIC, json.dumps(telemetry), qos=1)
        time.sleep(TICK_RATE)

# =====================
# MAIN
# =====================
client = mqtt.Client(client_id=f"mock-fc-{DRONE_ID}")
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)

threading.Thread(target=telemetry_loop, args=(client,), daemon=True).start()

print("[MOCK FC] Unified Flight Controller simulator running…")
client.loop_forever()
