(() => {
  const $ = (id) => document.getElementById(id);

  /* ------------------------------------------------------------------ */
  /* utils                                                               */
  /* ------------------------------------------------------------------ */

  const tryJson = (text) => { try { return JSON.parse(text); } catch { return null; } };

  const safePath = (p, fallback = "/") =>
    (typeof p === "string" && p.startsWith("/")) ? p : fallback;

  const withCacheBuster = (url) => {
    const u = new URL(url, window.location.origin);
    u.searchParams.set("_ts", String(Date.now()));
    return u.toString();
  };

  const fetchText = async (url, opts = {}) => {
    const res = await fetch(withCacheBuster(url), {
      credentials: "same-origin",
      cache: "no-store",
      ...opts,
    });
    const text = await res.text();
    return { ok: res.ok, status: res.status, statusText: res.statusText, text };
  };

  const fetchJson = async (url, opts = {}) => {
    const r = await fetchText(url, opts);
    return { ...r, json: tryJson(r.text) };
  };

  const el = (tag, attrs = {}, children = []) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === "text") n.textContent = v;
      else n.setAttribute(k, v);
    }
    for (const c of children) n.appendChild(c);
    return n;
  };

  /* ------------------------------------------------------------------ */
  /* top bar                                                             */
  /* ------------------------------------------------------------------ */

  function renderTopbar(state) {
    const logoutArea = $("logoutArea");
    if (!logoutArea) return;

    const logged = Boolean(state.logged_in);
    logoutArea.replaceChildren();

    if (!logged) return;

    const a = el("a", { href: safePath(state.logout_url, "/logout") });
    const btn = el("button", { type: "button", text: "Logout" });
    a.appendChild(btn);
    logoutArea.appendChild(a);
  }

  function renderInstanceList(sites) {
    const list = $("instanceList");
    if (!list) return;

    list.replaceChildren();

    if (!sites.length) {
      list.appendChild(el("span", { class: "pill inactive", text: "Aucune" }));
      return;
    }

    for (const s of sites) {
      const label = s.name || s.url || s.id;
      const isActive = activeCloudIds.has(s.id);
      const cls = isActive ? "pill active" : "pill inactive";
      const btn = el("button", {
        type: "button",
        class: cls,
        text: label,
        "data-cloud-id": s.id,
        "aria-pressed": isActive ? "true" : "false",
      });
      btn.addEventListener("click", () => toggleCloudId(s.id));
      list.appendChild(btn);
    }
  }

  /* ------------------------------------------------------------------ */
  /* jira multi-instance                                                  */
  /* ------------------------------------------------------------------ */

  const activeCloudIds = new Set();
  let knownSites = [];

  function setView(hasInstances) {
    const appContent = $("appContent");
    if (!appContent) return;
    appContent.classList.toggle("hidden", !hasInstances);
  }

  function toggleCloudId(id) {
    if (activeCloudIds.has(id)) activeCloudIds.delete(id);
    else activeCloudIds.add(id);
    renderInstanceList(knownSites);
  }

  async function refreshSites() {
    const r = await fetchJson("/jira/instances");

    if (!r.ok || !r.json) {
      renderInstanceList([]);
      setView(false);
      return;
    }

    knownSites = r.json.jira_sites || [];

    if (!knownSites.length) {
      renderInstanceList([]);
      setView(false);
      window.location.href = "/auth";
      return;
    }

    const knownIds = new Set(knownSites.map((s) => s.id));
    if (!activeCloudIds.size) {
      for (const id of knownIds) activeCloudIds.add(id);
    } else {
      for (const id of Array.from(activeCloudIds)) {
        if (!knownIds.has(id)) activeCloudIds.delete(id);
      }
      if (!activeCloudIds.size) {
        for (const id of knownIds) activeCloudIds.add(id);
      }
    }

    renderInstanceList(knownSites);
    setView(true);
  }

  /* ------------------------------------------------------------------ */
  /* boot                                                                 */
  /* ------------------------------------------------------------------ */

  async function boot() {
    const s = await fetchJson("/ui/state");
    if (!s.ok || !s.json) {
      console.error("Erreur /ui/state", s.status);
      return;
    }

    if (!s.json.logged_in) {
      window.location.href = "/auth";
      return;
    }

    renderTopbar(s.json);
    refreshSites();
  }

  window.addEventListener("DOMContentLoaded", () => {
    boot().catch((e) => console.error("Boot error", e));
  });
})();(() => {
  const $ = (id) => document.getElementById(id);

  /* ------------------------------------------------------------------ */
  /* utils                                                               */
  /* ------------------------------------------------------------------ */

  const tryJson = (text) => { try { return JSON.parse(text); } catch { return null; } };

  const safePath = (p, fallback = "/") =>
    (typeof p === "string" && p.startsWith("/")) ? p : fallback;

  const withCacheBuster = (url) => {
    const u = new URL(url, window.location.origin);
    u.searchParams.set("_ts", String(Date.now()));
    return u.toString();
  };

  const fetchText = async (url, opts = {}) => {
    const res = await fetch(withCacheBuster(url), {
      credentials: "same-origin",
      cache: "no-store",
      ...opts,
    });
    const text = await res.text();
    return { ok: res.ok, status: res.status, statusText: res.statusText, text };
  };

  const fetchJson = async (url, opts = {}) => {
    const r = await fetchText(url, opts);
    return { ...r, json: tryJson(r.text) };
  };

  const el = (tag, attrs = {}, children = []) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === "text") n.textContent = v;
      else n.setAttribute(k, v);
    }
    for (const c of children) n.appendChild(c);
    return n;
  };

  /* ------------------------------------------------------------------ */
  /* top bar                                                             */
  /* ------------------------------------------------------------------ */

  function renderTopbar(state) {
    const logoutArea = $("logoutArea");
    if (!logoutArea) return;

    // login / logout
    const logged = Boolean(state.logged_in);
    logoutArea.replaceChildren();

    if (!logged) return;

    const a = el("a", { href: safePath(state.logout_url, "/logout") });
    const btn = el("button", { type: "button", text: "Logout" });
    a.appendChild(btn);
    logoutArea.appendChild(a);
  }

  function renderInstanceList(sites) {
    const list = $("instanceList");
    if (!list) return;

    list.replaceChildren();

    if (!sites.length) {
      list.appendChild(el("span", { class: "pill inactive", text: "Aucune" }));
      return;
    }

    for (const s of sites) {
      const label = s.name || s.url || s.id;
      const isActive = activeCloudIds.has(s.id);
      const cls = isActive ? "pill active" : "pill inactive";
      const btn = el("button", {
        type: "button",
        class: cls,
        text: label,
        "data-cloud-id": s.id,
        "aria-pressed": isActive ? "true" : "false",
      });
      btn.addEventListener("click", () => toggleCloudId(s.id));
      list.appendChild(btn);
    }
  }

  /* ------------------------------------------------------------------ */
  /* jira multi-instance                                                  */
  /* ------------------------------------------------------------------ */

  const activeCloudIds = new Set();
  let knownSites = [];

  function setView(hasInstances) {
    const appContent = $("appContent");
    if (!appContent) return;
    appContent.classList.toggle("hidden", !hasInstances);
  }

  function getActiveCloudIds() {
    return Array.from(activeCloudIds);
  }

  function getSiteLabel(id) {
    const site = knownSites.find((s) => s.id === id);
    return site?.name || site?.url || id;
  }

  function toggleCloudId(id) {
    if (activeCloudIds.has(id)) activeCloudIds.delete(id);
    else activeCloudIds.add(id);
    renderInstanceList(knownSites);
  }

  async function streamSse(url, options, onEvent) {
    const res = await fetch(url, options);
    if (!res.ok) {
      const text = await res.text();
      onEvent("error", JSON.stringify({ code: res.status, message: text }));
      return;
    }
    const reader = res.body?.getReader();
    if (!reader) {
      onEvent("error", JSON.stringify({ code: 0, message: "Aucun flux recu." }));
      return;
    }

    const decoder = new TextDecoder();
    let buffer = "";
    let currentEvent = "message";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";
      for (const part of parts) {
        const lines = part.split("\n");
        let data = "";
        currentEvent = "message";
        for (const line of lines) {
          if (line.startsWith("event:")) {
            currentEvent = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            data += line.slice(5).trim();
          }
        }
        if (data) onEvent(currentEvent, data);
      }
    }
  }

  async function refreshSites() {
    const r = await fetchJson("/jira/instances");

    if (!r.ok || !r.json) {
      renderInstanceList([]);
      setView(false);
      return;
    }

    knownSites = r.json.jira_sites || [];

    if (!knownSites.length) {
      renderInstanceList([]);
      setView(false);
      window.location.href = "/auth";
      return;
    }

    const knownIds = new Set(knownSites.map((s) => s.id));
    if (!activeCloudIds.size) {
      for (const id of knownIds) activeCloudIds.add(id);
    } else {
      for (const id of Array.from(activeCloudIds)) {
        if (!knownIds.has(id)) activeCloudIds.delete(id);
      }
      if (!activeCloudIds.size) {
        for (const id of knownIds) activeCloudIds.add(id);
      }
    }

    renderInstanceList(knownSites);
    setView(true);
  }

  /* ------------------------------------------------------------------ */
  /* jira actions                                                         */
  /* ------------------------------------------------------------------ */

  async function fetchIssue(mode) {
    const key = $("issue").value.trim();
    const out = $("out");
    const status = $("issueStatus");
    if (!out) return;

    if (status) status.textContent = "";
    out.textContent = "";
    if (!key) {
      const msg = "Renseigne une clé (ex: ABC-123).";
      if (status) status.textContent = msg;
      else out.textContent = msg;
      return;
    }

    const activeIds = getActiveCloudIds();
    if (!activeIds.length) {
      const msg = "Active au moins une instance Jira.";
      if (status) status.textContent = msg;
      else out.textContent = msg;
      return;
    }

    const logs = [];
    const log = (msg) => {
      logs.push(msg);
      if (status) status.textContent = logs.join("\n");
      else out.textContent = logs.join("\n");
    };

    log("⏳ Analyse en cours…");
    await new Promise((resolve) => requestAnimationFrame(resolve));

    let lastError = null;
    const limits = mode === "detail"
      ? { max_links: 4, max_comments: 6 }
      : { max_links: 1, max_comments: 1 };

    for (const cloudId of activeIds) {
      log(`🔎 Instance ${getSiteLabel(cloudId)} — demarrage de l'analyse…`);

      let done = false;
      let hasResult = false;
      let errorCode = null;
      let errorMsg = null;

      await streamSse(
        "/ai/analyze-issue/stream",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            issue_key: key,
            cloud_id: cloudId,
            max_links: limits.max_links,
            max_comments: limits.max_comments,
          }),
        },
        (event, data) => {
          if (event === "log") {
            log(data);
          } else if (event === "result") {
            const payload = tryJson(data);
            const text = payload?.text || data;
            if (status) status.textContent = logs.join("\n") + "\n\n---\nResultat:";
            out.textContent = text;
            done = true;
            hasResult = true;
          } else if (event === "error") {
            const payload = tryJson(data);
            errorCode = payload?.code || null;
            errorMsg = payload?.message || data;
            done = true;
          }
        }
      );

      if (hasResult) return;
      if (errorCode === 404 || String(errorMsg).includes("Ticket introuvable")) {
        log(`⚠️ Ticket introuvable sur ${getSiteLabel(cloudId)}.`);
        continue;
      }
      if (done && errorMsg) {
        lastError = errorMsg;
      }
    }

    const finalMsg = lastError || "Aucune instance n'a repondu.";
    if (status) status.textContent = finalMsg;
    else out.textContent = finalMsg;
  }

  async function searchJql() {
    const jql = $("jql").value.trim();
    const out = $("out2");
    if (!out) return;

    out.textContent = "";
    if (!jql) {
      out.textContent = "Renseigne un JQL.";
      return;
    }

    const activeIds = getActiveCloudIds();
    if (!activeIds.length) {
      out.textContent = "Active au moins une instance Jira.";
      return;
    }

    const allIssues = [];
    let total = 0;
    let lastError = null;

    for (const cloudId of activeIds) {
      const r = await fetchJson(
        "/jira/search?jql=" + encodeURIComponent(jql) +
        "&cloud_id=" + encodeURIComponent(cloudId)
      );
      if (!r.ok || !r.json) {
        lastError = r.text || `Erreur (${r.status})`;
        continue;
      }

      const issues = r.json.issues || [];
      total += Number(r.json.total || issues.length);
      allIssues.push(...issues);
    }

    if (!allIssues.length && lastError) {
      out.textContent = lastError;
      return;
    }

    out.textContent = JSON.stringify(
      {
        total,
        returned: allIssues.length,
        issues: allIssues,
      },
      null,
      2
    );
  }

  const aiSummary = async () => {
  const out = $("out2");
  try {
    const jql = $("jql").value.trim();
    const activeIds = getActiveCloudIds();

    if (!jql) { out.textContent = "Renseigne un JQL."; return; }
    if (!activeIds.length) { out.textContent = "Active au moins une instance Jira."; return; }

    out.textContent = "⏳ Résumé IA en cours…";

    const allIssues = [];
    let lastError = null;

    for (const cloudId of activeIds) {
      const r = await fetchText("/ai/summarize-jql", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          jql,
          cloud_id: cloudId,
          max_results: 20
        }),
      });

      if (r.ok) {
        allIssues.push({ cloud_id: cloudId, summary: r.text });
        continue;
      }

      lastError = r.text || "Erreur IA";
    }

    if (!allIssues.length && lastError) {
      out.textContent = lastError;
      return;
    }

    if (activeIds.length === 1 && allIssues.length === 1) {
      out.textContent = allIssues[0].summary || "(réponse vide)";
      return;
    }

    out.textContent = allIssues
      .map((it) => `Instance ${it.cloud_id}:\n${it.summary}`)
      .join("\n\n");
  } catch (e) {
    out.textContent = "❌ Erreur JS: " + String(e);
    console.error(e);
  }
};


  /* ------------------------------------------------------------------ */
  /* boot                                                                 */
  /* ------------------------------------------------------------------ */

  async function boot() {
    const s = await fetchJson("/ui/state");
    if (!s.ok || !s.json) {
      console.error("Erreur /ui/state", s.status);
      return;
    }

    if (!s.json.logged_in) {
      window.location.href = "/auth";
      return;
    }

    renderTopbar(s.json);
    refreshSites();

    $("btnIssueQuick").addEventListener("click", () => fetchIssue("quick"));
    $("btnIssueDetail").addEventListener("click", () => fetchIssue("detail"));
    $("issue").addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        fetchIssue("quick");
      }
    });
    $("btnSearch").addEventListener("click", searchJql);
    $("btnAi").addEventListener("click", aiSummary);
  }

  window.addEventListener("DOMContentLoaded", () => {
    boot().catch((e) => console.error("Boot error", e));
  });
})();
