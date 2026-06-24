import requests
import random
import sys

# ===================== CONFIG =====================

BASE_URL = "http://localhost:3000"   # MUST be http if secure=false in dev

LOGIN_URL = f"{BASE_URL}/api/auth/login"
SENSOR_URL = f"{BASE_URL}/api/sensors"

EMAIL = "abhinn@rayonix.com"
PASSWORD = "pasword123"

AREA_ID = "6931431999f4abd621d89a53"

# Area bounds
LAT_MIN = 28.4360
LAT_MAX = 28.4620
LON_MIN = 77.0290
LON_MAX = 77.0530

TOTAL_SENSORS = 20   # 🔁 change this number

# ===================== HELPERS =====================

def random_lat_lon():
    lat = round(random.uniform(LAT_MIN, LAT_MAX), 6)
    lon = round(random.uniform(LON_MIN, LON_MAX), 6)
    return lat, lon


# ===================== AUTH =====================

def login(session):
    payload = {
        "email": EMAIL,
        "password": PASSWORD
    }

    r = session.post(LOGIN_URL, json=payload)

    if r.status_code != 200:
        print("❌ Login failed:", r.text)
        sys.exit(1)

    # Debug (optional)
    if not session.cookies:
        print("❌ No cookies stored. Check Secure flag.")
        sys.exit(1)

    print("✅ Logged in successfully")
    print("🍪 Cookies received:", session.cookies.get_dict())


# ===================== SENSOR CREATION =====================

def create_sensors(session, count):
    for i in range(1, count + 1):
        lat, lon = random_lat_lon()

        payload = {
            "sensorId": f"ipcam{i}",
            "name": f"IP Camera {i}",
            "sensorType": "Camera",
            "latitude": str(lat),
            "longitude": str(lon),
            "ipAddress": f"192.168.111.{100 + i}",
            "rtspUrl": None,
            "battery": "100",
            "status": "Active",
            "sendDrone": "Yes",
            "activeShuruMode": "true",
            "areaId": AREA_ID,
            "alarmId": ""
        }

        r = session.post(SENSOR_URL, json=payload)

        if r.status_code in (200, 201):
            print(f"✅ Created {payload['sensorId']}  @ ({lat}, {lon})")
        else:
            print(f"❌ Failed {payload['sensorId']}: {r.status_code} {r.text}")


# ===================== MAIN =====================

def main():
    with requests.Session() as session:
        login(session)
        create_sensors(session, TOTAL_SENSORS)


if __name__ == "__main__":
    main()
