
from flask import Flask, render_template_string, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_mqtt import Mqtt
from datetime import datetime
import threading
import http.client, urllib
from time import time

last_pushover_time = {'timestamp': 0}

PUSHOVER_COOLDOWN = 60  # seconds

alarm_state = {'enabled': True}

app = Flask(__name__)

# MQTT Configuration
app.config['MQTT_BROKER_URL'] = 'localhost'
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_USERNAME'] = 'mqttuser'
app.config['MQTT_PASSWORD'] = 'password'
mqtt = Mqtt(app)

# SQLite Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///distances.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database Model
class DistanceReading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class AlarmEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False)  # 'triggered' or 'toggled'
    detail = db.Column(db.String(120))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class PicoStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(10))  # "online" or "offline"
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

def set_pico_status(state):
    with app.app_context():
        existing = PicoStatus.query.first()
        if existing:
            existing.status = state
            existing.timestamp = datetime.utcnow()
        else:
            new_status = PicoStatus(status=state)
            db.session.add(new_status)
        db.session.commit()

@app.route('/')
def home():
    latest = DistanceReading.query.order_by(DistanceReading.timestamp.desc()).first()
    readings = DistanceReading.query.order_by(DistanceReading.timestamp.desc()).limit(10).all()
    labels = [r.timestamp.strftime("%H:%M:%S") for r in reversed(readings)]
    values = [r.value for r in reversed(readings)]
    status_obj = PicoStatus.query.first()
    pico_status = status_obj.status if status_obj else "unknown"


    return render_template_string('''
        <style>
            table {
                border-collapse: collapse;
                width: 100%;
                font-weight: bold;
                border-radius: 10px;
                overflow: hidden;
                border: 2px solid black;
            }

            table th, table td {
                border: 1px solid black;
                padding: 8px;
                text-align: left;
                width: 150px;
            }

            table thead {
                background-color: #f2f2f2;
            }

            table tbody tr:nth-child(even) {
                background-color: #f9f9f9;
            }
        </style>

        <h1 style="text-align: center; margin-bottom: 20px;">Sensor Alarm Dashboard</h1>

        <div id="distance-alert" style="padding: 12px; font-size: 18px; font-weight: bold; color: white; border-radius: 8px; margin-bottom: 20px; text-align: center;">
            Distance Status: <span id="latest-distance">{{ distance if distance else "--" }}</span> cm
        </div>

        <!-- Alarm / Status Row -->
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 20px; margin: 40px 0 20px;">
            <!-- Alarm toggle + status -->
            <div style="display: flex; align-items: center; gap: 10px;">
                <button id="toggle-alarm" style="padding: 10px; font-size: 16px; border: none; border-radius: 6px;">Loading...</button>
                <div id="alarm-status" style="font-size: 18px;">Loading...</div>
            </div>

            <!-- Pico W connection status -->
            <div style="font-size: 18px; font-weight: bold;">
                Pico Status: <span id="pico-status" style="font-weight: normal;">Loading...</span>
            </div>


            <!-- Alarm History link -->
            <a href="/alarm-history" style="font-size: 16px; background-color: #6c63ff; color: white; padding: 8px 14px; border-radius: 6px; text-decoration: none;">📜 View Alarm History</a>
        </div>

        <div style="margin-top: 100px;">
            <h2>Recent Readings</h2>
            <div style="display: flex; flex-wrap: wrap; gap: 50px;">
                <!-- Table Section -->
                <div style="flex: 1 1 300px; max-width: 340px; border: 3px solid black; border-radius: 10px; overflow: hidden;">
                    <table style="width: 100%; border-collapse: collapse; font-weight: bold;">
                        <thead>
                            <tr style="background-color: #f0f0f0;">
                                <th style="border-bottom: 2px solid black; padding: 10px; text-align: left;">Time</th>
                                <th style="border-bottom: 2px solid black; padding: 10px; text-align: left;">Distance (cm)</th>
                            </tr>
                        </thead>
                        <tbody id="distance-table-body">
                            {% for r in readings %}
                            <tr>
                                <td style="padding: 8px; border-bottom: 1px solid #ccc;">{{ r.timestamp.strftime('%Y-%m-%d %H:%M:%S') }}</td>
                                <td style="padding: 8px; border-bottom: 1px solid #ccc;">{{ r.value }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>

                <!-- Chart Section -->
                <div style="flex: 2 1 700px; min-width: 450px;">
                    <canvas id="distanceChart" style="width: 100%; height: 400px; border: 3px solid black; border-radius: 8px;"></canvas>
                </div>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script>
            const ctx = document.getElementById('distanceChart').getContext('2d');
            const distanceChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: {{ labels | safe }},
                    datasets: [{
                        label: 'Distance (cm)',
                        data: {{ values | safe }},
                        borderWidth: 2,
                        borderColor: 'blue',
                        fill: false,
                        tension: 0.3
                    }]
                },
                options: {
                    plugins: {
                        legend: {
                            labels: {
                                font: { weight: 'bold' }
                            }
                        }
                    },
                    scales: {
                        x: {
                            ticks: { font: { weight: 'bold' } }
                        },
                        y: {
                            beginAtZero: true,
                            ticks: { font: { weight: 'bold' } }
                        }
                    }
                }
            });

            function fetchLatest() {
                fetch('/latest')
                    .then(response => response.json())
                    .then(data => {
                        // Chart update
                        distanceChart.data.labels = data.labels;
                        distanceChart.data.datasets[0].data = data.values;
                        distanceChart.update();

                        // Status update
                        const alertBox = document.getElementById('distance-alert');
                        const latestSpan = document.getElementById('latest-distance');
                        const latest = data.latest;

                        if (latest !== null) {
                            latestSpan.textContent = latest;
                            if (latest < 20) {
                                alertBox.style.backgroundColor = '#dc3545';
                                alertBox.innerHTML = `🚨 Too Close: <span id="latest-distance">${latest}</span> cm`;
                            } else if (latest < 100) {
                                alertBox.style.backgroundColor = '#ffc107';
                                alertBox.innerHTML = `⚠️ Medium Distance: <span id="latest-distance">${latest}</span> cm`;
                            } else {
                                alertBox.style.backgroundColor = '#28a745';
                                alertBox.innerHTML = `✅ Safe Distance: <span id="latest-distance">${latest}</span> cm`;
                            }
                        } else {
                            latestSpan.textContent = "--";
                            alertBox.innerHTML = "Distance Status: --";
                            alertBox.style.backgroundColor = '#6c757d';
                        }

                        // Table update
                        const tableBody = document.getElementById('distance-table-body');
                        tableBody.innerHTML = "";
                        data.rows.forEach(row => {
                            const tr = document.createElement("tr");
                            tr.innerHTML = `<td>${row.time}</td><td>${row.value}</td>`;
                            tableBody.appendChild(tr);
                        });
                    });
            }

            function fetchAlarmState() {
                fetch('/alarm/state')
                    .then(response => response.json())
                    .then(data => {
                        const alarmStatus = document.getElementById("alarm-status");
                        const toggleBtn = document.getElementById("toggle-alarm");

                        if (data.enabled) {
                            alarmStatus.textContent = "🔔 Alarm ON";
                            toggleBtn.textContent = "🔕 Disable Alarm";
                            toggleBtn.style.backgroundColor = "#dc3545";
                            toggleBtn.style.color = "white";
                        } else {
                            alarmStatus.textContent = "🔕 Alarm OFF";
                            toggleBtn.textContent = "🔔 Enable Alarm";
                            toggleBtn.style.backgroundColor = "#28a745";
                            toggleBtn.style.color = "white";
                        }

                        // 🛑 Disable button if Pico is offline
                        if (data.pico_status !== "online") {
                            toggleBtn.disabled = true;
                            toggleBtn.style.opacity = "0.5";
                            toggleBtn.title = "Pico W is offline — cannot change alarm state.";
                        } else {
                            toggleBtn.disabled = false;
                            toggleBtn.style.opacity = "1";
                            toggleBtn.title = "";
                        }
                    });
            }


           function fetchPicoStatus() {
                fetch('/pico/status')
                    .then(response => response.json())
                    .then(data => {
                        const statusSpan = document.getElementById("pico-status");
                        const status = data.status;

                        if (status === 'online') {
                            statusSpan.textContent = "📶 CONNECTED";
                            statusSpan.style.color = "green";
                        } else if (status === 'offline') {
                            statusSpan.textContent = "🔌 DISCONNECTED";
                            statusSpan.style.color = "red";
                        } else {
                            statusSpan.textContent = "❔ UNKNOWN";
                            statusSpan.style.color = "gray";
                        }
                    });
           }

	   document.getElementById("toggle-alarm").addEventListener("click", () => {
               fetch('/alarm/toggle')
                   .then(() => {
                       fetchAlarmState(); // Update UI after toggling
                   });
  	   });


           setInterval(() => {
    	       fetchLatest();
    	       fetchAlarmState();
               fetchPicoStatus();
           }, 5000);

        </script>
    ''', distance=latest.value if latest else None, readings=readings, labels=labels, values=values, pico_status=pico_status)

