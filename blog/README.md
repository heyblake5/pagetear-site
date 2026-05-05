# Pagetear Blog Directory

This folder hosts the Pagetear SEO blog. Article HTML files are committed here by the SEO agent pipeline (skills under `brands/pagetear/` in the plugin workspace).

## Structure

```
public/blog/
  _assets/                    # shared brand assets (avatar, logo, og default)
  {article-slug}/             # one folder per published article
    index.html                # full self-contained HTML page
    images/                   # sourced charts/diagrams for that article
  index.html                  # blog gallery page (this folder's landing page)
```

## How articles get added

1. The daily-seo-article-pagetear scheduled task picks the next queued keyword from the Notion tracker.
2. seo-article-writer drafts an HTML article using `brands/pagetear/article-template.html`.
3. seo-voice-engine validates it against `brands/pagetear/voice-rules.json`.
4. vercel-publisher commits the new folder under `public/blog/{slug}/`, updates `public/sitemap.xml`, and patches the gallery card list in `public/blog/index.html` between the `<!-- ARTICLES_GALLERY_START -->` and `<!-- ARTICLES_GALLERY_END -->` markers.
5. Vercel auto-deploys on push to `main`.
6. The publisher submits the new URL to Google Indexing API.

## Manual edits

Avoid editing `public/blog/index.html` and `public/sitemap.xml` by hand inside the marker blocks. The publisher overwrites those regions on every run. Edits outside the markers stay safe.
