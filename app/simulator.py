# simulator.py

import json
import threading
import time

import paho.mqtt.client as mqtt
import ssl

from app.config import (
    MQTT_BROKER,
    MQTT_PORT,
    MQTT_USERNAME,
    MQTT_PASSWORD,
    COMMAND_TOPIC,
    BATTLE_COMMAND_TOPIC,
    BATTLE_TELEMETRY_PREFIX,
    TICK_RATE,
    DRONES,
    BATTLE_DRONES,
)

from app.drone import DroneFC


# =====================
# INIT FLEETS
# =====================

FLEET = {
    drone_id: DroneFC(drone_id, pos["lat"], pos["lng"])
    for drone_id, pos in DRONES.items()
}

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

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("[MQTT] Connected")
        client.subscribe(COMMAND_TOPIC)
        client.subscribe(BATTLE_COMMAND_TOPIC)
    else:
        print(f"[MQTT] Connection failed with code {rc}")


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

        # ------------------------
        # Operations Fleet
        # ------------------------

        for drone in FLEET.values():

            drone.tick()

            topic = f"drones/{drone.id}/telemetry"
            print(f"Publishing -> {topic}")

            client.publish(
                topic,
                json.dumps(drone.telemetry()),
                qos=1,
            )

        # ------------------------
        # Battle Fleet
        # ------------------------

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
# START SIMULATOR
# =====================

client = None

def start_simulator():

    global client

    if client is not None:
        return

    client = mqtt.Client(client_id="mock-multi-fc")

    client.username_pw_set(
        MQTT_USERNAME,
        MQTT_PASSWORD,
    )
    client.tls_set(cert_reqs=ssl.CERT_REQUIRED)

    client.on_connect = on_connect
    client.on_message = on_message

    def mqtt_worker():

        while True:

            try:

                print(f"[MQTT] Connecting to {MQTT_BROKER}:{MQTT_PORT}...")

                client.connect(
                    MQTT_BROKER,
                    MQTT_PORT,
                    60,
                )

                print("[MQTT] Connected Successfully")

                threading.Thread(
                    target=telemetry_loop,
                    args=(client,),
                    daemon=True,
                ).start()

                client.loop_forever()

            except Exception as e:

                print(f"[MQTT] Connection Failed: {e}")
                print("[MQTT] Retrying in 5 seconds...\n")

                time.sleep(5)

    threading.Thread(
        target=mqtt_worker,
        daemon=True,
    ).start()

    print("[MOCK FC] Simulator Started")