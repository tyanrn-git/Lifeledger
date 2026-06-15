#!/usr/bin/env python3
"""HTTP smoke tests for LifeLedger (local or production).

Usage:
  python scripts/smoke_http.py
  python scripts/smoke_http.py --base https://lifeledger-production-c53d.up.railway.app
  ADMIN_PASSWORD=secret python scripts/smoke_http.py --base http://127.0.0.1:8080
"""

from __future__ import annotations

import argparse
import os
import sys
import urllib.error
import urllib.request


def check(url: str, *, expect: int | range = 200) -> tuple[bool, str]:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            code = resp.status
            body = resp.read(500).decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        code = exc.code
        body = exc.read(200).decode("utf-8", errors="replace")
    except OSError as exc:
        return False, f"FAIL {url} — {exc}"

    ok = code in expect if isinstance(expect, range) else code == expect
    status = "OK" if ok else "FAIL"
    snippet = body.replace("\n", " ")[:80]
    return ok, f"{status} {code} {url} — {snippet}"


def main() -> int:
    parser = argparse.ArgumentParser(description="LifeLedger HTTP smoke tests")
    parser.add_argument(
        "--base",
        default=os.environ.get(
            "SMOKE_BASE_URL",
            "https://lifeledger-production-c53d.up.railway.app",
        ),
        help="Base URL without trailing slash",
    )
    args = parser.parse_args()
    base = args.base.rstrip("/")
    admin_password = os.environ.get("ADMIN_PASSWORD", "")

    checks: list[tuple[str, int | range]] = [
        (f"{base}/health", 200),
        (f"{base}/admin/login", range(200, 500)),
    ]

    results = [check(url, expect=code) for url, code in checks]

    if admin_password:
        import http.cookiejar
        import urllib.parse

        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        login_data = urllib.parse.urlencode({"password": admin_password}).encode()
        login_req = urllib.request.Request(
            f"{base}/admin/login",
            data=login_data,
            method="POST",
        )
        try:
            with opener.open(login_req, timeout=15) as resp:
                if resp.status not in (200, 302):
                    results.append((False, f"FAIL login POST {resp.status}"))
                else:
                    for path in ("/admin", "/admin/dashboard", "/admin/activity"):
                        req = urllib.request.Request(f"{base}{path}")
                        with opener.open(req, timeout=15) as page:
                            ok = page.status == 200
                            results.append(
                                (ok, f"{'OK' if ok else 'FAIL'} {page.status} {base}{path}")
                            )
        except OSError as exc:
            results.append((False, f"FAIL admin login flow — {exc}"))
    else:
        results.append(
            (
                True,
                "SKIP admin pages (set ADMIN_PASSWORD env to test authenticated routes)",
            )
        )

    print(f"Smoke: {base}\n")
    failed = 0
    for ok, line in results:
        print(line)
        if not ok and not line.startswith("SKIP"):
            failed += 1

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
