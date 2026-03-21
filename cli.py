# AtlasKernel v0.1.0

import argparse
import json

from core.router import route_text
from core.executor import execute_route, run_execution


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("text", help="Input text")
    args = parser.parse_args()

    routing = route_text(args.text)
    execution = execute_route(routing.route, routing.input)
    result = run_execution(execution, routing.input)

    print(json.dumps({
        "routing": routing.__dict__,
        "execution": execution.__dict__,
        "result": result
    }, indent=2))


if __name__ == "__main__":
    main()
