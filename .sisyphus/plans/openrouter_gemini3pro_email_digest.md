# FinNews — OpenRouter (Gemini 3 Pro) 24h Rolling Digest → Gmail HTML Email

## Goal
After each pipeline run (both `python main.py --mode once` and scheduled runs), generate an **AI-written HTML digest** summarizing **all data collected within the last 24 hours** (rolling window) and send it to **multiple recipients via Gmail SMTP**.

Constraints (from user):
- Window: **rolling 24 hours**.
- Content scope: **all queried/collected information** (news + macro/econ + prices + fx, etc.).
- Email body: **AI summary only** (not full data dump).
- No local caching of “today’s news” as files. (In-memory rolling buffer is acceptable; user confirmed.)
- LLM provider: **OpenRouter**; model: **Gemini 3 Pro**.
- Email format: **HTML**.
- SMTP: **Google (Gmail)**.

## Success Criteria
### Functional
- When `ENABLE_EMAIL_DIGEST=true`, each run ends with exactly **one** digest email send attempt.
- Digest includes only items with `timestamp >= now - 24h` (rolling).
- Uses OpenRouter model id `google/gemini-3-pro-preview`.
- Sends HTML email via Gmail SMTP to `EMAIL_TO` list.

### Observable
- Logs show: window start/end, record counts per type/source, OpenRouter call status, SMTP status.
- Recipient inbox receives a readable HTML digest with:
  - Key themes
  - Top stories
  - Macro/econ snapshot
  - Price/fx snapshot
  - Gold/Silver impact section
  - Risk watchlist

### Pass/Fail
- PASS if OpenRouter call returns schema-valid JSON and SMTP sends successfully.
- FAIL if OpenRouter or SMTP fails; must be logged clearly and must not crash pipeline.

## Architecture Fit (Minimal Invasive)
FinNews currently:
- Builds records via scrapers → `DataCleaner` → `Deduplicator`.
- `main.py:run_once()` enriches articles with `ContentFetcher.enrich_articles()`.
- `schedulers/job_scheduler.py:run_pipeline()` does NOT enrich full content currently.
- Storage outputs are files, but digest must be built in-memory.

Plan:
1. Add a **digest controller** that maintains an **in-memory rolling buffer** across scheduled runs.
2. Add an **OpenRouter client** for chat completions.
3. Add an **SMTP mailer** for Gmail.
4. Wire digest send into:
   - `main.py:run_once()` end
   - `JobScheduler.run_pipeline()` end

## Data Windowing Strategy (No Local Cache)
### Chosen approach: In-memory rolling buffer
- Keep `self.rolling_records` in scheduler process memory.
- On each run:
  - Merge in new output records.
  - Deduplicate across runs using stable hash.
  - Prune anything older than `now - 24h`.

Trade-off:
- Restarting the process clears buffer and reduces the window to “this run only”.

## OpenRouter Integration Details
- Base URL: `https://openrouter.ai/api/v1`
- Endpoint: `POST /chat/completions`
- Auth: `Authorization: Bearer $OPENROUTER_API_KEY`
- Model: `google/gemini-3-pro-preview`
- Prefer `response_format.type=json_schema` with `strict=true` to ensure parseable output.

## Email Integration Details (Gmail SMTP)
- Server: `smtp.gmail.com`
- Port: `587`
- Use STARTTLS
- Credentials: Google **App Password** recommended (not interactive login).

## Files to Change / Add
### Modify
- `config/config.py`
  - Add env-backed config for OpenRouter + digest + SMTP.
  - Extend `Config.validate()` for digest enablement.

- `.env.example`
  - Add OpenRouter and Gmail SMTP variables.

- `main.py`
  - After `storage.save_processed(enriched_data)`, invoke digest controller to build summary and send email.

- `schedulers/job_scheduler.py`
  - Instantiate digest controller once in `__init__`.
  - Ensure scheduled pipeline also performs `ContentFetcher.enrich_articles()` (to match `main.py`).
  - After saving, call digest send.

