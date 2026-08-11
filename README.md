# Newsletter Automation

Give it a topic, get back a researched, branded, chart-illustrated HTML newsletter
sent (or drafted) straight to Gmail.

Built on the **WAT framework** (Workflows, Agents, Tools): Markdown SOPs in
[`workflows/`](workflows/) describe *what* to do, an AI agent (Claude Code)
orchestrates *when* and *how*, and deterministic Python scripts in
[`tools/`](tools/) do the actual execution — API calls, chart rendering, email
sending. See [`CLAUDE.md`](CLAUDE.md) for the full philosophy.

## What it does

1. **Research** a topic via the Tavily Search API (free tier, web-grounded).
2. **Synthesize** it into newsletter sections, pulling out real statistics
   worth visualizing.
3. **Chart** those statistics with matplotlib — bar charts, pie charts, or
   stat-tile callouts, rendered deterministically so numbers are always
   accurate (never AI-hallucinated text).
4. **Generate** any purely decorative/mood art via Pollinations.ai (free,
   no key) — kept strictly separate from real data visualization.
5. **Render** it all into a single branded, email-safe HTML file (fully
   inlined CSS, embedded images).
6. **Deliver** it as a Gmail draft (default) or send it immediately, via the
   Gmail API.

## Project layout

```
assets/brand/       Brand config (colors, font, logo) + reference material
config/              recipients.json (gitignored — copy from .example)
tools/                The deterministic scripts (see below)
tools/templates/      Jinja2 HTML email template
workflows/            The SOP: workflows/create_newsletter.md
.tmp/                 Disposable intermediates (research JSON, rendered charts/HTML)
```

## Setup

### 1. Install dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Research API key (free)

Copy `.env.example` to `.env` and fill in a [Tavily](https://tavily.com) API
key (free tier: 1,000 search credits/month, no credit card).
`tools/make_infographics.py` (Pollinations.ai) needs no key at all.

### 3. Gmail API access (one-time, manual)

This is the fiddly part — three separate things all need to be true, or
you'll hit one of the errors below:

1. **Create an OAuth client of type "Desktop app"** in
   [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials).
   ("Web application" will *not* work — see troubleshooting below.)
   Download its JSON and save it as `credentials.json` in the project root.
2. **Add your sending Gmail address as a Test user** on the OAuth consent
   screen config (APIs & Services → OAuth consent screen → Test users).
3. **Enable the Gmail API** for the project (APIs & Services → Library →
   Gmail API → Enable).

The first time you run `tools/send_newsletter_email.py`, it'll open a
browser consent screen and cache a `token.json`; after that it's
non-interactive.

| Error | Cause | Fix |
|---|---|---|
| `Error 400: redirect_uri_mismatch` | OAuth client is "Web application" type | Recreate as "Desktop app" |
| `Access blocked: ... has not completed the Google verification process` | Sending address isn't a Test user | Add it under OAuth consent screen → Test users |
| `403 accessNotConfigured: Gmail API has not been used...` | Gmail API not enabled | Enable it in APIs & Services → Library |

### 4. Brand config

Edit [`assets/brand/brand.json`](assets/brand/brand.json) — accent color,
text colors, font stack, and `logo_url` (a local path gets auto-embedded as
a base64 data URI at build time; leave blank for a text-only masthead).

### 5. Recipients

```powershell
Copy-Item config\recipients.example.json config\recipients.json
# then edit config/recipients.json with real addresses
```

## Usage

Run the steps manually (or ask Claude Code to follow
[`workflows/create_newsletter.md`](workflows/create_newsletter.md) end to end):

```powershell
# 1. Research
.\.venv\Scripts\python.exe tools\research_topic.py "your topic" --out .tmp\research.json

# 2. Write .tmp\content.json by hand (see schema in tools/build_newsletter_html.py),
#    pulling real numbers out of the research for chart data.

# 3. Chart the real numbers
.\.venv\Scripts\python.exe tools\make_chart.py --data .tmp\chart.json --out .tmp\infographics\chart1.png

# 4. (Optional) decorative art
.\.venv\Scripts\python.exe tools\make_infographics.py "a mood/hero image prompt" --out .tmp\infographics\hero.png

# 5. Render the final HTML
.\.venv\Scripts\python.exe tools\build_newsletter_html.py --content .tmp\content.json --out .tmp\newsletter.html

# 6. Draft (default) or send
.\.venv\Scripts\python.exe tools\send_newsletter_email.py .tmp\newsletter.html --subject "Subject line"
.\.venv\Scripts\python.exe tools\send_newsletter_email.py .tmp\newsletter.html --subject "Subject line" --send
```

## Tools reference

| Script | Purpose |
|---|---|
| `research_topic.py` | Tavily Search API → synthesized answer + citations (JSON) |
| `make_chart.py` | matplotlib bar / pie / category-grid charts, brand-styled, real numbers only |
| `make_infographics.py` | Pollinations.ai generative images — decorative/mood art only, never for numbers or legible text |
| `build_newsletter_html.py` | Jinja2 + premailer → final inlined-CSS HTML, embeds local images as base64 |
| `send_newsletter_email.py` | Gmail API — draft by default, `--send` to send immediately; converts embedded images to inline CID attachments (Gmail strips raw `data:` URIs on received mail) |

## Content JSON schema

See the docstring in `tools/build_newsletter_html.py` for the full shape.
Each section can independently carry a `stats` block (native HTML stat
tiles) and/or an `infographic` image — mix and match per section.

## Design notes / lessons learned

- **AI image generation ≠ data visualization.** Free/open image models
  (Pollinations, and Google's own "Nano Banana" family) reliably fail at
  rendering legible text and exact numbers. Anything that needs to be
  *accurate* goes through `make_chart.py` (matplotlib); AI image generation
  is reserved for purely decorative art with no text/number requirements.
- **Pie charts must sum to ~100%**, or they misrepresent completeness —
  `make_chart.py` warns on the chart itself if they don't.
- **Gmail strips inline `data:` base64 images** from received mail even
  though they render fine in a local browser preview. Images must go out as
  proper inline CID attachments (handled automatically in
  `send_newsletter_email.py`).
- Recipients go in **Bcc**, not To/Cc, so they don't see each other's
  addresses.

## What's gitignored (and why)

`.env`, `credentials.json`, `token.json`, `client_secret*.json`,
`config/recipients.json` — all real secrets/PII. `.tmp/` is fully disposable
regenerated output. Copy the corresponding `.example` files to get started.
