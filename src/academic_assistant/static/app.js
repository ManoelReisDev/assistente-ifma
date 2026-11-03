"use strict";

const form = document.querySelector("#question-form");
const question = document.querySelector("#question");
const send = document.querySelector("#send");
const level = document.querySelector("#course-level");
const campus = document.querySelector("#campus");
const modality = document.querySelector("#modality");
const messages = document.querySelector("#messages");
const welcome = document.querySelector("#welcome");
const activity = document.querySelector("#activity");
const clear = document.querySelector("#clear-chat");
const contextError = document.querySelector("#context-error");
const retryContext = document.querySelector("#retry-context");
const contextPanel = document.querySelector("#context-panel");
let busy = false;
let contextReady = false;
let turn = 0;

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function updateControls() {
  send.disabled = busy || !contextReady || !level.value || !question.value.trim();
  clear.disabled = busy || !messages.children.length;
  level.disabled = busy || !contextReady;
  campus.disabled = busy || !contextReady || campus.options.length < 2;
  modality.disabled = busy || !contextReady || modality.options.length < 2;
  question.readOnly = busy;
}

function populate(select, values) {
  select.replaceChildren(select.options[0]);
  values.forEach((value) => select.append(new Option(value, value)));
  // Mesmo com uma única opção, o nível exige escolha explícita.
  select.value = "";
}

async function loadContext() {
  contextReady = false;
  contextError.hidden = true;
  retryContext.hidden = true;
  activity.textContent = "Carregando opções de consulta…";
  updateControls();
  try {
    const response = await fetch("/api/context", { cache: "no-store" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error?.message || "Não foi possível carregar as opções de consulta.");
    if (!data.course_levels.length) throw new Error("O cadastro não possui níveis de curso. Confira os metadados dos documentos no servidor.");
    populate(level, data.course_levels);
    populate(campus, data.campuses);
    populate(modality, data.modalities);
    contextReady = true;
    activity.textContent = "Selecione o nível do curso para começar.";
  } catch (error) {
    contextError.textContent = error instanceof TypeError ? "Não foi possível conectar ao servidor. Confira se ele está em execução e recarregue as opções." : error.message;
    contextError.hidden = false;
    retryContext.hidden = false;
    contextPanel.open = true;
    activity.textContent = "As opções de consulta estão indisponíveis.";
  }
  updateControls();
}

function appendUser(text, context) {
  const article = element("article", "message user");
  article.append(element("div", "message-label", "Você"), element("p", "question-text", text));
  const description = [context.course_level, context.campus, context.modality].filter(Boolean).join(" · ");
  article.append(element("p", "message-context", description));
  messages.append(article);
}

function appendAnswer(data, turnId) {
  const article = element("article", "message assistant");
  const label = element("div", "message-label", "Assistente");
  const statusLabels = { partial: "Resposta parcial", conflict: "Fontes em conflito", insufficient_evidence: "Evidência insuficiente" };
  if (statusLabels[data.status]) label.append(element("span", "answer-status", statusLabels[data.status]));
  article.append(label);
  const text = element("p", "answer-text");
  const sourceTargets = new Map(data.sources.map((source, index) => [source.source_id, `source-${turnId}-${index}`]));
  // Vincular somente IDs existentes, sem interpretar HTML ou Markdown do modelo.
  data.answer.split(/(\[[^\[\]\n]+\])/g).forEach((part) => {
    const id = part.slice(1, -1);
    if (part.startsWith("[") && part.endsWith("]") && sourceTargets.has(id)) {
      const link = element("a", "citation-link", part);
      link.href = `#${sourceTargets.get(id)}`;
      link.setAttribute("aria-label", `Conferir fonte ${id} desta resposta`);
      link.addEventListener("click", () => {
        document.getElementById(sourceTargets.get(id)).focus({ preventScroll: true });
      });
      text.append(link);
    } else {
      text.append(document.createTextNode(part));
    }
  });
  article.append(text);
  if (data.sources.length) {
    const sources = element("section", "sources");
    sources.setAttribute("aria-label", "Fontes desta resposta");
    sources.append(element("h2", "", "Fontes utilizadas"));
    data.sources.forEach((source, index) => {
      const card = element("article", "source");
      card.id = `source-${turnId}-${index}`;
      card.tabIndex = -1;
      const heading = element("h3", "source-heading");
      heading.append(element("span", "source-id", `[${source.source_id}]`), document.createTextNode(source.document_name));
      card.append(heading, element("p", "source-page", `Página do PDF: ${source.page_number}`), element("blockquote", "", source.excerpt));
      sources.append(card);
    });
    article.append(sources);
  }
  messages.append(article);
  return article;
}

async function submitQuestion(text, context, isRetry = false, errorCard = null) {
  if (busy) return;
  busy = true;
  welcome.hidden = true;
  if (errorCard) errorCard.remove();
  if (!isRetry) appendUser(text, context);
  question.value = "";
  const turnId = ++turn;
  activity.textContent = "Consultando documentos…";
  messages.setAttribute("aria-busy", "true");
  updateControls();
  activity.scrollIntoView({ block: "nearest" });
  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: text, context }),
      cache: "no-store",
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error?.message || "Não foi possível concluir a consulta. Tente novamente.");
    const article = appendAnswer(data, turnId);
    activity.textContent = "Consulta concluída. A resposta e as fontes estão disponíveis acima.";
    article.scrollIntoView({ block: "start" });
  } catch (error) {
    const card = element("div", "message error-message");
    card.setAttribute("role", "alert");
    const description = error instanceof TypeError ? "Não foi possível conectar ao servidor. Confira a conexão e tente novamente." : error.message;
    card.append(element("p", "", description));
    const retry = element("button", "", "Tentar novamente");
    retry.type = "button";
    retry.addEventListener("click", () => submitQuestion(text, context, true, card));
    card.append(retry);
    messages.append(card);
    activity.textContent = "A consulta não foi concluída.";
    card.scrollIntoView({ block: "nearest" });
  } finally {
    busy = false;
    messages.setAttribute("aria-busy", "false");
    updateControls();
    question.focus({ preventScroll: true });
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = question.value.trim();
  if (busy || !contextReady || !text) return;
  if (!level.value) {
    contextPanel.open = true;
    level.focus();
    activity.textContent = "Selecione o nível do curso para começar.";
    return;
  }
  const context = { institution: "IFMA", course_level: level.value, campus: campus.value || null, modality: modality.value || null };
  submitQuestion(text, context);
});
question.addEventListener("input", updateControls);
question.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    if (!busy) form.requestSubmit();
  }
});
level.addEventListener("change", () => {
  updateControls();
  activity.textContent = level.value ? "" : "Selecione o nível do curso para começar.";
});
document.querySelectorAll("[data-question]").forEach((button) => {
  button.addEventListener("click", () => {
    question.value = button.dataset.question;
    updateControls();
    question.focus();
  });
});
clear.addEventListener("click", () => {
  if (busy) return;
  messages.replaceChildren();
  welcome.hidden = false;
  activity.textContent = "Conversa limpa.";
  updateControls();
  question.focus({ preventScroll: true });
});
retryContext.addEventListener("click", loadContext);
const mobileLayout = window.matchMedia("(max-width: 760px)");
contextPanel.open = !mobileLayout.matches;
mobileLayout.addEventListener("change", (event) => { contextPanel.open = !event.matches; });
loadContext();
