# AGENTS.md — Desi Roots

Rules for any AI coding agent working in this repository. Read this file and `docs/PROJECT_BRIEF.md` before writing code. If a request in chat conflicts with this file, stop and ask rather than guessing.

---

## What this project is

A **B2B wholesale product catalogue** website for Desi Roots (renamed from Spice Pantry on 7 Nov 2026) — a UK spice and grocery wholesaler serving Bristol and nearby areas. Roughly 480 products across six categories. Business buyers browse the catalogue and submit a **wholesale enquiry**. That enquiry form is the only conversion mechanism on the site.

It is **not a shop**. Nobody buys anything on this website.

---

## Hard rules — do not break these

**Architecture**

- Django templates rendered server-side. **No React, Next.js, Vue, Svelte, or any SPA.**
- **No REST API and no Django REST Framework.** There is no separate frontend to feed.
- **No Node, npm, webpack, Vite, or any JavaScript build step.** Bootstrap comes from a CDN.
- **No Tailwind.** Bootstrap 5.3 only.
- Vanilla JavaScript only, and as little as possible. Bootstrap 5 does not need jQuery — do not add it.

**Scope — none of the following exist in this project**

- No cart, checkout, basket, payment, or Stripe.
- No `price` field anywhere. Products have no prices. Pricing is quoted privately by email.
- No stock levels, inventory counts, or order management.
- No customer accounts, registration, login, password reset, or order history.
- No wishlist, reviews, ratings, or star scores.

**Authentication**

- Only staff authenticate, through the **built-in Django admin**. Do not build a custom admin dashboard.
- The admin lives at a non-obvious URL path from an environment variable, never at `/admin/`.

**Free tier only**

This project has a £0 infrastructure budget. Do not introduce Redis, Celery, Elasticsearch, AWS S3, Cloudinary, or any paid or subscription service. Caching uses Django's built-in local-memory backend. Static files are served by WhiteNoise. Media files sit on the server's local disk.

**Never invent content**

This is a real business with real legal exposure. Do not fabricate:

- Testimonials, customer names, or quotes. The testimonials section must **hide itself entirely** when no active testimonials exist.
- Phone numbers, WhatsApp numbers, email addresses, or postal addresses.
- Company registration numbers, VAT numbers, or ICO registration details.
- Privacy policy, cookie policy, or terms and conditions text. Use clearly marked `TODO` placeholders.
- Product names, SKUs, ingredients, or country of origin. Product data comes from the CSV import only.

Where real information is missing, use an obvious placeholder and leave a `{# TODO: confirm with business #}` comment.

**Contact details are never hardcoded**

The phone number, WhatsApp number, email, address and announcement bar text all live in the single-row `SiteSettings` model and reach templates through a context processor. Never type a contact detail into a template. The business must be able to change these from the admin without a deploy.

---

## Stack

| Layer | Choice |
|---|---|
| Language | Python 3.12+ |
| Framework | Django 5.2 LTS |
| Database | PostgreSQL 16+ |
| Templates | Django templates |
| CSS | Bootstrap 5.3 via CDN + one custom stylesheet |
| Icons | Bootstrap Icons |
| Fonts | Google Fonts — Poppins (headings), Inter (body) |
| Forms | django-crispy-forms + crispy-bootstrap5 |
| Bulk import | django-import-export |
| Static files | WhiteNoise |
| Server | Gunicorn behind Nginx, managed by systemd |
| Host | Oracle Cloud Always Free, Ubuntu 24.04 |

Do not add a package that is not already in `requirements.txt` without asking first.

---

## Brand tokens — use these exact values

Define once as CSS custom properties in `:root` and reference them everywhere. No hex codes scattered through templates, no inline styles.

```css
:root {
  --sp-saffron:    #C98A2B;  /* primary */
  --sp-olive:      #667A3E;  /* secondary */
  --sp-bg:         #FCFBF8;  /* page background */
  --sp-card:       #FFFFFF;  /* cards */
  --sp-text:       #2F2F2F;  /* body text */
  --sp-border:     #E8E2D8;  /* borders, dividers */
  --sp-font-head:  'Poppins', sans-serif;
  --sp-font-body:  'Inter', sans-serif;
}
```

