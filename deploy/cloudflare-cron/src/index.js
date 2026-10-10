// Calls Apparel ERP's cron tick on the schedule in wrangler.toml. The app
// decides which jobs are due; this Worker only provides the clock.
//
// Env:  APP_URL (var)  e.g. https://apparel-erp.onrender.com
//       CRON_SECRET (secret) — must match CRON_SECRET on Render

async function tick(env) {
  const url = `${env.APP_URL}/api/v1/internal/cron/tick`;
  // A sleeping free Render service answers 502/503 while it boots; give it
  // a couple of chances before reporting a failure.
  for (let attempt = 1; attempt <= 3; attempt++) {
    const res = await fetch(url, { method: "POST", headers: { "X-Cron-Secret": env.CRON_SECRET } });
    const body = await res.text();
    if (res.ok) {
      console.log(`tick ok (attempt ${attempt}): ${body.slice(0, 1000)}`);
      return;
    }
    console.log(`tick attempt ${attempt} failed: HTTP ${res.status} ${body.slice(0, 300)}`);
    if (res.status !== 502 && res.status !== 503 && res.status !== 504) break;
    await new Promise((r) => setTimeout(r, 30_000));
  }
  throw new Error("cron tick failed");
}

export default {
  async scheduled(_event, env, ctx) {
    ctx.waitUntil(tick(env));
  },
  async fetch() {
    return new Response("Not Found", { status: 404 });
  },
};
