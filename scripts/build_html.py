#!/usr/bin/env python3
"""Build index.html from data/collection.md and template.html.

Parses the markdown collection file, extracts all metadata, downloads cover
images, and populates the HTML template with the data.
"""

import html
import os
import re
import sys
import urllib.request
import urllib.error
from collections import Counter
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MD_PATH = BASE_DIR / "data" / "collection.md"
TEMPLATE_PATH = BASE_DIR / "template.html"
OUTPUT_PATH = BASE_DIR / "index.html"
IMAGES_DIR = BASE_DIR / "images"

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
MONTH_ABBR = [
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
]


def die(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)


# ── Markdown parsing ──────────────────────────────────────────────────────────

def parse_md():
    text = MD_PATH.read_text(encoding="utf-8")

    title_m = re.match(r"^#\s+(.+)", text)
    title = title_m.group(1).strip() if title_m else "My Musical Journey!"

    tagline_m = re.search(r"Tagline:\s*(.+)", text)
    tagline = tagline_m.group(1).strip() if tagline_m else ""
    chain_m = re.search(r"Chain:\s*(.+)", text)
    chain = chain_m.group(1).strip() if chain_m else ""

    headline_m = re.search(r"Headline:\s*(.+)", text)
    headline = headline_m.group(1).strip() if headline_m else ""
    signoff_m = re.search(r"Signoff:\s*(.+)", text)
    signoff = signoff_m.group(1).strip() if signoff_m else ""

    body_text = ""
    preface_block = re.search(
        r"Headline:.*?\n\n(.*?)\n\nSignoff:", text, re.DOTALL
    )
    if preface_block:
        body_text = preface_block.group(1).strip()

    records = []
    record_blocks = re.findall(
        r"###\s+(\d+)\.\s+(.+?)\s+—\s+(.+?)\n(.*?)(?=\n###\s|\n## Colophon)",
        text, re.DOTALL
    )
    for num_str, artist, album, block in record_blocks:
        num = int(num_str)
        release_m = re.search(r"<!--\s*release:(\d+)\s+master:(\d+)\s*-->", block)
        release_id = release_m.group(1) if release_m else ""
        date_m = re.search(r"(\d{4}-\d{2}-\d{2})", block)
        date_str = date_m.group(1) if date_m else ""
        from_m = re.search(r"From:\s*(.+)", block)
        from_str = from_m.group(1).strip() if from_m else ""
        sparked_m = re.search(r"Sparked By:\s*(.+)", block)
        sparked_by = sparked_m.group(1).strip() if sparked_m else ""
        note = ""
        note_m = re.search(r"Sparked By:.*?\n\n(.*?)\n\n!\[", block, re.DOTALL)
        if note_m:
            note_text = note_m.group(1).strip()
            if note_text != "TBD":
                note = note_text
        cover_m = re.search(r"!\[.*?\]\((https://[^)]+)\)", block)
        cover_url = cover_m.group(1) if cover_m else ""
        alt_m = re.search(r"!\[(.*?)\]", block)
        cover_alt = alt_m.group(1) if alt_m else ""

        records.append({
            "num": num,
            "artist": artist.strip(),
            "album": album.strip(),
            "release_id": release_id,
            "date": date_str,
            "from": from_str,
            "sparked_by": sparked_by,
            "note": note,
            "cover_url": cover_url,
            "cover_alt": cover_alt,
        })

    colophon_m = re.search(r"## Colophon\n\n(.*)", text, re.DOTALL)
    colophon = colophon_m.group(1).strip() if colophon_m else ""

    return {
        "title": title,
        "tagline": tagline,
        "chain": chain,
        "headline": headline,
        "body": body_text,
        "signoff": signoff,
        "records": records,
        "colophon": colophon,
    }


# ── Image downloading ─────────────────────────────────────────────────────────

