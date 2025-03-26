from ProcessSimulator import ProcessSimulator
import argparse

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--process_name", type=str, required=True, help="Process name")
    parser.add_argument("--status_url", type=str, help="Status URL")
    parser.add_argument("--process_url", type=str, help="Process URL")
    parser.add_argument("--mode", type=str, choices=["producer", "consumer"], required=True, help="Mode: producer or consumer")
    parser.add_argument("--sim_speed", type=float, default=5.0, help="Simulation speed")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    
    sim = ProcessSimulator(
        process_name=args.process_name,
        status_url=args.status_url,
        process_url=args.process_url,
        sim_speed=args.sim_speed
    )
    
    if args.mode == "producer":
        sim.run_producer()
    elif args.mode == "consumer":
        sim.run_consumer()