
# Spice Pantry — Project Brief

Source of truth for scope and content decisions. Save this at `docs/PROJECT_BRIEF.md` in the repository. Paired with `AGENTS.md` at the repo root, which holds the technical rules.

---

## 1. Business identity

Customer-facing brand is **Spice Pantry**, the trading name of the registered business **Desi Roots**. Business email is `support@desiroots.co.uk`. The domain is already owned.

Tagline: **WE SUPPLY THE SPICE, YOU CREATE THE MAGIC.**

Use the supplied logo exactly as provided. Do not redesign it. Logo and tagline are subject to final sign-off before launch.

## 2. Business model

A **B2B wholesale supplier** currently serving **Bristol and surrounding areas**, delivering with its own vehicles.

The business may later expand beyond Bristol, serve more of the UK, stock products from countries other than India, and grow the catalogue. **The website must therefore not permanently position Spice Pantry as an Indian-only spice company.** Imagery and copy should read as global premium grocery, not region-specific.

## 3. Target customers

Business buyers only: restaurants, cafés, hotels, grocery stores, retailers, supermarkets, catering companies, and other wholesale buyers. The site must feel professional and B2B rather than like a consumer grocery store.

## 4. Website purpose

A **product catalogue and wholesale showcase**, not an e-commerce site.

Visitors **can** view, search and filter products, browse categories and brands, open detailed product pages, submit wholesale enquiries, contact the business, and read about the company and the wholesale process.

Visitors **cannot** create an account, log in, add to cart, purchase, check out, pay online, place an order, or view order history. None of this functionality exists.

## 5. Authentication

No customer login of any kind. Only administrators authenticate, via Django admin at a non-default URL path, secured with Django authentication, HTTPS, CSRF protection, secure cookies, rate limiting, security headers, 2FA where practical, and logging where appropriate. The admin must never be linked from public navigation.

## 6. Catalogue

Approximately **450–500 products**.

Six categories: **Rice, Spices, Flour, Oils, Lentils, Pickles.**

Multiple brands; the final brand list is still to be supplied.

**Product card** shows a large product image, category, product name, brand, available pack sizes, an optional badge such as Featured or Best Seller, and a View Details button. It shows **no price, no Add to Cart, no Buy Now.**

## 7. Product detail page

One reusable template per product, covering: image, name, brand, category, description, available sizes, country of origin, ingredients where applicable, storage information, packaging information, product code / SKU, nutrition information where available, related products, and a wholesale enquiry call to action.

Primary action wording: **Request Wholesale Information** or **Enquire About This Product**.

## 8. Search

Search must cover product name, brand, and category. Searching "rice" returns rice products; searching a brand name returns that brand's products.

## 9. Sitemap

Home · About Us · Products · Product Detail · Brands · Wholesale · FAQ · Contact · Privacy Policy · Cookie Policy · Terms & Conditions · 404

**No separate gallery page** — quality photography is used throughout the site instead.

## 10. Homepage structure

In this order: announcement bar → sticky navigation → hero → Why Choose Spice Pantry → product categories → featured products → featured brands → wholesale process → testimonials → FAQ preview → contact CTA → footer.

## 11. Hero section

**One single hero image. No slider.** A premium lifestyle food photograph — spices, rice, lentils, flour, herbs, natural or wooden surfaces, warm natural light. It should feel global rather than specifically Indian.

Title: **Premium Spices & Grocery Products for Your Business**

Subtitle: Supplying restaurants, cafés, retailers and food businesses with carefully selected products across Bristol and nearby areas.

Buttons: **Browse Products** and **Request Wholesale Quote**.

## 12. Why Choose Spice Pantry

Four points: Premium Quality Products · Reliable Local Delivery · Trusted Wholesale Supply · Multiple Leading Brands.

## 13. Wholesale process

A four-step visual, built in HTML and CSS rather than as an image: **Browse Products → Send Enquiry → Receive Quote → Delivery.** The business handles delivery itself within Bristol and nearby areas.

## 14. Testimonials

The section may exist structurally, but **real testimonials will be added later and must never be invented.** The section hides itself entirely while no approved testimonials exist.

## 15. FAQ

Planned questions: which areas do you deliver to; do you supply restaurants; how can I request wholesale pricing; do you supply retailers; do you supply multiple brands; what types of products do you stock; how can I enquire about a specific product. **Final answers must be supplied and approved by the business.** Stored in a model so they stay editable from the admin.

## 16. Enquiry form

The site's main conversion mechanism. Fields: Full Name, Business Name, Business Type, Email, Phone, Product or Category of Interest, Message, and a privacy consent checkbox. Button reads **Submit Enquiry**.

Enquiries are saved to the database **and** emailed to the business. They never create a customer account.

## 17. Admin capability

Administrators manage products (add, edit, delete, publish/unpublish, images, category, brand, sizes, specifications, SEO fields), categories (including display ordering), brands (logo, description), enquiries (view, search, mark status, add notes), and editable site content including homepage featured selections, FAQs and contact information.

## 18. Visual direction

Premium, minimal, modern, wholesale. The site should feel elegant, trustworthy, professional, warm, spacious and established — **not** flashy, overly colourful, cluttered, neon, or consumer-grocery. Predominantly light and airy.

**Palette:** Warm Saffron `#C98A2B` (primary) · Olive Green `#667A3E` (secondary) · Soft White `#FCFBF8` (background) · White `#FFFFFF` (cards) · Charcoal `#2F2F2F` (text) · Light Beige `#E8E2D8` (borders).

**Typography:** Poppins for headings, Inter for body.

## 19. Photography

Product images: clean white background, professional pack shots, consistent aspect ratios. Hero and banner images: lifestyle food photography, natural light, premium composition.

## 20. Responsive behaviour

Must work on desktop, laptop, tablet and mobile. Product grid runs 4 columns on desktop, 2–3 on tablet, and 1–2 on mobile.

## 21. SEO requirements

Built SEO-first: semantic HTML, correct H1/H2/H3 hierarchy, unique SEO titles and meta descriptions, canonical URLs, breadcrumbs, XML sitemap, `robots.txt`, structured data including Product schema, descriptive URLs, image alt text, fast pages, and mobile-friendly layout. Every product needs its own SEO-friendly URL.

## 22. Performance approach

With only ~500 products, no distributed architecture is needed. Focus on optimised images in modern formats, lazy loading, pagination, database indexes, efficient queries, responsive images, minimal JavaScript and lightweight CSS.

## 23. Cookies and legal

Minimal cookies. Necessary cookies cover admin sessions and CSRF. Non-essential analytics or marketing cookies load only according to the consent setup. A UK-appropriate cookie consent system is required.

Privacy Policy, Cookie Policy and Terms & Conditions are all required. **Legal text must be finalised by the business before launch — do not invent company or legal details.**

## 24. Backups

Code in GitHub. Database via `pg_dump`. Server snapshots if affordable. A separate strategy for product media as the image library grows. Avoid depending on a single server.

---

## Still to be finalised

Exact domain · phone number · WhatsApp number · exact business address · final brand list · final product data · logo approval · UI approval · final hosting confirmation · final legal text · actual product images.

Anywhere these are needed, use an obvious placeholder and a `TODO` comment. Contact details in particular must be read from the `SiteSettings` model so they can be filled in later without a code change.

---

## The guiding principle

Spice Pantry is a **catalogue-first B2B platform, not an online shop.** The architecture should be simple enough to run cheaply today, but structured so that customer accounts, restaurant accounts, a cart, orders, Stripe payments, order tracking, inventory and eventually a mobile app can be added later **without throwing away this project.**
