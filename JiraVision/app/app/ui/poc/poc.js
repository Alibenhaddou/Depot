(() => {
  const $ = (id) => document.getElementById(id);

  /* ------------------------------------------------------------------ */
  /* utils                                                               */
  /* ------------------------------------------------------------------ */

  const tryJson = (text) => {
    try {
      return JSON.parse(text);
    } catch {
      return null;
    }
  };

  const safePath = (p, fallback = "/") =>
    typeof p === "string" && p.startsWith("/") ? p : fallback;

  const withCacheBuster = (url) => {
    const u = new URL(url, window.location.origin);
    u.searchParams.set("_ts", String(Date.now()));
    return u.toString();
  };

  let announceTimeoutId;
  const announce = (msg) => {
    const node = $("panelStatus");
    const visible = $("panelStatusVisible");

    if (announceTimeoutId !== undefined) {
      window.clearTimeout(announceTimeoutId);
    }

    if (node) node.textContent = "";
    if (visible) visible.textContent = "";

    announceTimeoutId = window.setTimeout(() => {
      if (node) node.textContent = msg;
      if (visible) visible.textContent = msg;
    }, 50);
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

  /* ------------------------------------------------------------------ */
  /* jira multi-instance                                                 */
  /* ------------------------------------------------------------------ */

  const activeCloudIds = new Set();
  let knownSites = [];
  const projectState = {
    projects: [],
    inactive: [],
    lastSyncedAt: null,
    selectedId: null,
    lastSelectedId: null,
    lastInteractionWasKeyboard: false,
    filter: "active",
    inactiveOpen: false,
  };

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
    renderProjects();
  }

  function projectId(p) {
    return `${p.cloud_id || "default"}:${p.project_key}`;
  }

  function formatTs(ts) {
    if (!ts) return "";
    const d = new Date(Number(ts) * 1000);
    if (Number.isNaN(d.getTime())) return "";
    return d.toLocaleString("fr-FR");
  }

  function projectScore(p) {
    const candidates = [
      Number(p.story_etude_open_assigned_count),
      Number(p.story_open_assigned_count),
      Number(p.etude_open_assigned_count),
    ];
    for (const v of candidates) {
      if (Number.isFinite(v)) return v;
    }
    return 0;
  }

  function sortProjects(list) {
    return [...list].sort((a, b) => {
      const scoreDiff = projectScore(b) - projectScore(a);
      if (scoreDiff !== 0) return scoreDiff;
      return (a.project_key || "").localeCompare(b.project_key || "");
    });
  }

  function isVisibleForInstances(p) {
    if (!p.cloud_id) return true;
    if (!activeCloudIds.size) return true;
    return activeCloudIds.has(p.cloud_id);
  }

  function splitMasked(items) {
    let masked = 0;
    const visible = [];
    const maskedItems = [];
    for (const p of items) {
      if (!isVisibleForInstances(p)) continue;
      if (p.mask_type && p.mask_type !== "none") {
        masked += 1;
        maskedItems.push(p);
        continue;
      }
      visible.push(p);
    }
    return { visible, masked, maskedItems };
  }

  let toastTimeout;
  function showToast(message, variant = "info") {
    const toast = $("toast");
    if (!toast) return;
    toast.textContent = message;
    toast.className = `toast ${variant} show`;
    window.clearTimeout(toastTimeout);
    toastTimeout = window.setTimeout(() => {
      toast.classList.remove("show");
    }, 4000);
  }

  function renderProjects() {
    const tabs = $("projectTabs");
    const detailTitle = $("projectTitle");
    const detailMeta = $("projectMeta");
    const detailBadge = $("projectStatusBadge");
    const statStories = $("statStories");
    const statEtudes = $("statEtudes");
    const statSynced = $("statSynced");
    const inactiveList = $("inactiveList");
    const btnMaskTemp = $("btnMaskTemp");
    const btnMaskDef = $("btnMaskDef");
    const btnReadd = $("btnReadd");
    const filtersContainer = $("projectFilters");
    const toggleInactive = $("toggleInactive");
    const skeleton = $("projectsSkeleton");

    if (!tabs || !inactiveList) return;

    const activeSplit = splitMasked(projectState.projects);
    const inactiveSplit = splitMasked(projectState.inactive);
    const maskedItems = sortProjects([...activeSplit.maskedItems, ...inactiveSplit.maskedItems]);

    const visibleProjects = sortProjects(activeSplit.visible);
    const visibleInactive = sortProjects(inactiveSplit.visible);

    // Filtres (Actifs/Inactifs/Masqués)
    if (filtersContainer) {
      const filters = [
        { id: "active", label: "Actifs", count: visibleProjects.length },
        { id: "inactive", label: "Inactifs", count: visibleInactive.length },
        { id: "masked", label: "Masqués", count: maskedItems.length },
      ];
      const btns = [];
      filtersContainer.replaceChildren();
      filters.forEach((f, idx) => {
        const isActive = projectState.filter === f.id;
        const btn = el("button", {
          type: "button",
          class: `pill filter-btn${isActive ? " active" : ""}`,
          "data-filter": f.id,
          "aria-pressed": isActive ? "true" : "false",
          "aria-current": isActive ? "true" : "false",
          text: `${f.label}${f.count !== undefined ? ` (${f.count})` : ""}`,
        });
        btn.addEventListener("click", () => {
          if (projectState.filter === f.id) return;
          projectState.filter = f.id;
          projectState.selectedId = null;
          projectState.lastInteractionWasKeyboard = true;
          announce(`Filtre ${f.label} appliqué${f.count ? `, ${f.count} projets` : ""}.`);
          renderProjects();
        });
        btn.addEventListener("keydown", (e) => {
          if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
          e.preventDefault();
          const nextIdx = e.key === "ArrowRight" ? (idx + 1) % filters.length : (idx - 1 + filters.length) % filters.length;
          btns[nextIdx]?.focus();
        });
        filtersContainer.appendChild(btn);
        btns.push(btn);
      });
    }

    let currentList = visibleProjects;
    if (projectState.filter === "inactive") currentList = visibleInactive;
    else if (projectState.filter === "masked") currentList = maskedItems;

    if (!projectState.selectedId && currentList.length) {
      projectState.selectedId = projectId(currentList[0]);
    } else {
      const stillThere = currentList.some((p) => projectId(p) === projectState.selectedId);
      if (!stillThere) projectState.selectedId = currentList[0] ? projectId(currentList[0]) : null;
    }

    tabs.replaceChildren();
    if (skeleton) skeleton.style.display = "none";
    const tabButtons = [];
    const emptyMessages = {
      active: "Aucun projet actif",
      inactive: "Aucun projet détecté sans activité",
      masked: "Aucun projet masqué",
    };
    if (!currentList.length) {
      tabs.appendChild(el("div", { class: "muted small", text: emptyMessages[projectState.filter] || "Aucun projet" }));
    } else {
      for (let i = 0; i < currentList.length; i += 1) {
        const p = currentList[i];
        const pid = projectId(p);
        const isSelected = pid === projectState.selectedId;
        const btn = el("button", {
          type: "button",
          class: `project-card${isSelected ? " active" : ""}`,
          role: "tab",
          "aria-selected": isSelected ? "true" : "false",
          "aria-controls": "projectTitle",
          id: `project-tab-${pid}`,
          tabindex: isSelected ? "0" : "-1",
        });
        const title = el("div", { class: "title", text: p.project_key });
        const statusBadge = el("span", {
          class: `badge ${p.is_active === false ? "warn" : "ok"}`,
          text: p.is_active === false ? "Inactif" : "Actif",
        });
        title.appendChild(statusBadge);
        const meta = el("div", { class: "meta", text: p.project_name || "–" });
        const activity = el("div", { class: "activity-chip" });
        activity.textContent = `${projectScore(p)} focus`;
        btn.appendChild(title);
        btn.appendChild(meta);
        btn.appendChild(activity);
        btn.addEventListener("click", () => {
          projectState.selectedId = pid;
          projectState.lastInteractionWasKeyboard = false;
          renderProjects();
        });
        btn.addEventListener("keydown", (e) => {
          const focusTab = (idx) => {
            tabButtons.forEach((b, j) => {
              b.tabIndex = j === idx ? 0 : -1;
            });
            tabButtons[idx]?.focus();
          };

          if (e.key === "ArrowRight") {
            e.preventDefault();
            const next = tabButtons[i + 1] || tabButtons[0];
            const idx = tabButtons.indexOf(next);
            if (idx >= 0) focusTab(idx);
          } else if (e.key === "ArrowLeft") {
            e.preventDefault();
            const prev = tabButtons[i - 1] || tabButtons[tabButtons.length - 1];
            const idx = tabButtons.indexOf(prev);
            if (idx >= 0) focusTab(idx);
          } else if (e.key === "Enter" || e.key === " " || e.key === "Spacebar") {
            e.preventDefault();
            projectState.selectedId = pid;
            projectState.lastInteractionWasKeyboard = true;
            renderProjects();
          }
        });
        tabs.appendChild(btn);
        tabButtons.push(btn);
      }
    }

    const selected = currentList.find((p) => projectId(p) === projectState.selectedId);
    const isInactiveFilter = projectState.filter === "inactive";
    const isMaskedFilter = projectState.filter === "masked";

    detail.replaceChildren();
    detail.setAttribute("aria-labelledby", "");
    if (!selected) {
      detail.appendChild(el("div", { class: "muted", text: "Sélectionne un projet." }));
      if (btnMaskTemp) btnMaskTemp.disabled = true;
      if (btnMaskDef) btnMaskDef.disabled = true;
      if (btnReadd) btnReadd.disabled = true;
    } else {
      const selectedTabId = `project-tab-${projectId(selected)}`;
      detail.setAttribute("aria-labelledby", selectedTabId);
      detail.appendChild(el("div", { text: `${selected.project_name || selected.project_key}` }));
      detail.appendChild(el("div", { class: "small muted", text: `Clé: ${selected.project_key}` }));
      detail.appendChild(el("div", { class: "small muted", text: `Source: ${selected.source || "?"}` }));
      detail.appendChild(el("div", { class: "small muted", text: `Instance: ${selected.cloud_id || "default"}` }));
      if (isMaskedFilter && selected.mask_type) {
        detail.appendChild(el("div", { class: "small muted", text: `Masqué: ${selected.mask_type}` }));
      }
      detail.appendChild(el("div", { class: "small muted", text: `Actif: ${selected.is_active === false ? "non" : "oui"}` }));

      // Actions selon filtre
      const maskDisabled = !projectState.selectedId || isInactiveFilter || isMaskedFilter;
      if (btnMaskTemp) btnMaskTemp.disabled = maskDisabled;
      if (btnMaskDef) btnMaskDef.disabled = maskDisabled;

      if (btnReadd) {
        btnReadd.disabled = !isInactiveFilter;
      }
    }

    const shouldFocusDetail = projectState.lastInteractionWasKeyboard
      && projectState.selectedId
      && projectState.selectedId !== projectState.lastSelectedId;
    projectState.lastSelectedId = projectState.selectedId;
    if (shouldFocusDetail && detail) detail.focus();

    const activeTab = tabButtons.find((b) => b.getAttribute("aria-selected") === "true");
    if (projectState.lastInteractionWasKeyboard && !shouldFocusDetail && activeTab) activeTab.focus();

    projectState.lastInteractionWasKeyboard = false;

    const inactiveIsOpen = projectState.inactiveOpen;
    inactiveList.replaceChildren();
    inactiveList.hidden = !inactiveIsOpen;
    if (toggleInactive) toggleInactive.setAttribute("aria-expanded", inactiveIsOpen ? "true" : "false");
    if (inactiveIsOpen) {
      if (!visibleInactive.length) {
        inactiveList.appendChild(el("div", { class: "muted small", text: "Aucun projet inactif" }));
      } else {
        for (const p of visibleInactive) {
          const item = el("div", { class: "inactive-item" });
          const meta = el("div", { class: "meta" }, [
            el("strong", { text: p.project_key }),
            el("span", { class: "muted", text: p.project_name || p.project_key }),
            el("span", { class: "muted", text: `Instance: ${p.cloud_id || "default"}` }),
          ]);
          const btn = el("button", { type: "button", text: "Ré-ajouter" });
          btn.addEventListener("click", () => addInactiveProject(p));
          item.appendChild(meta);
          item.appendChild(btn);
          inactiveList.appendChild(item);
        }
      }
    }
  }

  async function loadProjects() {
    const r = await fetchJson("/po/projects");
    if (r.status === 401) {
      window.location.href = "/auth";
      return;
    }
    if (!r.ok || !r.json) {
      announce("Erreur lors du chargement des projets.");
      return;
    }

    projectState.projects = r.json.projects || [];
    projectState.inactive = r.json.inactive_projects || [];
    projectState.lastSyncedAt = r.json.last_synced_at || null;
    renderProjects();
    announce("Projets chargés.");
  }

  async function refreshProjects() {
    const r = await fetchJson("/po/projects/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reset_definitif: false }),
    });
    if (!r.ok || !r.json) {
      announce("Erreur lors du rafraîchissement.");
      return;
    }

    projectState.projects = r.json.projects || [];
    projectState.inactive = r.json.inactive_projects || [];
    projectState.lastSyncedAt = r.json.last_synced_at || null;
    renderProjects();
    announce("Projets rafraîchis.");
  }

  async function addProject() {
    const key = window.prompt("Clé projet (ex: ABC)");
    if (!key) return;
    const name = window.prompt("Nom du projet", key) || key;
    const payload = {
      project_key: key.trim(),
      project_name: name.trim(),
      source: "manual",
      is_active: true,
    };

    const r = await fetchJson("/po/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!r.ok) {
      announce("Erreur lors de l’ajout du projet.");
      return;
    }
    await loadProjects();
    announce("Projet ajouté.");
  }

  async function addInactiveProject(p) {
    const payload = {
      project_key: p.project_key,
      project_name: p.project_name || p.project_key,
      source: "manual",
      is_active: true,
      cloud_id: p.cloud_id || null,
    };

    const r = await fetchJson("/po/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!r.ok) {
      announce("Erreur lors de l’ajout du projet inactif.");
      return;
    }
    await loadProjects();
    announce("Projet inactif ajouté.");
  }

  async function readdSelected() {
    if (projectState.filter !== "inactive") return;
    const selected = projectState.inactive.find((p) => projectId(p) === projectState.selectedId);
    if (!selected) return;
    await addInactiveProject(selected);
  }

  async function maskSelected(maskType) {
    const selected = projectState.projects.find((p) => projectId(p) === projectState.selectedId);
    if (!selected) return;
    const url = `/po/projects/${encodeURIComponent(selected.project_key)}${selected.cloud_id ? `?cloud_id=${encodeURIComponent(selected.cloud_id)}` : ""}`;
    const r = await fetchJson(url,
      {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mask_type: maskType, cloud_id: selected.cloud_id || null }),
      }
    );
    if (!r.ok) {
      announce("Erreur lors du masquage.");
      return;
    }
    await loadProjects();
    announce("Projet masqué.");
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
    loadProjects();
  }

  /* ------------------------------------------------------------------ */
  /* jira actions                                                        */
  /* ------------------------------------------------------------------ */

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

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";
      for (const part of parts) {
        const lines = part.split("\n");
        let data = "";
        let currentEvent = "message";
        for (const line of lines) {
          if (line.startsWith("event:")) currentEvent = line.slice(6).trim();
          else if (line.startsWith("data:")) data += line.slice(5).trim();
        }
        if (data) onEvent(currentEvent, data);
      }
    }
  }

  async function fetchIssue(mode) {
    const issueEl = $("issue");
    const out = $("out");
    const status = $("issueStatus");
    if (!out || !issueEl) return;

    const key = issueEl.value.trim();
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
    const limits =
      mode === "detail" ? { max_links: 4, max_comments: 6 } : { max_links: 1, max_comments: 1 };

    for (const cloudId of activeIds) {
      log(`🔎 Instance ${getSiteLabel(cloudId)} — demarrage de l'analyse…`);

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
            hasResult = true;
          } else if (event === "error") {
            const payload = tryJson(data);
            errorCode = payload?.code || null;
            errorMsg = payload?.message || data;
          }
        }
      );

      if (hasResult) return;
      if (errorCode === 404 || String(errorMsg).includes("Ticket introuvable")) {
        log(`⚠️ Ticket introuvable sur ${getSiteLabel(cloudId)}.`);
        continue;
      }
      if (errorMsg) lastError = errorMsg;
    }

    const finalMsg = lastError || "Aucune instance n'a repondu.";
    if (status) status.textContent = finalMsg;
    else out.textContent = finalMsg;
  }

  async function searchJql() {
    const jqlEl = $("jql");
    const out = $("out2");
    if (!out || !jqlEl) return;

    const jql = jqlEl.value.trim();
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
        "/jira/search?jql=" + encodeURIComponent(jql) + "&cloud_id=" + encodeURIComponent(cloudId)
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

    out.textContent = JSON.stringify({ total, returned: allIssues.length, issues: allIssues }, null, 2);
  }

  const aiSummary = async () => {
    const out = $("out2");
    const jqlEl = $("jql");
    if (!out || !jqlEl) return;

    try {
      const jql = jqlEl.value.trim();
      const activeIds = getActiveCloudIds();

      if (!jql) {
        out.textContent = "Renseigne un JQL.";
        return;
      }
      if (!activeIds.length) {
        out.textContent = "Active au moins une instance Jira.";
        return;
      }

      out.textContent = "⏳ Résumé IA en cours…";

      const allIssues = [];
      let lastError = null;

      for (const cloudId of activeIds) {
        const r = await fetchText("/ai/summarize-jql", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ jql, cloud_id: cloudId, max_results: 20 }),
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
  /* Panel Projets PO                                                    */
  /* ------------------------------------------------------------------ */

  async function loadPoProjects() {
    const panel = $("poProjectsPanel");
    const loading = $("poProjectsLoading");
    const error = $("poProjectsError");
    const list = $("poProjectsList");
    const empty = $("poProjectsEmpty");
    if (!panel || !loading || !error || !list || !empty) return;

    panel.style.display = "block";
    loading.style.display = "block";
    error.style.display = "none";
    list.innerHTML = "";
    empty.style.display = "none";

    try {
      const r = await fetchJson("/po/projects");
      loading.style.display = "none";
      if (!r.ok || !r.json) {
        error.textContent = "Erreur lors du chargement des projets PO.";
        error.style.display = "block";
        return;
      }

      const projects = r.json.projects || [];
      if (!projects.length) {
        empty.style.display = "block";
        return;
      }

      for (const p of projects) {
        const li = document.createElement("li");
        li.textContent = `${p.project_key} — ${p.project_name}`;
        list.appendChild(li);
      }
    } catch {
      loading.style.display = "none";
      error.textContent = "Erreur réseau ou serveur.";
      error.style.display = "block";
    }
  }

  /* ------------------------------------------------------------------ */
  /* boot                                                                */
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
    await refreshSites();

    // Synchronisation automatique des projets PO au démarrage
    await refreshProjects();

    const btnRefresh = $("btnProjectsRefresh");
    if (btnRefresh) btnRefresh.addEventListener("click", refreshProjects);
    const btnAdd = $("btnProjectAdd");
    if (btnAdd) btnAdd.addEventListener("click", addProject);
    const btnMaskTemp = $("btnMaskTemp");
    if (btnMaskTemp) btnMaskTemp.addEventListener("click", () => maskSelected("temporaire"));
    const btnMaskDef = $("btnMaskDef");
    if (btnMaskDef) btnMaskDef.addEventListener("click", () => maskSelected("definitif"));
    const btnReadd = $("btnReadd");
    if (btnReadd) btnReadd.addEventListener("click", readdSelected);
    const toggleInactive = $("toggleInactive");
    if (toggleInactive) {
      toggleInactive.addEventListener("click", () => {
        projectState.inactiveOpen = !projectState.inactiveOpen;
        renderProjects();
      });
    }

    const btnIssueQuick = $("btnIssueQuick");
    if (btnIssueQuick) btnIssueQuick.addEventListener("click", () => fetchIssue("quick"));

    const btnIssueDetail = $("btnIssueDetail");
    if (btnIssueDetail) btnIssueDetail.addEventListener("click", () => fetchIssue("detail"));
    const issueInput = $("issue");
    if (issueInput) {
      issueInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          fetchIssue("quick");
        }
      });
    }
    const btnSearch = $("btnSearch");
    if (btnSearch) btnSearch.addEventListener("click", searchJql);

    const btnAi = $("btnAi");
    if (btnAi) btnAi.addEventListener("click", aiSummary);

    // PO panel
    await loadPoProjects();
  }

  window.addEventListener("DOMContentLoaded", () => {
    boot().catch((e) => console.error("Boot error", e));
  });
})();
</replace_in_file>