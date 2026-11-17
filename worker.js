/**
 * YFP Assurance: website worker (Cloudflare Pages "advanced mode")
 * -----------------------------------------------------------------
 * build.py copies this file to dist/_worker.js. It:
 *   1. serves the website files normally
 *   2. handles "Login with GitHub" for the editor at /admin:
 *        /api/auth      → sends you to GitHub to sign in
 *        /api/callback  → GitHub returns here; passes the login to the editor
 *   3. adds standard security headers
 *
 * Needs these variables in Cloudflare → your Pages project → Settings → Variables and Secrets:
 *   GITHUB_CLIENT_ID       (text)
 *   GITHUB_CLIENT_SECRET   (secret)
 */

const SECURITY_HEADERS = {
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "X-Frame-Options": "SAMEORIGIN",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
};

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/api/auth") return auth(request, env);
    if (url.pathname === "/api/callback") return callback(request, env);

    const res = await env.ASSETS.fetch(request);
    const out = new Response(res.body, res);
    for (const [k, v] of Object.entries(SECURITY_HEADERS)) out.headers.set(k, v);
    if (url.pathname.startsWith("/admin")) out.headers.set("Cache-Control", "no-store");
    return out;
  },
};

function text(msg, status) {
  return new Response(msg, { status, headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store" } });
}

async function auth(request, env) {
  const url = new URL(request.url);
  if (!env.GITHUB_CLIENT_ID || !env.GITHUB_CLIENT_SECRET) {
    return text("The website editor login is not configured yet. Add GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in Cloudflare Pages settings, then redeploy.", 500);
  }
  const state = crypto.randomUUID();
  const github = new URL("https://github.com/login/oauth/authorize");
  github.searchParams.set("client_id", env.GITHUB_CLIENT_ID);
  github.searchParams.set("redirect_uri", `${url.origin}/api/callback`);
  github.searchParams.set("scope", url.searchParams.get("scope") || "repo,user");
  github.searchParams.set("state", state);
  return new Response(null, {
    status: 302,
    headers: {
      Location: github.toString(),
      "Set-Cookie": `yfp_cms_state=${state}; Path=/api; HttpOnly; Secure; SameSite=Lax; Max-Age=600`,
      "Cache-Control": "no-store",
    },
  });
}

async function callback(request, env) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  const cookies = request.headers.get("Cookie") || "";
  const saved = (cookies.match(/(?:^|;\s*)yfp_cms_state=([^;]+)/) || [])[1];

  let status = "error";
  let content = { message: "Sign-in failed. Please close this window and try again." };

  if (!code || !state || !saved || state !== saved) {
    content = { message: "Sign-in could not be verified (it may have expired). Please close this window and try again." };
  } else {
    try {
      const res = await fetch("https://github.com/login/oauth/access_token", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json", "User-Agent": "yfp-assurance-cms" },
        body: JSON.stringify({
          client_id: env.GITHUB_CLIENT_ID,
          client_secret: env.GITHUB_CLIENT_SECRET,
          code,
          redirect_uri: `${url.origin}/api/callback`,
        }),
      });
      const data = await res.json();
      if (data.access_token) {
        status = "success";
        content = { token: data.access_token, provider: "github" };
      } else {
        content = { message: data.error_description || "GitHub did not return a login token." };
      }
    } catch (err) {
      content = { message: "Could not reach GitHub. Please try again." };
    }
  }

  const message = `authorization:github:${status}:${JSON.stringify(content)}`;
  const shown = status === "success" ? "Signed in. This window will close automatically." : content.message;
  const page = `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>YFP Assurance editor sign-in</title>
<style>body{font-family:system-ui,sans-serif;background:#f7f4ee;color:#23262b;display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0;padding:24px;text-align:center}</style>
</head><body><p>${shown.replace(/[<>&]/g, "")}</p>
<script>
(function () {
  var origin = ${JSON.stringify(url.origin)};
  var message = ${JSON.stringify(message).replace(/</g, "\\u003c")};
  if (!window.opener) return;
  function receive(e) {
    if (e.origin !== origin) return;
    window.removeEventListener("message", receive);
    window.opener.postMessage(message, origin);
  }
  window.addEventListener("message", receive);
  window.opener.postMessage("authorizing:github", origin);
})();
</script></body></html>`;

  return new Response(page, {
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-store",
      "Set-Cookie": "yfp_cms_state=; Path=/api; HttpOnly; Secure; SameSite=Lax; Max-Age=0",
    },
  });
}
