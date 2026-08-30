# Screen Records of the Late War, 1931–1949

**[Read it here → christofstadler.github.io/ww2-screen-records](https://christofstadler.github.io/ww2-screen-records/)**

A graded index of 214 Second World War films, television serials and documentaries,
arranged by **the period of history they depict** rather than the year they were released.
Styled as a declassified War Department registry sheet.

## What's in it

- **214 titles** across ten parts, from the 1937 war in China to the trials and rubble of 1949
- **19 countries**, with roughly 45% subtitled — Soviet, German, Japanese, Polish,
  French, Italian, Nordic, Dutch and Chinese cinema alongside the Anglo-American canon
- **Gradings** on the Admiralty pattern (A1 essential → C3 entertainment only)
- **Origin flags** beside each country code, drawn inline so nothing is fetched
- **Poster plates** beside each entry, which grow to 3× on hover (see below)
- **Caveat flags** on 14 titles that mislead on a specific point of record, with the reason given
- Filter by form (film / serial / factual), by language, by decade of release
  (1950+ through 2000+), and by free-text search — the filters combine
- Every title links to its IMDb entry

## Running it

No build step, no dependencies and no third-party requests. `index.html` holds
the markup, styling and data; the poster images sit beside it in `posters/`.
Open `index.html` in a browser, or serve the folder:

```
python3 -m http.server 8000
```

## Publishing

Hosted with GitHub Pages from the repository root at
<https://christofstadler.github.io/ww2-screen-records/>. In **Settings → Pages**, set
the source to the `main` branch and the `/ (root)` folder.

## IMDb ratings

**You don't need to do anything.** A GitHub Action
(`.github/workflows/update-ratings.yml`) runs on your first push, fills real
ratings into `index.html` from IMDb's own published dataset, and commits the
result. It re-runs monthly so the figures stay current, and you can trigger it
by hand from the **Actions** tab at any time.

Ratings need no secrets — that pass uses the built-in `GITHUB_TOKEN`. Pushes made
with that token don't trigger workflows, so it can't loop. **Posters do need one**,
covered in the next section.

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

## Poster plates

Posters are optional and off until you add a key. IMDb's published dataset carries
no images, so they come from [TMDb](https://developer.themoviedb.org/docs/getting-started),
matched on the IMDb id the ratings pass has already resolved.

Add your TMDb key as a repository secret named `TMDB_API_KEY` under
**Settings → Secrets and variables → Actions**, then re-run the workflow from the
**Actions** tab. The script downloads TMDb's `w342` renditions into `posters/`,
one `<imdb-id>.jpg` per title, and writes relative paths to them into the
`POSTERS` block in `index.html`. TMDb serves the size we want, so nothing is
resized locally and no packages are needed.

The images live beside the page rather than inside it. That keeps `index.html`
under 100 KB and means a browser only fetches the plates that scroll into view —
inlining them at this resolution would have cost several megabytes on every load.
The page still opens from `file://` with the network off, so long as `posters/`
is sitting next to it.

Until the secret exists the plate column collapses itself rather than showing rows
of empty boxes, so the page looks exactly as it did before.

Don't hand-edit `POSTERS` — like `r`, it's regenerated wholesale by the script,
which also deletes posters for titles you've removed from the list.

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
