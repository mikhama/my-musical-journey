#!/usr/bin/env python3
"""Build data/collection.json and download tracklists for each release.

Parses data/collection.md, outputs data/collection.json with basic metadata,
then fetches tracklists from the Discogs API for releases not yet cached
in data/albums/<release_id>.json.
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MD_PATH = BASE_DIR / "data" / "collection.md"
COLLECTION_JSON_PATH = BASE_DIR / "data" / "collection.json"
ALBUMS_DIR = BASE_DIR / "data" / "albums"

API_BASE = "https://api.discogs.com"
USER_AGENT = "MyMusicalJourney/1.0"
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


def http_get_json(url, token):
    """GET a Discogs JSON endpoint with rate-limit handling."""
    headers = {
        "Authorization": f"Discogs token={token}",
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }
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


def parse_md():
    """Parse collection.md and return list of records with metadata."""
    text = MD_PATH.read_text(encoding="utf-8")

    records = []
    record_blocks = re.findall(
        r"###\s+(\d+)\.\s+(.+?)\s+—\s+(.+?)\n(.*?)(?=\n###\s|\n## Colophon)",
        text, re.DOTALL,
    )
    for num_str, artist, album, block in record_blocks:
        release_m = re.search(r"<!--\s*release:(\d+)\s+master:(\d+)\s*-->", block)
        release_id = release_m.group(1) if release_m else ""
        master_id = release_m.group(2) if release_m else ""

        records.append({
            "id": num_str,
            "release_id": release_id,
            "master_id": master_id,
            "title": album.strip(),
            "artist": artist.strip(),
        })

    return records


def build_collection_json(records):
    """Write data/collection.json."""
    COLLECTION_JSON_PATH.write_text(
        json.dumps(records, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(records)} records to {COLLECTION_JSON_PATH}")


def fetch_tracklist(release_id, token):
    """Fetch release data from Discogs and return the tracklist."""
    url = f"{API_BASE}/releases/{release_id}"
    return http_get_json(url, token)


def fetch_master_durations(master_id, token):
    """Fetch master release data to get track durations as fallback."""
    if not master_id or master_id == "0":
        return {}
    url = f"{API_BASE}/masters/{master_id}"
    data = http_get_json(url, token)
    durations = {}
    for track in data.get("tracklist", []):
        if track.get("type_") == "track":
            pos = track.get("position", "")
            dur = track.get("duration", "")
            if pos and dur:
                durations[pos] = dur
    return durations


def build_album_json(record, release_data, master_durations):
    """Build the album JSON structure from Discogs release data."""
    tracklist = release_data.get("tracklist", [])

    # Determine if tracks have varying artists
    track_artists = set()
    for track in tracklist:
        if track.get("type_") == "track":
            artists = track.get("artists", [])
            if artists:
                artist_name = ", ".join(a.get("name", "") for a in artists)
                track_artists.add(artist_name)

    has_various_artists = len(track_artists) > 1

    # Group tracks by side/position prefix
    sides = {}
    for track in tracklist:
        if track.get("type_") != "track":
            continue

        position = track.get("position", "")
        # Extract side label from position (e.g., "A1" -> "A", "B2" -> "B")
        side_label = ""
        if position:
            match = re.match(r"([A-Za-z]+)", position)
            if match:
                side_label = match.group(1).upper()
            else:
                side_label = ""

        if side_label not in sides:
            sides[side_label] = []

        track_entry = {}

        if has_various_artists:
            artists = track.get("artists", [])
            if artists:
                track_artist = ", ".join(a.get("name", "") for a in artists)
                if track_artist:
                    track_entry["artist"] = track_artist

        track_entry["title"] = track.get("title", "")

        duration = track.get("duration", "")
        if not duration and position:
            duration = master_durations.get(position, "")
        track_entry["time"] = duration

        sides[side_label].append(track_entry)

    # Convert to ordered list of side objects
    sides_list = []
    for side_label in sorted(sides.keys()):
        sides_list.append({
            "side_label": side_label,
            "tracks": sides[side_label],
        })

    return {
        "release_id": record["release_id"],
        "master_id": record["master_id"],
        "title": record["title"],
        "artist": record["artist"],
        "sides": sides_list,
    }


def download_tracklists(records, token):
    """Download tracklists for releases not already cached."""
    ALBUMS_DIR.mkdir(parents=True, exist_ok=True)

    for record in records:
        release_id = record["release_id"]
        if not release_id:
            continue

        album_path = ALBUMS_DIR / f"{release_id}.json"
        if album_path.exists():
            print(f"Skipping #{record['id']} {record['artist']} — {record['title']} (already cached)")
            continue

        print(f"Fetching tracklist for #{record['id']} {record['artist']} — {record['title']}...")
        release_data = fetch_tracklist(release_id, token)

        # Check if any track is missing duration; if so, fetch master for fallback
        master_durations = {}
        needs_master = any(
            not t.get("duration", "")
            for t in release_data.get("tracklist", [])
            if t.get("type_") == "track"
        )
        if needs_master and record["master_id"] and record["master_id"] != "0":
            print(f"  Fetching master {record['master_id']} for durations...")
            time.sleep(THROTTLE_SECONDS)
            master_durations = fetch_master_durations(record["master_id"], token)

        album_json = build_album_json(record, release_data, master_durations)

        album_path.write_text(
            json.dumps(album_json, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"  Saved {album_path}")
        time.sleep(THROTTLE_SECONDS)


def main():
    if not MD_PATH.exists():
        die(f"{MD_PATH} not found.")

    token = get_token()
    records = parse_md()
    build_collection_json(records)
    download_tracklists(records, token)
    print("Done.")


if __name__ == "__main__":
    main()
