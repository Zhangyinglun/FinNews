# AGENTS.md — Utils Directory

## OVERVIEW
Shared services: logging, LLM digest, email notifications.

## MODULES
| Module | Purpose | Key Interface |
|--------|---------|---------------|
| `logger.py` | Colored console/file logging | `setup_logger(name, log_file)` |
| `helpers.py` | Utility functions | `format_date()`, `read_json()` |
| `digest.py` | LLM summaries via OpenRouter | `generate_digest(data, template)` |
| `digest_controller.py` | Orchestrates digest generation | 517 lines, main digest logic |
| `email_sender.py` | Gmail SMTP | `EmailSender.send_html_email()` |

## CONVENTIONS

### Logging
- `setup_logger()` only in entrypoints (main.py, tests)
- Within modules: `logging.getLogger(__name__)`
- Bilingual format: `"任务完成 | Task complete"`

### LLM Digest
- All LLM calls through `digest.py` via OpenRouter
- Requires `OPENROUTER_API_KEY` in `.env`
- Output maintains Markdown structure

### Email
- Requires `GMAIL_USER`, `GMAIL_APP_PASSWORD` in `.env`
- HTML templates with plain-text fallback

## STYLE
- Keep `helpers.py` flat
- Handle `FileNotFoundError`/`PermissionError` in IO ops
- Type hints mandatory
