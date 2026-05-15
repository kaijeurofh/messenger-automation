"use strict";

// Backend base URL. In Docker this is rewritten by nginx to the backend
// service; for local dev served via `python -m http.server` set it via
// window.API_BASE before this script loads.
const API_BASE = window.API_BASE || "/api";

const state = {
  students: [],
  selectedId: null,
  triggers: [],
};

const TRIGGER_LABELS = {
  lernplan_woche: "Lernplan für die Woche",
  inaktivitaet: "Inaktivität auf dem Campus",
  pruefung_vorbereitung: "Vorbereitung auf nächste Prüfung",
  meilenstein: "Meilenstein feiern",
  motivation_allgemein: "Allgemeine Motivation",
};

async function fetchJson(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return res.json();
}

async function loadHealth() {
  try {
    const h = await fetchJson("/health");
    document.getElementById("model-name").textContent = h.modell;
    document.getElementById("ollama-url").textContent = h.ollama_base_url;
  } catch (err) {
    document.getElementById("model-name").textContent = "offline";
    document.getElementById("ollama-url").textContent = err.message;
  }
}

async function loadTriggers() {
  const data = await fetchJson("/triggers");
  state.triggers = data.trigger;
  const sel = document.getElementById("trigger-select");
  sel.innerHTML = "";
  for (const t of state.triggers) {
    const opt = document.createElement("option");
    opt.value = t;
    opt.textContent = TRIGGER_LABELS[t] || t;
    sel.appendChild(opt);
  }
}

async function loadStudents() {
  state.students = await fetchJson("/students");
  renderStudentList();
}

function renderStudentList() {
  const ul = document.getElementById("student-list");
  ul.innerHTML = "";
  for (const s of state.students) {
    const li = document.createElement("li");
    li.className = "student-row" + (s.id === state.selectedId ? " active" : "");
    li.dataset.id = s.id;
    li.innerHTML = `
      <div class="font-medium">${escapeHtml(s.vorname)} ${escapeHtml(s.nachname)}</div>
      <div class="meta">${escapeHtml(s.studiengang)} &middot; Monat ${s.aktueller_monat_im_studium}/${s.regelstudienzeit_monate}</div>
    `;
    li.addEventListener("click", () => selectStudent(s.id));
    ul.appendChild(li);
  }
}

function selectStudent(id) {
  state.selectedId = id;
  renderStudentList();
  renderStudentDetail();
  document.getElementById("trigger-panel").classList.remove("hidden");
}

function renderStudentDetail() {
  const s = state.students.find((x) => x.id === state.selectedId);
  const container = document.getElementById("student-detail");
  if (!s) {
    container.innerHTML =
      '<p class="text-slate-500 text-sm">Kein Profil ausgewählt.</p>';
    return;
  }

  const naechste = s.naechste_pruefung
    ? `${escapeHtml(s.naechste_pruefung.modul)} am ${s.naechste_pruefung.datum}`
    : "—";

  const abgeschlossen = s.abgeschlossene_pruefungen
    .map(
      (p) =>
        `<li>${escapeHtml(p.modul)} — ${p.status}${p.note ? ` (${p.note})` : ""} <span class="text-slate-400">${p.datum}</span></li>`,
    )
    .join("");

  const kurse = s.kurse
    .map(
      (k) =>
        `<li><span class="font-medium">${escapeHtml(k.modul)}</span> — ${k.fortschritt_prozent}%${k.abgeschlossen ? " ✓" : ""}</li>`,
    )
    .join("");

  container.innerHTML = `
    <div class="flex items-start justify-between">
      <div>
        <h2 class="text-lg font-semibold">${escapeHtml(s.vorname)} ${escapeHtml(s.nachname)}</h2>
        <p class="text-sm text-slate-500">${escapeHtml(s.studiengang)}</p>
      </div>
      <div class="text-right text-xs text-slate-500">
        <div>Studienbeginn: ${s.studienbeginn}</div>
        <div>Monat ${s.aktueller_monat_im_studium} / ${s.regelstudienzeit_monate}</div>
        ${s.notendurchschnitt ? `<div>⌀ Note: ${s.notendurchschnitt}</div>` : ""}
      </div>
    </div>
    <hr class="my-3 border-slate-200" />
    <div class="grid grid-cols-2 gap-4 text-sm">
      <div>
        <h3 class="font-semibold mb-1">Nächste Prüfung</h3>
        <p>${naechste}</p>
      </div>
      <div>
        <h3 class="font-semibold mb-1">Campus-Aktivität</h3>
        <p>Letzter Login: ${s.campus_aktivitaet.letzter_login}</p>
        <p>${s.campus_aktivitaet.logins_letzte_30_tage} Logins (30 Tage)</p>
      </div>
    </div>
    <div class="mt-3 text-sm">
      <h3 class="font-semibold mb-1">Abgeschlossene Prüfungen</h3>
      <ul class="list-disc list-inside text-slate-700">${abgeschlossen || "<li class='list-none text-slate-400'>(noch keine)</li>"}</ul>
    </div>
    <div class="mt-3 text-sm">
      <h3 class="font-semibold mb-1">Kurs-Fortschritt</h3>
      <ul class="list-disc list-inside text-slate-700">${kurse || "<li class='list-none text-slate-400'>(keine Kurse erfasst)</li>"}</ul>
    </div>
  `;
}