Visual direction (updated 2026-11-14 at the owner's request): colourful, vibrant and attractive, while staying professional, trustworthy and easy to use, to the standard of leading UK food and wholesale websites. Use the spice accent colours below for sections, badges and icons; show real product packs and food photography generously. It must still read as a professional wholesale supplier. Avoid neon, clutter, and anything that hurts readability: every text/background pair must meet WCAG 2.2 AA contrast.

```css
:root {
  --sp-turmeric:   #E8A317;  /* accent: badges, highlights (dark text on it) */
  --sp-chilli:     #B8322A;  /* accent: offers, emphasis (white text on it) */
  --sp-cardamom:   #4F7D3A;  /* accent: success, fresh (white text on it) */
  --sp-masala:     #7A3E1D;  /* accent: deep warm sections (white text on it) */
}
```

Saffron (`--sp-saffron`, 2.9:1 on white) is too light for text or buttons. Use it only for decoration (borders, rings, backgrounds without text). For text and buttons use the text-safe shades, added 2026-11-17 after a contrast check:

```css
:root {
  --sp-saffron-text: #8F5E14;  /* gold text, links, outline buttons (5.6:1 on white) */
  --sp-cta:          #B35A12;  /* main buttons, white text (4.8:1) */
  --sp-cta-dark:     #9C4D10;  /* main buttons' darker end and hover (6.0:1) */
}
```

---

## Project structure

```
config/
  settings/  base.py · dev.py · prod.py
core/        SiteSettings, context processors, base.html, shared partials
catalogue/   Category, Brand, Product, PackSize, ProductImage
enquiries/   Enquiry model, form, views
pages/       About, Wholesale, FAQ, Contact, legal pages, FAQ + Testimonial models
docs/        PROJECT_BRIEF.md
```

## URL scheme

Descriptive, lowercase, hyphenated, and stable — these get indexed by Google and must not change later.

```
/                          home
/products/                 listing, with ?category= &brand= &q= &page=
/products/<slug>/          product detail
/categories/<slug>/        category listing
/brands/                   brand index
/brands/<slug>/            brand's products
/wholesale/                process + enquiry form
/about/  /faq/  /contact/
/privacy/  /cookies/  /terms/
```

---

## Conventions

Every public model gets a unique indexed `SlugField`, populated from the name and set as `prepopulated_fields` in the admin. `Product` additionally carries `is_published`, `is_featured`, `meta_title` and `meta_description`. Public views must filter on `is_published=True` — unpublished products are invisible to visitors and absent from the sitemap.

List views always use `select_related('category', 'brand')` and `prefetch_related` for images and pack sizes. A product grid must never fire a query per card; if you are unsure, check with django-debug-toolbar before moving on.

Pagination is 24 products per page. Search covers product name, brand name and category name using `Q` objects with `icontains` — at this catalogue size that is more than fast enough, so do not reach for full-text search or a search engine.

Images require an `alt` attribute, explicit `width` and `height`, and `loading="lazy"` below the fold. Products with no photograph fall back to the branded SVG placeholder, never to a broken image or a stock "no image" graphic.

Secrets and environment-specific values come from `.env` via django-environ. Never commit `.env`, never hardcode `SECRET_KEY`, and never leave `DEBUG = True` reachable in production settings.

---

## Definition of done for any page

Before you call a template finished, confirm all of it:

- Extends `base.html`; nav and footer are not duplicated.
- Responsive at 4 / 3 / 2 / 1 columns across desktop, tablet, small tablet and mobile. Check at 375px width.
- Exactly one `<h1>`, with a sensible `<h2>`/`<h3>` hierarchy beneath it.
- Unique `<title>` and meta description, plus canonical URL and Open Graph tags.
- All images have meaningful alt text.
- No hardcoded contact details, no invented content, no `lorem ipsum`.
- No N+1 queries.
- Keyboard reachable, with visible focus states on links and buttons.

---

## Testing and self-check (required for every change)

An agent finishes tasks; it does not prove they are right. Every change follows these steps:

1. **Tests come with the change.** Add or update tests in the same change:
   - unit and integration tests (Django `TestCase`) for models, views, forms and admin behaviour;
   - a browser test in `e2e/` (Playwright) when a page, form or user journey changes.
2. **Everything passes before a commit.** Run the full suite (`python manage.py test --settings=config.settings.dev`), then the browser tests (`E2E=1 python manage.py test e2e --settings=config.settings.dev`; needs `requirements-dev.txt` and `python -m playwright install chromium`). Never commit with a failing or skipped-by-hand test.
3. **Attack your own work.** After building, act as a security tester and try to break it: bad and oversized input, HTML/script in every text field, missing or forged CSRF tokens, header injection in emails, URLs for unpublished or other people's data, repeated submissions and brute force. Report what you tried and what you found.
4. **Check under load when it matters.** For changes to the catalogue, search, home page or enquiry form, run `scripts/load_test.py` and compare the response times with the previous run.
5. **Say what was not verified.** If something could not be tested here (live email, the real server), say so plainly.

Development-only tools (Playwright, debug toolbar) live in `requirements-dev.txt` and are never installed on the live server.

---

## How to work in this repo

Work in small vertical slices and stop between them. Build the models first and wait for review before generating views or templates, because a schema mistake propagates into everything downstream. Then admin configuration. Then one template at a time.

Show migrations before applying them. Do not refactor files unrelated to the current task. Do not rename existing models or fields without asking — slugs and URLs are SEO-critical once live.

After each change, say plainly what the user should click to verify it works. When something breaks, ask for the actual traceback rather than guessing.

The deadline is tight and the budget is zero. Prefer the boring, built-in Django solution over the clever one every single time.
