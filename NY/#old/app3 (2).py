import eventlet
eventlet.monkey_patch()

import os
import time
from flask import Flask, render_template
from flask_socketio import SocketIO
from influxdb_client import InfluxDBClient
from dotenv import load_dotenv
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

INFLUX_URL = os.getenv("INFLUX_URL")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")

influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)


def get_recent_status(bucket):
    query = f'''
    from(bucket: "{bucket}")
      |> range(start: -30s)
      |> filter(fn: (r) => r._measurement == "status_log" and r._field == "event_type")
      |> sort(columns: ["_time"], desc: true)
      |> limit(n: 3)
    '''
    result = influx_client.query_api().query(org=INFLUX_ORG, query=query)

    events = []
    for table in result:
        for record in table.records:
            events.append(record.get_value())
    return events if events else None


def emit_status():
    prev_event_p1 = None
    prev_event_p2 = None

    while True:
        # P1
        events_p1 = get_recent_status("P1_status")
        if events_p1:
            latest_p1 = events_p1[0]
            print(f"[Influx] P1 상태: {latest_p1}")
            if latest_p1 != prev_event_p1:
                print(f"[Influx] P1 상태 변경: {latest_p1}")
                socketio.emit('status_update', {
                    'P1-A': {'event_type': latest_p1}
                })
                prev_event_p1 = latest_p1

        # P2
        events_p2 = get_recent_status("P2_status")
        if events_p2:
            latest_p2 = events_p2[0]
            print(f"[Influx] P2 상태: {latest_p2}")
            if latest_p2 != prev_event_p2:
                print(f"[Influx] P2 상태 변경: {latest_p2}")
                socketio.emit('status_update', {
                    'P2-A': {'event_type': latest_p2}
                })
                prev_event_p2 = latest_p2

        socketio.sleep(1)


@app.route("/")
def index():
    return render_template("index.html")


@socketio.on('connect')
def handle_connect():
    print('Client connected')

    # 접속 시 초기 상태 전달
    events_p1 = get_recent_status("P1_status")
    if events_p1:
        latest_p1 = events_p1[0]
        socketio.emit('status_update', {
            'P1-A': {'event_type': latest_p1}
        })

    events_p2 = get_recent_status("P2_status")
    if events_p2:
        latest_p2 = events_p2[0]
        socketio.emit('status_update', {
            'P2-A': {'event_type': latest_p2}
        })


if __name__ == "__main__":
    socketio.start_background_task(target=emit_status)
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, use_reloader=False)
