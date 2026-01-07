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

def benchmark(mcrl2_path: Path, rewriter: str, rec_dir: Path, output_dir: Path) -> None:

    if rewriter not in (Rewriter.INNERMOST, Rewriter.SABRE):
        raise ValueError("Invalid rewriter")

    merc_rewrite_bin = shutil.which("merc-rewrite", path=mcrl2_path)
    if merc_rewrite_bin is None:
        raise RuntimeError("Cannot find merc-rewrite")

    pattern = re.compile(r"Innermost rewrite took ([0-9]+) ms") if rewriter == Rewriter.INNERMOST else re.compile(r"Sabre rewrite took ([0-9]+) ms")

    with open(os.path.join(output_dir, f"merc_{rewriter}_results.json"), "w", encoding="utf-8") as result_file:
        for file in rec_dir.glob("*.rec"):
            print(f"Benchmarking {file}")

            results = {"experiment":  os.path.basename(file), "rewriter": rewriter, "timings": []}

            for _ in range(5):
                try:
                    proc = subprocess.run([merc_rewrite_bin, "rewrite", file], capture_output=True, text=True, timeout=600, check=True)
                except Exception as e:
                    print(f"Benchmark {results} timed out or crashed")
                    break

                output_lines = proc.stdout.splitlines() + proc.stderr.splitlines()
                for line in output_lines:
                    m = pattern.search(line)
                    if m:
                        ms = float(m.group(1))
                        results["timings"].append(ms)

            json.dump(results, result_file)
            result_file.write("\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="run.py")
    parser.add_argument("merc_path", help="Path to the merc binary directory")
    parser.add_argument("rewriter", choices=(Rewriter.INNERMOST, Rewriter.SABRE), help="rewriter to use")
    parser.add_argument("rec_path", type=Path, help="Path to the REC specifications")
    parser.add_argument("output", help="Output JSON file")

    args = parser.parse_args()

    benchmark(args.merc_path, args.rewriter, args.rec_path, args.output)