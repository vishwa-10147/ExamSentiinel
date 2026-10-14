"""Install the language runtimes ExamSentinel needs into a Piston instance.

    python scripts/install_piston_runtimes.py [--url http://localhost:2000]

Idempotent: already-installed runtimes are skipped. For each language the
newest version published in the Piston package index is installed.
"""

import argparse
import os
import sys

import httpx

# Piston package names (gcc provides both c and c++; sqlite3 serves SQL questions)
REQUIRED_PACKAGES = ["python", "node", "java", "gcc", "sqlite3"]


def version_key(v: str) -> tuple:
    return tuple(int(p) if p.isdigit() else 0 for p in v.split("."))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=os.environ.get("PISTON_BASE_URL", "http://localhost:2000"))
    args = parser.parse_args()

    with httpx.Client(base_url=args.url.rstrip("/"), timeout=900) as client:
        packages = client.get("/api/v2/packages").json()
        failed = False
        for name in REQUIRED_PACKAGES:
            versions = [p for p in packages if p["language"] == name]
            if not versions:
                print(f"[MISSING] {name}: not in the Piston package index")
                failed = True
                continue
            newest = max(versions, key=lambda p: version_key(p["language_version"]))
            if newest["installed"]:
                print(f"[OK]      {name} {newest['language_version']} already installed")
                continue
            print(f"[INSTALL] {name} {newest['language_version']} ...", flush=True)
            r = client.post("/api/v2/packages", json={"language": name, "version": newest["language_version"]})
            if r.status_code >= 400:
                print(f"[FAIL]    {name}: HTTP {r.status_code} {r.text[:200]}")
                failed = True
            else:
                print(f"[OK]      {name} {newest['language_version']} installed")

        runtimes = client.get("/api/v2/runtimes").json()
        print("\nAvailable runtimes:", ", ".join(sorted(f"{r['language']}@{r['version']}" for r in runtimes)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
