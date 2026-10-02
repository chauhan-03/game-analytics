/**
 * Coach proxy: lets the dashboard's Coach answer free-form questions through the model API
 * without putting the API key in the public page.
 *
 *   POST /  {"question": "...", "history": [{"role": "user"|"assistant", "content": "..."}]}
 *   ->      {"answer": "..."}
 *
 * The facts Coach may use are bundled at deploy time from src/facts.json, which
 * src/run_analysis.py regenerates, so a visitor cannot feed it different numbers.
 */
import ApiClient from "@anthropic-ai/sdk";
import facts from "./facts.json";

export interface Env {
  API_KEY: string;
  ALLOWED_ORIGINS: string;
}

const MAX_QUESTION = 500;
const MAX_HISTORY = 6;

const SYSTEM = `You are Coach, a friendly helper on a mobile game analytics dashboard called "Player Journey".
Answer in plain, simple words that a 10-year-old could follow: short sentences, at most 4 sentences,
numbers said as "X out of 100" where that helps. Use only the facts below. If a question is not about
this dashboard, its games, or its data, say kindly that you only know about this dashboard.
Never invent numbers. Do not use markdown headings or tables; **bold** for one key number is fine.

FACTS
${facts.facts}`;

type Turn = { role: "user" | "assistant"; content: string };

function cors(origin: string | null, env: Env): Record<string, string> {
  const allowed = env.ALLOWED_ORIGINS.split(",").map(s => s.trim());
  return origin && allowed.includes(origin)
    ? { "Access-Control-Allow-Origin": origin, "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type", "Vary": "Origin" }
    : {};
}

function json(body: unknown, status: number, headers: Record<string, string>): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json", ...headers } });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const origin = request.headers.get("Origin");
    const headers = cors(origin, env);
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers });
    if (request.method !== "POST") return json({ error: "Use POST" }, 405, headers);
    if (!headers["Access-Control-Allow-Origin"]) return json({ error: "Origin not allowed" }, 403, headers);

    let body: { question?: unknown; history?: unknown };
    try { body = await request.json(); } catch { return json({ error: "Send JSON" }, 400, headers); }
    const question = typeof body.question === "string" ? body.question.trim().slice(0, MAX_QUESTION) : "";
    if (!question) return json({ error: "Ask a question" }, 400, headers);

    // Keep only well-formed, alternating text turns, newest last, starting with a user turn.
    const history: Turn[] = (Array.isArray(body.history) ? body.history : [])
      .filter((t): t is Turn => !!t && (t.role === "user" || t.role === "assistant") && typeof t.content === "string")
      .slice(-MAX_HISTORY)
      .map((t): Turn => ({ role: t.role, content: t.content.slice(0, 1000) }));
    while (history.length && history[0].role !== "user") history.shift();
    const asked: Turn = { role: "user", content: question };
    const messages: Turn[] = [...history, asked]
      .filter((t, i, all) => i === 0 || t.role !== all[i - 1].role);
    if (messages[messages.length - 1].role !== "user") messages.push(asked);

    const client = new ApiClient({ apiKey: env.API_KEY });
    try {
      const response = await client.beta.messages.create({
        model: "claude-opus-5-5",
        max_tokens: 2048,
        output_config: { effort: "low" },          // short chat answers
        betas: ["server-side-fallback-2026-07-01"],
        fallbacks: "default",                        // re-run a declined request on the recommended fallback model
        system: [{ type: "text", text: SYSTEM, cache_control: { type: "ephemeral" } }],
        messages,
      });
      if (response.stop_reason === "refusal") {
        return json({ answer: "I can't help with that one. Ask me about the players, the shops or the levels!" }, 200, headers);
      }
      const answer = response.content.flatMap(b => (b.type === "text" ? [b.text] : [])).join("\n").trim();
      return json({ answer: answer || "Hmm, I'm not sure. Try asking another way!" }, 200, headers);
    } catch (err) {
      if (err instanceof ApiClient.RateLimitError) return json({ error: "Busy, try again soon" }, 429, headers);
      if (err instanceof ApiClient.AuthenticationError) return json({ error: "Coach is not set up" }, 502, headers);
      if (err instanceof ApiClient.APIError) return json({ error: "Coach had a problem" }, 502, headers);
      throw err;
    }
  },
};
