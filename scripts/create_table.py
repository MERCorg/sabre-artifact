import argparse
import json
import os

from email import parser
import re

def average(values):
    return sum(values) / len(values) if values else None

def print_float(value: float|None) -> str:
    return f"{value / 1000.0:.1f}" if value is not None else "-"

def human_sort(text: str) -> list:
    """
    Sort key function for sorting strings in human-friendly order.
    Splits text into alternating strings and integers for natural sorting.
    """
    parts = []
    for part in re.split(r'(\d+)', text):
        if part.isdigit():
            parts.append(int(part))
        else:
            parts.append(part)
    return parts

def read_results(directory: str) -> dict[str, dict[str, float]]:
    results = {}

    # Open all the JSON files in the directory and yield their contents
    for file in os.listdir(directory):
        if file.endswith(".json"):
            with open(os.path.join(directory, file), "r", encoding="utf-8") as f:
                for line in f:
                    result = json.loads(line)

                    rewriter = result["rewriter"]
                    experiment = result["experiment"]
                    # Remove the .dataspec and .rec suffix
                    experiment = os.path.splitext(experiment)[0]

                    if experiment not in results:
                        results[experiment] = {}

                    if rewriter not in results[experiment]:
                        results[experiment][rewriter] = {}
                    
                    results[experiment][rewriter] = average(result.get("timings", []))

    return results

def create_table(json_path: str) -> None:
    results = read_results(json_path)
    # Generate a latex table from the results
    print("\\documentclass{standalone}")
    print("\\usepackage{booktabs}")

    print("\\begin{document}")

    print("\\begin{tabular}{lrrrr}")
    print("\\toprule")
    print("Experiment & Jitty (s) & Jittyc (s) & Innermost (s) & Sabre (s) \\\\")

    print("\\midrule")

    # Sort the experiments by name
    for experiment, data in sorted(results.items()):
        jitty = print_float(data.get("jitty", None))
        jittyc = print_float(data.get("jittyc", None))
        innermost = print_float(data.get("innermost", None))
        sabre = print_float(data.get("sabre", None))

        print(f"{experiment} & {jitty} & {jittyc} & {innermost} & {sabre} \\\\")

    print("\\bottomrule")
    print("\\end{tabular}")
    print("\\end{document}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="run.py")
    parser.add_argument("input", help="Input JSON directory")

    args = parser.parse_args()

    create_table(args.input)
