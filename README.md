# Call Compass

An eight-stage guide a caller can keep beside a cold call. Built for DeepThought’s FDE assignment by Soumyadeep Roy with AI coding assistance.

## Live links

- Frontend: Vercel import in progress.
- Backend: https://call-compass-api.onrender.com
- Health: https://call-compass-api.onrender.com/health

## What it does

- Covers Opening, Purpose, Permission, Their business, Their need in their words, Objection, Next step, and Close.
- Stage-specific guidance, anticipated responses, quick result buttons, and an exact-words field.
- Move between stages or end at any stage. No requirement to pretend an early call reached all eight.
- Saves stage results to Supabase. Browser drafts survive a refresh and failed requests; errors never pretend a save succeeded.
- Call history shows the reached stage, outcome, follow-up, and original notes. Outcomes distinguish information-only, referrals, meetings, and callbacks.
- Optional Gemini handover draft after a call, grounded in recorded evidence. AI never changes the original words or outcome.

## Architecture

`Vercel static frontend → Render Python REST API → Supabase Postgres`

`Render API → Gemini generateContent (free tier)`

The frontend is HTML, CSS, and vanilla JavaScript. The backend uses Python’s standard library: there is no package build or framework dependency. Supabase is accessed through its REST API. `supabase/schema.sql` defines tables, constraints, RLS, and transactional functions for stage saving and closing. A primary key per call/stage preserves eight distinct records while allowing corrections. Stage updates and closing lock the call row to avoid concurrent lost updates.

## Why this screen

Reading the supplied 100-call corpus revealed repeated confusion about the offer, outdated contact data, requests to see evidence first, reluctance to disclose information, and polite agreement to receive material being recorded as stronger interest. These patterns shaped the choices and reminders. Guidance is paraphrased; the source transcripts are excluded from this public repository and the deployed app. No corpus or real contact list is bundled.

The LLM earns its place after the conversation: it reduces handover work without adding latency to the live call. The caller retains responsibility for reviewing the draft. No sentiment scoring, automatic outcome changes, inferred needs, call recording, dialler, or unsolicited messaging is included.

## Local run

Python 3.9+ is sufficient:

```sh
STORAGE=sqlite SERVE_FRONTEND=1 PORT=8000 python3 backend/server.py
```

Open `http://localhost:8000`. SQLite is an explicit development adapter only; the production default is Supabase. Configure a Gemini key in the process environment to test real AI summaries. Without it, the app reports that AI is not configured and the saved call remains available.

```sh
python3 -m unittest discover -s tests -v
```

## Deploy

1. Create a free Supabase project. Enable Data API, disable automatic table exposure, enable automatic RLS. Run `supabase/schema.sql` in SQL Editor.
2. Create a free Python web service on Render from this repo. Build: `python -m compileall -q backend`. Start: `python backend/server.py`. Health: `/health`.
3. Set Render environment variables: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`, `GEMINI_MODEL=gemini-3.1-flash-lite`, and `ALLOWED_ORIGINS` to the exact Vercel origin. `PORT` is supplied by Render. Do not set `STORAGE=sqlite` in production.
4. Set `window.CALL_COMPASS_API` in `frontend/config.js` to the Render service URL.
5. Import the repo into Vercel with Root Directory `frontend`, Framework Preset `Other`, and no build command. Publish the directory itself.
6. Verify `/health`, start a call, save all eight stages, finish, refresh history, and draft a real Gemini summary. Render’s free instance can sleep: the app preserves drafts and offers a retry rather than fabricating success.

## API

Every call endpoint requires `Authorization: Bearer <64 lowercase hex characters>`. The browser generates a random 256-bit workspace token; the database stores its SHA-256 hash. Queries are scoped to that hash, and the service-role key is only on Render. This is a lightweight demo workspace, not a full user authentication system. Clearing browser storage loses workspace access; a copied token grants access. For production, replace it with user authentication and retention controls.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Checks database connectivity and reports whether AI is configured |
| POST | `/calls` | Starts a call with a client UUID (safe to retry) |
| GET | `/calls` | Lists up to 200 recent calls in this workspace |
| GET | `/calls/:id` | Reads a call with its stage results |
| PUT | `/calls/:id/stages` | Saves or corrects one stage result and exact words |
| POST | `/calls/:id/close` | Closes at the stage reached, with outcome and next step (safe to retry) |
| POST | `/calls/:id/summary` | Generates and caches an optional Gemini handover draft |

Notes have length limits, strict stage numbers, validated outcomes, and parameterized/structured database requests. CORS uses an explicit origin allowlist. RLS is enabled with no anonymous table access. The public API rate-limits requests; AI has per-workspace and global hourly limits in memory (reset on restart). Production should use durable quotas and identity-based limits.

## AI and privacy

Provider: Google Gemini, model `gemini-3.1-flash-lite` (configurable on Render). Purpose: a short, factual post-call handover. The backend sends stage selections, prospect words entered by the caller, outcome, and next step; it omits the prospect name, company, workspace token, and full call corpus. It uses low temperature and caps output. Provider errors or quota exhaustion leave the saved call intact and are shown explicitly. The free Gemini tier may use inputs to improve Google’s products: use fictional/sample notes for this demo. Source transcripts must remain private.

## Verification

Automated backend tests cover workspace isolation, retry behavior, distinct stage preservation, exact multilingual words, early close, post-close edits, validation, CORS, and graceful missing-AI behavior. The deployed Render → Supabase → Gemini smoke test also passed: all eight stages persisted, retries did not duplicate the call, another workspace could not read it, the finished record was readable, and Gemini returned a factual information-only handover. Full frontend deployment verification is pending. See `docs/verification.md`.
