import json
import time
import random
import paho.mqtt.client as mqtt

def s(value):
    """Convert any value to string safely"""
    if value is None:
        return ""
    return str(value)


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
# TARGET COORDINATES
# ======================
TARGET_LATITUDE = 28.447960
TARGET_LONGITUDE = 77.040915

# ======================
# INITIAL STATE
# ======================
current_latitude =  28.442422
current_longitude =  77.037893
current_altitude = 0.0  # Start on ground
battery_percent = 100.0
drone_speed = 0.0  # Start stationary
sat_count = 10
gps_fix = "3D"
drone_mode = "AUTO"

# Movement tuning
STEP_FACTOR = 0.05
ALTITUDE_STEP = 0.4
REACH_THRESHOLD = 0.0001  # Distance threshold to consider "reached"

# ======================
# FLIGHT PHASES
# ======================
# Phase 1: ground (0-5 seconds)
# Phase 2: on_air (takeoff and flying to target)
# Phase 3: reached (at target for 10 seconds)
# Phase 4: on_air (returning)
# Phase 5: ground (landed)

phase = "ground"
phase_timer = 0
phase_duration = 5  # seconds on ground before takeoff

# ======================
# MQTT CALLBACKS
# ======================
def on_connect(client, userdata, flags, rc):
    print("[MQTT] Connected" if rc == 0 else "[MQTT] Failed")

