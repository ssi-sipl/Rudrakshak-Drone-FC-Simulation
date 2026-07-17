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


COMMAND_TOPIC = "drone"
BATTLE_COMMAND_TOPIC = "battle/drone"
TICK_RATE = 1  # seconds
BATTLE_TELEMETRY_PREFIX = "battle"

# =====================
# DRONES TO SIMULATE
# =====================
DRONES = {
    "falcon": {
        "lat": 28.6215111,
        "lng": 77.2143111,
    }
}
# =====================
# BATTLE DRONES
# =====================
BATTLE_DRONES = {
    "falcon": {
        "name": "Falcon",
        "type": "Reconnaissance",
        "lat": 28.6420,
        "lng": 77.1920,
        "range": 15000,
    },
    "viper": {
        "name": "Viper",
        "type": "Strike",
        "lat": 28.6410,
        "lng": 77.2280,
        "range": 12000,
    },
    "specter": {
        "name": "Specter",
        "type": "Loitering Munition",
        "lat": 28.62050,
        "lng": 77.21200,
        "range": 20000,
    },
    "sentinel": {
        "name": "Sentinel",
        "type": "Surveillance",
        "lat": 28.5980,
        "lng": 77.1940,
        "range": 25000,
    },
}

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
# FLIGHT CONTROLLER CLASS
# =====================
class DroneFC:
    def __init__(self, drone_id, lat, lng):
        self.id = drone_id
        self.lock = threading.Lock()
        self.droneType = None
        self.missionTimer = 0

        self.state = {
            "status": "ground",    # ground | on_air | reached | returning
            "mode": "STABILIZE",

            "lat": lat,
            "lng": lng,
            "alt": 0.0,

            "speed": 0.0,
            "verticalSpeed": 0.0,
            "heading": 0,

            "battery": 100.0,
            "signalStrength": -60,
            "linkQuality": 100,

            "targetLat": None,
            "targetLng": None,

            "homeLat": lat,
            "homeLng": lng,
        }

    # =====================
    # COMMAND HANDLER
    # =====================
    def handle_command(self, payload):
        print("[MQTT COMMAND]", payload)
        with self.lock:
            event = payload.get("event")

            # 🚫 HARD RULE: no retarget mid-flight
            if self.state["status"] == "on_air" and event == "send_drone":
                print(f"[BLOCKED] {self.id} already flying")
                return

            if event == "send_drone":
                self.state["targetLat"] = float(payload["latitude"])
                self.state["targetLng"] = float(payload["longitude"])
                self.state["status"] = "on_air"
                self.state["mode"] = "AUTO"
                print(f"[CMD] {self.id} SEND → {self.state['targetLat']}, {self.state['targetLng']}")

            elif event == "recall_drone":
                self.state["targetLat"] = self.state["homeLat"]
                self.state["targetLng"] = self.state["homeLng"]
                self.state["status"] = "on_air"
                self.state["mode"] = "RTL"
                print(f"[CMD] {self.id} RECALL")

            elif event == "patrol":
                print(f"[CMD] {self.id} PATROL (ignored)")

    # =====================
    # TELEMETRY TICK
    # =====================
    def tick(self):
        with self.lock:
            if self.state["status"] == "reached" and self.droneType:

                if self.missionTimer > 0:
                    self.missionTimer -= 1
                    return

                if self.droneType == "Reconnaissance":
                    self.state["targetLat"] = self.state["homeLat"]
                    self.state["targetLng"] = self.state["homeLng"]
                    self.state["mode"] = "RTL"
                    self.state["status"] = "on_air"

                elif self.droneType == "Strike":
                    print(f"[ATTACK] {self.id} Strike complete")

                    self.state["targetLat"] = self.state["homeLat"]
                    self.state["targetLng"] = self.state["homeLng"]
                    self.state["mode"] = "RTL"
                    self.state["status"] = "on_air"

                elif self.droneType == "Loitering Munition":
                    print(f"[BOOM] {self.id} Destroyed")

                    self.state["status"] = "destroyed"
                    self.state["speed"] = 0
                    self.state["alt"] = 0

                elif self.droneType == "Surveillance":
                    self.state["targetLat"] = self.state["homeLat"]
                    self.state["targetLng"] = self.state["homeLng"]
                    self.state["mode"] = "RTL"
                    self.state["status"] = "on_air"
            if self.state["status"] in ("on_air", "returning"):
                self.state["alt"] = min(40, self.state["alt"] + 0.6)
                self.state["speed"] = random.uniform(5.0, 8.0)
                self.state["verticalSpeed"] = 0.6
                self.state["heading"] = random.randint(0, 359)

                dist = haversine_m(
                    self.state["lat"], self.state["lng"],
                    self.state["targetLat"], self.state["targetLng"]
                )

                if dist > 6:
                    self.state["lat"] = move_towards(self.state["lat"], self.state["targetLat"])
                    self.state["lng"] = move_towards(self.state["lng"], self.state["targetLng"])
                else:
                    if self.state["mode"] == "RTL":
                        # ✅ recall completed → LAND
                        self.state["status"] = "ground"
                        self.state["alt"] = 0
                        self.state["speed"] = 0
                        self.state["verticalSpeed"] = 0
                        self.state["mode"] = "STABILIZE"
                        self.state["targetLat"] = None
                        self.state["targetLng"] = None
                        print(f"[STATE] {self.id} LANDED AT BASE")
                    else:
                        # ✅ mission reached (sensor)
                        self.state["status"] = "reached"
                        self.state["speed"] = 0
                        self.state["verticalSpeed"] = 0
                        if self.droneType:
                            self.missionTimer = 5
                        print(f"[STATE] {self.id} TARGET REACHED")
                        self.state["battery"] = max(self.state["battery"] - 0.05, 15)
                        self.state["signalStrength"] = random.randint(-70, -55)
                        self.state["linkQuality"] = random.randint(90, 100)

    # =====================
    # TELEMETRY PACKET
    # =====================
    def telemetry(self):
        targetDistance = None
        if self.state["targetLat"] is not None:
            targetDistance = int(
                haversine_m(
                    self.state["lat"], self.state["lng"],
                    self.state["targetLat"], self.state["targetLng"]
                )
            )

        return {
            "droneDbId": self.id,
            "droneId": self.id,

            "status": self.state["status"],
            "mode": self.state["mode"],

            "lat": round(self.state["lat"], 7),
            "lng": round(self.state["lng"], 7),
            "alt": round(self.state["alt"], 2),

            "speed": round(self.state["speed"], 2),
            "verticalSpeed": round(self.state["verticalSpeed"], 2),
            "heading": self.state["heading"],

            "battery": round(self.state["battery"], 1),

            "gpsFix": "3D",
            "satellites": 10,
            "windSpeed": random.randint(2, 6),

            "signalStrength": self.state["signalStrength"],
            "linkQuality": self.state["linkQuality"],

            "targetLatitude": self.state["targetLat"],
            "targetLongitude": self.state["targetLng"],
            "targetDistance": targetDistance,

            "ts": int(time.time() * 1000),
        }


    def battle_telemetry(self, metadata):
        packet = self.telemetry()

        packet["name"] = metadata["name"]
        packet["type"] = metadata["type"]
        packet["range"] = metadata["range"]

        return packet
