import os
import argparse
from ProcessSimulator import ProcessSimulator
from dotenv import load_dotenv

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--process_name", type=str, required=True, help="Process name")
    parser.add_argument("--mode", type=str, choices=["producer","relay","consumer"], required=True, help="Mode: producer or consumer")
    parser.add_argument("--process_prev", type=str, default=None, help="Start time for simulation")
    parser.add_argument("--process_next", type=str, default=None, help="End time for simulation")
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
    redis_password = os.getenv("REDIS_PASSWORD")
    
    sim = ProcessSimulator(
        process_name=args.process_name,
        mode=args.mode,
        process_prev=args.process_prev,
        process_next=args.process_next,
        influxdb_url=influxdb_url,
        influxdb_token=influxdb_token,
        influxdb_org=influxdb_org,
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