# Spice Pantry — 5-Day Build Roadmap

**Brand:** Spice Pantry (trading name of Desi Roots)
**Build:** B2B wholesale product catalogue — no cart, no checkout, no customer login
**Budget:** £0. Every tool below is free or has a permanent free tier.
**Time available:** 4–5 hours/day × 5 days ≈ **22 hours total**
**Confirmed:** Oracle Cloud Always Free VPS · product list ready, no product images

---

## Read this bit first — the honest maths

You have about 22 working hours. A Django catalogue with 480 products, an admin panel, an enquiry system, eleven pages, SEO, and a self-managed Linux server is roughly a 22–23 hour job **if nothing goes wrong**. There is no slack in this plan.

Two things follow from that.

**One: the plan below has a cut list.** If you fall behind, you cut from the bottom of the cut list, not from Day 5. Deployment is not optional; testimonials are.

**Two: the things most likely to stop you launching are not code.** They are your domain login details, the phone number, the business address, the legal text, your sister's approval, and product photos. Every one of those sits with someone other than you. Chase them on Day 1 morning, not Day 5. The build is designed so the site can go live with those fields empty and be filled in later from the admin panel without touching code.

---

## Decision you asked me to make: how Lovable's design reaches the site

**Build the pages as Django templates with Bootstrap 5. Use Lovable purely as a visual reference — look at it, screenshot it, then rebuild it.** Do not port Lovable's React code.

Three reasons.

The whole commercial point of this site is that a chef in Bristol googles "wholesale spices supplier Bristol" and finds you. Django templates send finished HTML to Google on the first request. A React app sends an empty page and then fills it in with JavaScript, which needs extra machinery to rank properly — machinery you do not have 22 hours to build.

Porting the React code means running two applications that talk to each other over an API. That is two deployments, two sets of bugs, and roughly double the work, on a free server with limited memory.

And your original brief already said Bootstrap 5 and vanilla JavaScript. That instinct was right. Stick with it.

Practical consequence: budget **one hour, once** in Lovable. Generate the homepage, the product card, and the product detail page. Screenshot them. Freeze. The free Lovable tier limits how many prompts you get per day, so do not burn them iterating on button corners.

---

## The free tool stack

> **Verify the numbers before you rely on them.** The tool choices below are sound, but free-tier *limits* drift constantly and I could not check them live. Spend ten minutes on Day 1 confirming these five on the vendors' own pricing pages, because each one shapes a build decision: Oracle's Always Free compute allowance, Brevo's daily email cap, Lovable's current free prompt limit, Neon's free tier (Neon was acquired by Databricks, so this is the likeliest to have changed), and whether Antigravity is still free. If any has tightened, the alternatives in each row still work.

### Design and assets

| Job | Tool | Notes / limits |
|---|---|---|
| Visual direction | **Lovable** free tier | Limited prompts per day. One hour, then freeze. |
| CSS framework | **Bootstrap 5.3** via CDN | Zero build step. Saves hours. |
| Icons | **Bootstrap Icons** or **Lucide** | Free, MIT. |
| Fonts | **Google Fonts** — Poppins (headings), Inter (body) | Already your decision. Self-host later for speed. |
| Free component snippets | **Start Bootstrap**, **Flowbite**, **Themewagon** | MIT-licensed blocks to adapt, not copy wholesale. |
| Hero + category photos | **Unsplash**, **Pexels**, **Pixabay** | Free commercial use. Pick warm, natural-light, wooden-surface shots. Keep them global-looking, not specifically Indian. |
| Image compression / WebP | **Squoosh.app** | Browser-based, free. Target under 150 KB for the hero. |
| Favicon | **RealFaviconGenerator** | Feed it your existing logo. |
| Diagrams (wholesale 4-step) | Plain HTML + CSS | Do not use an image. Text is better for SEO and mobile. |

### Code and database

| Job | Tool | Notes |
|---|---|---|
| AI coding IDE | **Antigravity** (free) | See the section on driving it properly. |
| Editor | **VS Code** | Free. |
| Version control | **Git** + **GitHub** private repo | Free. Your only real backup on Days 1–4. |
| Language | **Python 3.12+** | Free. |
| Framework | **Django 5.2 LTS** | LTS means security patches for years. Deliberately *not* the newest release — Django 6.x exists but is not LTS. Confirm on djangoproject.com that 5.2 is still the current LTS before you start. |
| Database | **PostgreSQL 16 or 17** | Free. |
| DB viewer | **DBeaver Community** or **pgAdmin** | Free. Optional. |

