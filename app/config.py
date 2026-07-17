# config.py

# =====================
# MQTT CONFIG
# =====================

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_USERNAME = "dro"
MQTT_PASSWORD = "gxuvimr"

COMMAND_TOPIC = "drone"
BATTLE_COMMAND_TOPIC = "battle/drone"

BATTLE_TELEMETRY_PREFIX = "battle"

TICK_RATE = 1


# =====================
# OPERATIONS DRONES
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