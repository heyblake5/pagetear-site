# Pagetear Blog Assets

Shared assets used by every published article.

## Files expected here

- `blake-avatar.png` — circular byline avatar for Blake. 256x256 minimum, square crop. Reuse the same file Gallopeer uses, or upload a fresh one.
- `pagetear-logo.png` — square logo for JSON-LD `publisher.logo`. 256x256 minimum.
- `og-default.png` — fallback OpenGraph image when an article ships without a custom OG image. 1200x630, brand colors (white background, black + #ec3e39).
- `favicon.png` — site favicon. 256x256.

## Files vercel-publisher creates

Per-article images live one folder deeper, inside the article's own `images/` directory. Example layout:

```
public/blog/
  _assets/
    blake-avatar.png
    pagetear-logo.png
    og-default.png
  saas-homepage-copy-examples/
    index.html
    images/
      hubspot-conversion-chart.png
      animalz-content-ratio.png
      wynter-message-test-result.png
  index.html
```

The publisher writes article HTML into `public/blog/{slug}/index.html` and any sourced images into `public/blog/{slug}/images/{filename}.png`. Sources cited in the figcaption of each embed.
