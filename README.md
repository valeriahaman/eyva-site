# eyva-site — the public site at eyva.me

What is here

- `build_site.py` — builds `public/` from `../Brand/reference-briefs/eyva-landing-founder-preview.html`
  (the reference page Val and Claude Code edit). It adds the legal footer, writes `terms.html` and
  `privacy.html` (their words live in the script), wires the three forms to `/api/…`, copies the
  assets, `robots.txt`, `llms.txt`, and writes `sitemap.xml`.
- `public/` — the built site. Committed, so Cloudflare deploys exactly what was reviewed.
- `src/worker.js` — the Cloudflare Worker: serves `public/`, redirects www and eyva.shop to eyva.me,
  and handles `POST /api/join` and `POST /api/salon` (saves to KV `WAITLIST`, emails Val).
- `wrangler.jsonc` — Worker config (assets, KV, email binding).

Publishing a change

1. Edit the reference page (or the Terms/Privacy text in `build_site.py`).
2. `python3 build_site.py`
3. `git add -A && git commit -m "…" && git push`
   Cloudflare (Workers Builds) deploys from `main` in about a minute.

Reading the waitlist

Cloudflare dashboard → Storage & Databases → KV → `eyva-waitlist`. Keys `join:<time>:<id>`,
`salon:<time>:<id>`, and `email:<address>` → key of that person's entry. Every entry is also
emailed to the MAIL_TO address at the moment it arrives.