Django packages, all free and all pulling real weight in this timeline:

- **django-import-export** — bulk CSV/Excel product import through the admin. This is the package that turns 480 products from a two-day typing job into a ten-minute job. Non-negotiable.
- **django-environ** — keeps secrets out of Git.
- **Pillow** — image handling.
- **django-crispy-forms** + **crispy-bootstrap5** — renders the enquiry form as tidy Bootstrap without you writing form HTML.
- **whitenoise** — serves CSS/JS straight from Django. Means you do not need to configure Nginx static file rules or a CDN.
- **gunicorn** — the production application server.
- **psycopg[binary]** — Postgres driver.
- **django-axes** — locks out repeated failed admin logins. Cheap, important.
- **django-cleanup** — deletes image files when you delete a product, so the server disk does not silently fill.
- **django-debug-toolbar** — development only, shows you slow queries.
- **sentry-sdk** — free error tracking, catches the bugs real visitors hit.

Built into Django, so use them rather than installing anything: `django.contrib.sitemaps` for the XML sitemap, `django.contrib.postgres.search` if you want proper full-text search later, and the built-in cache framework using local memory — you do **not** need Redis for 480 products.

### Forms, email, and consent

| Job | Tool | Free limit |
|---|---|---|
| Enquiry notification emails | **Brevo** SMTP | 300 emails/day free, forever. Best choice. |
| Fallback email | **Gmail SMTP** with an App Password | Works in 5 minutes. Fine to start. |
| Spam protection | **Cloudflare Turnstile** | Free, unlimited, no annoying puzzles. Plus a hidden honeypot field. |
| Cookie banner | **vanilla-cookieconsent** (Orest Bida, MIT) | Free, lightweight, UK/GDPR-shaped. |

Important: every enquiry saves to the database **as well as** emailing you. If email delivery ever fails, you have not lost a customer.

### Hosting and operations

| Job | Tool | Notes |
|---|---|---|
| Server | **Oracle Cloud Always Free** — Ampere ARM, Ubuntu 24.04 | Up to 4 cores / 24 GB RAM, free forever. Read the capacity warning below. |
| DNS, CDN, WAF | **Cloudflare** free plan | Also gives you caching and basic DDoS protection. Set it up even if nothing else. |
| SSL certificate | **Let's Encrypt** via Certbot | Free, auto-renews. |
| Web server | **Nginx** | Free. |
| Process management | **systemd** | Already on Ubuntu. Simpler than Docker for this. |
| Firewall | **UFW** + **fail2ban** | Free. |
| Database backups | **pg_dump** cron + **rclone** to **Google Drive** (15 GB free) | Or Backblaze B2, 10 GB free. |
| Uptime alerts | **UptimeRobot** free | 50 monitors, 5-minute checks. Emails you when the site dies. |
| Error tracking | **Sentry** free | 5,000 errors/month. |
| Analytics | **Cloudflare Web Analytics** | Free and cookieless, which greatly simplifies your consent obligations compared to Google Analytics. It does not remove the need for a banner covering essential cookies — have that confirmed alongside your legal text. |

Skip Docker for version one. It is the right call eventually, but on a free box with 22 hours on the clock, `systemd` + `gunicorn` + `nginx` gets you live faster and breaks in more googleable ways.

### SEO and testing — all free

Google Search Console, Bing Webmaster Tools, PageSpeed Insights, Chrome Lighthouse, Google Rich Results Test, securityheaders.com, and Screaming Frog free edition (crawls up to 500 URLs, which happens to be exactly your catalogue size).

---

## ⚠️ The Oracle warnings that will save you a day

Oracle's free ARM instances are frequently **"Out of capacity"** in popular regions. People lose whole afternoons to this. Do three things:

1. **Sign up in the first 20 minutes of Day 1**, not Day 5. Account verification can take hours, occasionally longer.
2. If you hit a capacity error, **try a different availability domain** in your region, and try again at off-peak hours.
3. **Upgrade the account to Pay As You Go.** This sounds alarming but it does not remove your Always Free resources — it keeps them free while dramatically improving your chances of getting an ARM instance. Set a £0 budget alert.

**Plan B, and it is a good one:** if Oracle refuses to give you a server on Day 5, deploy to **Render free tier + Neon free Postgres** instead. Thirty minutes, custom domain, free SSL. The site sleeps after 15 minutes of inactivity, which is not ideal, but a slightly slow site beats no site. Then move to Oracle the following week with zero code changes. Keep this in your back pocket.

