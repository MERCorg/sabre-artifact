import argparse
from email import parser
import json
from statistics import mean

def average(values):
    return mean(values) if values else 0.0

def print_float(value: float) -> str:
    return f"{value:.1f}"

def create_table(json_path: str) -> None:
    with open(json_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    results = {}
    rewriters = set()

    for line in lines:
        obj = json.loads(line)
        rw = obj["rewriter"]
        bn = obj["benchmark_name"]
        timings = obj.get("timings", [])
        rewriters.add(rw)
        results.setdefault(bn, {})[rw] = average(timings)

    rewriters = sorted(rewriters)

    # Header
    first = True
    for rw in rewriters:
        if first:
            print(f"{rw:>30}", end="")
            first = False
        else:
            print(f"{rw:>10} |", end="")
    print()

    for bench in sorted(results.keys()):
        print(f"{bench:>30}", end="")
        for rw in rewriters:
            val = results[bench].get(rw)
            if val is not None:
                print(f"| {print_float(val):>10}", end="")
            else:
                print(f"| {'-':>10}", end="")
        print()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="run.py")
    parser.add_argument("input", help="Input JSON file")

    args = parser.parse_args()

    create_table(args.input)
