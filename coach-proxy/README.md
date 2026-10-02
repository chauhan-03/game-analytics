# Coach proxy: connect the dashboard helper to your API key

The dashboard's Coach works without this, using built-in answers. Deploy this small
Cloudflare Worker to let Coach answer free-form questions through your model API.

**Why a proxy?** The dashboard is a public page. An API key placed in it would be readable
by anyone, who could then spend your credits. The Worker keeps the key as an encrypted
Cloudflare secret. The page only ever talks to the Worker.

## What it does

- **Accepts** `POST {"question": "...", "history": [...]}` only from the origins in
  `ALLOWED_ORIGINS`, which defaults to `https://chauhan-03.github.io`.
- **Calls the model** (low effort for quick chat replies) with a system prompt that limits it
  to this dashboard. Answers come only from `src/facts.json`, which `src/run_analysis.py`
  regenerates from the latest findings.
- **Fallbacks** are on (`fallbacks: "default"`): if a request is declined, the API re-runs it
  on the recommended fallback model instead of failing. To turn this off, remove `betas` and
  `fallbacks` from `src/index.ts`.
- **Limits:** questions are capped at 500 characters, and the history at the last 6 turns.

## Deploy

```bash
cd coach-proxy
npm install
npx wrangler login                 # your Cloudflare account (free tier is fine)
npx wrangler secret put API_KEY    # paste your key when prompted; it is never written to disk here
npx wrangler deploy                # prints https://game-analytics-coach.<you>.workers.dev
```

Then rebuild the dashboard pointing at it, and publish:

```bash
cd ..
COACH_API_URL=https://game-analytics-coach.<you>.workers.dev python src/run_analysis.py
```

Coach's header changes to "Live answers". If the Worker is unreachable or returns an
error, Coach falls back to its built-in answers, so the page never breaks.

**After the numbers change:** rerun `src/run_analysis.py`, then `npx wrangler deploy`, so the
Worker serves the new facts.

**Testing from your own machine:** add your local address to `ALLOWED_ORIGINS` in
`wrangler.toml`, e.g. `https://chauhan-03.github.io,http://localhost:8000`.

## Cost control

- Set a monthly spend limit for the key in your API console.
- Each answer is short (low effort; system prompt cached after the first call).
- For a public portfolio page, consider Cloudflare's rate-limiting rules on the Worker route.

## Check

```bash
npm run check   # TypeScript type-check against the installed SDK
```
