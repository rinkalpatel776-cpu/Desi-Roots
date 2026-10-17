# Spice Pantry — Migration & Developer Guide for Claude Code

This guide provides the complete context, setup steps, architectural rules, and pending tasks for continuing development of Spice Pantry using Claude Code on macOS.

---

## 1. Project Overview & Architecture

- **Project:** Spice Pantry (B2B wholesale product catalogue)
- **Business:** Customer-facing trading brand of Desi Roots (Bristol, UK).
- **Purpose:** A clean, professional wholesale supplier showcase and product enquiry portal.
- **Strict Scope Constraints (see `AGENTS.md`):**
  - **NOT an e-commerce shop.** No cart, no checkout, no payment gateways (no Stripe/PayPal), no customer accounts/registration.
  - **No public prices.** Products have no `price` field. Pricing is quoted privately via email.
  - **No JavaScript SPA / No Node build step.** Django templates rendered server-side with Bootstrap 5.3 CDN + vanilla CSS. No React, Vue, Next.js, Tailwind, Webpack, or Vite.
  - **Zero paid infrastructure budget (£0).** Local-memory caching, WhiteNoise for static assets, local disk for media. No Redis, Celery, AWS S3, or Elasticsearch.
  - **Authentication:** Only staff authenticate via Django Admin at a non-obvious URL path (`ADMIN_URL_PATH`).

---

## 2. Directory Structure

```
Spice Pantry/
├── config/
│   ├── settings/
│   │   ├── base.py              # Shared Django settings, apps, auth, brand tokens
│   │   ├── dev.py               # Development settings (local DB, debug tools)
│   │   └── prod.py              # Production settings (WhiteNoise, SSL, security)
│   ├── asgi.py
│   ├── urls.py                  # Root URL router (admin located at env-defined path)
│   └── wsgi.py
├── core/                        # SiteSettings (singleton), context processors, shared templates
├── catalogue/                   # Category, Brand, Product, PackSize, ProductImage
│   ├── management/commands/
│   │   ├── seed_catalogue.py        # Import products from CSV
│   │   └── collect_product_images.py# Candidate image discovery and audit tool
│   └── tests.py                 # Comprehensive catalogue & import test suite
├── enquiries/                   # Wholesale enquiry model, crispy form, submission & email views
├── pages/                       # Home, About, FAQ, Contact, legal pages (Cookies, Privacy, Terms)
├── docs/                        # PROJECT_BRIEF.md
├── media/                       # Uploaded & linked media
│   ├── brands/                  # Brand logo PNGs (background removed)
│   └── products/                # Product packshots (e.g. sp_fudco_pawa-thick-rice-flakes_f050959.jpg)
├── static/                      # Static CSS (`style.css`), logos, favicons, hero banners
├── templates/                   # Django server-rendered HTML templates
├── manage.py
├── AGENTS.md                    # Core project rules & constraints
├── PROJECT_BRIEF.md             # Business brief & brand requirements
├── requirements.txt             # Pinned Python dependencies
└── .env.example                 # Sanitized environment variable template
```

---

## 3. Environment & Python Setup

### Python Environment
- **Version:** Python 3.12 (via micromamba environment `spice-pantry`)
- **Python Binary Path:** `/Users/mantra1424/micromamba/envs/spice-pantry/bin/python`

### Activate Environment:
```bash
micromamba activate spice-pantry
# or use the full path directly:
/Users/mantra1424/micromamba/envs/spice-pantry/bin/python manage.py ...
```

### Install / Verify Dependencies:
```bash
pip install -r requirements.txt
```

---

## 4. PostgreSQL Database Configuration

### Database Details:
- **Engine:** PostgreSQL 18.4 (local cluster)
- **Database Name:** `spice_pantry_db`
- **Host:** `localhost`
- **Port:** `5432`
- **User:** `mantra1424`
- **Current Data Status:**
  - 111 Products imported in draft status (`is_published=False`).
  - 11 Brands (East End, TRS, Fudco, etc.).
  - 13 Categories (Rice, Spices, Flour, Oils, Lentils, Pickles, etc.).
  - 199 Pack sizes created and linked.
  - 1 Wholesale enquiry record.
  - 1 SiteSettings singleton record.

### Required Environment Configuration (`.env`):
Ensure `.env` exists in the project root with your local credentials:
```bash
cp .env.example .env
# Edit .env with your local settings:
# DATABASE_URL=postgres://mantra1424@localhost:5432/spice_pantry_db
# SECRET_KEY=<your-local-development-secret-key>
# DEBUG=True
```

---

## 5. Development Commands & Verification

### Run Django System Check:
```bash
python manage.py check --settings=config.settings.dev
```

### Run Automated Tests (all 22 currently passing):
```bash
# Run catalogue tests:
python manage.py test catalogue

# Run full project test suite:
python manage.py test
```

### Start Development Server:
```bash
python manage.py runserver --settings=config.settings.dev
# Access site at: http://127.0.0.1:8000/
# Access admin at: http://127.0.0.1:8000/<ADMIN_URL_PATH>/
```

---

## 6. Current Git State & Uncommitted Work

- **Branch:** `main`
- **HEAD Commit:** `579f04b` (*"Fix audit issues: align enquiry form with brief, restore CSS brand tokens, clean import/export and JSON-LD schema"*)
- **Tracked Modified Files:**
  - `catalogue/admin.py`: ProductResource extended with safe image import (pipe-separated filenames, directory traversal sanitization, idempotency, primary preservation).
  - `catalogue/tests.py`: Automated tests for image import, path traversal rejection, primary preservation, and command execution.
  - `.env.example`: Sanitized with safe generic placeholders.
- **Untracked Working Files:**
  - `catalogue/management/commands/collect_product_images.py`: Candidate image discovery & audit reporting command.
  - `candidate_images_report.csv`: 10-product image discovery audit report.
  - `products-import-ready-draft.csv` & `spice_pantry_111_products_staging.csv`: Importer-ready catalogue spreadsheets.
  - `media/products/sp_fudco_pawa-thick-rice-flakes_f050959.jpg`: Verified non-corrupt 600x400 JPEG downloaded for SKU `F050959`.

---

## 7. Backups Available

Two verified full backups exist outside the repository:
1. `~/SpicePantry_Backups/backup_2026-10-17_03-42-25/`
2. `~/SpicePantry_Backups/backup_2026-10-17_18-54-58/` (includes `CHECKSUMS.sha256`, PostgreSQL `.dump` archive, and full git bundle).

---

## 8. Remaining Tasks & Next Steps for Claude Code

1. **Git History Sanitization (Prior to GitHub Push):**
   - Review and execute the Git history cleanup plan to ensure early commits do not retain development default strings in `.env.example`.
2. **Product Image Linking:**
   - Link the downloaded image `sp_fudco_pawa-thick-rice-flakes_f050959.jpg` to product `F050959` via the CSV importer.
3. **Catalogue Image Discovery:**
   - Run `python manage.py collect_product_images` for remaining catalogue products.
   - For East End and TRS products, obtain packshots directly from the wholesaler trade price list/PDF catalogue.
4. **Product Review & Launch:**
   - Review imported products with stakeholders.
   - Bulk-publish approved products (`is_published=True`) via the Django Admin.
