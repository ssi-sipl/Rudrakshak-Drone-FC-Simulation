# drone.py

import math
import random
import threading
import time


# =====================
# HELPERS
# =====================

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)

    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1)
        * math.cos(phi2)
        * math.sin(dlambda / 2) ** 2
    )

    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def move_towards(current, target, factor=0.05):
    return current + (target - current) * factor


# =====================
# FLIGHT CONTROLLER
# =====================

class DroneFC:

    def __init__(self, drone_id, lat, lng):

        self.id = drone_id
        self.lock = threading.Lock()

        self.droneType = None
        self.missionTimer = 0

        self.state = {
            "status": "ground",
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

            if self.state["status"] == "on_air" and event == "send_drone":
                print(f"[BLOCKED] {self.id} already flying")
                return

            if event == "send_drone":

                self.state["targetLat"] = float(payload["latitude"])
                self.state["targetLng"] = float(payload["longitude"])

                self.state["status"] = "on_air"
                self.state["mode"] = "AUTO"

                print(
                    f"[CMD] {self.id} SEND -> "
                    f"{self.state['targetLat']}, {self.state['targetLng']}"
                )

            elif event == "recall_drone":

                self.state["targetLat"] = self.state["homeLat"]
                self.state["targetLng"] = self.state["homeLng"]

                self.state["status"] = "on_air"
                self.state["mode"] = "RTL"

                print(f"[CMD] {self.id} RECALL")

            elif event == "patrol":
                print(f"[CMD] {self.id} PATROL (ignored)")

    # =====================
    # TELEMETRY UPDATE
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
    # NORMAL TELEMETRY
    # =====================

    def telemetry(self):

        targetDistance = None

        if self.state["targetLat"] is not None:

            targetDistance = int(
                haversine_m(
                    self.state["lat"],
                    self.state["lng"],
                    self.state["targetLat"],
                    self.state["targetLng"],
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

    # =====================
    # BATTLE TELEMETRY
    # =====================

    def battle_telemetry(self, metadata):

        packet = self.telemetry()

        packet["name"] = metadata["name"]
        packet["type"] = metadata["type"]
        packet["range"] = metadata["range"]

        return packet