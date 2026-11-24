// DOM mínimo: testa a lógica do script real, não layout ou tecnologia assistiva.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const staticDir = path.join(__dirname, "../src/academic_assistant/static");

class Element {
  constructor(tag = "div", text = "") {
    this.tagName = tag;
    this.children = [];
    this.listeners = {};
    this.value = "";
    this.options = [{}];
    this.textContent = text;
  }
  set textContent(text) { this.text = text; this.children = []; }
  get textContent() { return this.text + this.children.map(child => child.textContent).join(""); }
  append(...nodes) {
    nodes.forEach(node => {
      if (typeof node === "string") node = new Element("#text", node);
      node.parent = this;
      this.children.push(node);
    });
  }
  replaceChildren(...nodes) { this.children = []; this.append(...nodes); }
  remove() {
    if (!this.parent) return;
    this.parent.children.splice(this.parent.children.indexOf(this), 1);
    this.parent = null;
  }
  replaceWith(node) {
    const parent = this.parent;
    const index = parent.children.indexOf(this);
    node.remove();
    parent.children.splice(index, 1, node);
    node.parent = parent;
    this.parent = null;
  }
  setAttribute(name, value) { this[name] = value; }
  addEventListener(name, callback) { this.listeners[name] = callback; }
  focus() {}
  scrollIntoView() {}
}

async function fixture(outcomes) {
  const elements = new Map();
  const calls = [];
  const context = vm.createContext({
    document: {
      querySelector(selector) {
        if (!elements.has(selector)) elements.set(selector, new Element());
        return elements.get(selector);
      },
      querySelectorAll: () => [],
      createElement: tag => new Element(tag),
      createTextNode: text => new Element("#text", text),
    },
    window: { matchMedia: () => ({ matches: false, addEventListener() {} }) },
    Option: function(text, value) { return Object.assign(new Element("option", text), { value }); },
    fetch: async (url, options) => {
      if (url === "/api/context") {
        return { ok: true, json: async () => ({
          course_levels: ["graduação"], campuses: [], modalities: [],
        }) };
      }
      calls.push(JSON.parse(options.body));
      const outcome = outcomes.shift();
      assert.ok(outcome, "Requisição inesperada");
      return { ok: !outcome.error, json: async () => outcome };
    },
  });
  await vm.runInContext(fs.readFileSync(path.join(staticDir, "app.js"), "utf8"), context);
  return {
    elements, calls,
    submit: (text, scope) => context.submitQuestion(text, scope),
  };
}

function answer(text) {
  return { status: "supported", answer: `${text} [1]`, sources: [{
    source_id: "1", document_name: `${text}.pdf`, page_number: 7, excerpt: text,
  }] };
}

function retry(card) { return card.children.at(-1).listeners.click(); }

test("retry de pergunta antiga mantém turno, contexto, fontes e rascunho", async () => {
  const ui = await fixture([
    { error: { message: "Falha A" } }, answer("Resposta B"), answer("Resposta A"),
  ]);
  const scopeA = { course_level: "graduação", campus: "Norte" };
  await ui.submit("Pergunta A", scopeA);
  const messages = ui.elements.get("#messages");
  const errorCard = messages.children[1];
  await ui.submit("Pergunta B", { course_level: "graduação", campus: "Sul" });
  ui.elements.get("#question").value = "Rascunho C";
  await retry(errorCard);

  assert.equal(ui.elements.get("#question").value, "Rascunho C");
  assert.equal(messages.children.length, 4);
  assert.match(messages.children[0].textContent, /Pergunta A/);
  assert.match(messages.children[1].textContent, /Resposta A.*Resposta A\.pdf/s);
  assert.match(messages.children[2].textContent, /Pergunta B/);
  assert.match(messages.children[3].textContent, /Resposta B.*Resposta B\.pdf/s);
  assert.deepEqual(ui.calls[2], { question: "Pergunta A", context: scopeA });
});

test("retry que falha novamente também permanece no turno original", async () => {
  const ui = await fixture([
    { error: { message: "Falha A" } }, answer("Resposta B"),
    { error: { message: "Falha A novamente" } }, answer("Resposta A"),
  ]);
  await ui.submit("Pergunta A", { course_level: "graduação" });
  const messages = ui.elements.get("#messages");
  const errorCard = messages.children[1];
  await ui.submit("Pergunta B", { course_level: "graduação" });
  ui.elements.get("#question").value = "Rascunho C";
  await retry(errorCard);
  assert.match(messages.children[1].textContent, /Falha A novamente/);
  assert.equal(messages.children.length, 4);
  await retry(messages.children[1]);
  assert.match(messages.children[1].textContent, /Resposta A/);
  assert.equal(messages.children.length, 4);
  assert.equal(ui.elements.get("#question").value, "Rascunho C");
});

test("placeholder tem contraste mínimo de 4,5:1 sobre o fundo branco", () => {
  const css = fs.readFileSync(path.join(staticDir, "styles.css"), "utf8");
  const color = css.match(/textarea::placeholder\s*\{\s*color:\s*(#[\da-f]{6})/i)[1];
  const channels = color.slice(1).match(/../g).map(hex => {
    const value = parseInt(hex, 16) / 255;
    return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
  });
  const luminance = channels.reduce((sum, value, i) => sum + value * [0.2126, 0.7152, 0.0722][i], 0);
  const ratio = 1.05 / (luminance + 0.05);
  assert.ok(ratio >= 4.5, `Contraste ${ratio.toFixed(3)}:1`);
});
