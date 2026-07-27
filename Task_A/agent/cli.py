# Entrypoint CLI driver (run, resume, replay)

import sys
import argparse
from .loop import AgentLoop
from .observability import replay_run

def main():
    parser = argparse.ArgumentParser(description="Adversarial Agent Runtime CLI")
    subparsers = parser.add_subparsers(dest="command")

    run_p = subparsers.add_parser("run")
    run_p.add_argument("--task", required=True)
    run_p.add_argument("--run-id", default="run_demo")

    resume_p = subparsers.add_parser("resume")
    resume_p.add_argument("run_id")

    replay_p = subparsers.add_parser("replay")
    replay_p.add_argument("run_id")

    args = parser.parse_args()

    if args.command == "run":
        agent = AgentLoop(run_id=args.run_id, task=args.task)
        agent.run()
    elif args.command == "resume":
        agent = AgentLoop(run_id=args.run_id, task="")
        agent.run()
    elif args.command == "replay":
        replay_run(args.run_id)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()