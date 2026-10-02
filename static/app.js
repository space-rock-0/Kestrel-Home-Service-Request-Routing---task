const $ = id => document.getElementById(id);
const el = (tag, text, cls) => { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (cls) e.className = cls; return e; };
const clear = n => { while (n.firstChild) n.removeChild(n.firstChild); return n; };

async function api(path, opts) {
  const r = await fetch(path, opts);
  let body = null;
  try { body = await r.json(); } catch (_) {}
  if (!r.ok) {
    const e = (body && body.error) || (body && body.detail ? { message: JSON.stringify(body.detail) } : { message: "Request failed (" + r.status + ")" });
    const err = new Error(e.message); err.info = e; err.status = r.status; throw err;
  }
  return body;
}
function card(parent, cls) { const c = el("div", undefined, "card " + (cls || "")); parent.appendChild(c); return c; }
function showError(parent, e) { clear(parent); const c = card(parent, "bad"); c.appendChild(el("strong", e.message || String(e))); }

// tabs
document.querySelectorAll("#tabs button").forEach(b => b.onclick = () => {
  document.querySelectorAll("#tabs button").forEach(x => x.classList.toggle("active", x === b));
  document.querySelectorAll("main > section").forEach(s => s.hidden = s.id !== "tab-" + b.dataset.tab);
  ({ data: loadData, pipeline: loadJob, results: loadResults, ext: loadExt })[b.dataset.tab]?.();
});

// header badge
async function refreshBadge() {
  const b = $("badge");
  try {
    const h = await api("/api/health");
    b.textContent = h.model_ready ? "model ready" : "no model yet";
    b.className = "badge " + (h.model_ready ? "ok" : "warn");
    $("indir").textContent = h.input_dir;
    return h.model_ready;
  } catch (e) { b.textContent = "service unreachable"; b.className = "badge warn"; return false; }
}

// route tab
function fill(id, vals) {
  const s = clear($(id));
  ["unknown", ...vals.filter(v => v !== "unknown")].forEach(v => { const o = el("option", v); o.value = v; s.appendChild(o); });
}
async function loadMeta() {
  try {
    const m = await api("/api/meta");
    fill("p", m.products); fill("w", m.warranties); fill("c", m.channels);
  } catch (e) {
    ["p", "w", "c"].forEach(i => fill(i, []));
  }
}
$("go").onclick = async () => {
  const out = clear($("route-out"));
  out.textContent = "Working...";
  try {
    const j = await api("/api/v1/predict", { method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ request_text: $("t").value, product_family: $("p").value, warranty_status: $("w").value, channel: $("c").value }) });
    clear(out);
    const c = card(out, j.needs_clarification ? "warn" : "");
    c.appendChild(el("div", j.predicted_team, "team"));
    const pct = Math.round(j.confidence * 100);
    c.appendChild(el("div", "Confidence " + pct + "%"));
    const bar = el("div", undefined, "bar"), fillBar = el("div"); fillBar.style.width = pct + "%"; bar.appendChild(fillBar); c.appendChild(bar);
    if (j.needs_clarification) c.appendChild(el("p", "Needs a human check. " + j.clarifying_question));
    c.appendChild(el("h3", "Why"));
    c.appendChild(el("p", j.justification, "why"));
    if (j.alternatives && j.alternatives.length) {
      const alt = el("p", "Runner-up: " + j.alternatives.map(a => a.team + " (" + Math.round(a.probability * 100) + "%)").join(", "), "alt");
      c.appendChild(alt);
    }
    if (j.warnings.length) c.appendChild(el("p", "Notes: " + j.warnings.join(" "), "warn-note"));
  } catch (e) { showError(out, e); }
};

