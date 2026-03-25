import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

GENERATORS = [
    ("Odoo", "odoo.main"),
    ("SQLite Demo", "sqlite.main"),
]

for label, module_path in GENERATORS:
    try:
        mod = importlib.import_module(module_path)
    except Exception as e:
        print(f"\n[{label}] Failed to import: {e}")
        continue

    print(f"\nChecking {label}...", end=" ", flush=True)
    if not mod.check():
        print(f"not reachable. Skipping.")
        continue
    print("OK.")

    try:
        answer = input(f"Generate data for {label}? (Y/n): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        sys.exit(0)

    if answer == "n":
        print(f"  Skipped {label}.")
        continue

    try:
        mod.run()
    except Exception as e:
        print(f"  Error: {e}")
        print(f"  Skipping {label}.")

print("\nDone.")