# ======================
# HELPER FUNCTIONS
# ======================
def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance in degrees (approximate)"""
    return ((lat2 - lat1)**2 + (lon2 - lon1)**2) ** 0.5

def calculate_distance_meters(lat1, lon1, lat2, lon2):
    """Calculate distance in meters (rough approximation)"""
    return calculate_distance(lat1, lon1, lat2, lon2) * 111000

# ======================
# MQTT CLIENT
# ======================
client = mqtt.Client(client_id=f"mock-drone-{DRONE_ID}")
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.on_connect = on_connect
client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
client.loop_start()

print("[MOCK] Starting drone simulation with status phases...")
print("Phase 1: 'ground' - Drone on ground (5s)")
print("Phase 2: 'on_air' - Takeoff and flying to target")
print("Phase 3: 'reached' - At target location (10s)")
print("Phase 4: 'on_air' - Return to base")
print("Phase 5: 'ground' - Landed at base")
print("\nPress CTRL+C to stop\n")

# Starting position
start_latitude = current_latitude
start_longitude = current_longitude

try:
    while True:
        phase_timer += 1
        
        # ======================
        # PHASE 1: GROUND (Pre-flight)
        # ======================
        if phase == "ground" and phase_timer <= phase_duration:
            drone_speed = 0.0
            current_altitude = 0.0
            drone_mode = "STABILIZE"
            status = "ground"
            
            print(f"[{phase_timer}s] Phase: GROUND - Pre-flight checks")
        
        # ======================
        # PHASE 2: ON_AIR (Flying to target)
        # ======================
        elif phase == "ground" and phase_timer > phase_duration:
            phase = "on_air"
            phase_timer = 0
            drone_mode = "AUTO"
            print("\n[TAKEOFF] Phase: ON_AIR - Flying to target\n")
        
        if phase == "on_air":
            status = "on_air"
            
            # Takeoff - gradually increase altitude
            if current_altitude < 40:
                current_altitude += ALTITUDE_STEP
            
            # Calculate distance to target
            distance_to_target = calculate_distance(
                current_latitude, current_longitude,
                TARGET_LATITUDE, TARGET_LONGITUDE
            )
            
            # Move toward target
            if distance_to_target > REACH_THRESHOLD:
                lat_diff = TARGET_LATITUDE - current_latitude
                lng_diff = TARGET_LONGITUDE - current_longitude
                
                current_latitude += lat_diff * STEP_FACTOR
                current_longitude += lng_diff * STEP_FACTOR
                
                # Stop micro jitter near target
                if abs(lat_diff) < 0.000001:
                    current_latitude = TARGET_LATITUDE
                if abs(lng_diff) < 0.000001:
                    current_longitude = TARGET_LONGITUDE
                
                drone_speed = round(random.uniform(5.0, 8.0), 2)
                
                print(f"[FLYING] Distance to target: {int(distance_to_target * 111000)}m")
            
            else:
                # Reached target
                phase = "reached"
                phase_timer = 0
                phase_duration = 10  # Stay at target for 10 seconds
                drone_speed = 0.0
                print("\n[ARRIVED] Phase: REACHED - At target location\n")
        
        # ======================
        # PHASE 3: REACHED (At target)
        # ======================
        if phase == "reached":
            status = "reached"
            drone_speed = 0.0
            current_latitude = TARGET_LATITUDE
            current_longitude = TARGET_LONGITUDE
            
            print(f"[{phase_timer}s] Phase: REACHED - Hovering at target")
            
            if phase_timer >= phase_duration:
                # Start returning
                phase = "returning"
                phase_timer = 0
                drone_mode = "RTL"  # Return To Launch
                print("\n[RETURNING] Phase: ON_AIR - Returning to base\n")
        
        # ======================
        # PHASE 4: RETURNING (Flying back)
        # ======================
        if phase == "returning":
            status = "on_air"
            
            # Calculate distance to start
            distance_to_start = calculate_distance(
                current_latitude, current_longitude,
                start_latitude, start_longitude
            )
            
            # Move toward start
            if distance_to_start > REACH_THRESHOLD:
                lat_diff = start_latitude - current_latitude
                lng_diff = start_longitude - current_longitude
                
                current_latitude += lat_diff * STEP_FACTOR
                current_longitude += lng_diff * STEP_FACTOR
                
                drone_speed = round(random.uniform(5.0, 8.0), 2)
                
                print(f"[RETURNING] Distance to base: {int(distance_to_start * 111000)}m")
            
            else:
                # Reached base
                phase = "landing"
                phase_timer = 0
                drone_mode = "LAND"
                print("\n[LANDING] Phase: GROUND - Landing at base\n")
        
        # ======================
        # PHASE 5: LANDING (Descending)
        # ======================
        if phase == "landing":
            status = "on_air"  # Still in air while descending
            drone_speed = 0.0
            current_latitude = start_latitude
            current_longitude = start_longitude
            
            # Descend
            if current_altitude > 0:
                current_altitude = max(0, current_altitude - ALTITUDE_STEP)
                print(f"[LANDING] Altitude: {current_altitude:.1f}m")
            else:
                # Landed
                phase = "landed"
                phase_timer = 0
                status = "ground"
                drone_mode = "STABILIZE"
                print("\n[LANDED] Phase: GROUND - Mission complete\n")
        
        # ======================
        # PHASE 6: LANDED (Mission complete)
        # ======================
        if phase == "landed":
            status = "ground"
            drone_speed = 0.0
            current_altitude = 0.0
            print(f"[{phase_timer}s] Phase: GROUND - Mission complete")
            
            # Optional: Restart mission after 10 seconds
            if phase_timer >= 10:
                phase = "ground"
                phase_timer = 0
                phase_duration = 5
                battery_percent = 100.0
                print("\n[RESTART] Starting new mission...\n")

        # ======================
        # PUBLISH TELEMETRY
        # ======================
        battery_percent = max(battery_percent - 0.08, 15)
        
        distance_to_target_meters = int(calculate_distance_meters(
            current_latitude, current_longitude,
            TARGET_LATITUDE, TARGET_LONGITUDE
        ))
        
        message = {
            "event": "send_drone",
            "command": "altitudeData",

            "droneid": s(DRONE_ID),
            "status": s(status),
            "droneMode": s(drone_mode),

            "currentLatitude": s(round(current_latitude, 7)),
            "currentLongitude": s(round(current_longitude, 7)),
            "currentAltitude": s(round(current_altitude, 2)),

            "droneSpeed": s(round(drone_speed, 2)),
            "batteryVoltage": s(round(battery_percent, 1)),

            "GPSFix": s(gps_fix),
            "satelliteCount": s(sat_count),
            "windSpeed": s(random.randint(2, 6)),

            "targetLatitude": s(TARGET_LATITUDE),
            "targetLongitude": s(TARGET_LONGITUDE),
            "targetDistance": s(distance_to_target_meters)
        }


        client.publish(TOPIC, json.dumps(message), qos=1)

        time.sleep(1)

except KeyboardInterrupt:
    print("\n[MOCK] Simulation stopped")

finally:
    client.loop_stop()
    client.disconnect()