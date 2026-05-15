#!/usr/bin/env python3
"""Export the authenticated Discogs user's full collection to discogs_collection.json."""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API_BASE = "https://api.discogs.com"
USER_AGENT = "DiscogsCollectionExport/1.0"
OUTPUT_PATH = "data/discogs_collection.json"
PER_PAGE = 100
THROTTLE_SECONDS = 1.0
MAX_429_RETRIES = 3


def die(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def get_token():
    token = os.environ.get("DISCOGS_API_TOKEN", "").strip()
    if not token or token == "DISCOGS_API_TOKEN":
        die(
            "DISCOGS_API_TOKEN is not set. "
            "Export it first, e.g.: `set -a; source .env; set +a`"
        )
    return token


def build_headers(token):
    return {
        "Authorization": f"Discogs token={token}",
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }


def http_get_json(url, token):
    """GET a Discogs JSON endpoint. Handles 429 with Retry-After. Raises on other errors."""
    headers = build_headers(token)
    attempts = 0
    while True:
        attempts += 1
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempts <= MAX_429_RETRIES:
                retry_after = e.headers.get("Retry-After", "1")
                try:
                    wait = float(retry_after)
                except ValueError:
                    wait = 1.0
                print(
                    f"Rate limited. Sleeping {wait:.1f}s "
                    f"(attempt {attempts}/{MAX_429_RETRIES}).",
                    file=sys.stderr,
                )
                time.sleep(wait)
                continue
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            die(f"HTTP {e.code} on {url}\n{body}")
        except urllib.error.URLError as e:
            die(f"Network error on {url}: {e.reason}")


def fetch_all_releases(username, token):
    """Page through folder 0 (All) and return every release item as a list."""
    encoded_user = urllib.parse.quote(username, safe="")
    releases = []
    page = 1
    total_pages = 1
    while page <= total_pages:
        url = (
            f"{API_BASE}/users/{encoded_user}/collection/folders/0/releases"
            f"?per_page={PER_PAGE}&page={page}"
        )
        data = http_get_json(url, token)
        page_items = data.get("releases", [])
        releases.extend(page_items)
        pagination = data.get("pagination", {})
        total_pages = int(pagination.get("pages", 1))
        total_items = pagination.get("items", len(releases))
        print(
            f"Fetched page {page}/{total_pages} "
            f"({len(page_items)} items, {len(releases)}/{total_items} total).",
            file=sys.stderr,
        )
        page += 1
        if page <= total_pages:
            time.sleep(THROTTLE_SECONDS)

    releases.sort(key=lambda r: r.get("date_added", ""))

    return releases


def main():
    token = get_token()
    identity = http_get_json(f"{API_BASE}/oauth/identity", token)
    username = identity.get("username")
    if not username:
        die(f"Could not determine username from /oauth/identity response: {identity!r}")
    print(f"Authenticated as: {username!r}", file=sys.stderr)
    releases = fetch_all_releases(username, token)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(releases, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(releases)} releases to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