// data tab
function renderIssues(parent, rep) {
  clear(parent);
  const c = card(parent, rep.ok ? "" : "bad");
  c.appendChild(el("strong", rep.ok ? "Input is usable for " + rep.action + "." : "Input is not usable for " + rep.action + "."));
  if (rep.rows && Object.keys(rep.rows).length) c.appendChild(el("p", "Rows: " + Object.entries(rep.rows).map(([k, v]) => k + " " + v).join(", ")));
  [["Errors", rep.errors], ["Warnings", rep.warnings]].forEach(([title, list]) => {
    if (!list || !list.length) return;
    c.appendChild(el("h4", title));
    const ul = el("ul"); list.forEach(i => ul.appendChild(el("li", i.message))); c.appendChild(ul);
  });
}
async function loadData() {
  try {
    const d = await api("/api/data/status");
    $("indir").textContent = d.input_dir;
    const msg = clear($("data-msg"));
    if (d.message) card(msg, "warn").appendChild(el("span", d.message));
    if (d.stale && d.files.length) card(msg, "warn").appendChild(el("span", "Input files changed since the last training run. Run the pipeline."));
    const tb = $("files").tBodies[0]; clear(tb);
    d.files.forEach(f => {
      const tr = el("tr");
      [f.file, f.role || "unmatched", f.matched_by + (f.note ? " (" + f.note + ")" : ""), f.columns.join(", ")].forEach(v => tr.appendChild(el("td", v)));
      tb.appendChild(tr);
    });
    const miss = clear($("missing"));
    Object.entries(d.missing_roles).forEach(([a, roles]) => card(miss, "warn").appendChild(el("span", "Missing for " + a + ": " + roles.join(", "))));
    d.warnings.forEach(w => card(miss, "warn").appendChild(el("span", w)));
  } catch (e) { showError($("data-msg"), e); }
}
$("validate").onclick = async () => {
  try { renderIssues($("validation"), await api("/api/data/validate?action=train", { method: "POST" })); }
  catch (e) { showError($("validation"), e); }
};

// pipeline tab
let poll = null;
function renderJob(j) {
  const box = clear($("job"));
  if (!j) { box.appendChild(el("p", "No run yet.")); $("joblog").textContent = ""; return; }
  const c = card(box, j.state === "failed" ? "bad" : j.state === "running" ? "warn" : "");
  c.appendChild(el("strong", j.name + ": " + j.state));
  if (j.error) c.appendChild(el("p", j.error.message));
  $("joblog").textContent = j.log.join("\n");
  $("run").disabled = j.state === "running";
}
async function loadJob() {
  try {
    const s = await api("/api/pipeline/status");
    renderJob(s.job);
    if (s.job && s.job.state === "running") { if (!poll) poll = setInterval(loadJob, 1500); }
    else if (poll) { clearInterval(poll); poll = null; refreshBadge(); loadMeta(); }
  } catch (e) { showError($("job"), e); }
}
$("run").onclick = async () => {
  try { await api("/api/pipeline/run", { method: "POST" }); loadJob(); }
  catch (e) { showError($("job"), e); }
};

// results tab
async function loadResults() {
  const box = clear($("metrics"));
  try {
    const m = await api("/api/metrics"), h = m.holdout;
    const c = card(box), kv = el("div", undefined, "kv"); c.appendChild(kv);
    const add = (k, v) => { kv.appendChild(el("div", k)); kv.appendChild(el("div", String(v))); };
    add("Trained at", m.trained_at);
    add("Holdout size (latest closed requests)", h.model.n);
    add("Bot right first time", (h.bot_vs_final.accuracy * 100).toFixed(1) + "%");
    add("This model right first time", (h.model.accuracy * 100).toFixed(1) + "%");
    add("Model 95% interval", h.model.accuracy_ci95.map(x => (x * 100).toFixed(1) + "%").join(" to "));
    add("Model agreement with bot's own labels", (h.model_agreement_with_bot_label.accuracy * 100).toFixed(1) + "%");
    add("Sent to a human (confidence gate)", (h.gate_on_holdout.share_flagged_for_human * 100).toFixed(1) + "%");
    add("Accuracy on unflagged requests", h.gate_on_holdout.accuracy_when_not_flagged == null ? "n/a" : (h.gate_on_holdout.accuracy_when_not_flagged * 100).toFixed(1) + "%");
    if (m.test) add("Test rows predicted", m.test.rows);
  } catch (e) { showError(box, e); }
}

// extensions tab
async function loadExt() {
  const box = clear($("ext"));
  try {
    const x = await api("/api/extensions");
    ["tools", "commands", "skills", "workflows", "agents"].forEach(k => {
      const c = card(box); c.appendChild(el("h3", k + " (" + x[k].length + ")"));
      if (!x[k].length) c.appendChild(el("p", "None registered."));
      const ul = el("ul"); x[k].forEach(i => ul.appendChild(el("li", i.name + ": " + (i.description || "")))); c.appendChild(ul);
    });
    if (x.load_errors.length) { const c = card(box, "warn"); c.appendChild(el("strong", "Plugins that failed to load")); x.load_errors.forEach(e => c.appendChild(el("p", JSON.stringify(e)))); }
  } catch (e) { showError(box, e); }
}

(async () => { await refreshBadge(); await loadMeta(); })();
