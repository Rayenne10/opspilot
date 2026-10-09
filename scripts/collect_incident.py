"""Collect bounded, read-only pod evidence with the user's existing kubectl context."""

import argparse
import json
import re
import subprocess
from pathlib import Path


def valid_name(value):
    if not re.fullmatch(r"[a-z0-9]([-a-z0-9.]{0,251}[a-z0-9])?", value):
        raise argparse.ArgumentTypeError("Use a valid Kubernetes resource name")
    return value


def run(args):
    try:
        result = subprocess.run(
            ["kubectl", "--request-timeout=10s", *args],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        raise SystemExit("kubectl is missing or the cluster request timed out") from None
    if result.returncode:
        # Do not persist provider/server error strings that may contain sensitive information.
        return "[Collection unavailable: verify permissions and container state]"
    return result.stdout[:20000]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pod", type=valid_name)
    parser.add_argument("--namespace", "-n", type=valid_name, default="default")
    parser.add_argument("--container", "-c", type=valid_name)
    parser.add_argument("--output", type=Path, default=Path("incident.json"))
    args = parser.parse_args()
    container = ["-c", args.container] if args.container else []
    describe = run(["describe", "pod", args.pod, "-n", args.namespace])
    previous = run(
        [
            "logs",
            args.pod,
            "-n",
            args.namespace,
            *container,
            "--previous",
            "--tail=100",
            "--limit-bytes=18000",
        ]
    )
    current = run(
        ["logs", args.pod, "-n", args.namespace, *container, "--tail=100", "--limit-bytes=18000"]
    )
    incident = {
        "title": f"Investigate pod {args.pod}"[:160],
        "namespace": args.namespace,
        "symptom": "",
        "logs": ("PREVIOUS:\n" + previous + "\nCURRENT:\n" + current)[:20000],
        "events": describe,
    }
    # The file can contain sensitive operational data; only its owner can read it.
    with args.output.open("w", encoding="utf-8") as output:
        args.output.chmod(0o600)
        output.write(json.dumps(incident, indent=2) + "\n")
    print(f"Saved {args.output}. Review and remove secrets before uploading.")
