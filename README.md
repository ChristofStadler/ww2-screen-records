# Screen Records of the Late War, 1931–1949

A graded index of 212 Second World War films, television serials and documentaries,
arranged by **the period of history they depict** rather than the year they were released.
Styled as a declassified War Department registry sheet.

## What's in it

- **212 titles** across ten parts, from the 1937 war in China to the trials and rubble of 1949
- **19 countries**, with roughly 45% subtitled — Soviet, German, Japanese, Polish,
  French, Italian, Nordic, Dutch and Chinese cinema alongside the Anglo-American canon
- **Gradings** on the Admiralty pattern (A1 essential → C3 entertainment only)
- **Caveat flags** on 14 titles that mislead on a specific point of record, with the reason given
- Filter by form (film / serial / factual), by language, by decade of release
  (1950+ through 2000+), and by free-text search — the filters combine
- Every title links to its IMDb entry

## Running it

It's a single self-contained HTML file with no build step, no dependencies and no
external requests. Open `index.html` in a browser, or serve the folder:

```
python3 -m http.server 8000
```

## Publishing

Hosted with GitHub Pages from the repository root. In **Settings → Pages**, set the
source to the `main` branch and the `/ (root)` folder.

## IMDb ratings

**You don't need to do anything.** A GitHub Action
(`.github/workflows/update-ratings.yml`) runs on your first push, fills real
ratings into `index.html` from IMDb's own published dataset, and commits the
result. It re-runs monthly so the figures stay current, and you can trigger it
by hand from the **Actions** tab at any time.

The Action needs no secrets — it uses the built-in `GITHUB_TOKEN`. Pushes made
with that token don't trigger workflows, so it can't loop.

To do the same thing locally instead:

```
python3 update_ratings.py
```

The **IMDb above** filter stays disabled until ratings exist, then switches on
by itself — nothing to configure.

Standard library only, no packages to install. The first run downloads about
190 MB and takes a few minutes; the files are cached in `.imdb-cache/` so later
runs are quick. It's safe to re-run whenever you want to refresh the numbers —
existing values are replaced rather than duplicated. Anything it can't match
confidently is listed at the end so you can fill it in by hand.

The dumps land in `.imdb-cache/`, which is already gitignored. Anything the
matcher can't resolve is listed in the run log with a search link; pin those by
IMDb id in the `MANUAL` table at the top of the script.

## Editing the list

All entries live in the `PARTS` array in the `<script>` block at the bottom of
`index.html`. Each one looks like this:

```js
{
  t: "Come and See",          // title
  o: "Иди и смотри",          // original-language title (optional)
  y: 1985,                    // year of release
  r: 8.4,                     // IMDb rating (filled in by update_ratings.py)
  c: "SU",                    // country code
  k: "F",                     // form: F film, S serial, D factual
  g: "A1",                    // grading: A1 A2 B1 B2 C3
  lg: ["Russian","German"],   // spoken languages; drives the Tongue filter
  n: "A Belarusian boy…",     // the note shown under the title
  w: "…"                      // caveat text (optional; adds a red CAVEAT flag)
}
```

Add an entry to the relevant part's `items` array and reload. A language that
doesn't yet appear in the list gets its own filter button automatically. The counts, filters
and IMDb links all derive from the data, so nothing else needs touching.

## Licence

The code is yours to do as you like with. The assessments are opinions.