def download_images(records):
    IMAGES_DIR.mkdir(exist_ok=True)
    for rec in records:
        if not rec["cover_url"] or not rec["release_id"]:
            continue
        ext = ".png" if rec["cover_url"].split("?")[0].endswith(".png") else ".jpeg"
        filename = f"{rec['release_id']}{ext}"
        filepath = IMAGES_DIR / filename
        rec["local_cover"] = f"images/{filename}"
        if filepath.exists():
            continue
        print(f"Downloading cover for #{rec['num']:02d} {rec['artist']} — {rec['album']}...")
        try:
            req = urllib.request.Request(
                rec["cover_url"],
                headers={"User-Agent": "MyMusicalJourney/1.0"},
            )
            with urllib.request.urlopen(req) as resp:
                filepath.write_bytes(resp.read())
        except urllib.error.URLError as e:
            print(f"  Warning: failed to download: {e}", file=sys.stderr)
            rec["local_cover"] = rec["cover_url"]


# ── Template helpers ──────────────────────────────────────────────────────────

def _extract_template(html_text, tag):
    pattern = rf"<!--{tag}-->(.*?)<!--/{tag}-->"
    m = re.search(pattern, html_text, re.DOTALL)
    return m.group(1) if m else ""


def _remove_block(html_text, tag):
    pattern = rf"\s*<!--{tag}-->.*?<!--/{tag}-->\s*"
    return re.sub(pattern, "", html_text, flags=re.DOTALL)


def _fmt_num(n, total):
    width = len(str(total))
    return str(n).zfill(width)


def _parse_date(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d")


def _format_date_display(date_str):
    dt = _parse_date(date_str)
    return f"{dt.day:02d} {MONTH_ABBR[dt.month - 1]} {dt.year}"


def _headline_to_html(text):
    return re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)


def _body_to_html(text):
    paragraphs = text.split("\n")
    return "\n".join(f"      <p>{p.strip()}</p>" for p in paragraphs if p.strip())


def _colophon_to_html(text):
    return text.replace("\n", "<br>")


def _compute_period(records):
    if not records:
        return "", ""
    first_date = _parse_date(records[0]["date"])
    now = datetime.now()
    first_month_name = MONTH_NAMES[first_date.month - 1]
    current_month_name = MONTH_NAMES[now.month - 1]
    from_to = f"from {first_month_name} {first_date.year} to {current_month_name} {now.year}"
    total_months = (now.year - first_date.year) * 12 + (now.month - first_date.month)
    years = total_months // 12
    months = total_months % 12
    parts = []
    if years > 0:
        parts.append(f"{years}<span> {'year' if years == 1 else 'years'}</span>")
    if months > 0:
        parts.append(f"{months}<span> {'month' if months == 1 else 'months'}</span>")
    if not parts:
        parts.append("0<span> months</span>")
    return " ".join(parts), from_to


def _compute_countries(records):
    countries = []
    seen = set()
    for rec in records:
        parts = rec["from"].split(", ")
        country = parts[-1] if len(parts) >= 2 else rec["from"]
        if country not in seen:
            seen.add(country)
            countries.append(country)
    return len(countries), ", ".join(countries)


def _compute_top_artist(records):
    counter = Counter(rec["artist"] for rec in records)
    if not counter:
        return "", 0
    artist, count = counter.most_common(1)[0]
    return artist, count


def _compute_top_artists(records):
    counter = Counter(rec["artist"] for rec in records)
    top5 = counter.most_common(5)
    return "<br>".join(f"{artist} — {count}" for artist, count in top5)


def _build_led_to_map(records):
    led_to = {}
    for rec in records:
        sparked = rec["sparked_by"]
        if sparked.isdigit():
            source_num = int(sparked)
            led_to.setdefault(source_num, []).append(rec)
    return led_to


def _build_timeline_items(records, total):
    seen = set()
    items = []
    first_year = None
    for rec in records:
        dt = _parse_date(rec["date"])
        key = (dt.year, dt.month)
        if key in seen:
            continue
        seen.add(key)
        if first_year is None:
            first_year = dt.year
        is_year_start = not any(i["year_val"] == dt.year for i in items)
        items.append({
            "year_start_class": "is-year-start" if is_year_start and dt.year != first_year else "",
            "num": _fmt_num(rec["num"], total),
            "month_year": f"{MONTH_NAMES[dt.month - 1].upper()} {dt.year}",
            "year": str(dt.year),
            "mon": MONTH_ABBR[dt.month - 1],
            "year_val": dt.year,
        })
    return items


