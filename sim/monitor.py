from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import redis
import time
import os
import argparse
from dotenv import load_dotenv

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue_name", type=str, required=True, help="Queue name")
    parser.add_argument("--bucket", type=str, default="redis_metrics", help="InfluxDB bucket")
    parser.add_argument("--influx_url", type=str, default="http://localhost:8086", help="InfluxDB URL")
    parser.add_argument("--influx_token", type=str, default=None, help="InfluxDB token")
    parser.add_argument("--influx_org", type=str, default="org_kpmg", help="InfluxDB organization")
    parser.add_argument("--redis_host", type=str, default="localhost", help="Redis host")
    parser.add_argument("--redis_port", type=int, default=6379, help="Redis port")
    parser.add_argument("--redis_password", type=str, default=None, help="Redis password")
    return parser.parse_args()

if __name__ == "__main__":
    load_dotenv()
    args = parse_args()

    # Redis 설정
    r = redis.Redis(host='localhost', port=6379, db=0)
    queue_name = 'P2_queue'

    # InfluxDB 설정
    token = os.getenv("INFLUXDB_TOKEN")
    org = args.influx_org
    bucket = args.bucket
    influx_url = args.influx_url

    client = InfluxDBClient(
        url=influx_url,
        token=token,
        org=org
    )
    write_api = client.write_api(write_options=SYNCHRONOUS)

    while True:
        queue_length = r.llen(queue_name)
        point = Point("queue_status").tag("queue", queue_name).field("length", queue_length)
        write_api.write(bucket=bucket, org=org, record=point)
        print(f"Queue length: {queue_length}")
        time.sleep(5)