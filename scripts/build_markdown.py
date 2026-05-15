#!/usr/bin/env python3
"""Build collection.md from discogs_collection.json.

On first run: creates the full markdown with all sections, filling Discogs
fields and leaving manual fields as TBD.
On subsequent runs: appends only new records (deduplicated by master_id when
truthy, otherwise by release_id) before the Colophon section.
"""

import json
import os
import re
import sys

INPUT_PATH = "data/discogs_collection.json"
OUTPUT_PATH = "data/collection.md"


def die(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def load_collection():
    try:
        with open(INPUT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        die(
            f"{INPUT_PATH} not found. Run `python3 fetch_collection.py` first "
            f"to export your Discogs collection."
        )
    except json.JSONDecodeError as e:
        die(f"{INPUT_PATH} is not valid JSON: {e}")


def _valid_items(items):
    """Yield items that have the minimum required fields."""
    for item in items:
        basic = item.get("basic_information") or {}
        artists = basic.get("artists") or []
        if not basic.get("title") or not artists or not artists[0].get("name"):
            print(
                f"Skipping item {item.get('id', '?')}: missing artist/title",
                file=sys.stderr,
            )
            continue
        yield item


def entry_block(idx, item):
    """Return a list of markdown lines for one record."""
    basic = item.get("basic_information") or {}
    artist = basic["artists"][0]["name"]
    title = basic["title"]
    date_added = (item.get("date_added") or "")[:10]
    release_id = item.get("id", "")
    master_id = basic.get("master_id", "")
    cover = basic.get("cover_image", "")
    num = str(idx).zfill(2)

    lines = [
        f"### {num}. {artist} — {title}",
        "",
        f"<!-- release:{release_id} master:{master_id} -->",
        date_added,
        "",
        "From: TBD",
        "",
        "Sparked By: TBD",
        "",
        "TBD",
        "",
    ]
    if cover:
        lines.append(f"![Cover of {artist} — {title}]({cover})")
    lines += ["", "---", ""]
    return lines


def build_full(items):
    """Build the complete markdown from scratch."""
    sorted_items = sorted(items, key=lambda it: it.get("date_added") or "")
    valid = list(_valid_items(sorted_items))

    lines = [
        "# TBD",
        "",
        "## Masthead",
        "",
        "Tagline: TBD",
        "Chain: TBD",
        "",
        "## Preface",
        "",
        "Headline: TBD",
        "",
        "TBD",
        "",
        "---",
        "",
        "## Records",
        "",
    ]

    for idx, item in enumerate(valid, 1):
        lines.extend(entry_block(idx, item))

    lines += [
        "## Colophon",
        "",
        "TBD",
        "",
    ]

    return "\n".join(lines).rstrip() + "\n"


def get_existing_keys(content):
    """Return two sets extracted from the markdown comment tags:
    - existing_masters: truthy master IDs already recorded
    - existing_releases: release IDs already recorded
    """
    existing_masters = set()
    existing_releases = set()
    for release_str, master_str in re.findall(
        r"<!-- release:(\d+) master:(\d+) -->", content
    ):
        release_id = int(release_str)
        master_id = int(master_str)
        existing_releases.add(release_id)
        if master_id:
            existing_masters.add(master_id)
    return existing_masters, existing_releases


def _is_already_present(item, existing_masters, existing_releases):
    """Return True if this item is already in the markdown.

    Checks master_id first (if truthy), then falls back to release_id.
    This ensures that swapping a release for a better edition of the same
    album (same master, different release) is not treated as a new record.
    """
    basic = item.get("basic_information") or {}
    master_id = int(basic.get("master_id") or 0)
    release_id = int(item.get("id") or 0)
    if master_id:
        return master_id in existing_masters
    return release_id in existing_releases


def append_new(content, items):
    """Insert new records before the Colophon section and return (content, count)."""
    existing_masters, existing_releases = get_existing_keys(content)
    sorted_items = sorted(items, key=lambda it: it.get("date_added") or "")
    valid_new = [
        it for it in _valid_items(sorted_items)
        if not _is_already_present(it, existing_masters, existing_releases)
    ]
    if not valid_new:
        return content, 0

    start_idx = len(existing_releases) + 1
    new_lines = []
    for i, item in enumerate(valid_new, start_idx):
        new_lines.extend(entry_block(i, item))

    new_block = "\n".join(new_lines)

    colophon = re.search(r"^## Colophon", content, re.MULTILINE)
    if colophon:
        pos = colophon.start()
        content = content[:pos] + new_block + "\n" + content[pos:]
    else:
        content = content.rstrip() + "\n\n" + new_block

    return content, len(valid_new)


def main():
    items = load_collection()

    if os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        content, added = append_new(content, items)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Appended {added} new entr{'y' if added == 1 else 'ies'} to {OUTPUT_PATH}")
    else:
        content = build_full(items)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        valid_count = sum(1 for _ in _valid_items(items))
        print(f"Built {OUTPUT_PATH} with {valid_count} entries")


if __name__ == "__main__":
    main()