def _build_month_marker_set(records):
    seen = set()
    markers = set()
    for rec in records:
        dt = _parse_date(rec["date"])
        key = (dt.year, dt.month)
        if key not in seen:
            seen.add(key)
            markers.add(rec["num"])
    return markers


# ── Main build ────────────────────────────────────────────────────────────────

def build():
    if not MD_PATH.exists():
        die(f"{MD_PATH} not found.")
    if not TEMPLATE_PATH.exists():
        die(f"{TEMPLATE_PATH} not found.")

    data = parse_md()
    records = data["records"]
    total = len(records)

    download_images(records)

    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    # Extract sub-templates before removing blocks
    timeline_tpl = _extract_template(template, "template_timeline")
    record_tpl = _extract_template(template, "template_record")
    sparked_event_tpl = _extract_template(record_tpl, "sparked_event")
    sparked_target_tpl = _extract_template(record_tpl, "sparked_target")
    led_to_tpl = _extract_template(record_tpl, "led_to")

    # Clean the record template of its sub-template markers
    record_tpl_clean = _remove_block(record_tpl, "sparked_event")
    record_tpl_clean = _remove_block(record_tpl_clean, "sparked_target")
    record_tpl_clean = _remove_block(record_tpl_clean, "led_to")

    # Remove example and template blocks from main template
    output = _remove_block(template, "example")
    output = _remove_block(output, "template_timeline")
    output = _remove_block(output, "template_record")

    # Build timeline
    timeline_items = _build_timeline_items(records, total)
    timeline_html = ""
    for item in timeline_items:
        t = timeline_tpl
        t = t.replace("{{YEAR_START_CLASS}}", item["year_start_class"])
        t = t.replace("{{NUM}}", item["num"])
        t = t.replace("{{MONTH_YEAR}}", item["month_year"])
        t = t.replace("{{YEAR}}", item["year"])
        t = t.replace("{{MON}}", item["mon"])
        timeline_html += t

    # Insert timeline into the track div
    output = re.sub(
        r'(<div class="timeline__track" id="timelineTrack">)\s*(</div>)',
        lambda m: m.group(1) + timeline_html + m.group(2),
        output,
    )

    # Build records
    led_to_map = _build_led_to_map(records)
    month_markers = _build_month_marker_set(records)
    rec_by_num = {r["num"]: r for r in records}
    records_html = ""

    for rec in records:
        entry = record_tpl_clean

        marker_class = "month-marker" if rec["num"] in month_markers else ""
        entry = entry.replace("{{MONTH_MARKER_CLASS}}", marker_class)

        side = "A" if rec["num"] % 2 == 1 else "B"
        entry = entry.replace("{{SIDE}}", side)

        local_cover = rec.get("local_cover", rec["cover_url"])
        entry = entry.replace("{{COVER_URL}}", local_cover)
        entry = entry.replace("{{COVER_ALT_TEXT}}", html.escape(rec["cover_alt"], quote=True))

        discogs_url = f"https://www.discogs.com/release/{rec['release_id']}"
        entry = entry.replace("{{DISCOGS_URL}}", discogs_url)

        fmt_num = _fmt_num(rec["num"], total)
        entry = entry.replace("{{RN}}", fmt_num)
        entry = entry.replace('id="entry-01"', f'id="entry-{fmt_num}"')

        entry = entry.replace("{{DATE_ADDED}}", _format_date_display(rec["date"]))
        entry = entry.replace("{{FROM}}", html.escape(rec["from"], quote=True))

        cat_no = f"{fmt_num}/{total}"
        entry = entry.replace("{{CAT_NO}}", cat_no)
        entry = entry.replace("{{ARTIST}}", html.escape(rec["artist"], quote=True))
        entry = entry.replace("{{ALBUM}}", html.escape(rec["album"], quote=True))

        # Sparked by
        sparked = rec["sparked_by"]
        sparked_html = ""
        if sparked.isdigit():
            source_num = int(sparked)
            source_rec = rec_by_num.get(source_num)
            if source_rec:
                s = sparked_target_tpl
                s = s.replace("{{SPARKED_TARGET_NUM}}", _fmt_num(source_num, total))
                s = s.replace("{{SPARKED_TARGET}}", f"№ {_fmt_num(source_num, total)} — {html.escape(source_rec['artist'], quote=True)}")
                sparked_html = s
        elif sparked:
            s = sparked_event_tpl
            s = s.replace("{{SPARKED_EVENT}}", html.escape(sparked, quote=True))
            sparked_html = s

        # Note
        note_html = html.escape(rec["note"], quote=True) if rec["note"] else ""
        entry = entry.replace("{{NOTE}}", note_html)

        # Led to
        led_to_entries = led_to_map.get(rec["num"], [])
        led_to_html = ""
        for target_rec in led_to_entries:
            lt = led_to_tpl
            lt = lt.replace("{{LED_TO_NUM}}", _fmt_num(target_rec["num"], total))
            lt = lt.replace("{{LED_TO_TARGET}}", f"№ {_fmt_num(target_rec['num'], total)} — {html.escape(target_rec['artist'], quote=True)}")
            led_to_html += lt

        # Place sparked and led_to into the two entry__connections divs
        sparked_section = ""
        if sparked_html:
            sparked_section = f'<div class="entry__connections">\n        {sparked_html.strip()}</div>'

        led_to_section = ""
        if led_to_html:
            led_to_section = f'<div class="entry__connections">\n{led_to_html}\n        </div>'

        conn_pattern = r'<div class="entry__connections">\s*</div>'
        entry = re.sub(conn_pattern, "SPARKED_PLACEHOLDER", entry, count=1)
        entry = re.sub(conn_pattern, "LEDTO_PLACEHOLDER", entry, count=1)
        entry = entry.replace("SPARKED_PLACEHOLDER", sparked_section)
        entry = entry.replace("LEDTO_PLACEHOLDER", led_to_section)

        # Remove empty note div
        if not rec["note"]:
            entry = re.sub(r'\s*<div class="entry__note"></div>', "", entry)

        records_html += entry

    # Insert records into entries section
    output = re.sub(
        r'(<main class="entries">)\s*(</main>)',
        lambda m: m.group(1) + "\n" + records_html + "\n" + m.group(2),
        output,
    )

    # Global replacements
    output = output.replace("{{TITLE}}", html.escape(data["title"], quote=True))
    output = output.replace("{{ISSUE_NO}}", _fmt_num(total, total))
    output = output.replace("{{TAGLINE}}", html.escape(data["tagline"], quote=True))
    output = output.replace("{{CHAIN}}", html.escape(data["chain"], quote=True))
    output = output.replace("{{HEADLINE}}", _headline_to_html(data["headline"]))
    output = output.replace("{{BODY}}", _body_to_html(data["body"]))
    output = output.replace("{{SIGNOFF}}", html.escape(data["signoff"], quote=True))
    output = output.replace("{{RC}}", str(total))

    ot, from_to = _compute_period(records)
    output = output.replace("{{OT}}", ot)
    output = output.replace("{{FROM_TO}}", from_to)

    cc, countries = _compute_countries(records)
    output = output.replace("{{CC}}", str(cc))
    output = output.replace("{{COUNTRIES}}", html.escape(countries, quote=True))

    mc_artist, mc_count = _compute_top_artist(records)
    output = output.replace("{{MC_ARTIST}}", html.escape(mc_artist, quote=True))
    output = output.replace("{{MC_ARTIST_RC}}", str(mc_count))

    output = output.replace("{{COLOPHON}}", _colophon_to_html(html.escape(data["colophon"], quote=True)))
    output = output.replace("{{TOP_ARTISTS}}", _compute_top_artists(records))

    OUTPUT_PATH.write_text(output, encoding="utf-8")
    print(f"Built {OUTPUT_PATH} with {total} records.")


if __name__ == "__main__":
    build()
