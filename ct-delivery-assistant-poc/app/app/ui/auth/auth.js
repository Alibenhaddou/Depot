(() => {
  const $ = (id) => document.getElementById(id);

  const tryJson = (text) => { try { return JSON.parse(text); } catch { return null; } };
  const safePath = (p, fallback) => (typeof p === "string" && p.startsWith("/")) ? p : fallback;

  async function getState() {
    const res = await fetch("/auth/state", { credentials: "same-origin", cache: "no-store" });
    const text = await res.text();
    const json = tryJson(text);
    return { ok: res.ok, status: res.status, json, text };
  }

  function renderActions(state) {
    const wrap = $("actions");
    if (!wrap) return;
    wrap.replaceChildren();

    const logged = Boolean(state?.logged_in);
    const loginUrl = safePath(state?.login_url, "/login");
    const logoutUrl = safePath(state?.logout_url, "/logout");

    const a = document.createElement("a");
    a.href = logged ? logoutUrl : loginUrl;

    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = logged ? "Logout" : "Se connecter a Atlassian";

    a.appendChild(btn);
    wrap.appendChild(a);
  }

  async function boot() {
    const s = await getState();
    if (!s.ok || !s.json) {
      return;
    }

    renderActions(s.json);
  }

  window.addEventListener("DOMContentLoaded", () => {
    boot().catch((e) => {
      console.error(e);
    });
  });
})();