### And a second Oracle trap, further out

Oracle reclaims Always Free compute instances it considers **idle** — historically, low CPU and low network traffic across a seven-day window. A brand-new B2B catalogue with barely any visitors is exactly the profile that gets flagged, so this is a real risk for you around week two, not a theoretical one.

The fix is already in your plan: the **UptimeRobot monitor checking the site every five minutes** generates enough steady traffic to keep the instance looking alive. Set it up on Day 5 as listed and this mostly takes care of itself. Confirm Oracle's current idle policy when you sign up, since the thresholds have moved before.

---

## Day 1 — Foundation, database, admin, and all 480 products in

**Target by end of day: you can browse every real product in the Django admin.**

- [ ] **(First 20 minutes, do these before anything else)** Start the Oracle Cloud signup. Create a Cloudflare account. Create the private GitHub repo. Message your sister asking for: phone number, WhatsApp number, business address, final brand list, and confirmation on the logo. Ask whoever holds the domain for the registrar login.
- [ ] Scaffold the Django project. Apps: `catalogue`, `enquiries`, `pages`, `core`. Split settings into `base.py` / `dev.py` / `prod.py` now — retrofitting this on Day 5 under pressure is miserable.
- [ ] Local PostgreSQL running, `.env` file, `.gitignore`, `requirements.txt`.
- [ ] Write the models. This is the most important hour of the week:
  - `Category` — name, slug, description, image, display_order, is_active
  - `Brand` — name, slug, logo, description, is_featured
  - `Product` — name, slug, sku, category FK, brand FK, description, country_of_origin, ingredients, storage_info, packaging_info, nutrition_info, is_published, is_featured, badge, meta_title, meta_description, created/updated
  - `PackSize` — product FK, size label, display_order
  - `ProductImage` — product FK, image, alt_text, is_primary
  - `Enquiry` — name, business_name, business_type, email, phone, product FK (nullable), category interest, message, consent_given, status, admin_notes, created
  - `FAQ` — question, answer, display_order, is_active
  - `Testimonial` — quote, author, business, is_active
  - `SiteSettings` — a single-row model holding phone, WhatsApp, email, address, announcement bar text, social links
- [ ] **That `SiteSettings` model is deliberate.** Your phone number and address are still unknown. Putting them in the database instead of hardcoding them into templates means you can launch with blanks and your sister can fill them in herself later, from the admin, with no developer and no redeploy.
- [ ] Add database indexes on every slug, plus `is_published`, `is_featured`, and the category/brand foreign keys.
- [ ] Configure the Django admin: `list_display`, `list_filter`, `search_fields`, `prepopulated_fields` for slugs, `PackSize` and `ProductImage` as inlines on `Product`, bulk publish/unpublish actions.
- [ ] Wire up **django-import-export** on `Product`. Use the CSV template supplied alongside this roadmap.
- [ ] Convert your existing product list into that CSV and **import all 480 products**. Check the count. Spot-check twenty rows.
- [ ] Commit and push.

---

## Day 2 — Freeze the design, then build the product pages

**Target by end of day: the product catalogue works and looks right on your phone.**

- [ ] **One hour in Lovable, hard stop.** Give it your palette (saffron `#C98A2B`, olive `#667A3E`, soft white `#FCFBF8`, charcoal `#2F2F2F`, beige borders `#E8E2D8`), Poppins and Inter, the tagline, and the brief "premium, minimal, spacious, B2B wholesale, not a consumer grocery shop". Generate the homepage, a product card, and a product detail page. Screenshot everything. Freeze.
- [ ] Build `base.html` properly, once: announcement bar, sticky navigation with a working mobile menu, footer, Bootstrap CDN, Google Fonts, and your palette as CSS custom properties in `:root`. Everything else in the week inherits from this, so get the spacing generous and the type sizes right here.
- [ ] Build the reusable product card partial: image, category, name, brand, pack sizes, optional badge, View Details button. No price, no cart — exactly as decided.
- [ ] Products listing page: responsive grid at 4 columns desktop / 3 tablet / 2 small tablet / 1–2 mobile, category filter, brand filter, search box, pagination at 24 per page, and a proper empty state for "no products match".
- [ ] Search across product name, brand name, and category name using `Q` objects with `icontains`. At 480 products this is instant — resist the urge to build anything cleverer.
- [ ] Product detail page: image, breadcrumbs, specification table, pack sizes, related products from the same category, and the "Request Wholesale Information" call to action that carries the product name through to the enquiry form.
- [ ] Open the site on your actual phone, not just a resized browser window.
- [ ] **Send your sister screenshots tonight.** Her feedback then arrives during Day 3, which is the only way approval fits in this week.

