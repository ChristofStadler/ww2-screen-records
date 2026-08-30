#!/usr/bin/env python3
"""
update_ratings.py — fill real IMDb ratings and poster plates into index.html

Downloads IMDb's own published dataset (https://developer.imdb.com/non-commercial-datasets/)
and writes an `r:` value into every entry in the PARTS array.

If TMDB_API_KEY is set, it also fetches a poster thumbnail for every title it
resolved and rewrites the POSTERS block as inline data URIs — IMDb's datasets
carry no images, so posters come from TMDb, matched on the IMDb id. Without the
key the ratings pass runs exactly as before and the POSTERS block is left alone.

    python3 update_ratings.py

No third-party packages needed — TMDb's w92 renditions are already thumbnail
sized, so nothing has to be resized locally. First run downloads ~190 MB and
takes a few minutes; the files are cached in ./.imdb-cache so later runs are
quick. Safe to run repeatedly — ratings and posters are replaced, not duplicated.
"""

import base64
import csv
import gzip
import io
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

BASE = "https://datasets.imdbws.com/"
CACHE = ".imdb-cache"
HTML = "index.html"

# IMDb title types we care about, mapped loosely to our k field
TYPES = {"movie", "tvMovie", "tvSeries", "tvMiniSeries", "documentary", "short", "video"}


def fetch(name):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, name)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    url = BASE + name
    print(f"  downloading {name} …", flush=True)
    try:
        urllib.request.urlretrieve(url, path)
    except Exception as e:
        if os.path.exists(path):
            os.remove(path)
        sys.exit(f"Could not download {url}\n  {e}")
    return path


