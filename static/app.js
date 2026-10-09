const $ = id => document.getElementById(id);
let examples = [];
function headers() { const h = {"Content-Type": "application/json"}; if ($("token").value) h.Authorization = `Bearer ${$("token").value}`; return h; }
function element(tag, text, className) { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; if (className) node.className = className; return node; }
async function loadExamples() {
  try { const response = await fetch("/api/examples", {headers: headers()}); if (!response.ok) throw new Error("Examples require a valid workspace token."); examples = await response.json(); $("example").replaceChildren(element("option", "Choose an incident…")); examples.forEach((x, i) => { const option = element("option", x.incident.title); option.value = String(i); $("example").append(option); }); $("example").firstChild.value = ""; $("error").textContent = ""; }
  catch (error) { $("error").textContent = error.message; }
}
async function initialize() {
  try { const response = await fetch("/api/config"); if (!response.ok) throw new Error("Workspace configuration is unavailable."); const config = await response.json(); $("mode").textContent = config.mode === "demo" ? "OFFLINE DEMO" : "LIVE RAG"; $("notice").textContent = config.mode === "demo" ? `Demo mode · ${config.runbooks} runbooks · BM25 retrieval + deterministic rules. No LLM calls or API key required.` : `Live mode · ${config.runbooks} runbooks · Semantic + lexical retrieval and LLM analysis. Review your evidence before sending it.`; $("auth-panel").hidden = !config.auth_required; if (!config.auth_required) await loadExamples(); }
  catch (error) { $("notice").textContent = error.message; }
}
$("load-examples").addEventListener("click", loadExamples);
$("example").addEventListener("change", () => { if ($("example").value === "") return; const incident = examples[Number($("example").value)].incident; ["title", "namespace", "symptom", "logs", "events"].forEach(key => { $(key).value = incident[key] || ""; }); });
function references(ids) { return element("div", `Sources: ${ids.join(", ")}`, "refs"); }
function render(result) {
  $("empty").hidden = true; $("results").hidden = false; const d = result.diagnosis;
  $("summary").textContent = d.summary; $("confidence").textContent = `${d.confidence.toUpperCase()} · qualitative confidence`; $("retrieval").textContent = `${result.retrieval.toUpperCase()} retrieval`; $("insufficient").hidden = !d.insufficient_evidence;
  $("hypotheses").replaceChildren(); d.hypotheses.forEach(h => { const card = element("div", undefined, "hypothesis"); card.append(element("p", h.cause)); h.evidence.forEach(quote => card.append(element("blockquote", quote))); card.append(references(h.source_ids)); $("hypotheses").append(card); });
  $("checks").replaceChildren(); if (!d.checks.length) $("checks").append(element("p", "Gather the missing information below before selecting a troubleshooting action.", "hint"));
  d.checks.forEach(check => { const card = element("div", undefined, "check"); card.append(element("p", check.description)); if (check.command) { card.append(element("code", check.command)); const button = element("button", "Copy suggested command"); button.type = "button"; button.addEventListener("click", async () => { try { await navigator.clipboard.writeText(check.command); button.textContent = "Copied — review placeholders before use"; } catch { button.textContent = "Select the command above to copy it"; } }); card.append(button); } card.append(references(check.source_ids)); $("checks").append(card); });
  $("missing").replaceChildren(...d.missing_information.map(x => element("li", x))); $("sources").replaceChildren(); $("source-count").textContent = `${result.sources.length} passages`;
  result.sources.forEach(source => { const detail = element("details", undefined, "source"); detail.append(element("summary", `${source.id} · ${source.title} / ${source.section}`), element("pre", source.excerpt), element("p", `Ranking score: ${source.score}`)); $("sources").append(detail); });
  $("telemetry").replaceChildren(...[`${result.latency_ms} ms`, `${result.input_tokens} input / ${result.output_tokens} output tokens`, `${result.embedding_tokens} embedding tokens`, `${result.redactions} redactions`].map(x => element("span", x))); $("result-notice").textContent = result.notice;
}
$("incident-form").addEventListener("submit", async event => {
  event.preventDefault(); $("error").textContent = ""; $("submit").disabled = true; $("submit").textContent = "Investigating evidence…"; $("results").hidden = true; $("empty").hidden = false;
  const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), 180000);
  try { const incident = Object.fromEntries(["title", "namespace", "symptom", "logs", "events"].map(key => [key, $(key).value])); const response = await fetch("/api/analyze", {method: "POST", headers: headers(), body: JSON.stringify(incident), signal: controller.signal}); const payload = await response.json(); if (!response.ok) { const detail = typeof payload.detail === "string" ? payload.detail : "Check the input lengths, namespace, and incident evidence."; throw new Error(detail); } render(payload); }
  catch (error) { $("error").textContent = error.name === "AbortError" ? "The request timed out. Check provider availability before retrying." : error.message; }
  finally { clearTimeout(timer); $("submit").disabled = false; $("submit").textContent = "Investigate incident ↗"; }
});
initialize();