# =====================
# INIT DRONES
# =====================
FLEET = {
    drone_id: DroneFC(drone_id, pos["lat"], pos["lng"])
    for drone_id, pos in DRONES.items()
}

# =====================
# INIT BATTLE DRONES
# =====================
BATTLE_FLEET = {}

for drone_id, drone in BATTLE_DRONES.items():
    fc = DroneFC(
        drone_id,
        drone["lat"],
        drone["lng"],
    )

    fc.droneType = drone["type"]

    BATTLE_FLEET[drone_id] = fc

# =====================
# MQTT CALLBACKS
# =====================
def on_connect(client, userdata, flags, rc):
    print("[MQTT] Connected")

    client.subscribe(COMMAND_TOPIC)
    client.subscribe(BATTLE_COMMAND_TOPIC)

def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode())
    drone_id = payload.get("droneId")
    print("[TOPIC]", msg.topic)
    print("[PAYLOAD]", payload)

    # -----------------------
    # Operations Fleet
    # -----------------------
    if msg.topic == COMMAND_TOPIC:
        if drone_id in FLEET:
            FLEET[drone_id].handle_command(payload)

    # -----------------------
    # Battle Fleet
    # -----------------------
    elif msg.topic == BATTLE_COMMAND_TOPIC:
        if drone_id in BATTLE_FLEET:
            BATTLE_FLEET[drone_id].handle_command(payload)
# =====================
# TELEMETRY LOOP
# =====================
def telemetry_loop(client):
    while True:
        for drone in FLEET.values():
            drone.tick()

            print(
                drone.state["lat"],
                drone.state["lng"],
                drone.state["status"]
            )

            topic = f"drones/{drone.id}/telemetry"
            client.publish(topic, json.dumps(drone.telemetry()), qos=1)

        
        for drone_id, drone in BATTLE_FLEET.items():
            drone.tick()

            topic = f"{BATTLE_TELEMETRY_PREFIX}/{drone_id}/telemetry"

            client.publish(
                topic,
                json.dumps(
                    drone.battle_telemetry(
                        BATTLE_DRONES[drone_id]
                    )
                ),
                qos=1,
            )

        time.sleep(TICK_RATE)

# =====================
# MAIN
# =====================
client = mqtt.Client(client_id="mock-multi-fc")
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)

threading.Thread(target=telemetry_loop, args=(client,), daemon=True).start()

print("[MOCK FC] Multi-drone flight controller running…")
client.loop_forever()
