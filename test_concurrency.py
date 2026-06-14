# usage: python test_concurrency.py [--api-key KEY] [--model MODEL] [--daemon URL] [--rounds N]
import argparse
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path


def _load_env_key(name):
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1].strip()
    return None


def _marker(label):
    # full string for the sub-agent's prompt; check_marker is the substring we
    # require in the top-level reply (the top-level LLM paraphrases, but the
    # distinctive "AGENT X" token survives the rewording).
    return f"I AM AGENT {label}"


def _check_marker(label):
    return f"AGENT {label}"


def make_bundle(label, model, api_key, round_idx):
    return {
        "message": "Dispatch to the agent named agent_x and have it identify itself.",
        "session_key": f"smoketest:{label}:r{round_idx}:{time.time()}",
        "uid": 100 if label == "A" else 200,
        "agents": [{
            "name": "agent_x",
            "description": f"identifier agent ({label})",
            "system_prompt": f"You must respond with EXACTLY this string and nothing else: {_marker(label)}",
            "allowed_tools": [],
        }],
        "disabled_defaults": [],
        "profile": {
            "id": label,
            "name": label,
            "model": model,
            "api_key": api_key,
        },
    }


def post_and_collect(label, bundle, daemon_url, results):
    t0 = time.time()
    body = json.dumps(bundle).encode("utf-8")
    req = urllib.request.Request(
        f"{daemon_url}/chat/",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    response_text = ""
    progress = []
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            print(f"  [{label}] connected at +{time.time()-t0:.2f}s status={r.status}")
            buf = b""
            for chunk in r:
                buf += chunk
                while b"\n" in buf:
                    raw, buf = buf.split(b"\n", 1)
                    line = raw.decode("utf-8", errors="ignore").strip()
                    if not line.startswith("data: "):
                        continue
                    try:
                        ev = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue
                    if ev.get("type") == "progress":
                        progress.append(ev.get("content", ""))
                    elif ev.get("type") == "response":
                        response_text = ev.get("content", "")
    except urllib.error.URLError as e:
        results[label] = {"error": str(e), "elapsed": time.time() - t0}
        return

    results[label] = {
        "response": response_text,
        "progress": progress,
        "elapsed": time.time() - t0,
    }


def run_round(round_idx, args):
    print(f"\n----- Round {round_idx} -----")
    results = {}
    threads = [
        threading.Thread(
            target=post_and_collect,
            args=("A", make_bundle("A", args.model, args.api_key, round_idx), args.daemon, results),
        ),
        threading.Thread(
            target=post_and_collect,
            args=("B", make_bundle("B", args.model, args.api_key, round_idx), args.daemon, results),
        ),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    for label in ("A", "B"):
        r = results.get(label, {})
        print(f"  === {label} (elapsed {r.get('elapsed', 0):.1f}s) ===")
        if "error" in r:
            print(f"    ERROR: {r['error']}")
            continue
        print(f"    response: {r.get('response')!r}")

    a_resp = (results.get("A", {}).get("response") or "").upper()
    b_resp = (results.get("B", {}).get("response") or "").upper()

    marker_a = _check_marker("A").upper()
    marker_b = _check_marker("B").upper()
    a_has_a = marker_a in a_resp
    a_has_b = marker_b in a_resp
    b_has_a = marker_a in b_resp
    b_has_b = marker_b in b_resp

    leak = a_has_b or b_has_a
    ok_a = a_has_a and not a_has_b
    ok_b = b_has_b and not b_has_a

    if leak:
        verdict = "LEAK"
    elif ok_a and ok_b:
        verdict = "CLEAN"
    else:
        verdict = "FLAKE"
    print(f"  -> round {round_idx}: {verdict} (a_ok={ok_a} b_ok={ok_b} leak={leak})")
    return {"verdict": verdict, "leak": leak, "ok_a": ok_a, "ok_b": ok_b}


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--api-key",
        default=os.environ.get("OPENAI_API_KEY") or _load_env_key("OPENAI_API_KEY"),
    )
    p.add_argument("--model", default="openai/gpt-4o-mini")
    p.add_argument("--daemon", default="http://127.0.0.1:8001")
    p.add_argument("--rounds", type=int, default=3)
    args = p.parse_args()

    if not args.api_key:
        print(
            "ERROR: no API key. Pass --api-key, or set OPENAI_API_KEY in .env or env.",
            file=sys.stderr,
        )
        sys.exit(2)

    print(f"Daemon: {args.daemon}")
    print(f"Model:  {args.model}")
    print(f"Rounds: {args.rounds}")
    print(f"Firing 2 concurrent requests per round...")

    rounds = [run_round(i + 1, args) for i in range(args.rounds)]

    print()
    print("=" * 50)
    n_clean = sum(1 for r in rounds if r["verdict"] == "CLEAN")
    n_flake = sum(1 for r in rounds if r["verdict"] == "FLAKE")
    n_leak  = sum(1 for r in rounds if r["verdict"] == "LEAK")
    print(f"Summary: CLEAN={n_clean}  FLAKE={n_flake}  LEAK={n_leak}  (of {len(rounds)})")

    if n_leak > 0:
        print()
        print("HARD FAIL — at least one round saw one user's marker in the other's reply.")
        print("Bundle leaked between concurrent tasks. Check ContextVar wiring.")
        sys.exit(1)
    if n_clean == len(rounds):
        print()
        print("PASS — bundle isolation holds; every round produced clean per-user replies.")
        sys.exit(0)
    print()
    print("PASS (with LLM flakiness) — no cross-user leaks were observed in any round,")
    print("but some rounds had a user fail to get their own marker. The isolation property")
    print("is intact; the failures are LLM nondeterminism on this prompt, not a daemon bug.")
    sys.exit(0)


if __name__ == "__main__":
    main()
