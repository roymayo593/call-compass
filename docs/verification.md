# Verification record

## Automated local API checks

`python3 -m unittest discover -s tests -v` — 6 tests passed on 13 November 2026.

Coverage includes all eight distinct stages, unchanged multilingual words, repeated starts, repeated close, updates rejected after close, workspace isolation, invalid stages/types/oversized notes, required follow-up details, CORS, and preserving saved calls when AI is not configured.

## Browser checks

Verified in the in-app browser: creating a sample call, reload restoring the active call, selecting stage results, jumping to stage 5, preserving a verbatim need, ending at stage 5, inspecting the unchanged need and information-only outcome, and seeing stage 5 in history. Unrecorded stages remain marked as unrecorded.

## Deployed checks

`python3 tests/deployed_smoke.py https://call-compass-api.onrender.com` — passed on 13 November 2026 against the deployed Supabase database and real free-tier Gemini API.

- Health reported database connected and AI configured.
- Start retried with the same UUID kept the same call/start time.
- Eight distinct stages persisted, including mixed-language notes.
- A different workspace received 404 for the call.
- The finished call preserved stage 8, the information-only outcome, and follow-up.
- Gemini generated a factual handover explicitly stating that no meeting was agreed.

The test used synthetic data only. No supplied transcript was sent to Gemini.

## Public browser end-to-end check

https://call-compass-iota.vercel.app — passed on 13 November 2026.

- A sample call was started through the public Vercel frontend and Render backend.
- Each of the eight stages was selected and saved in order.
- A synthetic English/Hindi need was entered at stage 5. Reloading restored both its exact words and the selected result before continuing.
- The call was finished as information-only with a recorded email follow-up.
- The saved record showed stage 8 reached and all eight individual results, including the unchanged need.
- The Gemini button generated a real summary that explicitly said no meeting or callback had been agreed.
- Render's origin allowlist was updated to the exact production Vercel origin. No wildcard origin or browser API key was used.

Only the applicant's own video and final application/WhatsApp steps remain. The software build is complete.
