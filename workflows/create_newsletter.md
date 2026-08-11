# Workflow: Create Newsletter

## Objective
Given a topic, produce a researched, branded, HTML newsletter with 1-3
AI-generated infographics, and leave it as a Gmail draft for the user to
review and send.

## Required Inputs
- **Topic** (from the user): what the newsletter is about, plus any angle,
  audience, or tone notes.
- `.env`: `TAVILY_API_KEY` must be filled in (free tier: 1,000 search
  credits/month, no credit card). `make_infographics.py` uses Pollinations.ai,
  which needs no API key at all.
- `credentials.json` at the project root: a Google OAuth client downloaded
  from the Google Cloud Console. One-time manual setup by the user — the
  agent cannot do this step. **Exact requirements, learned the hard way:**
  1. Application type must be **Desktop app**, not "Web application" — the
     downloaded JSON should have an `"installed"` top-level key, not `"web"`.
     A Web-app client fails OAuth with `Error 400: redirect_uri_mismatch`
     because `run_local_server()` uses a random localhost port that can't be
     pre-registered.
  2. On the **OAuth consent screen** config (not the client itself), add the
     sending Gmail address under **Test users** — otherwise auth fails with
     "has not completed the Google verification process... developer-approved
     testers." This applies even to the account that owns the Cloud project.
  3. The **Gmail API** must be explicitly enabled for the project (APIs &
     Services → Library → Gmail API → Enable), separate from creating OAuth
     credentials — otherwise API calls fail with 403 `accessNotConfigured`
     even after a successful OAuth consent.
- `config/recipients.json`: the list of recipient email addresses for this
  send.
- `assets/brand/brand.json`: newsletter name, accent color, font stack, logo
  URL. Ships with neutral defaults; edit directly to rebrand.

## Steps

1. **Confirm the brief.** Make sure the topic, angle, and audience are clear.
   Research runs on a free-tier quota (Tavily: 1,000 credits/month) and
   infographics are fully free (Pollinations.ai, no key/quota) — no need to
   ask before every single call, but avoid re-running the same research
   repeatedly since Tavily's quota is finite.

2. **Research.**
   ```
   python tools/research_topic.py "<topic>"
   ```
   Calls the Tavily Search API (free tier). Writes `.tmp/research_<slug>.json`
   containing a synthesized answer and citation URLs/content snippets.

3. **Synthesize structure.** Read the research JSON and draft the newsletter
   content as a JSON file (e.g. `.tmp/content_<slug>.json`) matching the shape
   `tools/build_newsletter_html.py` expects:
   ```json
   {
     "headline": "...",
     "intro": "... (optional)",
     "sections": [ {"heading": "...", "body_html": "<p>...</p>"} ],
     "infographics": [ {"src": "...", "alt": "...", "caption": "... (optional)"} ],
     "sources": [ {"title": "...", "url": "..."} ]
   }
   ```
   Pull `sources` straight from the research citations.

4. **Generate infographics.** For each concept worth visualizing (1-3 per
   issue), write an image prompt that describes the concept and references
   the brand accent color/style, then run:
   ```
   python tools/make_infographics.py "<prompt>" --out .tmp/infographics/<slug>.png
   ```
   Calls Pollinations.ai (free, no key — switched from Gemini's direct API,
   which turned out to require a linked billing account even on its
   "free tier": live testing returned `limit: 0` on every image model).
   **Visually check the downloaded image** before using it: free/open image
   models are unreliable at rendering legible text — don't rely on them for
   numbers or wordmarks that need to be accurate. For a logo/wordmark, it
   works much better to generate an icon/mark only (no text in the prompt's
   expected output) and overlay real HTML text next to it, rather than
   fighting the model to render text correctly. If the model's background
   isn't the color you asked for, a quick corner-color chroma-key in PIL
   (see how `assets/brand/logo.png` was produced) can make it transparent.
   Add the resulting path into the content JSON's `infographics` list.

5. **Render the HTML.**
   ```
   python tools/build_newsletter_html.py --content .tmp/content_<slug>.json --out .tmp/newsletter_<slug>.html
   ```
   Uses `assets/brand/brand.json` automatically. Open the output file in a
   browser to sanity-check layout before sending.

6. **Create the Gmail draft (default) or send directly (`--send`).**
   ```
   python tools/send_newsletter_email.py .tmp/newsletter_<slug>.html --subject "<subject line>"
   python tools/send_newsletter_email.py .tmp/newsletter_<slug>.html --subject "<subject line>" --send
   ```
   The first run on a machine opens a browser OAuth consent screen and
   caches `token.json`; later runs are non-interactive. Recipients come from
   `config/recipients.json` and are placed in Bcc. Default behavior creates a
   **draft** for review; only use `--send` when the user has explicitly asked
   to send immediately (it's a real, hard-to-reverse send — confirm the
   recipient list first if it's not just the user's own address).

## Edge Cases & Notes
- If `research_topic.py` returns thin results, consider a more specific
  topic/query rather than retrying the same call (Tavily free tier is
  1,000 credits/month — basic search costs 1, advanced costs 2).
- If `make_infographics.py` returns a low-quality/blank image, retry with a
  more explicit prompt and/or a fixed `--seed`; don't expect legible text in
  the output (see step 4).
- If `send_newsletter_email.py` errors about invalid_grant or expired token,
  delete `token.json` and rerun to re-trigger the OAuth consent flow.
- Gmail OAuth setup errors seen in practice, in the order they'll likely
  appear on a fresh setup — see "Required Inputs" above for the fixes:
  1. `Error 400: redirect_uri_mismatch` → OAuth client is "Web application"
     type, needs to be "Desktop app".
  2. `Access blocked: ... has not completed the Google verification
     process` → sending address isn't added as a Test user on the OAuth
     consent screen.
  3. `403 accessNotConfigured: Gmail API has not been used in project...` →
     Gmail API isn't enabled for the Cloud project.
- If images (logo/infographics) don't appear in the received email despite
  looking correct in the local `.tmp/*.html` preview: Gmail strips/ignores
  inline `data:` base64 image URIs in received mail even though they render
  fine in a browser. `send_newsletter_email.py` already handles this — it
  converts any `data:` URI `<img>` into a proper inline CID attachment
  (multipart/related) before sending. If a different email client still
  doesn't show images, check whether it needs `Content-Disposition: inline`
  handled differently, but CID is the standard fix.
- Update this section with anything learned in real runs (rate limits,
  Gmail quirks, better prompt patterns for infographics, etc.), per the
  self-improvement loop in `CLAUDE.md`.