async function generateMessage() {
  if (!state.selectedId) {
    return;
  }
  const trigger = document.getElementById("trigger-select").value;
  const btn = document.getElementById("btn-generate-message");
  const statusEl = document.getElementById("generate-status");
  btn.disabled = true;
  btn.classList.add("opacity-60");
  statusEl.textContent = "Generiere Nachricht...";

  try {
    const t0 = performance.now();
    const result = await fetchJson("/messages", {
      method: "POST",
      body: JSON.stringify({ studi_id: state.selectedId, trigger }),
    });
    const dauer = ((performance.now() - t0) / 1000).toFixed(1);
    appendChatBubble(result, dauer);
    statusEl.textContent = `Erzeugt in ${dauer}s mit ${result.modell}.`;
  } catch (err) {
    statusEl.textContent = `Fehler: ${err.message}`;
  } finally {
    btn.disabled = false;
    btn.classList.remove("opacity-60");
  }
}

function appendChatBubble(antwort, dauerSekunden) {
  const chat = document.getElementById("chat-area");
  const bubble = document.createElement("div");
  bubble.className = "chat-bubble";
  const steps = (antwort.nachricht.empfohlene_naechste_schritte || [])
    .map((s) => `<li>${escapeHtml(s)}</li>`)
    .join("");
  const ts = new Date(antwort.erzeugt_am).toLocaleTimeString();
  bubble.innerHTML = `
    <div class="subject">${escapeHtml(antwort.nachricht.betreff)}</div>
    <div>${escapeHtml(antwort.nachricht.nachricht)}</div>
    ${steps ? `<div class="steps"><strong>Nächste Schritte:</strong><ul>${steps}</ul></div>` : ""}
    <div class="meta">
      <span>${escapeHtml(antwort.trigger)} &middot; ${escapeHtml(antwort.nachricht.tonalitaet)}</span>
      <span>${ts} &middot; ${dauerSekunden}s</span>
    </div>
  `;
  chat.appendChild(bubble);
  chat.scrollTop = chat.scrollHeight;
}

async function generateRandomStudent() {
  const fresh = await fetchJson("/students/generate", {
    method: "POST",
    body: JSON.stringify({ count: 1 }),
  });
  await loadStudents();
  if (fresh.length) {
    selectStudent(fresh[0].id);
  }
}

function escapeHtml(s) {
  if (s === null || s === undefined) {
    return "";
  }
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

document.addEventListener("DOMContentLoaded", async () => {
  document
    .getElementById("btn-generate-message")
    .addEventListener("click", generateMessage);
  document
    .getElementById("btn-generate")
    .addEventListener("click", generateRandomStudent);

  await loadHealth();
  await loadTriggers();
  await loadStudents();
});
