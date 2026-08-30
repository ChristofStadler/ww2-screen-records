#!/usr/bin/env python3
"""
update_ratings.py — fill real IMDb ratings into index.html

Downloads IMDb's own published dataset (https://developer.imdb.com/non-commercial-datasets/)
and writes an `r:` value into every entry in the PARTS array.

    python3 update_ratings.py

No third-party packages needed. First run downloads ~190 MB and takes a few
minutes; the files are cached in ./.imdb-cache so later runs are quick.
Safe to run repeatedly — existing ratings are replaced, not duplicated.
"""

import csv
import gzip
import io
import os
import re
import sys
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


ENTRY = re.compile(r'^\s*\{t:"')
FIELD = re.compile(r'(\w+):"((?:[^"\\]|\\.)*)"')


def main():
    if not os.path.exists(HTML):
        sys.exit(f"{HTML} not found — run this from the repository root.")

    idx, ratings = load_index(), load_ratings()

    lines = open(HTML, encoding="utf-8").read().split("\n")
    matched = missed = 0
    unresolved = []

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

        scored = [(ratings[t][1], ratings[t][0]) for t in cands if t in ratings]
        if scored:
            scored.sort(reverse=True)  # most-voted title wins
            rating = scored[0][1]
            lines[i] = line.replace(
                f'g:"{fields["g"]}"', f'g:"{fields["g"]}",r:{rating:.1f}', 1
            )
            matched += 1
        else:
            missed += 1
            q = urllib.parse.quote_plus(f"{title} {year}")
            unresolved.append(f"{title} ({year})\n      https://www.imdb.com/find/?q={q}")

    open(HTML, "w", encoding="utf-8").write("\n".join(lines))

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
