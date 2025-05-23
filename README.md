# Home Alarm System on Raspberry Pi Zero 2 W and Pico W

## Overview 

This project is a real-time sensor-based alarm monitoring dashboard developed using Flask, MQTT, SQLite, Javascript, C, and Pushover notification service. It is deployed on a Raspberry Pi Zero 2 W and includes both a frontend dashboard and a backend system to monitor distance data from a connected device (Raspberry Pico W) and trigger alerts when objects get too close. This is the repository for the Raspberry Pi Zero 2 W.

## Sensor Alarm Dashboard

A real-time dashboard for monitoring distance readings sent from a Raspberry Pi Pico W using MQTT. The backend is built with Flask, and includes features like alarm toggling, device status syncing, and live notifications.

---

## Project Structure

sensor-alarm-dashboard/<br>
├── app.py # Main Flask server<br>
├── instance/<br>
│ └── distances.db # SQLite database (auto-generated)<br>
├── myenv/ # Python virtual environment<br>
└── README.md # You're reading it<br>

## Backend Description 

- Framework: Flask (Python web framework) 
- Database: SQLite (via SQLAlchemy ORM) 
- MQTT Integration: Flask-MQTT for subscribing and publishing to MQTT topics. 
- Notification System: Pushover API is used to send notifications when alarms are triggered or device statuses change. 
- Sensor Data: Distance readings (in meters) are collected from the motion/distance topic and converted to centimeters before being saved to the database. 
 
### Database Models: 
1. DistanceReading: Stores sensor values and timestamps. 
2. AlarmEvent: Logs alarm state changes and triggers. 
3. PicoStatus: Tracks the online/offline status of the Pico W device. 
 
### MQTT Topics Used: 
- motion/distance: Receives distance readings. 
- device/status: Updates whether the Pico W is online or offline. 
- device/alarm/request: Handles alarm state requests from the Pico W. 
 
### Alarm Logic: 
- If the distance is below 20 cm and the alarm is enabled, a Pushover alert is sent (if cooldown period has passed). On the Pico side, the buzzer will beep continously and a red LED will be lit. 
- If the distance is between 20cm and 50cm, on the Pico side, the buzzer will beep intermittently and a blue LED will be lit. 
- Alarm state can be toggled manually from the dashboard. 
- Pico W can request the current alarm state to synchronize with the server. 

## Frontend Description 

- Rendering: Uses render_template_string in Flask to dynamically render HTML templates. 
- Styling: Inline CSS for layout, tables, buttons, and visual status indicators. 
- Charting: Chart.js is used to visualize the recent distance values as a line graph. 
- Dynamic Updates: JavaScript fetch() is used to poll the server every 5 seconds for: 
  - Latest distance readings 
  - Alarm state 
  - Pico W online/offline status 
 
### Features: 
- Display of latest distance with color-coded status (Safe, Medium, Danger). 
- Toggle alarm button with state reflection. 
- Pico W connection status (online/offline) with visual indicator. 
- Alarm event history view. 
- Real-time updates without page refresh. 

> To view the repository for the Raspberry Pico W, follow this url: https://github.com/Damz04/pico_w

---

## Setup Instructions

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

## Running the App
1. Start the MQTT broker (e.g. Mosquitto)
2. Run the Flask server:
```bash
source myenv/bin/activate
python app.py
```
Then open the dashboard at: http://localhost:5000
Or from another device: http://<raspberry-pi-ip>:5000

The SQLite database (distances.db) is created automatically inside the instance/ directory on first run.

## MQTT Setup

Install Mosquitto on your Pi or server:

```bash
sudo apt update
sudo apt install mosquitto mosquitto-clients
sudo systemctl enable mosquitto
```

## Pushover Notification Setup

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

## Testing MQTT Without Pico

You can simulate messages using mosquitto_pub:

```bash
# Simulate Pico going online
mosquitto_pub -t device/status -m online

# Simulate distance (in meters)
mosquitto_pub -t motion/distance -m 0.15
```

## Notes

Alarm state is stored server-side and persists across Pico reboots.

Page updates every 5 seconds for distance, Pico status, and alarm sync.

The SQLite database will grow with historical readings and logs (toggling, triggers).

## Future Improvements 

- Implement user authentication for secure access to the dashboard. 
- Integrate a camera module for capturing images upon alarm trigger. 
- Use cloud storage (e.g., Firebase or AWS) for scalable data logging. 
- Improve UI responsiveness and make the dashboard mobile-friendly. 
