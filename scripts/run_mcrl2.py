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
    JITTY = "jitty"
    JITTYC = "jittyc"


TIME_REGEX = re.compile(r"printing: ([0-9]+) milliseconds.")


def benchmark(mcrl2_path: Path, rewriter: str, rec_dir: Path, output_dir: Path) -> None:
    cwd = Path.cwd()

    if rewriter not in (Rewriter.JITTY, Rewriter.JITTYC):
        raise ValueError("Invalid rewriter")

    mcrl2rewrite_bin = shutil.which("mcrl2rewrite", path=mcrl2_path)
    if mcrl2rewrite_bin is None:
        raise RuntimeError("Cannot find mcrl2rewrite")

    with open(
        os.path.join(output_dir, f"mcrl2_{rewriter}_results.json"), "w", encoding="utf-8"
    ) as result_file:
        for file in rec_dir.glob("*.dataspec"):
            expressions = file.with_suffix(".expressions")

            print(f"Benchmarking {file}")

            results = {"experiment": os.path.basename(file), "rewriter": rewriter, "timings": []}

            for _ in range(5):
                try:
                    proc = subprocess.run(
                        [mcrl2rewrite_bin, "--timings", file, expressions],
                        capture_output=True,
                        text=True,
                        timeout=600,
                        check=True,
                    )
                except Exception as e:
                    print(f"Benchmark {file} timed out or crashed")
                    break

                output_lines = proc.stdout.splitlines() + proc.stderr.splitlines()
                for line in output_lines:
                    m = TIME_REGEX.search(line)
                    if m:
                        ms = float(m.group(1))
                        results["timings"].append(ms)

            print(results)

            json.dump(results, result_file)
            result_file.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="run.py")
    parser.add_argument(
        "mcrl2_path", type=Path, help="Path to the mcrl2 binary directory"
    )
    parser.add_argument(
        "rewriter", choices=(Rewriter.JITTY, Rewriter.JITTYC), help="rewriter to use"
    )
    parser.add_argument("rec_path", type=Path, help="Path to the REC specifications")
    parser.add_argument("output_dir", type=Path, help="Output directory")

    args = parser.parse_args()

    benchmark(args.mcrl2_path, args.rewriter, args.rec_path, args.output_dir)
