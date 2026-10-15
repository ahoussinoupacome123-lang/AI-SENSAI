/* Sensai web UI (feature X1). Plain JavaScript, no build step, no dependency.
   Every piece of text that comes from a document or a model is inserted with textContent,
   never as HTML, so a malicious PDF or a model reply cannot inject script into the page. */
(function () {
  "use strict";

  var NS = "http://www.w3.org/2000/svg";
  var ICONS = {
    file: ["M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z", "M14 3v5h5", "M9 13h6", "M9 17h6"],
    chat: ["M21 15a2 2 0 0 1-2 2H8l-5 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"],
    gear: ["M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z", "M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"],
    upload: ["M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4", "M17 8l-5-5-5 5", "M12 3v12"],
    download: ["M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4", "M7 10l5 5 5-5", "M12 15V3"],
    sparkles: ["M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z", "M19 15l.9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9z"],
    stop: ["M6 6h12v12H6z"],
    send: ["M22 2L11 13", "M22 2l-7 20-4-9-9-4z"],
    copy: ["M9 9h11v11H9z", "M5 15H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1"],
    refresh: ["M23 4v6h-6", "M1 20v-6h6", "M3.5 9a9 9 0 0 1 14.9-3.4L23 10", "M1 14l4.6 4.4A9 9 0 0 0 20.5 15"],
    check: ["M20 6L9 17l-5-5"],
    alert: ["M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z", "M12 9v4", "M12 17h.01"],
    info: ["M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z", "M12 16v-4", "M12 8h.01"],
    x: ["M18 6L6 18", "M6 6l12 12"],
    external: ["M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6", "M15 3h6v6", "M10 14L21 3"],
    edit: ["M12 20h9", "M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"],
    moon: ["M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"],
    sun: ["M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10z", "M12 1v2", "M12 21v2", "M4.2 4.2l1.4 1.4", "M18.4 18.4l1.4 1.4", "M1 12h2", "M21 12h2", "M4.2 19.8l1.4-1.4", "M18.4 5.6l1.4-1.4"]
  };
  var SUGGESTIONS = ["Explain what retrieval-augmented generation is in two sentences.",
    "What is the difference between TCP and UDP?", "Give me three tips for a clear technical presentation."];
  var SETTING_LABELS = { chat_model: "Chat model", judge_model: "Judge model", embed_model: "Embedding model",
    top_k: "Passages per question", chunk_size: "Chunk size", chunk_overlap: "Chunk overlap",
    num_ctx: "Context window", max_retries: "Retries" };
  var SETTING_GROUPS = [
    { title: "Models", keys: ["chat_model", "judge_model", "embed_model"], help: {
      chat_model: "Writes the answers and the chat replies.", judge_model: "Checks each answer against the passages.",
      embed_model: "Turns text into numbers for the search. Changing it needs a rebuilt index." } },
    { title: "Retrieval", keys: ["top_k", "chunk_size", "chunk_overlap"], help: {
      top_k: "How many passages are sent to the model for each question.", chunk_size: "Characters per chunk when a PDF is indexed.",
      chunk_overlap: "Characters shared by neighbouring chunks, so a cut sentence stays whole." } },
    { title: "Limits", keys: ["num_ctx", "max_retries"], help: {
      num_ctx: "The model's context window in tokens. More uses more memory.", max_retries: "Retries when the model returns invalid JSON." } }
  ];
  var BURST_COLORS = ["#0b45ff", "#ff5b37", "#00c98d", "#ffc247", "#8aa6ff"];

  var $ = function (id) { return document.getElementById(id); };
  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var state = { docs: [], doc: null, runDoc: null, questions: [], results: {}, status: null, running: false,
                abort: null, chatMessages: [], chatAbort: null, examples: {}, t0: 0, timer: null, filterReview: false,
                lastFocus: null, draftTimer: null };

  // ---------- small helpers ----------
  function icon(name) {
    var svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("class", "icon");
    svg.setAttribute("aria-hidden", "true");
    (ICONS[name] || []).forEach(function (d) {
      var path = document.createElementNS(NS, "path");
      path.setAttribute("d", d);
      svg.appendChild(path);
    });
    return svg;
  }
  function applyIcons(root) {
    root.querySelectorAll("[data-icon]").forEach(function (n) {
      if (!n.firstChild) n.appendChild(icon(n.getAttribute("data-icon")));
    });
  }
  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === "class") node.className = attrs[k];
      else if (k === "text") node.textContent = attrs[k];
      else node.setAttribute(k, attrs[k]);
    });
    (children || []).forEach(function (c) { node.appendChild(typeof c === "string" ? document.createTextNode(c) : c); });
    return node;
  }
  function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }
  function show(node, on) { node.hidden = !on; }
  function showNotice(node, message, info) {
    node.textContent = message || "";
    node.classList.toggle("info", !!info);
    show(node, !!message);
  }
  function toast(message, bad) {
    var node = el("div", { class: "toast" + (bad ? " bad" : ""), text: message });
    $("toasts").appendChild(node);
    setTimeout(function () { if (node.parentNode) node.parentNode.removeChild(node); }, 4300);
  }
  function fmtTime(seconds) {
    var m = Math.floor(seconds / 60), s = Math.floor(seconds % 60);
    return m + ":" + (s < 10 ? "0" : "") + s;
  }
  function fmtInt(n) { return Number(n).toLocaleString("en-US"); }
  function autosize(area, maxPx) {
    area.style.height = "auto";
    area.style.height = Math.min(area.scrollHeight + 2, maxPx) + "px";
  }
  function store(key, value) { try { if (value == null) localStorage.removeItem(key); else localStorage.setItem(key, value); } catch (e) {} }
  function recall(key) { try { return localStorage.getItem(key); } catch (e) { return null; } }
  function readJson(res) {
    return res.json().catch(function () { return {}; }).then(function (data) {
      if (!res.ok) throw new Error(data.error || res.statusText);
      return data;
    });
  }
  function apiGet(url) { return fetch(url).then(readJson); }
  function apiPost(url, body) {
    return fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) }).then(readJson);
  }

  // Read a Server-Sent Events stream from a POST request, calling onEvent(name, data) for each event.
  function streamPost(url, body, onEvent, signal) {
    return fetch(url, { method: "POST", headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(body), signal: signal }).then(function (res) {
      if (!res.ok) return readJson(res);
      var reader = res.body.getReader();
      var decoder = new TextDecoder();
      var buffer = "";
      function pump() {
        return reader.read().then(function (chunk) {
          if (chunk.done) return;
          buffer += decoder.decode(chunk.value, { stream: true });
          var end;
          while ((end = buffer.indexOf("\n\n")) >= 0) {
            var block = buffer.slice(0, end);
            buffer = buffer.slice(end + 2);
            var name = "message", data = "";
            block.split("\n").forEach(function (line) {
              if (line.indexOf("event: ") === 0) name = line.slice(7);
              else if (line.indexOf("data: ") === 0) data += line.slice(6);
            });
            if (data) onEvent(name, JSON.parse(data));
          }
          return pump();
        });
      }
      return pump();
    });
  }

  // ---------- safe Markdown for chat replies (DOM nodes only, no HTML parsing) ----------
  function mdInline(parent, text) {
    var re = /(`[^`\n]+`)|(\*\*[^*\n]+\*\*)|(\*[^*\n]+\*)|(\[[^\]\n]+\]\(https?:\/\/[^)\s]+\))/g;
    var last = 0, m;
    while ((m = re.exec(text)) !== null) {
      if (m.index > last) parent.appendChild(document.createTextNode(text.slice(last, m.index)));
      var tok = m[0];
      if (m[1]) parent.appendChild(el("code", { text: tok.slice(1, -1) }));
      else if (m[2]) parent.appendChild(el("strong", { text: tok.slice(2, -2) }));
      else if (m[3]) parent.appendChild(el("em", { text: tok.slice(1, -1) }));
      else {
        var close = tok.indexOf("](");
        parent.appendChild(el("a", { href: tok.slice(close + 2, -1), target: "_blank", rel: "noopener noreferrer",
                                     text: tok.slice(1, close) }));
      }
      last = m.index + tok.length;
    }
    if (last < text.length) parent.appendChild(document.createTextNode(text.slice(last)));
  }
  function splitRow(line) {
    var s = line.trim();
    if (s.charAt(0) === "|") s = s.slice(1);
    if (s.charAt(s.length - 1) === "|") s = s.slice(0, -1);
    return s.split("|").map(function (c) { return c.trim(); });
  }
  function renderMarkdown(container, text) {
    clear(container);
    var lines = text.replace(/\r/g, "").split("\n");
    var i = 0;
    while (i < lines.length) {
      var line = lines[i];
      if (!line.trim()) { i++; continue; }
      var fence = line.match(/^\s*```(.*)$/);
      if (fence) {
        var code = []; i++;
        while (i < lines.length && !/^\s*```/.test(lines[i])) { code.push(lines[i]); i++; }
        i++;
        container.appendChild(el("pre", {}, [el("code", { text: code.join("\n") })]));
        continue;
      }
      var head = line.match(/^(#{1,4})\s+(.*)$/);
      if (head) { var h = el("h" + head[1].length); mdInline(h, head[2]); container.appendChild(h); i++; continue; }
      if (/^\s*---+\s*$/.test(line)) { container.appendChild(el("hr")); i++; continue; }
      if (line.indexOf("|") >= 0 && i + 1 < lines.length && /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(lines[i + 1])) {
        var header = splitRow(line); i += 2;
        var thead = el("tr"), tbody = el("tbody");
        header.forEach(function (c) { var th = el("th"); mdInline(th, c); thead.appendChild(th); });
        while (i < lines.length && lines[i].indexOf("|") >= 0 && lines[i].trim()) {
          var tr = el("tr");
          splitRow(lines[i]).forEach(function (c) { var td = el("td"); mdInline(td, c); tr.appendChild(td); });
          tbody.appendChild(tr); i++;
        }
        container.appendChild(el("table", {}, [el("thead", {}, [thead]), tbody]));
        continue;
      }
      var li = line.match(/^(\s*)([-*]|\d+\.)\s+(.*)$/);
      if (li) {
        // nested lists: a deeper indent opens a list inside the previous item
        var stack = [];
        while (i < lines.length && (li = lines[i].match(/^(\s*)([-*]|\d+\.)\s+(.*)$/))) {
          var indent = li[1].replace(/\t/g, "    ").length, isOl = /\d/.test(li[2]);
          while (stack.length && indent < stack[stack.length - 1].indent) stack.pop();
          var top = stack[stack.length - 1];
          if (top && indent === top.indent && top.ol !== isOl) { stack.pop(); top = stack[stack.length - 1]; }
          if (!top || indent > top.indent || (top.ol !== isOl && indent === top.indent)) {
            var node = el(isOl ? "ol" : "ul");
            if (isOl && parseInt(li[2], 10) > 1) node.setAttribute("start", String(parseInt(li[2], 10)));
            var parent = top && top.node.lastChild;
            (parent || container).appendChild(node);
            top = { indent: indent, node: node, ol: isOl };
            stack.push(top);
          }
          var item = el("li"); mdInline(item, li[3]); top.node.appendChild(item); i++;
          while (i < lines.length && !lines[i].trim() && i + 1 < lines.length && /^\s*([-*]|\d+\.)\s+/.test(lines[i + 1])) i++;
        }
        continue;
      }
      if (/^>\s?/.test(line)) {
        var quote = [];
        while (i < lines.length && /^>\s?/.test(lines[i])) { quote.push(lines[i].replace(/^>\s?/, "")); i++; }
        var bq = el("blockquote"); mdInline(bq, quote.join(" ")); container.appendChild(bq);
        continue;
      }
      var para = [];
      while (i < lines.length && lines[i].trim() && !/^\s*(```|#{1,4}\s|[-*]\s|\d+\.\s|>|---+\s*$)/.test(lines[i]) &&
             !(lines[i].indexOf("|") >= 0 && /^\s*\|?\s*:?-{2,}/.test(lines[i + 1] || ""))) { para.push(lines[i]); i++; }
      if (!para.length) { para.push(lines[i]); i++; }
      var p = el("p");
      para.forEach(function (t, n) { if (n) p.appendChild(el("br")); mdInline(p, t); });
      container.appendChild(p);
    }
  }

  // ---------- header: tabs, theme, status ----------
  function moveIndicator() {
    var active = document.querySelector(".tab-btn.active");
    var ind = $("tab-indicator");
    if (!active || !ind) return;
    ind.style.width = active.offsetWidth + "px";
    ind.style.transform = "translateX(" + active.offsetLeft + "px)";
  }
  function selectTab(name) {
    document.querySelectorAll(".tab-btn").forEach(function (b) {
      var on = b.getAttribute("data-tab") === name;
      b.classList.toggle("active", on);
      b.setAttribute("aria-selected", on ? "true" : "false");
    });
    document.querySelectorAll(".tab").forEach(function (t) {
      var on = t.id === "tab-" + name;
      t.classList.toggle("active", on);
      t.hidden = !on;
    });
    document.body.setAttribute("data-tab", name);
    moveIndicator();
    window.scrollTo({ top: 0 });
    if (name === "settings") buildSettings();
    if (name === "chat") setTimeout(function () { $("chat-input").focus({ preventScroll: true }); }, 60);
  }
  function toggleTheme() {
    var root = document.documentElement;
    var attr = root.getAttribute("data-theme");
    var dark = attr ? attr === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
    var next = dark ? "light" : "dark";
    root.setAttribute("data-theme", next);
    store("sensai-theme", next);
  }
  function setPill(kind, text, detail) {
    $("status-pill").className = "pill pill-" + kind;
    $("status-text").textContent = text;
    $("status-detail").textContent = detail ? " - " + detail : "";
  }
  function refreshStatus() {
    return apiGet("/api/status").then(function (s) {
      state.status = s;
      var banner = $("banner");
      if (s.ollama) {
        setPill("ok", "Ollama ready", s.config.chat_model);
        if (s.missing_models.length) {
          banner.textContent = "Missing model(s): " + s.missing_models.join(", ") + ". Install with: " +
            s.missing_models.map(function (m) { return "ollama pull " + m; }).join("  and  ");
          show(banner, true);
        } else {
          show(banner, false);
        }
      } else {
        setPill("bad", "Ollama not reachable");
        banner.textContent = s.error + " Then reload this page.";
        show(banner, true);
      }
      var list = $("model-list");
      clear(list);
      s.models.forEach(function (m) { list.appendChild(el("option", { value: m })); });
      return s;
    }).catch(function (e) {
      setPill("bad", "server not reachable");
      $("banner").textContent = "Cannot talk to the Sensai server: " + e.message;
      show($("banner"), true);
    });
  }

  // ---------- documents and questions ----------
  function examplesFor(doc) {
    var ex = doc && state.examples[doc.id];
    return ex ? { quick: ex.quick || [], all: ex.questions || [] } : { quick: [], all: [] };
  }
  function questionLines() {
    return $("questions").value.split("\n").map(function (l) { return l.trim(); }).filter(Boolean);
  }
  function updateCount() {
    var n = questionLines().length;
    $("q-count").textContent = n + (n === 1 ? " question" : " questions");
    autosize($("questions"), 320);
    if (state.doc) {
      clearTimeout(state.draftTimer);
      state.draftTimer = setTimeout(function () { store("sensai-draft-" + state.doc.id, $("questions").value.trim() || null); }, 400);
    }
  }
  function loadDocuments(selectId) {
    return apiGet("/api/documents").then(function (data) {
      state.docs = data.documents;
      var select = $("doc-select");
      clear(select);
      state.docs.forEach(function (d) {
        select.appendChild(el("option", { value: d.id, text: d.name + (d.source === "builtin" ? " (demo)" : "") }));
      });
      show($("doc-card"), state.docs.length > 0);
      var wanted = selectId || (state.doc && state.doc.id) || (state.docs[0] && state.docs[0].id) || "";
      select.value = wanted;
      chooseDocument(wanted);
    });
  }
  function chooseDocument(id) {
    var changed = !state.doc || state.doc.id !== id;
    state.doc = state.docs.filter(function (d) { return d.id === id; })[0] || null;
    var info = $("doc-info");
    clear(info);
    if (!state.doc) return;
    info.appendChild(el("span", { class: "chip grey", text: state.doc.pages + " pages" }));
    info.appendChild(el("span", { class: "chip " + (state.doc.indexed ? "green" : "grey"), text: state.doc.indexed ? "indexed" : "not indexed yet" }));
    if (state.doc.has_answers) info.appendChild(el("span", { class: "chip", text: "has answers" }));
    if (changed || !$("questions").value.trim()) {
      var draft = recall("sensai-draft-" + state.doc.id);
      var quick = examplesFor(state.doc).quick;
      if (draft) $("questions").value = draft;
      else if (quick.length) $("questions").value = quick.join("\n");
      else if (changed) $("questions").value = "";
      updateCount();
    }
  }
  function upload(file) {
    if (!file) return;
    showNotice($("notice"), "Checking " + file.name + "...", true);
    fetch("/api/upload?name=" + encodeURIComponent(file.name), { method: "POST", body: file })
      .then(readJson)
      .then(function (data) {
        showNotice($("notice"), data.document.name + " is ready (" + data.document.pages + " pages).", true);
        toast(data.document.name + " is ready");
        return loadDocuments(data.document.id);
      })
      .catch(function (e) { showNotice($("notice"), "Upload failed: " + e.message, false); })
      .then(function () { $("upload").value = ""; });
  }

  // ---------- PDF drawer (check a quote without leaving the page) ----------
  function openDrawer(url, title) {
    state.lastFocus = document.activeElement;
    $("drawer-title").textContent = title;
    $("drawer-open").setAttribute("href", url);
    $("drawer-frame").setAttribute("src", url);
    show($("drawer-backdrop"), true);
    show($("drawer"), true);
    $("drawer-close").focus();
  }
  function closeDrawer() {
    if ($("drawer").hidden) return;
    show($("drawer"), false);
    show($("drawer-backdrop"), false);
    $("drawer-frame").setAttribute("src", "about:blank");
    if (state.lastFocus && state.lastFocus.focus) state.lastFocus.focus();
  }

  // ---------- answer cards ----------
  function skeleton() { return el("div", { class: "skeleton" }, [el("i"), el("i"), el("i")]); }
  function isRefusal(c) { return /^the document does not cover this/i.test(c.answer || ""); }
  // How much attention an answer needs. A correct refusal ("not in the document", judge agrees) is calm, not an alarm.
  function assess(c) {
    var refusal = isRefusal(c), verdict = c.verdict;
    if (refusal) {
      if (verdict === "unfaithful") return { cls: "review", refusal: true,
        note: "The judge thinks the document does answer this question, although the model said it does not. Check the PDF." };
      return { cls: "notin", refusal: true, note: "" };
    }
    if (c.disagreement) return { cls: "review", refusal: false, note: "The quote check and the judge disagree. Compare this answer with the page before trusting it." };
    if (c.status !== "supported") return { cls: "review", refusal: false, note: "The quote could not be found word for word in the passages. Check this answer against the PDF." };
    if (verdict === "unfaithful" || verdict === "partial") return { cls: "review", refusal: false, note: "The judge doubts this answer (verdict: " + verdict + "). Check it against the PDF." };
    return { cls: "done", refusal: false, note: "" };
  }
  function buildCard(i, question) {
    var title = el("div", { class: "qtext", text: question });
    var editBtn = el("button", { type: "button", class: "small-btn edit" }, [icon("edit"), "Edit and re-run"]);
    var area = el("textarea", { rows: "2", "aria-label": "Question " + i });
    area.value = question;
    var rerun = el("button", { type: "button", class: "primary rerun" }, [icon("refresh"), "Re-run this question"]);
    var cancel = el("button", { type: "button", class: "link cancel" }, ["Cancel"]);
    var box = el("div", { class: "qedit", hidden: "" }, [area, el("div", { class: "row" }, [rerun, cancel])]);
    editBtn.addEventListener("click", function () { show(box, box.hidden); if (!box.hidden) area.focus(); });
    cancel.addEventListener("click", function () { area.value = state.questions[i - 1]; show(box, false); });
    rerun.addEventListener("click", function () {
      var text = area.value.trim();
      if (!text) return;
      state.questions[i - 1] = text;
      title.textContent = text;
      show(box, false);
      startRun(i);
    });
    var card = el("article", { class: "qcard waiting", id: "card-" + i }, [
      el("div", { class: "qhead" }, [el("span", { class: "qnum", text: "Q" + i }), title, editBtn]),
      box,
      el("div", { class: "qbody" }, [skeleton()])
    ]);
    card.style.animationDelay = Math.min(i - 1, 8) * 60 + "ms";
    return card;
  }
  function buildCards(questions) {
    var box = $("cards");
    clear(box);
    questions.forEach(function (q, i) { box.appendChild(buildCard(i + 1, q)); });
    $("tab-qa").classList.add("has-results");
  }
  function setCard(index, cls, nodes) {
    var card = $("card-" + index);
    card.className = "qcard " + cls;
    card.style.animation = "none"; card.offsetWidth; card.style.animation = "";
    var body = card.querySelector(".qbody");
    clear(body);
    nodes.forEach(function (n) { body.appendChild(n); });
    applyFilter();
  }
  function badge(kind, text, tip, iconName) {
    return el("span", { class: "badge " + kind, title: tip }, iconName ? [icon(iconName), text] : [text]);
  }
  function renderAnswer(index, checked, seconds) {
    var a = assess(checked);
    var iconName = a.cls === "review" ? "alert" : a.cls === "notin" ? "info" : "check";
    var nodes = [el("div", { class: "ans" + (a.refusal ? " refusal" : "") }, [
      el("span", { class: "status-ico" }, [icon(iconName)]), el("span", { class: "answer", text: checked.answer || "" })])];

    if (checked.quote) {
      var label = el("div", { class: "label" }, [el("span", { text: "Quote from the PDF" })]);
      if (checked.page) {
        var url = "/files/" + state.runDoc + "#page=" + checked.page;
        var link = el("a", { class: "page-link", href: url, target: "_blank", rel: "noopener",
                             title: "Open the PDF at this page" }, [icon("external"), "page " + checked.page]);
        link.addEventListener("click", function (e) {
          if (e.metaKey || e.ctrlKey || e.shiftKey || e.button === 1) return;
          e.preventDefault();
          openDrawer(url, "Page " + checked.page + " of " + state.runDoc.split("/")[1]);
        });
        label.appendChild(link);
      }
      nodes.push(el("div", { class: "source" }, [label, el("blockquote", { text: checked.quote })]));
    }
    var checks = el("div", { class: "checks" });
    if (checked.status === "supported") {
      checks.appendChild(badge("ok", "quote check: supported", "The quote was found word for word in the passages the model was given.", "check"));
    } else if (a.refusal) {
      checks.appendChild(badge("neutral", "not in the document", "The model said the document does not cover this, so there is no quote to check."));
    } else {
      checks.appendChild(badge("bad", "quote check: not supported", "The quote was not found in the passages. Read this answer against the PDF.", "x"));
    }
    var verdict = checked.verdict;
    var kinds = { faithful: "ok", partial: "mid", unfaithful: "bad" };
    checks.appendChild(badge(kinds[verdict] || "neutral", "judge: " + (verdict || "not evaluated"),
      "A second model call reads the question, the passages and the answer, and says if the answer is supported.", kinds[verdict] === "ok" ? "check" : null));
    nodes.push(checks);
    if (a.note) nodes.push(el("div", { class: "callout" }, [icon("alert"), el("span", { text: "Review needed. " + a.note })]));

    var actions = el("div", { class: "card-actions" });
    var copy = el("button", { type: "button", class: "small-btn" }, [icon("copy"), "Copy answer"]);
    copy.addEventListener("click", function () {
      var text = checked.answer + (checked.page ? "\n(page " + checked.page + ")" : "") + (checked.quote ? "\n\"" + checked.quote + "\"" : "");
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(function () { toast("Answer copied"); });
    });
    actions.appendChild(copy);
    nodes.push(actions);

    var why = el("details", { class: "why" }, [el("summary", { text: "How this was checked" })]);
    if (checked.reason) why.appendChild(el("p", { text: "Judge: " + checked.reason }));
    var facts = [];
    if (checked.retrieved_pages && checked.retrieved_pages.length) facts.push("passages came from pages " + checked.retrieved_pages.join(", "));
    if (seconds != null) facts.push("took " + seconds + " s");
    if (facts.length) why.appendChild(el("p", { text: facts.join(" - ") }));
    nodes.push(why);
    setCard(index, a.cls, nodes);
  }
  function applyFilter() {
    document.querySelectorAll("#cards .qcard").forEach(function (c) {
      var needs = c.classList.contains("review") || c.classList.contains("failed");
      c.classList.toggle("filtered-out", state.filterReview && !needs);
    });
  }

  // ---------- summary tiles ----------
  function countUp(node, target, suffix) {
    if (reduceMotion || target === 0) { node.textContent = target + suffix; return; }
    var start = null;
    function step(ts) {
      if (start === null) start = ts;
      var t = Math.min(1, (ts - start) / 700), eased = 1 - Math.pow(1 - t, 3);
      node.textContent = Math.round(target * eased) + suffix;
      if (t < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }
  function renderTiles(totalAsked) {
    var results = Object.keys(state.results).map(function (k) { return state.results[k]; });
    var sourced = results.filter(function (r) { return !isRefusal(r); });
    var supported = sourced.filter(function (r) { return r.status === "supported"; }).length;
    var faithful = results.filter(function (r) { return r.verdict === "faithful"; }).length;
    var review = results.filter(function (r) { return assess(r).cls === "review"; }).length;
    var tiles = $("tiles");
    clear(tiles);
    var defs = [
      { label: "Answered", n: results.length, suffix: " / " + totalAsked, cls: results.length === totalAsked ? "good" : "", tip: "Questions that got an answer" },
      { label: "Sourced answers", n: supported, suffix: " / " + sourced.length, cls: "", tip: "Answers whose quote was found word for word in the document" },
      { label: "Judge: faithful", n: faithful, suffix: " / " + results.length, cls: "", tip: "Answers the judge found supported by the passages" }];
    defs.forEach(function (d, i) {
      var b = el("b", { text: "0" + d.suffix });
      tiles.appendChild(el("div", { class: "tile " + d.cls, style: "--i:" + i, title: d.tip }, [b, el("span", { text: d.label })]));
      countUp(b, d.n, d.suffix);
    });
    var rb = el("b", { text: "0" });
    var tile = el("button", { type: "button", class: "tile " + (review ? "warn" : "good") + (state.filterReview ? " active" : ""), style: "--i:3",
                              title: review ? "Show only the answers that need review" : "Nothing needs review" }, [rb, el("span", { text: review ? "Needs review (click to filter)" : "Needs review" })]);
    tile.disabled = !review && !state.filterReview;
    tile.addEventListener("click", function () {
      state.filterReview = !state.filterReview;
      applyFilter();
      tile.classList.toggle("active", state.filterReview);
      toast(state.filterReview ? "Showing only the answers that need review" : "Showing all answers");
    });
    tiles.appendChild(tile);
    countUp(rb, review, "");
  }
  function celebrate() {
    if (reduceMotion) return;
    var box = $("burst");
    clear(box);
    for (var i = 0; i < 18; i++) {
      var angle = (Math.PI * 2 * i) / 18 + Math.random() * 0.3, dist = 46 + Math.random() * 50;
      var dot = el("i");
      dot.style.setProperty("--c", BURST_COLORS[i % BURST_COLORS.length]);
      dot.style.setProperty("--dx", Math.round(Math.cos(angle) * dist) + "px");
      dot.style.setProperty("--dy", Math.round(Math.sin(angle) * dist) + "px");
      dot.style.animationDelay = Math.round(Math.random() * 120) + "ms";
      box.appendChild(dot);
    }
    setTimeout(function () { clear(box); }, 1300);
  }

  // ---------- run (ask a PDF) ----------
  function setRunning(on) {
    state.running = on;
    $("run").disabled = on;
    $("try-demo").disabled = on;
    show($("stop"), on);
    $("stop").disabled = !on;
    $("send").disabled = on || !!state.chatAbort;
    document.querySelectorAll(".qcard button").forEach(function (b) { b.disabled = on; });
  }
  function startTimer() {
    state.t0 = Date.now();
    clearInterval(state.timer);
    state.timer = setInterval(function () { $("elapsed").textContent = fmtTime((Date.now() - state.t0) / 1000); }, 1000);
    $("elapsed").textContent = "0:00";
  }
  function stopTimer() { clearInterval(state.timer); state.timer = null; }
  function setProgress(pct, text) {
    $("bar-fill").style.width = pct + "%";
    document.querySelector("#progress .bar").setAttribute("aria-valuenow", String(Math.round(pct)));
    if (text) $("progress-text").textContent = text;
  }

  function startRun(only) {
    if (state.running) return;
    if (!state.doc) { showNotice($("notice"), "Choose or upload a PDF first.", false); return; }
    var questions = (only ? state.questions.slice() : questionLines()).filter(Boolean);
    if (!questions.length) { showNotice($("notice"), "Write at least one question.", false); $("questions").focus(); return; }
    showNotice($("notice"), "", true);
    state.runDoc = state.doc.id;
    show($("empty"), false);
    if (!only) { state.questions = questions.slice(); state.results = {}; state.filterReview = false; buildCards(questions); }
    else { setCard(only, "running", [skeleton()]); delete state.results[only]; }
    show($("summary-panel"), false);
    var progress = $("progress");
    progress.classList.remove("done", "stopped");
    show(progress, true);
    progress.scrollIntoView({ block: "nearest", behavior: reduceMotion ? "auto" : "smooth" });
    setProgress(0, "Starting...");
    setRunning(true);
    startTimer();
    state.abort = new AbortController();
    var finished = false, failedCount = 0, startedAt = Date.now();
    streamPost("/api/run", { doc: state.runDoc, questions: questions, only: only || null,
                             force: $("force").checked }, function (name, data) {
      if (name === "ingest") {
        if (data.stage === "embedding") setProgress(100 * data.done / data.total * 0.15, "Indexing the PDF: " + data.done + " of " + data.total + " chunks");
        else if (data.stage === "reuse") setProgress(0, "Using the saved index");
        else if (data.stage === "saved") setProgress(0, "Index saved (" + data.chunks + " chunks)");
      } else if (name === "question_start") {
        setProgress(15 + 85 * (data.position - 1) / data.total, "Answering question " + data.position + " of " + data.total + "...");
        setCard(data.index, "running", [skeleton()]);
        $("card-" + data.index).scrollIntoView({ block: "nearest", behavior: reduceMotion ? "auto" : "smooth" });
      } else if (name === "question_done") {
        state.results[data.index] = data.checked;
        renderAnswer(data.index, data.checked, data.seconds);
      } else if (name === "question_failed") {
        failedCount += 1;
        delete state.results[data.index];
        var retry = el("button", { type: "button", class: "small-btn" }, [icon("refresh"), "Try again"]);
        retry.addEventListener("click", function () { startRun(data.index); });
        setCard(data.index, "failed", [el("div", { class: "ans" }, [el("span", { class: "status-ico" }, [icon("x")]),
          el("span", { class: "answer", text: "This question failed: " + data.message })]), el("div", { class: "card-actions" }, [retry])]);
      } else if (name === "summary") {
        setProgress(100);
        $("summary").textContent = data.text;
        renderTiles(state.questions.length);
        show($("summary-panel"), true);
      } else if (name === "done") {
        finished = true;
        refreshAnswersFile(data.doc);
      } else if (name === "error") {
        finished = true;
        showNotice($("notice"), data.message, false);
        $("progress-text").textContent = "Stopped.";
        progress.classList.add("stopped");
      }
    }, state.abort.signal).catch(function (e) {
      progress.classList.add("stopped");
      if (e.name === "AbortError") {
        $("progress-text").textContent = "Stopped. Answers already written are kept.";
        $("cards").querySelectorAll(".qcard.running").forEach(function (c) { c.classList.remove("running"); });
      } else {
        showNotice($("notice"), e.message, false);
        $("progress-text").textContent = "Stopped.";
      }
    }).then(function () {
      var seconds = (Date.now() - startedAt) / 1000;
      stopTimer();
      $("elapsed").textContent = "";
      if (finished && !progress.classList.contains("stopped")) {
        $("progress-text").textContent = "Done in " + fmtTime(seconds);
        if (!failedCount) celebrate();
      }
      progress.classList.add("done");
      setRunning(false);
      state.abort = null;
      if (!finished) loadDocuments(state.runDoc);
    });
  }
  function refreshAnswersFile(docId) {
    return fetch("/api/answers?doc=" + encodeURIComponent(docId)).then(function (res) {
      return res.ok ? res.text() : null;
    }).then(function (text) {
      if (text == null) return;
      $("answers-md").textContent = text;
      $("download").setAttribute("href", "/api/answers?download=1&doc=" + encodeURIComponent(docId));
      show($("file-preview"), true);
      return loadDocuments(docId);
    });
  }
  function tryDemo() {
    var demo = state.docs.filter(function (d) { return d.id === "builtin/demo.pdf"; })[0];
    if (!demo) { toast("The demo document is not available on this server.", true); return; }
    $("try-demo").classList.remove("attn");
    $("doc-select").value = demo.id;
    chooseDocument(demo.id);
    var quick = examplesFor(demo).quick;
    if (quick.length) $("questions").value = quick.join("\n");
    updateCount();
    startRun(null);
  }

  // ---------- chat ----------
  function nearBottom(node) { return node.scrollHeight - node.scrollTop - node.clientHeight < 120; }
  function scrollChat(force) {
    var body = $("chat-body");
    if (force || nearBottom(body)) body.scrollTop = body.scrollHeight;
  }
  function addMessage(role, text) {
    var bubble = el("div", { class: "bubble" + (role === "bot" ? " md" : ""), text: text || "" });
    var msg = el("div", { class: "msg " + role }, [el("div", { class: "avatar", text: role === "user" ? "You" : "AI" }), bubble]);
    $("messages").appendChild(msg);
    show($("chat-empty"), false);
    scrollChat(true);
    return { msg: msg, bubble: bubble };
  }
  function updateMeter(usage) {
    var pct = Math.min(100, Math.round(100 * usage.total_tokens / usage.num_ctx));
    $("meter-fill").style.width = pct + "%";
    $("meter-fill").className = pct > 90 ? "danger" : pct > 75 ? "warn" : "";
    document.querySelector("#meter .bar").setAttribute("aria-valuenow", String(pct));
    $("meter-text").textContent = fmtInt(usage.total_tokens) + " / " + fmtInt(usage.num_ctx) + " tokens (" + pct + "%)";
    $("meter").title = "Prompt " + fmtInt(usage.prompt_tokens) + " + reply " + fmtInt(usage.reply_tokens) +
      " tokens, of a " + fmtInt(usage.num_ctx) + "-token context window. The reply count includes the model's hidden reasoning.";
  }
  function setChatBusy(on) {
    $("send").disabled = on || state.running;
    $("run").disabled = on || state.running;
    $("try-demo").disabled = on || state.running;
    show($("chat-stop"), on);
    $("chat-stop").disabled = !on;
    show($("send"), !on);
  }
  function sendChat(textOverride) {
    if (state.chatAbort || state.running) return;
    var input = $("chat-input");
    var text = (textOverride || input.value).trim();
    if (!text) return;
    input.value = "";
    autosize(input, 144);
    state.chatMessages.push({ role: "user", content: text });
    addMessage("user", text);
    var bot = addMessage("bot", "");
    var typing = el("span", { class: "typing" }, [el("i"), el("i"), el("i")]);
    var note = el("span", { class: "think" });
    bot.bubble.appendChild(typing);
    var reply = "", tokens = 0, failed = false, frame = 0;
    function paint() {
      frame = 0;
      renderMarkdown(bot.bubble, reply);
      bot.bubble.classList.add("caret");
      scrollChat(false);
    }
    setChatBusy(true);
    state.chatAbort = new AbortController();
    streamPost("/api/chat", { messages: state.chatMessages }, function (name, data) {
      if (name === "thinking") {
        note.textContent = " thinking...";
        if (!note.parentNode) bot.bubble.appendChild(note);
      } else if (name === "token") {
        tokens += 1;
        reply += data.text;
        if (!frame) frame = requestAnimationFrame(paint);
        $("meter-text").textContent = "reply so far: about " + tokens + " tokens";
      } else if (name === "done") {
        updateMeter(data.usage);
      } else if (name === "error") {
        failed = true;
        bot.msg.className = "msg bot err";
        bot.bubble.className = "bubble";
        bot.bubble.textContent = data.message;
      }
    }, state.chatAbort.signal).then(function () {
      if (failed) { state.chatMessages.pop(); input.value = text; }
      else { state.chatMessages.push({ role: "assistant", content: reply }); }
    }).catch(function (e) {
      state.chatMessages.pop();
      input.value = text;
      bot.msg.className = "msg bot err";
      bot.bubble.className = "bubble";
      bot.bubble.textContent = e.name === "AbortError" ? "(reply cancelled)" : e.message;
    }).then(function () {
      if (frame) cancelAnimationFrame(frame);
      if (!failed && reply) renderMarkdown(bot.bubble, reply);
      bot.bubble.classList.remove("caret");
      state.chatAbort = null;
      setChatBusy(false);
      scrollChat(false);
      input.focus({ preventScroll: true });
    });
  }
  function newChat() {
    if (state.chatAbort) state.chatAbort.abort();
    state.chatMessages = [];
    clear($("messages"));
    show($("chat-empty"), true);
    $("meter-fill").style.width = "0%";
    $("meter-fill").className = "";
    document.querySelector("#meter .bar").setAttribute("aria-valuenow", "0");
    $("meter-text").textContent = "nothing sent yet";
    $("meter").title = "How much of the model's context window this conversation uses";
  }

  // ---------- settings ----------
  function buildSettings() {
    var s = state.status;
    var form = $("settings-form");
    clear(form);
    if (!s) return;
    SETTING_GROUPS.forEach(function (group) {
      var keys = group.keys.filter(function (k) { return s.editable[k]; });
      if (!keys.length) return;
      var card = el("div", { class: "card group" }, [el("h3", { text: group.title })]);
      keys.forEach(function (key) {
        var rule = s.editable[key];
        var input;
        var help = group.help[key] || "";
        if (rule[0] === "int") {
          input = el("input", { type: "number", id: "set-" + key, min: rule[1], max: rule[2], step: "1" });
          help += " (" + fmtInt(rule[1]) + " to " + fmtInt(rule[2]) + ")";
        } else {
          input = el("input", { type: "text", id: "set-" + key, list: "model-list", spellcheck: "false" });
        }
        input.value = s.config[key];
        card.appendChild(el("div", { class: "field" }, [
          el("div", {}, [el("label", { for: "set-" + key, text: SETTING_LABELS[key] || key }), el("div", { class: "help", text: help })]), input]));
      });
      form.appendChild(card);
    });
  }
  function applySettings() {
    var s = state.status;
    var overrides = {};
    Object.keys(s.editable).forEach(function (key) {
      var node = $("set-" + key);
      if (!node) return;
      var raw = node.value.trim();
      var value = s.editable[key][0] === "int" ? Number(raw) : raw;
      if (value !== s.config[key]) overrides[key] = value;
    });
    if (!Object.keys(overrides).length) { showNotice($("settings-msg"), "Nothing changed.", true); return; }
    apiPost("/api/config", { overrides: overrides }).then(function () {
      var stale = "chunk_size" in overrides || "chunk_overlap" in overrides || "embed_model" in overrides;
      if (stale) $("force").checked = true;
      showNotice($("settings-msg"), "Applied." + (stale ? " The index will be rebuilt on the next run." : ""), true);
      toast("Settings applied");
      return refreshStatus().then(buildSettings);
    }).catch(function (e) { showNotice($("settings-msg"), e.message, false); });
  }
  function resetSettings() {
    apiPost("/api/config", { reset: true }).then(function () {
      showNotice($("settings-msg"), "Back to the values of config.json.", true);
      toast("Settings reset");
      return refreshStatus().then(buildSettings);
    }).catch(function (e) { showNotice($("settings-msg"), e.message, false); });
  }

  // ---------- wiring ----------
  function init() {
    applyIcons(document);
    var ring = document.querySelector(".done-ico");
    var svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    var circle = document.createElementNS(NS, "circle");
    circle.setAttribute("cx", "12"); circle.setAttribute("cy", "12"); circle.setAttribute("r", "10");
    var tick = document.createElementNS(NS, "path");
    tick.setAttribute("d", "M7 12.5l3.2 3.2L17 9");
    svg.appendChild(circle); svg.appendChild(tick); ring.appendChild(svg);

    if (location.protocol === "file:") {
      show($("needs-server"), true);
      show($("main"), false);
      show($("tabs"), false);
      show($("theme"), true);
      setPill("bad", "server not running");
      $("theme").addEventListener("click", toggleTheme);
      return;
    }
    document.querySelectorAll(".tab-btn").forEach(function (b) {
      b.addEventListener("click", function () { selectTab(b.getAttribute("data-tab")); });
    });
    window.addEventListener("resize", moveIndicator);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(moveIndicator);
    moveIndicator();
    window.addEventListener("scroll", function () { $("top").classList.toggle("scrolled", window.scrollY > 6); }, { passive: true });
    $("theme").addEventListener("click", toggleTheme);

    var dz = $("dropzone");
    dz.addEventListener("click", function () { $("upload").click(); });
    dz.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); $("upload").click(); } });
    ["dragenter", "dragover"].forEach(function (n) { dz.addEventListener(n, function (e) { e.preventDefault(); dz.classList.add("over"); }); });
    ["dragleave", "drop"].forEach(function (n) { dz.addEventListener(n, function (e) { e.preventDefault(); dz.classList.remove("over"); }); });
    dz.addEventListener("drop", function (e) { if (e.dataTransfer && e.dataTransfer.files.length) upload(e.dataTransfer.files[0]); });
    $("upload").addEventListener("change", function () { upload($("upload").files[0]); });
    $("doc-select").addEventListener("change", function () { chooseDocument($("doc-select").value); });
    $("questions").addEventListener("input", updateCount);
    $("questions").addEventListener("keydown", function (e) {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); startRun(null); }
    });
    $("load-example").addEventListener("click", function () {
      var ex = examplesFor(state.doc);
      if (ex.quick.length) { $("questions").value = ex.quick.join("\n"); updateCount(); }
      else toast("No example questions for this document.", true);
    });
    $("load-all").addEventListener("click", function () {
      var ex = examplesFor(state.doc);
      if (ex.all.length) { $("questions").value = ex.all.join("\n"); updateCount(); }
      else toast("No example questions for this document.", true);
    });
    $("run").addEventListener("click", function () { startRun(null); });
    $("try-demo").addEventListener("click", tryDemo);
    $("stop").addEventListener("click", function () { if (state.abort) state.abort.abort(); });
    $("copy-md").addEventListener("click", function (e) {
      e.preventDefault();
      var text = $("answers-md").textContent;
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(function () { toast("answers.md copied"); });
    });
    $("send").addEventListener("click", function () { sendChat(); });
    $("chat-stop").addEventListener("click", function () { if (state.chatAbort) state.chatAbort.abort(); });
    $("chat-new").addEventListener("click", newChat);
    $("chat-input").addEventListener("input", function () { autosize($("chat-input"), 144); });
    $("chat-input").addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); sendChat(); }
    });
    SUGGESTIONS.forEach(function (text) {
      var chip = el("button", { type: "button", text: text });
      chip.addEventListener("click", function () { sendChat(text); });
      $("chips").appendChild(chip);
    });
    $("drawer-close").addEventListener("click", closeDrawer);
    $("drawer-backdrop").addEventListener("click", closeDrawer);
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeDrawer(); });
    $("settings-apply").addEventListener("click", applySettings);
    $("settings-reset").addEventListener("click", resetSettings);
    refreshStatus().then(function () {
      return apiGet("/api/examples").catch(function () { return {}; });
    }).then(function (ex) {
      state.examples = ex || {};
      return loadDocuments();
    }).then(updateCount);
    setInterval(function () { if (!state.running && !state.chatAbort) refreshStatus(); }, 15000);
  }
  document.addEventListener("DOMContentLoaded", init);
})();
