from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import redis
import time
import os
import argparse
from dotenv import load_dotenv

def parse_args():
    parser = argparse.ArgumentParser()
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    
    load_dotenv()
    influxdb_url = os.getenv("INFLUXDB_URL")
    influxdb_token = os.getenv("INFLUXDB_TOKEN")
    influxdb_org = os.getenv("INFLUXDB_ORG")
    redis_url = os.getenv("REDIS_URL")

    # Redis 설정
    r = redis.from_url(
        redis_url,
        decode_responses=True
    )

    client = InfluxDBClient(
        url=influxdb_url,
        token=influxdb_token,
        org=influxdb_org
    )
    write_api = client.write_api(write_options=SYNCHRONOUS)

    while True:
        for queue_name in ['P1-A','P2-A','P1-B','P2-B','P3']:
            queue_length = r.llen(queue_name)
            #point = Point("queue_status").tag("queue", queue_name).field("length", queue_length)
            #write_api.write(bucket=bucket, org=org, record=point)
            print(f"{queue_name} Queue length: {queue_length}")
        time.sleep(5)