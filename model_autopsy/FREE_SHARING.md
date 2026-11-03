# Model Autopsy — Meta AI hackathon sharing (Meta is CORE, key stays hidden)

MIT licensed. Meta (Muse Spark via api.meta.ai) is the core investigator —
bounded tool-calling loop over real diagnostics. Local pandas/sklearn tools
are the evidence engine Meta drives, not a replacement. For the hackathon,
judges must see the Meta path.

## Your two questions, answered directly

**1. "Wouldn't they need their own API key?"**
Not if you host. Two valid hackathon paths:
- A (recommended for judging): you host the backend with YOUR key,
  share YOUR URL. Guests get full Meta investigation with zero setup,
  zero key, zero cost to them.
- B: they run locally with THEIR OWN key from https://api.meta.ai.
  Core diagnostics run free, but the scored Meta investigator turn
  requires a key either way (yours via A, or theirs via B).

**2. "Let them use MY key WITHOUT seeing it?"**
Yes — architecture already does this:
- Key lives only in backend process env (`model_autopsy/.env`, gitignored).
- Frontend never imports it; `/api/meta/status` and `/api/settings`
  return only `key_configured: true/false`, never the value.
- Guests click "Run Meta turn" on YOUR server → backend calls
  api.meta.ai server-side → they see Meta's answer, never the key.
- Never paste the key in chat, screenshots, or repo.

## Share path A — hosted Meta (best for judges, no key for them)

1. You run backend with your key in `model_autopsy/.env` (never share file).
2. Verify: Integrations → Test connection (GET /models, no spend) → OK,
   then run one full "Run Meta turn" yourself first.
3. Expose your server (same WiFi, ngrok/tailscale, or deploy) and share URL.
4. Judges open YOUR URL → upload CSV → Run Meta turn → report.
   Your key stays server-side. Set a spend cap/quota on your Meta account.

## Share path B — judges run locally with their own key

1. Share repo/zip (MIT permits use/modify/distribute).
2. They set `MODEL_API_KEY` in `model_autopsy/.env` (see `.env.example`),
   restart backend, Test connection → OK.
3. Without a key the app runs honestly in manual mode (tools still run),
   but that does NOT demonstrate the Meta hackathon entry — Meta turn
   will refuse with "MODEL_API_KEY is not configured."

## Cleaner version notes

- Not shared: `model_autopsy/backend/data/` (uploads), `*.log`, `.pid`,
  `__pycache__`, `frontend/dist` — all gitignored, none committed.
- `model_autopsy/.env.example` is template-only (real key never committed).
- License: MIT (`model_autopsy/LICENSE`).
