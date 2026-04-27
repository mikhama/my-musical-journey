# My Musical Journey

My personal blog about vinyl records I own.

## Building

1. Get collection:
```bash
set -a; source .env; set +a; python3 scripts/fetch_collection.py
```

2. Build markdown:
```bash
python3 scripts/build_markdown.py
```

3. Edit markdown in [collection.md](data/collection.md).

4. Build html:
```bash
python3 scripts/build_html.py
```