### Add
- `utils/openrouter_client.py`
  - `OpenRouterClient.chat_completions(...)` with retries/timeouts.

- `utils/digest_controller.py`
  - `DailyDigestController(window_hours=24, dedup=True)`
  - `update(records)` merge+dedup+prune
  - `build_llm_input()` produce a bounded prompt string

- `utils/mailer.py`
  - `GmailSmtpMailer.send_html(subject, html_body, to_list)`

- Test scripts (repo pattern is standalone scripts):
  - `test_openrouter_digest.py`
  - `test_gmail_smtp.py`

## Config Spec
Add to `config/config.py` (env vars):
- `ENABLE_EMAIL_DIGEST` (default false)
- `DIGEST_WINDOW_HOURS` (default 24)
- `DIGEST_INCLUDE_FULL_CONTENT` (default false)
- `DIGEST_FULL_CONTENT_MAX_CHARS_PER_ARTICLE` (default 2000)
- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL` (default `google/gemini-3-pro-preview`)
- `OPENROUTER_TEMPERATURE` (default 0.3)
- `OPENROUTER_MAX_TOKENS` (default 4096)
- `OPENROUTER_TIMEOUT` (default 60)
- `OPENROUTER_MAX_RETRIES` (default 3)
- `OPENROUTER_HTTP_REFERER` (optional)
- `OPENROUTER_X_TITLE` (optional)
- `SMTP_HOST` (default `smtp.gmail.com`)
- `SMTP_PORT` (default 587)
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_USE_TLS` (default true)
- `EMAIL_FROM`
- `EMAIL_TO` (comma-separated list)

Validation rule:
- If `ENABLE_EMAIL_DIGEST`:
  - require OpenRouter key
  - require SMTP host/port/user/pass/from/to

## Prompt & Output Contract
### LLM Input composition (high-level)
- Header: generated time, window start/end, counts.
- Sections with compact bullets:
  - Macro/econ items
  - Price/fx items
  - News items: timestamp, source, title, summary, url; optionally truncated full_content

### Output: JSON Schema (strict)
The model must return valid JSON matching:
- `subject`: string
- `html_body`: string (full HTML document or HTML fragment)
- `window_hours`: integer
- `stats`: object (counts by type/source)
- `highlights`: object with arrays

Implementation notes:
- If JSON parse fails, fallback to sending a plain failure email with raw model text.

## Error Handling & Retries
### OpenRouter
- Retry on: 429, 500, 502, 503, 504.
- Do not retry on: 401/402 (credentials/credits).
- Log errors with `exc_info=True`.

### SMTP
- If SMTP send fails: log and continue pipeline (do not crash).

## Test Plan
### Objective
Verify end-to-end digest generation and email sending.

### Prerequisites
- `.env` configured with OpenRouter + Gmail App Password.

### Test Cases
1. OpenRouter digest generation:
   - Input: small synthetic digest text
   - Expected: schema-valid JSON; HTML contains required sections
   - How: `python test_openrouter_digest.py`

2. Gmail SMTP HTML send:
   - Input: simple HTML body
   - Expected: email received by all recipients
   - How: `python test_gmail_smtp.py`

3. One-shot pipeline integration:
   - Command: `python main.py --mode once`
   - Expected: pipeline completes; email sent once; logs show window and counts

4. Scheduled integration smoke:
   - Command: `python main.py --mode scheduled`
   - Expected: initial run sends digest; subsequent interval run sends digest; no crashes

### Success Criteria
All test cases pass.

## Implementation Checklist (Step-by-step)
1. Add config variables + validation.
2. Add OpenRouter client with retries.
3. Add digest controller with rolling buffer (merge/dedup/prune).
4. Add Gmail SMTP mailer.
5. Wire into `main.py` once mode.
6. Wire into scheduler (and add content enrichment).
7. Add standalone test scripts.
8. Manual run validation with commands above.

## Notes / Open Questions
- Rolling buffer is in-memory; restart loses historical 24h context.
- If email HTML grows too large, enforce a hard cap in prompt and instruct model to keep HTML concise.
