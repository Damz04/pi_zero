# Sensor Alarm Dashboard

A real-time dashboard for monitoring distance readings sent from a Raspberry Pi Pico W using MQTT. The backend is built with Flask, and includes features like alarm toggling, device status syncing, and live notifications.

---

## 📦 Project Structure

sensor-alarm-dashboard/
├── app.py # Main Flask server
├── instance/
│ └── distances.db # SQLite database (auto-generated)
├── myenv/ # Python virtual environment
└── README.md # You're reading it

## ⚙️ Features Overview

- 📡 **MQTT Communication**  
  The Pico W sends distance readings via MQTT to the server and receives alarm state updates.

- 📊 **Live Dashboard**  
  Shows:
  - A chart of recent distance readings  
  - A table with timestamps  
  - Alarm toggle button  
  - Pico W connection status  

- 🔔 **Alarm Logic**  
  - The alarm is triggered when objects are too close (e.g. under 20 cm).
  - Sends a **Pushover notification** (optional).
  - The alarm can be toggled via the dashboard.

- 🔁 **Device Sync**  
  - The dashboard shows whether the Pico W is online.
  - The Pico requests and syncs alarm state at boot.

---

## 🔧 Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/Damz04/pi_zero.git
cd sensor-alarm-dashboard
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv myenv
source myenv/bin/activate
```

### 3. Install required Flask packages

```bash
pip install flask flask-mqtt flask-sqlalchemy
```

## 🚀 Running the App
1. Start the MQTT broker (e.g. Mosquitto)
2. Run the Flask server:
```bash
source myenv/bin/activate
python app.py
```
Then open the dashboard at: http://localhost:5000
Or from another device: http://<raspberry-pi-ip>:5000

The SQLite database (distances.db) is created automatically inside the instance/ directory on first run.

## 📡 MQTT Setup

Install Mosquitto on your Pi or server:

```bash
sudo apt update
sudo apt install mosquitto mosquitto-clients
sudo systemctl enable mosquitto
```

## 🔔 Pushover Notification Setup

To enable push alerts:

1. Create a Pushover account

2. Register an application

3. Get your user key and API token

4. Update these values in app.py:

```python
"user": "YOUR_USER_KEY",
"token": "YOUR_API_TOKEN",
```

You will receive notifications when motion triggers the alarm or the Pico W changes connection state.

## 🧪 Testing MQTT Without Pico

You can simulate messages using mosquitto_pub:

```bash
# Simulate Pico going online
mosquitto_pub -t device/status -m online

# Simulate distance (in meters)
mosquitto_pub -t motion/distance -m 0.15
```

## 📌 Notes

Alarm state is stored server-side and persists across Pico reboots.

Page updates every 5 seconds for distance, Pico status, and alarm sync.

The SQLite database will grow with historical readings and logs (toggling, triggers).