@app.route('/latest')
def latest():
    readings = DistanceReading.query.order_by(DistanceReading.timestamp.desc()).limit(10).all()
    labels = [r.timestamp.strftime("%H:%M:%S") for r in reversed(readings)]
    values = [r.value for r in reversed(readings)]
    latest_value = values[-1] if values else None
    rows = [{"time": r.timestamp.strftime('%Y-%m-%d %H:%M:%S'), "value": r.value} for r in readings]

    return jsonify({
        "latest": latest_value,
        "labels": labels,
        "values": values,
        "rows": rows
    })

@app.route('/alarm/toggle')
def toggle_alarm():
    alarm_state['enabled'] = not alarm_state['enabled']
    state = 'on' if alarm_state['enabled'] else 'off'
    mqtt.publish('device/alarm', state)

    with app.app_context():
        event = AlarmEvent(type='toggled', detail=f'Alarm turned {state.upper()}')
        db.session.add(event)
        db.session.commit()

    return f"Alarm turned {state}"

@app.route('/alarm/state')
def get_alarm_state():
    status_obj = PicoStatus.query.first()
    pico_status = status_obj.status if status_obj else "unknown"
    return jsonify({
        'enabled': alarm_state['enabled'],
        'pico_status': pico_status
    })


@app.route('/alarm-history')
def alarm_history():
    events = AlarmEvent.query.order_by(AlarmEvent.timestamp.desc()).limit(50).all()
    return render_template_string('''
        <p>
            <a href="/" style="
                display: inline-block;
                padding: 10px 20px;
                font-size: 16px;
                font-weight: bold;
                color: white;
                background-color: #007BFF;
                text-decoration: none;
                border-radius: 6px;
                margin-top: 20px;
            ">🏠 Home</a>
        </p>
        <h1>📜 Alarm Event History</h1>
        <table border="1" cellpadding="5">
            <thead>
                <tr><th>Time</th><th>Type</th><th>Detail</th></tr>
            </thead>
            <tbody>
                {% for e in events %}
                <tr>
                    <td>{{ e.timestamp.strftime('%Y-%m-%d %H:%M:%S') }}</td>
                    <td>{{ e.type }}</td>
                    <td>{{ e.detail }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    ''', events=events)

