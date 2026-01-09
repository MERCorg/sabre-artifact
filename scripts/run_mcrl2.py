#!/usr/bin/env python3

import argparse
import json
import os
import re
import shutil
import sys

from pathlib import Path

# make parent directory importable so we can import MERCpy as a module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "merc-py"))
from merc import RunProcess, MercLogger

class Rewriter:
    JITTY = "jitty"
    JITTYC = "jittyc"


TIME_REGEX = re.compile(r"rewriting: ([0-9]+) milliseconds.")


class ParserOutput:
    """Callable class that captures stdout and extracts timing information."""

    def __init__(self, logger: MercLogger):
        self.logger = logger
        self.timings = []

    def __call__(self, line: str) -> None:
        """Called for each line of stdout."""
        self.logger.info(line)

        m = TIME_REGEX.search(line)
        if m:
            ms = float(m.group(1))
            self.timings.append(ms)


def benchmark(
    logger: MercLogger, mcrl2_path: Path, rewriter: str, rec_dir: Path, output_dir: Path
) -> None:
    if rewriter not in (Rewriter.JITTY, Rewriter.JITTYC):
        raise ValueError("Invalid rewriter")

    mcrl2rewrite_bin = shutil.which("mcrl2rewrite", path=mcrl2_path)
    if mcrl2rewrite_bin is None:
        raise RuntimeError("Cannot find mcrl2rewrite")

    with open(
        os.path.join(output_dir, f"mcrl2_{rewriter}_results.json"),
        "a",
        encoding="utf-8",
    ) as result_file:
        for file in rec_dir.glob("*.dataspec"):
            expressions = file.with_suffix(".expressions")

            logger.info(f"Benchmarking {file}")
            results = {
                "experiment": os.path.basename(file),
                "rewriter": rewriter,
                "timings": [],
            }

            for _ in range(5):
                stdout_capture = ParserOutput(logger)

                try:
                    RunProcess(
                        mcrl2rewrite_bin,
                        [
                            "-v",
                            "--timings",
                            f"-r{rewriter}",
                            str(file),
                            str(expressions),
                        ],
                        read_stdout=stdout_capture,
                        max_time=600,
                    )
                except Exception as e:
                    logger.error(f"Benchmark {file} timed out or crashed: {e}")
                    break

                # Extract timings from the capture object instead of proc.stdout
                results["timings"].extend(stdout_capture.timings)

            print(results)

            json.dump(results, result_file)
            result_file.write("\n")
            result_file.flush()


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

    logger = MercLogger(args.output_dir / f"mcrl2_benchmark_{args.rewriter}.log")

    benchmark(logger, args.mcrl2_path, args.rewriter, args.rec_path, args.output_dir)
