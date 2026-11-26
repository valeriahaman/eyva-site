// eyva.me — static site plus two form endpoints.
// Static files come from public/ (the ASSETS binding). POST /api/join and POST /api/salon
// save the entry in KV (WAITLIST) and email it to Val through Cloudflare Email Routing (MAIL).
import { EmailMessage } from "cloudflare:email";

const CANONICAL = "eyva.me";
const FROM = "val@eyva.me";
const MAX_FIELD = 300;

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // One address in the world: www.eyva.me and eyva.shop go to eyva.me.
    const local = url.hostname === "localhost" || url.hostname === "127.0.0.1";
    if (url.hostname !== CANONICAL && !url.hostname.endsWith(".workers.dev") && !local) {
      url.hostname = CANONICAL;
      url.protocol = "https:";
      return Response.redirect(url.toString(), 301);
    }

    const kinds = { "/api/join": "join", "/api/salon": "salon", "/api/ask": "ask" };
    if (request.method === "POST" && kinds[url.pathname]) {
      return handleForm(request, env, ctx, kinds[url.pathname]);
    }
    if (url.pathname.startsWith("/api/")) {
      return json({ ok: false, error: "not found" }, 404);
    }
    return env.ASSETS.fetch(request);
  },
};

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
  });
}

const clean = (v) => (typeof v === "string" ? v.trim().slice(0, MAX_FIELD) : "");
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

async function handleForm(request, env, ctx, kind) {
  let data;
  try {
    data = await request.json();
  } catch {
    return json({ ok: false, error: "bad json" }, 400);
  }
  // Honeypot: a real person never fills this field.
  if (clean(data.hp)) return json({ ok: true });

  const entry = {
    kind,
    name: clean(data.name),
    email: clean(data.email),
    colour: clean(data.colour),
    friend: clean(data.friend),
    salon: clean(data.salon),
    contact: clean(data.contact),
    message: typeof data.message === "string" ? data.message.trim().slice(0, 4000) : "",
    consent: data.consent === true,
    source: clean(data.source),
    page: clean(data.page),
    country: request.headers.get("cf-ipcountry") || "",
    ua: (request.headers.get("user-agent") || "").slice(0, 200),
    at: new Date().toISOString(),
  };

  if (kind === "join") {
    if (!EMAIL_RE.test(entry.email)) return json({ ok: false, error: "email" }, 400);
    if (!entry.consent) return json({ ok: false, error: "consent" }, 400);
  } else if (kind === "ask") {
    if (!entry.name || !EMAIL_RE.test(entry.email) || !entry.message) return json({ ok: false, error: "fields" }, 400);
  } else {
    if (!entry.name || !entry.contact) return json({ ok: false, error: "fields" }, 400);
  }

  const key = `${kind}:${entry.at}:${crypto.randomUUID().slice(0, 8)}`;
  await env.WAITLIST.put(key, JSON.stringify(entry));
  if (kind === "join") {
    // One key per email too, so the same person twice is easy to see.
    await env.WAITLIST.put(`email:${entry.email.toLowerCase()}`, key);
  }

  ctx.waitUntil(notify(env, entry).catch((e) => console.log("mail failed", e && e.message)));
  return json({ ok: true });
}

async function notify(env, e) {
  if (!env.MAIL) return;
  const subject = e.kind === "join"
    ? `Waitlist: ${e.name || e.email}${e.colour ? " - " + e.colour : ""}`
    : e.kind === "ask"
    ? `Question: ${e.name}`
    : `Salon: ${e.name}${e.salon ? " - " + e.salon : ""}`;
  const lines = (e.kind === "ask" ? e.message + "\n\n---\n" : "") + Object.entries(e)
    .filter(([k, v]) => v !== "" && v !== false && k !== "message")
    .map(([k, v]) => `${k}: ${v}`)
    .join("\n");
  const replyTo = e.email && EMAIL_RE.test(e.email) ? e.email : (EMAIL_RE.test(e.contact) ? e.contact : "");
  const raw =
    `From: EYVA site <${FROM}>\r\n` +
    `To: <${env.MAIL_TO}>\r\n` +
    (replyTo ? `Reply-To: <${replyTo}>\r\n` : "") +
    `Subject: ${subject.replace(/[\r\n]/g, " ")}\r\n` +
    `Date: ${new Date().toUTCString()}\r\n` +
    `Message-ID: <${crypto.randomUUID()}@eyva.me>\r\n` +
    `MIME-Version: 1.0\r\n` +
    `Content-Type: text/plain; charset=utf-8\r\n\r\n` +
    lines + "\r\n";
  await env.MAIL.send(new EmailMessage(FROM, env.MAIL_TO, raw));
}
