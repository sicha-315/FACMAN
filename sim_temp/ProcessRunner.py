import os
import argparse
from ProcessSimulator import ProcessSimulator
from dotenv import load_dotenv

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, choices=["producer","relay","consumer"], required=True, help="Mode: producer or consumer")
    parser.add_argument("--process_name", type=str, required=True, help="Process name")
    parser.add_argument("--process_next", type=str, default=None, help="Next process name")
    parser.add_argument("--agent_url", type=str, default=None, help="Agent URL")
    parser.add_argument("--sim_speed", type=float, default=200.0, help="Simulation speed")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    
    load_dotenv()
    influxdb_url = os.getenv("INFLUXDB_URL")
    influxdb_token = os.getenv("INFLUXDB_TOKEN")
    influxdb_org = os.getenv("INFLUXDB_ORG")
    redis_url = os.getenv("REDIS_URL")
    
    for i in range(1, 5, 1):
        sim = ProcessSimulator(
            mode=args.mode,
            process_name=args.process_name,
            process_next=args.process_next,
            influxdb_url=influxdb_url,
            influxdb_token=influxdb_token,
            influxdb_org=influxdb_org,
            redis_url=redis_url,
            agent_url=args.agent_url,
            sim_speed=args.sim_speed,
            day = i
        )
        
        sim.run()