@app.route('/pico/status')
def get_pico_status():
    status_obj = PicoStatus.query.first()
    pico_status = status_obj.status if status_obj else "unknown"
    return jsonify({'status': pico_status})

@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ MQTT connected successfully.")
        mqtt.subscribe('motion/distance')
        mqtt.subscribe('device/status')
        mqtt.subscribe('device/alarm/request')
        print("🔄 Subscribed to topics: motion/distance, device/status, device/status/requests")
    else:
        print(f"❌ MQTT failed to connect. Return code: {rc}")

@mqtt.on_message()
def handle_message(client, userdata, message):
    topic = message.topic
    payload = message.payload.decode()
    
    if topic == 'motion/distance':
        try:
            dist = float(payload)
            print(f"📩 Received from MQTT: {dist} m")
            if 0 < dist < 5:
                with app.app_context():
                    reading = DistanceReading(value=dist * 100.0)
                    db.session.add(reading)
                    db.session.commit()
                    print(f"✅ Saved to database as {dist * 100.0:.2f} cm")

		# 🔔 ALARM TRIGGER CHECK
                if dist < 0.2 and alarm_state['enabled']:
                    now = time()
                    if now - last_pushover_time['timestamp'] > PUSHOVER_COOLDOWN:
                        last_pushover_time['timestamp'] = now
                        print("🚨 Triggering alarm notification via Pushover...")
                        try:
                            conn = http.client.HTTPSConnection("api.pushover.net:443")
                            conn.request("POST", "/1/messages.json",
                                urllib.parse.urlencode({
                                    "token": "aht73m2ii3vyotoz58swdkhrdmya4f",
                                    "user": "upcm7jkikk2p2i16i7dfxicnwqodp9",
                                    "message": f"🚨 Alarm Triggered! Object too close: {dist*100:.1f} cm",
                                }), { "Content-type": "application/x-www-form-urlencoded" })
                            conn.getresponse()
                        except Exception as e:
                            print(f"❌ Error sending Pushover message: {e}")
                        with app.app_context():
                            event = AlarmEvent(type='triggered', detail=f'Object too close: {dist*100:.1f} cm')
                            db.session.add(event)
                            db.session.commit()
                    else:
                        print("⏳ Skipping pushover: cooldown active")
        except Exception as e:
            print(f"❌ Error processing distance: {e}")

    elif topic == 'device/status':
        print(f"�� Pico W status update: {payload}")
        set_pico_status(payload)

        if payload == "online":
            try:
                conn = http.client.HTTPSConnection("api.pushover.net:443")
                conn.request("POST", "/1/messages.json",
                    urllib.parse.urlencode({
                        "token": "aht73m2ii3vyotoz58swdkhrdmya4f",
                        "user": "upcm7jkikk2p2i16i7dfxicnwqodp9",
                        "message": "📶 Pico W is now online and connected.",
                    }), { "Content-type": "application/x-www-form-urlencoded" })
                conn.getresponse()
                print("✅ Pushover: Pico online message sent.")
            except Exception as e:
                print(f"❌ Error sending Pushover (online): {e}")

        elif payload == "offline":
            try:
                conn = http.client.HTTPSConnection("api.pushover.net:443")
                conn.request("POST", "/1/messages.json",
                    urllib.parse.urlencode({
                        "token": "aht73m2ii3vyotoz58swdkhrdmya4f",
                        "user": "upcm7jkikk2p2i16i7dfxicnwqodp9",
                        "message": "🔌 Pico W is offline or disconnected.",
                    }), { "Content-type": "application/x-www-form-urlencoded" })
                conn.getresponse()
                print("✅ Pushover: Pico offline message sent.")
            except Exception as e:
                print(f"❌ Error sending Pushover (offline): {e}")


    elif topic == 'device/alarm/request':
        print("🔄 Pico requested current alarm state.")
        state = 'on' if alarm_state['enabled'] else 'off'
        mqtt.publish('device/alarm', state)
        print(f"✅ Sent alarm state: {state}")




def start_mqtt():
    try:
        mqtt.client.connect(app.config['MQTT_BROKER_URL'], app.config['MQTT_BROKER_PORT'], 60)
        print("📶 MQTT manual connection attempted.")
        mqtt.client.loop_start()
        print("📡 MQTT loop started.")
    except Exception as e:
        print(f"❌ Failed to connect to MQTT broker: {e}")

if __name__ == '__main__':
    threading.Thread(target=start_mqtt).start()
    app.run(host='0.0.0.0', port=5000)