---

## Day 3 — Homepage, enquiry system, and every remaining page

**Target by end of day: a stranger could use this site to send you a wholesale enquiry.**

- [ ] Homepage, following your agreed order: announcement bar → sticky nav → single hero image → Why Choose Spice Pantry (four points) → six category cards → featured products → featured brands → four-step wholesale process → testimonials → FAQ preview → contact CTA → footer.
- [ ] Make the testimonials section **hide itself entirely when there are no active testimonials**. You decided not to invent fake customer quotes, and this is how you honour that without leaving a hole in the page.
- [ ] Enquiry system: a `ModelForm` rendered with crispy-bootstrap5, hidden honeypot field, Cloudflare Turnstile, save to database, email notification via Brevo, and a real thank-you page rather than a JavaScript alert.
- [ ] Product-specific enquiries should arrive pre-filled with the product name so you know what they are asking about.
- [ ] Admin view for enquiries: newest first, filter by status, searchable by business name.
- [ ] Brands listing page, and brand pages that show that brand's products.
- [ ] About Us, Wholesale, FAQ (reading from the `FAQ` model so it stays editable), and Contact pages.
- [ ] Custom 404 and 500 templates that match the brand and offer a link back to Products.
- [ ] Privacy Policy, Cookie Policy, and Terms & Conditions as real pages with clearly marked placeholder text. **Do not invent company registration numbers, ICO registration details, or legal claims.** Mark them `TODO` and get them confirmed before launch.
- [ ] Act on your sister's Day 2 feedback.

---

## Day 4 — Images, SEO, security, speed

**Target by end of day: the site is genuinely ready to be seen by the public.**

- [ ] Images. You have no product photos, so build a **clean branded SVG placeholder** — soft white background, subtle olive or saffron mark, the product name — and use it wherever a photo is missing. Done well this reads as deliberate minimalism rather than an unfinished site, and it means missing photos never block launch.
- [ ] Source one hero image and six category images. Compress to WebP in Squoosh. Add explicit `width` and `height` attributes and `loading="lazy"` on everything below the fold. Write real alt text — this is both accessibility and free SEO.
- [ ] SEO pass: unique title and meta description per page pulled from the model fields, canonical URLs, Open Graph tags, breadcrumbs, `django.contrib.sitemaps` covering products, categories, brands and static pages, a `robots.txt` pointing at the sitemap, and JSON-LD structured data for `Product`, `Organization` and `BreadcrumbList`.
- [ ] Production settings: `DEBUG = False`, `ALLOWED_HOSTS`, `SECURE_SSL_REDIRECT`, HSTS, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `X_FRAME_OPTIONS`, `SECURE_CONTENT_TYPE_NOSNIFF`, secret key from the environment.
- [ ] Security: move the admin off `/admin/` to a private path, enable django-axes lockouts, set a genuinely strong superuser password.
- [ ] Cookie consent banner plus Cloudflare Web Analytics. Because that analytics is cookieless, your banner only has to cover the essential cookies — much simpler compliance story.
- [ ] Performance: add `select_related` on category and brand, `prefetch_related` on images and pack sizes, then run Lighthouse and fix whatever it flags. Aim above 90 on mobile.
- [ ] Test on a real phone, a tablet if you have one, and a laptop.

---

## Day 5 — Server, domain, SSL, launch

**Target by end of day: it is live at your real domain over HTTPS.**

