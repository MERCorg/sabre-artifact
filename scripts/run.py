import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from statistics import mean

#!/usr/bin/env python3

class Rewriter:
    INNERMOST = "innermost"
    SABRE = "sabre"

def benchmark(output_path: str, rewriter: str) -> None:
    cwd = Path.cwd()

    if rewriter not in (Rewriter.INNERMOST, Rewriter.SABRE):
        raise ValueError("Invalid rewriter")

    # Build the tool
    subprocess.run(["cargo", "build", "--profile", "bench", "--bin", "merc-rewrite"], check=True)

    # Prefer local target/release binary
    bin_name = "merc-rewrite.exe" if os.name == "nt" else "merc-rewrite"
    candidate = cwd / "target" / "release" / bin_name
    if candidate.exists():
        mcrl2_rewrite_path = str(candidate)
    else:
        found = shutil.which("merc-rewrite")
        if not found:
            raise FileNotFoundError("merc-rewrite not found")
        mcrl2_rewrite_path = found

    pattern = re.compile(r"Innermost rewrite took ([0-9]+) ms") if rewriter == Rewriter.INNERMOST else re.compile(r"Sabre rewrite took ([0-9]+) ms")

    outp = Path(output_path)
    if outp.parent:
        outp.parent.mkdir(parents=True, exist_ok=True)

    with outp.open("w", encoding="utf-8") as result_file:
        examples_dir = Path("examples/REC/rec")
        if not examples_dir.exists():
            raise FileNotFoundError("examples/REC/rec not found")

        for file in sorted(examples_dir.iterdir()):
            path = file
            benchmark_name = path.stem
            print(f"Benchmarking {benchmark_name}")

            cmd = [mcrl2_rewrite_path, "rewrite", rewriter, str(path)]

            measurements = {"rewriter": rewriter, "benchmark_name": benchmark_name, "timings": []}

            for _ in range(5):
                try:
                    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                except subprocess.TimeoutExpired:
                    print(f"Benchmark {benchmark_name} timed out or crashed")
                    break

                output_lines = proc.stdout.splitlines() + proc.stderr.splitlines()
                found_timing = False
                for line in output_lines:
                    m = pattern.search(line)
                    if m:
                        ms = float(m.group(1))
                        timing_s = ms / 1000.0
                        print(f"Benchmark {benchmark_name} timing {timing_s} milliseconds")
                        measurements["timings"].append(timing_s)
                        found_timing = True

                if not found_timing and proc.returncode != 0:
                    print(f"Benchmark {benchmark_name} timed out or crashed")
                    break

            json.dump(measurements, result_file)
            result_file.write("\n")

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
    parser.add_argument("output", help="Output JSON file")
    parser.add_argument("rewriter", choices=(Rewriter.INNERMOST, Rewriter.SABRE), help="rewriter to use")


    args = parser.parse_args()

    benchmark(args.output, args.rewriter)