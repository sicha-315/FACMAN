import os
import argparse
from ProcessSimulator import ProcessSimulator
from dotenv import load_dotenv

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--process_name", type=str, required=True, help="Process name")
    parser.add_argument("--mode", type=str, choices=["producer", "consumer"], required=True, help="Mode: producer or consumer")
    parser.add_argument("--status_bucket",  type=str, required=True, help="InfluxDB bucket for status logs")
    parser.add_argument("--process_bucket", type=str, required=True, help="InfluxDB bucket for process logs")
    parser.add_argument("--agent_url", type=str, default=None, help="Agent URL")
    parser.add_argument("--sim_speed", type=float, default=5.0, help="Simulation speed")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    
    load_dotenv()
    influxdb_url = os.getenv("INFLUXDB_URL")
    influxdb_token = os.getenv("INFLUXDB_TOKEN")
    influxdb_org = os.getenv("INFLUXDB_ORG")

    redis_host = os.getenv("REDIS_HOST")
    redis_port = int(os.getenv("REDIS_PORT"))
    redis_password = os.getenv("REDIS_PASSWORD") or None
    
    sim = ProcessSimulator(
        process_name=args.process_name,
        influxdb_url=influxdb_url,
        influxdb_token=influxdb_token,
        influxdb_org=influxdb_org,
        influxdb_status_bucket=args.status_bucket,
        influxdb_process_bucket=args.process_bucket,
        redis_host=redis_host,
        redis_port=redis_port,
        redis_password=redis_password,
        agent_url=args.agent_url,
        sim_speed=args.sim_speed
    )
    
    if args.mode == "producer":
        print(f"Producer started: {args.process_name}")
        sim.run_producer()
    elif args.mode == "consumer":
        print(f"Consumer started: {args.process_name}")
        sim.run_consumer()