- [ ] Provision the Ubuntu 24.04 ARM instance. Create a non-root user with sudo, set up SSH key login, disable password login.
- [ ] **Open the ports in two places.** Oracle has a cloud-level Security List *and* the instance firewall. Forgetting the Security List is the single most common Oracle Cloud mistake — the server looks fine and the site is simply unreachable. Open 80 and 443 in both.
- [ ] Install fail2ban, Python, PostgreSQL. Create the database and a dedicated database user.
- [ ] Deploy: clone the repo, create the virtualenv, install requirements, write the production `.env`, `migrate`, `collectstatic`, `createsuperuser`. Confirm it works over the raw IP before touching DNS.
- [ ] Gunicorn as a systemd service so it restarts on crash and on reboot. Nginx in front of it as a reverse proxy.
- [ ] Point the domain's nameservers at Cloudflare, add an A record to your server IP, then run Certbot for the Let's Encrypt certificate. Force HTTPS, redirect www to non-www (or the reverse — just pick one and be consistent).
- [ ] Import the product CSV into production, or dump and restore your local database.
- [ ] Backups: a nightly `pg_dump` cron job, `rclone` pushing the dump to Google Drive, and a 7-day retention rule. Test the restore once — an untested backup is not a backup.
- [ ] UptimeRobot monitor. Sentry connected. Verify the domain in Google Search Console and submit the sitemap.
- [ ] **Smoke test as a stranger:** load every page, run three searches, apply each filter, open five product pages, and submit a real enquiry from your phone. Confirm the email actually arrives.
- [ ] Write your sister a one-page admin guide: how to log in, how to add a product, how to upload a photo, how to read enquiries, how to edit the phone number and address.

---

## Cut list — sacrifice from the top down if you fall behind

1. Testimonials section (nothing real to show yet anyway)
2. Nutrition information fields
3. Structured data beyond `Product`
4. Admin 2FA (do it in week two — django-otp, about an hour)
5. Separate brand detail pages (redirect straight to a filtered product list instead)
6. Rich text editor in the admin (a plain textarea is fine)
7. Docker
8. Any staging environment

Never cut: deployment, HTTPS, backups, the enquiry form, or the legal pages.

---

## How to drive Antigravity without wasting your hours

AI coding tools lose you time in one specific way: you ask for too much at once, it produces something almost-right and sprawling, and you spend an hour untangling it. Avoid that.

Put your project brief into the repo as `docs/PROJECT_BRIEF.md` and tell Antigravity to read it before every significant task. Add a short `AGENTS.md` at the repo root stating the rules it must not break: Django templates only, Bootstrap 5, no React, no cart, no customer login, the exact hex palette, Poppins and Inter.

Then work in small vertical slices. Ask for the models file first and review it yourself before moving on, because every later mistake compounds off a bad schema. Then the admin configuration. Then one template at a time. Commit to Git after every piece that works, so you always have a known-good state to fall back to. When something breaks, paste the actual traceback rather than describing the symptom.

And read the models file with your own eyes. It is the one file where a bad decision costs you real hours later.

---

## What is still blocking launch, and who owns it

| Blocker | Owner | Needed by |
|---|---|---|
| Domain registrar access | You / domain holder | Day 5 morning |
| Phone + WhatsApp number | Sister | Can go in after launch via admin |
| Business address | Sister | Before launch — required on UK legal pages |
| Final brand list | Sister | Day 1 ideally, Day 3 at latest |
| Logo approval | Sister | Use as-is for now, as agreed |
| UI approval | Sister | Send Day 2 evening |
| Legal text | Sister / a real review | Before launch |
| Product photos | Sister | After launch — placeholders cover you |

The site is architected so that only the domain, the address, and the legal text genuinely gate launch. Everything else can arrive afterwards through the admin panel.

---

## After launch — the growth path you already designed for

Because you have `Product`, `Category`, `Brand` and `Enquiry` as clean separate models with real slugs and no e-commerce assumptions baked in, you can later add customer accounts, restaurant-specific pricing, a cart, orders, Stripe, inventory, and a mobile app on top of this same project. Nothing here has to be thrown away — which was the point.

Sensible week-two additions, in order: admin 2FA, real product photography, Google Business Profile for local Bristol search, a proper Docker setup, and self-hosted fonts to shave a few hundred milliseconds off load time.

---

## Additional Guidelines & Tasks

1. **Newsletter Signup**: Add a simple newsletter signup form in the footer utilizing Brevo's email service (and local database storage) early on to capture interested leads.
2. **SEO Sitemap Submission**: Manually submit your `sitemap.xml` file in Google Search Console once deployed.
3. **Mobile Responsiveness Audits**: Test mobile responsiveness thoroughly across desktop, tablet, and mobile breakpoints as B2B buyers frequently browse during operations.
4. **Sister Feedback loop**: Maintain visual confirmation with regular screenshots and review cycles to capture adjustments early.
5. **Dynamic Thumbnails with Pillow**: Post-launch, use Pillow inside `ProductImage` saves to auto-generate responsive thumbnails/optimized images.