def norm(s):
    """Fold a title down to something comparable."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("&", "and")
    s = re.sub(r"^(the|a|an|le|la|les|el|il|der|die|das)\s+", "", s)
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s


def load_index():
    """title-key -> list of (tconst, votes)"""
    print("Reading title index …", flush=True)
    idx = {}
    with gzip.open(fetch("title.basics.tsv.gz"), "rt", encoding="utf-8", errors="replace") as fh:
        rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
        next(rd, None)
        for row in rd:
            if len(row) < 6:
                continue
            tconst, ttype, primary, original, _adult, year = row[:6]
            if ttype not in TYPES or year == "\\N":
                continue
            try:
                year = int(year)
            except ValueError:
                continue
            for title in {primary, original}:
                if title and title != "\\N":
                    idx.setdefault((norm(title), year), []).append(tconst)
    return idx


def load_ratings():
    print("Reading ratings …", flush=True)
    out = {}
    with gzip.open(fetch("title.ratings.tsv.gz"), "rt", encoding="utf-8", errors="replace") as fh:
        rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
        next(rd, None)
        for tconst, avg, votes in rd:
            out[tconst] = (float(avg), int(votes))
    return out


# Titles the automatic matcher can't resolve — pin them by IMDb id here.
# The script prints a search link for anything it misses.
MANUAL = {
    # ("The Human Condition", 1959): "tt0053114",
}


def candidates_for(idx, title, year):
    """tconsts for a title, trying the exact name then the part before a colon."""
    names = [title]
    if ":" in title:
        names.append(title.split(":")[0].strip())
    out = []
    for name in names:
        for y in (year, year - 1, year + 1):
            out += idx.get((norm(name), y), [])
        if out:
            break
    return out


TMDB_KEY = os.environ.get("TMDB_API_KEY", "").strip()
TMDB_FIND = "https://api.themoviedb.org/3/find/{}?external_source=imdb_id&api_key={}"
TMDB_IMG = "https://image.tmdb.org/t/p/w92{}"
POSTER_CACHE = os.path.join(CACHE, "posters")


def poster_bytes(tconst):
    """w92 JPEG for an IMDb id, or None. Cached on disk, misses included."""
    os.makedirs(POSTER_CACHE, exist_ok=True)
    hit = os.path.join(POSTER_CACHE, tconst + ".jpg")
    miss = os.path.join(POSTER_CACHE, tconst + ".none")
    if os.path.exists(hit):
        return open(hit, "rb").read()
    if os.path.exists(miss):
        return None

    try:
        with urllib.request.urlopen(TMDB_FIND.format(tconst, TMDB_KEY), timeout=30) as r:
            found = json.load(r)
    except Exception as e:
        print(f"    TMDb lookup failed for {tconst}: {e}", flush=True)
        return None
    time.sleep(0.06)  # stay well inside TMDb's rate limit

    path = None
    for bucket in ("movie_results", "tv_results"):
        for row in found.get(bucket) or []:
            if row.get("poster_path"):
                path = row["poster_path"]
                break
        if path:
            break
    if not path:
        open(miss, "wb").close()
        return None

    try:
        with urllib.request.urlopen(TMDB_IMG.format(path), timeout=30) as r:
            data = r.read()
    except Exception as e:
        print(f"    poster download failed for {tconst}: {e}", flush=True)
        return None
    with open(hit, "wb") as fh:
        fh.write(data)
    return data


def write_posters(text, resolved):
    """Replace the POSTERS block with data URIs for everything we resolved."""
    print(f"\nFetching posters for {len(resolved)} titles …", flush=True)
    rows, got, total = [], 0, 0
    for title, year, tconst in resolved:
        data = poster_bytes(tconst)
        if not data:
            continue
        got += 1
        total += len(data)
        uri = "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")
        rows.append("  %s: %s," % (json.dumps(f"{title}|{year}"), json.dumps(uri)))

    block = "const POSTERS = {\n" + "\n".join(rows) + "\n};"
    new, n = re.subn(r"const POSTERS = \{.*?\};", lambda _: block, text, count=1, flags=re.S)
    if n != 1:
        sys.exit("Could not find the POSTERS block in index.html")
    print(f"Posters written: {got} of {len(resolved)}   ·   {total / 1024:.0f} KB of image data")
    return new


ENTRY = re.compile(r'^\s*\{t:"')
FIELD = re.compile(r'(\w+):"((?:[^"\\]|\\.)*)"')


def main():
    if not os.path.exists(HTML):
        sys.exit(f"{HTML} not found — run this from the repository root.")

    idx, ratings = load_index(), load_ratings()

    lines = open(HTML, encoding="utf-8").read().split("\n")
    matched = missed = 0
    unresolved = []
    resolved = []      # (title, year, tconst) — feeds the poster pass

    for i, line in enumerate(lines):
        if not ENTRY.match(line):
            continue

        line = re.sub(r",?\s*r:[\d.]+", "", line)  # clear any previous run
        fields = dict(FIELD.findall(line))
        ymatch = re.search(r"\by:(\d{4})", line)
        if "t" not in fields or not ymatch:
            continue
        year = int(ymatch.group(1))
        title = fields["t"]

        pinned = MANUAL.get((title, year))
        if pinned:
            cands = [pinned]
        else:
            cands = candidates_for(idx, title, year)
            if not cands and fields.get("o"):
                cands = candidates_for(idx, fields["o"], year)

        scored = [(ratings[t][1], ratings[t][0], t) for t in cands if t in ratings]
        if scored:
            scored.sort(key=lambda s: s[0], reverse=True)  # most-voted title wins
            rating, tconst = scored[0][1], scored[0][2]
            lines[i] = line.replace(
                f'g:"{fields["g"]}"', f'g:"{fields["g"]}",r:{rating:.1f}', 1
            )
            resolved.append((title, year, tconst))
            matched += 1
        else:
            missed += 1
            q = urllib.parse.quote_plus(f"{title} {year}")
            unresolved.append(f"{title} ({year})\n      https://www.imdb.com/find/?q={q}")

    text = "\n".join(lines)
    if TMDB_KEY:
        text = write_posters(text, resolved)
    else:
        print("\nTMDB_API_KEY not set — skipping posters, POSTERS block left as it is.")
    open(HTML, "w", encoding="utf-8").write(text)

    total = matched + missed
    print(f"\nRatings written: {matched} of {total}   ·   unmatched: {missed}")
    if unresolved:
        print("\nNo confident match for these. Open the link, copy the tt id,")
        print("and add it to the MANUAL table at the top of this script:")
        for t in unresolved:
            print("  ·", t)
    print(f"\n{HTML} updated. Commit and push to publish.")


if __name__ == "__main__":
    main()
