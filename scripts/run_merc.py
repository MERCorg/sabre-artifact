#!/usr/bin/env python3

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

from pathlib import Path
from statistics import mean

# make parent directory importable so we can import MERCpy as a module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "merc-py"))
from merc import RunProcess, MercLogger


class Rewriter:
    INNERMOST = "innermost"
    SABRE = "sabre"

class ParserOutput:
    """Callable class that captures stdout and extracts timing information."""

    def __init__(self, pattern, logger: MercLogger):
        self.logger = logger
        self.timings = []
        self.pattern = pattern

    def __call__(self, line: str) -> None:
        """Called for each line of stdout."""
        self.logger.info(line)

        m = self.pattern.search(line)
        if m:
            ms = float(m.group(1))
            self.timings.append(ms)

def benchmark(
    logger: MercLogger, merc_path: Path, rewriter: str, rec_dir: Path, output_dir: Path
) -> None:
    if rewriter not in (Rewriter.INNERMOST, Rewriter.SABRE):
        raise ValueError("Invalid rewriter")

    merc_rewrite_bin = shutil.which("merc-rewrite", path=merc_path)
    if merc_rewrite_bin is None:
        raise RuntimeError("Cannot find merc-rewrite")

    pattern = (
        re.compile(r"Innermost rewrite took ([0-9]+) ms")
        if rewriter == Rewriter.INNERMOST
        else re.compile(r"Sabre rewrite took ([0-9]+) ms")
    )

    with open(
        os.path.join(output_dir, f"merc_{rewriter}_results.json"), "w", encoding="utf-8"
    ) as result_file:
        for file in rec_dir.glob("*.rec"):
            logger.info(f"Benchmarking {file}")

            results = {
                "experiment": os.path.basename(file),
                "rewriter": rewriter,
                "timings": [],
            }

            for _ in range(5):
                parser = ParserOutput(pattern, logger)

                try:
                    RunProcess(
                        merc_rewrite_bin,
                        ["rewrite", str(rewriter), str(file)],
                        read_stdout=parser,
                        max_time=600,
                    )
                except Exception as e:
                    logger.error(f"Benchmark {file} timed out or crashed: {e}")
                    break

                results["timings"].extend(parser.timings)

            json.dump(results, result_file)
            result_file.write("\n")
            result_file.flush()


def main() -> None:
    parser = argparse.ArgumentParser(prog="run.py")
    parser.add_argument("merc_path", help="Path to the merc binary directory")
    parser.add_argument(
        "rewriter", choices=(Rewriter.INNERMOST, Rewriter.SABRE), help="rewriter to use"
    )
    parser.add_argument("rec_path", type=Path, help="Path to the REC specifications")
    parser.add_argument("output_dir", type=Path, help="Output JSON file")

    args = parser.parse_args()

    logger = MercLogger(args.output_dir / f"merc_benchmark_{args.rewriter}.log")

    benchmark(logger, args.merc_path, args.rewriter, args.rec_path, args.output_dir)


if __name__ == "__main__":
    main()
