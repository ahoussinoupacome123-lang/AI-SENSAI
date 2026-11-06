/* SENSAI web UI (feature X1): a ChatGPT-style interface. Plain JavaScript, no build step, no dependency.
   Every piece of text that comes from a document or a model is inserted with textContent,
   never as HTML, so a malicious PDF or a model reply cannot inject script into the page. */
(function () {
  "use strict";

  var NS = "http://www.w3.org/2000/svg";
  var ICONS = {
    logo: ["M5 8h14", "M5 12h14", "M5 16h8"],
    sidebar: ["M4 5h16a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z", "M9 5v14"],
    compose: ["M12 20h9", "M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"],
    chevron: ["M6 9l6 6 6-6"],
    plus: ["M12 5v14", "M5 12h14"],
    down: ["M12 5v14", "M19 12l-7 7-7-7"],
    arrowup: ["M12 19V5", "M5 12l7-7 7 7"],
    trash: ["M3 6h18", "M8 6V4h8v2", "M6 6l1 14h10l1-14"],
    file: ["M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z", "M14 3v5h5", "M9 13h6", "M9 17h6"],
    gear: ["M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z", "M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"],
    upload: ["M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4", "M17 8l-5-5-5 5", "M12 3v12"],
    download: ["M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4", "M7 10l5 5 5-5", "M12 15V3"],
    sparkles: ["M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z", "M19 15l.9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9z"],
    stop: ["M7 7h10v10H7z"],
    chat: ["M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"],
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
  var CHAT_CHIPS = ["Explain what retrieval-augmented generation is in two sentences.", "What is the difference between TCP and UDP?"];
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
  // Feature flags (config.json "feature_flags"): switch a part of the pipeline off for this server session.
  var FEATURE_FLAGS = [
    ["rag", "Retrieval (RAG)", "Search the PDF and send the best passages. Off: the model answers without reading the document."],
    ["judge", "Judge", "A second model call checks each answer against the passages."],
    ["quote_check", "Quote check", "Check the quote word for word against the passages (plain code, no model)."]
  ];
  var CONV_KEY = "sensai-convs";

  var $ = function (id) { return document.getElementById(id); };
  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var state = { convs: [], cur: null, docs: [], doc: null, status: null, examples: {}, busy: false, abort: null,
                uis: new WeakMap(), lastFocus: null, t0: 0, timer: null };

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

  // ---------- theme, sidebar, status ----------
  function toggleTheme() {
    var root = document.documentElement;
    var attr = root.getAttribute("data-theme");
    var dark = attr ? attr === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
    var next = dark ? "light" : "dark";
    root.setAttribute("data-theme", next);
    store("sensai-theme", next);
  }
  function isMobile() { return window.matchMedia("(max-width: 820px)").matches; }
  function openSidebar() {
    if (isMobile()) { $("app").classList.add("side-open"); }
    else { document.documentElement.removeAttribute("data-sidebar"); store("sensai-sidebar", "open"); }
  }
  function closeSidebar() {
    if (isMobile()) { $("app").classList.remove("side-open"); }
    else { document.documentElement.setAttribute("data-sidebar", "closed"); store("sensai-sidebar", "closed"); }
  }
  function setPill(kind, text, detail) {
    $("status-pill").className = "model-btn pill-" + kind;
    $("status-text").textContent = text;
    $("status-detail").textContent = detail ? " " + detail : "";
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
        } else { show(banner, false); }
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
      setPill("bad", "Server not reachable");
      $("banner").textContent = "Cannot talk to the Sensai server: " + e.message;
      show($("banner"), true);
    });
  }

  // ---------- scrolling ----------
  function distanceFromEnd() { var b = $("chat-body"); return b.scrollHeight - b.scrollTop - b.clientHeight; }
  function setEmpty(on) { show($("chat-empty"), on); $("main").classList.toggle("is-empty", on); }
  function scrollEnd(force) {
    var b = $("chat-body");
    if (force || distanceFromEnd() < 140) b.scrollTop = b.scrollHeight;
  }
  function updateJump() { show($("jump"), distanceFromEnd() > 260); }

  // ---------- conversations (kept in this browser only) ----------
  function loadConvs() {
    try {
      var list = JSON.parse(recall(CONV_KEY) || "[]");
      return Array.isArray(list) ? list.filter(function (c) { return c && c.id && Array.isArray(c.turns); }) : [];
    } catch (e) { return []; }
  }
  function saveConvs() { store(CONV_KEY, JSON.stringify(state.convs.slice(0, 40))); }
  function newConv() {
    return { id: "c" + Date.now().toString(36) + Math.floor(Math.random() * 1e4), title: "New chat", updated: Date.now(), turns: [], usage: null };
  }
  function ensureConv() {
    if (!state.cur) state.cur = newConv();
    if (state.convs.indexOf(state.cur) < 0) state.convs.unshift(state.cur);
    return state.cur;
  }
  function touch(conv, titleHint) {
    conv.updated = Date.now();
    if (titleHint && conv.title === "New chat") conv.title = titleHint.replace(/\s+/g, " ").slice(0, 44);
    state.convs.sort(function (a, b) { return b.updated - a.updated; });
    saveConvs();
    renderHistory();
  }
  function renderHistory() {
    var box = $("history");
    clear(box);
    if (!state.convs.length) { box.appendChild(el("div", { class: "hist-empty", text: "Your chats will appear here." })); return; }
    state.convs.forEach(function (c) {
      var open = el("button", { type: "button", class: "hist-open", text: c.title, title: c.title });
      open.addEventListener("click", function () { openConv(c); });
      var del = el("button", { type: "button", class: "hist-del", "aria-label": "Delete chat: " + c.title }, [icon("trash")]);
      del.addEventListener("click", function (e) { e.stopPropagation(); deleteConv(c); });
      box.appendChild(el("div", { class: "hist-row" + (c === state.cur ? " active" : "") }, [open, del]));
    });
  }
  function guardBusy() {
    if (!state.busy) return false;
    toast("Wait for the current reply to finish, or press Stop.", true);
    return true;
  }
  function openConv(c) {
    if (c === state.cur || guardBusy()) { if (isMobile()) $("app").classList.remove("side-open"); return; }
    state.cur = c;
    renderConv();
    renderHistory();
    if (isMobile()) $("app").classList.remove("side-open");
  }
  function deleteConv(c) {
    if (c === state.cur && guardBusy()) return;
    state.convs = state.convs.filter(function (x) { return x !== c; });
    if (state.cur === c) { state.cur = null; renderConv(); }
    saveConvs();
    renderHistory();
  }
  function newConversation() {
    if (guardBusy()) return;
    state.cur = null;
    state.doc = null;
    renderAttached();
    showNotice($("notice"), "", true);
    renderConv();
    renderHistory();
    if (isMobile()) $("app").classList.remove("side-open");
    $("chat-input").focus();
  }
  function renderConv() {
    clear($("messages"));
    var conv = state.cur;
    setEmpty(!conv || !conv.turns.length);
    if (conv) conv.turns.forEach(function (t) { t.role === "user" ? renderUser(t) : renderBot(t); });
    if (conv && conv.usage) updateMeter(conv.usage); else resetMeter();
    scrollEnd(true);
  }

  // ---------- turns ----------
  function renderUser(turn) {
    var node = el("div", { class: "turn user" });
    if (turn.doc) node.appendChild(el("div", { class: "user-doc" }, [icon("file"), turn.doc]));
    var bubble = el("div", { class: "user-bubble", text: turn.text });
    node.appendChild(bubble);

    // Actions: edit message & branch switcher (feature X2)
    var actions = el("div", { class: "user-actions" });
    var conv = state.cur;
    if (conv && conv.branches && conv.branches.length > 0) {
      var turnIdx = conv.turns.indexOf(turn);
      var matchingBranches = conv.branches.filter(function (b) { return b.turnIndex === turnIdx; });
      if (matchingBranches.length > 0) {
        var nav = el("div", { class: "user-branch-nav" });
        var totalBranches = matchingBranches.length + 1;
        var label = el("span", { class: "branch-count", text: totalBranches + " / " + totalBranches });
        var prevBtn = el("button", { type: "button", class: "branch-btn", title: "Switch to previous branch", "aria-label": "Previous branch" }, [icon("chevron")]);
        prevBtn.style.transform = "rotate(90deg)";
        prevBtn.addEventListener("click", function () {
          if (guardBusy()) return;
          switchBranch(conv, matchingBranches[matchingBranches.length - 1], turnIdx);
        });
        nav.appendChild(prevBtn);
        nav.appendChild(label);
        actions.appendChild(nav);
      }
    }

    var editBtn = el("button", { type: "button", class: "icon-btn user-edit-btn", title: "Edit message & branch", "aria-label": "Edit message" }, [icon("edit")]);
    editBtn.addEventListener("click", function () {
      if (guardBusy()) return;
      startEditUserTurn(turn, node, bubble);
    });
    actions.appendChild(editBtn);
    node.appendChild(actions);

    $("messages").appendChild(node);
    return node;
  }

  function switchBranch(conv, targetBranch, turnIdx) {
    var branchIdx = conv.branches.indexOf(targetBranch);
    if (branchIdx < 0) return;
    var currentTurnsCopy = JSON.parse(JSON.stringify(conv.turns));
    conv.turns = targetBranch.turns;
    conv.branches[branchIdx] = {
      timestamp: Date.now(),
      turnIndex: turnIdx,
      turns: currentTurnsCopy
    };
    touch(conv);
    renderConv();
    toast("Switched branch");
  }

  function startEditUserTurn(turn, node, bubble) {
    bubble.hidden = true;
    var editBox = el("div", { class: "user-edit-box" });
    var area = el("textarea", { class: "user-edit-area" });
    area.value = turn.text;
    autosize(area, 220);
    area.addEventListener("input", function () { autosize(area, 220); });

    var cancelBtn = el("button", { type: "button", class: "ghost-btn btn-sm", text: "Cancel" });
    var saveBtn = el("button", { type: "button", class: "ghost-btn btn-sm primary", text: "Save & Branch" });

    function cancelEdit() {
      if (editBox.parentNode) editBox.parentNode.removeChild(editBox);
      bubble.hidden = false;
    }

    cancelBtn.addEventListener("click", cancelEdit);
    saveBtn.addEventListener("click", function () {
      var newText = area.value.trim();
      if (!newText) { toast("Message cannot be empty", true); return; }
      if (newText === turn.text) { cancelEdit(); return; }
      executeBranchEdit(turn, newText);
    });

    editBox.appendChild(area);
    var actDiv = el("div", { class: "user-edit-actions" }, [cancelBtn, saveBtn]);
    editBox.appendChild(actDiv);
    node.insertBefore(editBox, bubble);
    area.focus();
  }

  function executeBranchEdit(turn, newText) {
    var conv = state.cur;
    if (!conv) return;
    var turnIdx = conv.turns.indexOf(turn);
    if (turnIdx < 0) return;

    conv.branches = conv.branches || [];
    conv.branches.push({
      timestamp: Date.now(),
      turnIndex: turnIdx,
      turns: JSON.parse(JSON.stringify(conv.turns))
    });

    turn.text = newText;
    conv.turns = conv.turns.slice(0, turnIdx + 1);
    touch(conv, conv.turns[0].text);
    renderConv();

    if (turn.doc) {
      var doc = state.docs.find(function (d) { return d.id === turn.doc || d.name === turn.doc; });
      if (doc) {
        state.doc = doc;
        var bot = { role: "bot", kind: "qa", doc: doc.id, docName: doc.name, questions: [newText], results: {}, failed: {}, summary: "" };
        conv.turns.push(bot);
        renderBot(bot);
        startQa(bot, null);
      }
    } else {
      var messages = chatHistory(conv).concat([{ role: "user", content: newText }]);
      streamBotTurn(conv, messages);
    }
  }
  function botShell() {
    var body = el("div", { class: "bot-body" });
    var node = el("div", { class: "turn bot" }, [el("div", { class: "avatar" }, [icon("logo")]), body]);
    $("messages").appendChild(node);
    return { node: node, body: body };
  }
  function copyButton(getText, label) {
    var b = el("button", { type: "button", class: "icon-btn", "aria-label": label || "Copy", title: label || "Copy" }, [icon("copy")]);
    b.addEventListener("click", function () {
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(getText()).then(function () { toast("Copied"); });
    });
    return b;
  }
  function renderBot(turn) {
    var s = botShell();
    if (turn.kind === "qa") { buildQa(turn, s); return s; }
    if (turn.kind === "error") { s.node.classList.add("err"); s.body.textContent = turn.text; return s; }
    var md = el("div", { class: "md" });
    renderMarkdown(md, turn.text || "");
    s.body.appendChild(md);
    s.body.appendChild(el("div", { class: "msg-actions" }, [copyButton(function () { return turn.text; }, "Copy reply")]));
    return s;
  }

  // ---------- PDF answers inside a reply ----------
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
  function buildQa(turn, s) {
    var ui = { body: s.body, items: [], filter: false, summary: null, finished: true };
    state.uis.set(turn, ui);
    ui.stext = el("span", { class: "stext shimmer" });
    ui.elapsed = el("span", { class: "muted elapsed" });
    ui.status = el("div", { class: "run-status", hidden: "" }, [el("span", { class: "spin" }), el("span", { class: "tick" }, [icon("check")]), ui.stext, ui.elapsed]);
    ui.fill = el("i");
    ui.bar = el("div", { class: "run-bar", role: "progressbar", "aria-label": "Progress", "aria-valuemin": "0", "aria-valuemax": "100", "aria-valuenow": "0", hidden: "" }, [ui.fill]);
    s.body.appendChild(ui.status);
    s.body.appendChild(ui.bar);
    turn.questions.forEach(function (q, i) {
      var item = buildItem(turn, i + 1, q);
      ui.items[i + 1] = item;
      s.body.appendChild(item.root);
      if (turn.results[i + 1]) renderAnswer(turn, i + 1, turn.results[i + 1], null);
      else if (turn.failed[i + 1]) renderFailed(turn, i + 1, turn.failed[i + 1]);
      else setItem(turn, i + 1, "stopped", [el("div", { class: "muted", text: "No answer was saved for this question." })]);
    });
    if (turn.summary) renderSummary(turn);
  }
  function buildItem(turn, i, question) {
    var title = el("div", { class: "q-text", text: question });
    var editBtn = el("button", { type: "button", class: "q-edit" }, [icon("edit"), "Edit and re-run"]);
    var area = el("textarea", { rows: "2", "aria-label": "Question " + i });
    area.value = question;
    var rerun = el("button", { type: "button", class: "btn dark rerun" }, [icon("refresh"), "Re-run this question"]);
    var cancel = el("button", { type: "button", class: "btn cancel" }, ["Cancel"]);
    var box = el("div", { class: "q-box", hidden: "" }, [area, el("div", { class: "row" }, [rerun, cancel])]);
    editBtn.addEventListener("click", function () {
      if (guardBusy()) return;
      show(box, box.hidden);
      if (!box.hidden) area.focus();
    });
    cancel.addEventListener("click", function () { area.value = turn.questions[i - 1]; show(box, false); });
    rerun.addEventListener("click", function () {
      var text = area.value.trim().replace(/\s+/g, " ");
      if (!text || guardBusy()) return;
      turn.questions[i - 1] = text;
      title.textContent = text;
      show(box, false);
      startQa(turn, i);
    });
    var body = el("div", { class: "q-body" });
    var root = el("article", { class: "qa", id: "q-" + turn.doc.replace(/\W/g, "_") + "-" + i + "-" + Math.floor(Math.random() * 1e6) },
      [el("div", { class: "q-head" }, [el("span", { class: "q-num", text: "Q" + i }), title, editBtn]), box, body]);
    return { root: root, body: body, title: title };
  }
  function setItem(turn, i, cls, nodes) {
    var ui = state.uis.get(turn), item = ui && ui.items[i];
    if (!item) return;
    item.root.className = "qa " + cls;
    clear(item.body);
    nodes.forEach(function (n) { item.body.appendChild(n); });
    applyFilter(turn);
  }
  function badge(kind, text, tip, iconName) {
    return el("span", { class: "badge " + kind, title: tip }, iconName ? [icon(iconName), text] : [text]);
  }
  function renderFailed(turn, i, message) {
    var retry = el("button", { type: "button", class: "small-btn" }, [icon("refresh"), "Try again"]);
    retry.addEventListener("click", function () { if (!guardBusy()) startQa(turn, i); });
    setItem(turn, i, "failed", [el("div", { class: "ans" }, [el("span", { class: "status-ico" }, [icon("x")]),
      el("span", { class: "answer", text: "This question failed: " + message })]), el("div", { class: "q-actions" }, [retry])]);
  }
  function renderAnswer(turn, index, checked, seconds) {
    var a = assess(checked);
    var iconName = a.cls === "review" ? "alert" : a.cls === "notin" ? "info" : "check";
    var nodes = [el("div", { class: "ans" + (a.refusal ? " refusal" : "") }, [
      el("span", { class: "status-ico" }, [icon(iconName)]), el("span", { class: "answer", text: checked.answer || "" })])];
    if (checked.quote) {
      var label = el("div", { class: "label" }, [el("span", { text: "Quote from the PDF" })]);
      if (checked.page) {
        var url = "/files/" + turn.doc + "#page=" + checked.page;
        var link = el("a", { class: "page-link", href: url, target: "_blank", rel: "noopener", title: "Open the PDF at this page" },
                      [icon("external"), "page " + checked.page]);
        link.addEventListener("click", function (e) {
          if (e.metaKey || e.ctrlKey || e.shiftKey || e.button === 1) return;
          e.preventDefault();
          openDrawer(url, "Page " + checked.page + " of " + turn.doc.split("/")[1]);
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
    var kinds = { faithful: "ok", partial: "mid", unfaithful: "bad" };
    checks.appendChild(badge(kinds[checked.verdict] || "neutral", "judge: " + (checked.verdict || "not evaluated"),
      "A second model call reads the question, the passages and the answer, and says if the answer is supported.", kinds[checked.verdict] === "ok" ? "check" : null));
    nodes.push(checks);
    if (a.note) nodes.push(el("div", { class: "callout" }, [icon("alert"), el("span", { text: "Review needed. " + a.note })]));
    var copy = el("button", { type: "button", class: "small-btn" }, [icon("copy"), "Copy answer"]);
    copy.addEventListener("click", function () {
      var text = checked.answer + (checked.page ? "\n(page " + checked.page + ")" : "") + (checked.quote ? "\n\"" + checked.quote + "\"" : "");
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(function () { toast("Answer copied"); });
    });
    nodes.push(el("div", { class: "q-actions" }, [copy]));
    var why = el("details", { class: "why" }, [el("summary", { text: "How this was checked" })]);
    if (checked.reason) why.appendChild(el("p", { text: "Judge: " + checked.reason }));
    var facts = [];
    if (checked.retrieved_pages && checked.retrieved_pages.length) facts.push("passages came from pages " + checked.retrieved_pages.join(", "));
    if (seconds != null) facts.push("took " + seconds + " s");
    if (facts.length) why.appendChild(el("p", { text: facts.join(" - ") }));
    nodes.push(why);
    setItem(turn, index, a.cls, nodes);
  }
  function applyFilter(turn) {
    var ui = state.uis.get(turn);
    if (!ui) return;
    ui.items.forEach(function (it) {
      if (!it) return;
      var needs = it.root.classList.contains("review") || it.root.classList.contains("failed");
      it.root.classList.toggle("filtered-out", ui.filter && !needs);
    });
  }
  function countUp(node, target, suffix) {
    if (reduceMotion || target === 0) { node.textContent = target + suffix; return; }
    var start = null;
    function step(ts) {
      if (start === null) start = ts;
      var t = Math.min(1, (ts - start) / 600), eased = 1 - Math.pow(1 - t, 3);
      node.textContent = Math.round(target * eased) + suffix;
      if (t < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }
  function renderSummary(turn) {
    var ui = state.uis.get(turn);
    if (!ui) return;
    if (ui.summary && ui.summary.parentNode) ui.summary.parentNode.removeChild(ui.summary);
    var results = Object.keys(turn.results).map(function (k) { return turn.results[k]; });
    var sourced = results.filter(function (r) { return !isRefusal(r); });
    var supported = sourced.filter(function (r) { return r.status === "supported"; }).length;
    var faithful = results.filter(function (r) { return r.verdict === "faithful"; }).length;
    var review = results.filter(function (r) { return assess(r).cls === "review"; }).length;
    var total = turn.questions.length;
    var tiles = el("div", { class: "tiles" });
    [{ label: "Answered", n: results.length, suffix: " / " + total, cls: results.length === total ? "good" : "" },
     { label: "Sourced answers", n: supported, suffix: " / " + sourced.length, cls: "" },
     { label: "Judge: faithful", n: faithful, suffix: " / " + results.length, cls: "" }].forEach(function (d) {
      var b = el("b", { text: "0" + d.suffix });
      tiles.appendChild(el("div", { class: "tile " + d.cls }, [b, el("span", { text: d.label })]));
      countUp(b, d.n, d.suffix);
    });
    var rb = el("b", { text: "0" });
    var tile = el("button", { type: "button", class: "tile " + (review ? "warn" : "good") + (ui.filter ? " active" : ""),
                              title: review ? "Show only the answers that need review" : "Nothing needs review" },
                  [rb, el("span", { text: review ? "Needs review (click to filter)" : "Needs review" })]);
    tile.disabled = !review && !ui.filter;
    tile.addEventListener("click", function () {
      ui.filter = !ui.filter;
      applyFilter(turn);
      tile.classList.toggle("active", ui.filter);
      toast(ui.filter ? "Showing only the answers that need review" : "Showing all answers");
    });
    tiles.appendChild(tile);
    countUp(rb, review, "");
    var acts = el("div", { class: "acts" });
    var dl = el("a", { class: "btn", href: "/api/answers?download=1&doc=" + encodeURIComponent(turn.doc) }, [icon("download"), "Download answers.md"]);
    var view = el("button", { type: "button", class: "btn" }, [icon("file"), "View answers.md"]);
    view.addEventListener("click", function () {
      fetch("/api/answers?doc=" + encodeURIComponent(turn.doc)).then(function (res) { return res.ok ? res.text() : Promise.reject(new Error("No answers file yet")); })
        .then(function (text) { openText("answers.md", text); }).catch(function (e) { toast(e.message, true); });
    });
    acts.appendChild(dl); acts.appendChild(view);
    acts.appendChild(copyButton(function () { return turn.summary; }, "Copy the summary"));
    ui.summary = el("div", { class: "summary" }, [tiles, el("p", { text: turn.summary }), acts]);
    ui.body.appendChild(ui.summary);
  }

  // ---------- run: ask a PDF ----------
  function startTimer(ui) {
    state.t0 = Date.now();
    clearInterval(state.timer);
    ui.elapsed.textContent = "0:00";
    state.timer = setInterval(function () { ui.elapsed.textContent = fmtTime((Date.now() - state.t0) / 1000); }, 1000);
  }
  function stopTimer(ui) { clearInterval(state.timer); state.timer = null; ui.elapsed.textContent = ""; }
  function setProgress(ui, pct, text) {
    ui.fill.style.width = pct + "%";
    ui.bar.setAttribute("aria-valuenow", String(Math.round(pct)));
    if (text) ui.stext.textContent = text;
  }
  function markPending(turn, message, retry) {
    var ui = state.uis.get(turn);
    ui.items.forEach(function (it, i) {
      if (!it || turn.results[i] || turn.failed[i]) return;
      if (retry) { turn.failed[i] = message; renderFailed(turn, i, message); }
      else setItem(turn, i, "stopped", [el("div", { class: "muted", text: message })]);
    });
  }
  function startQa(turn, only) {
    var ui = state.uis.get(turn);
    if (!ui || state.busy) return;
    if (only) {
      setItem(turn, only, "running", [skeleton()]);
      delete turn.results[only]; delete turn.failed[only]; turn.summary = "";
      if (ui.summary && ui.summary.parentNode) ui.summary.parentNode.removeChild(ui.summary);
    } else {
      ui.items.forEach(function (it, i) { if (it) setItem(turn, i, "waiting", [skeleton()]); });
    }
    ui.status.className = "run-status"; show(ui.status, true); show(ui.bar, true);
    ui.stext.className = "stext shimmer";
    setProgress(ui, 0, "Starting...");
    setBusy(true);
    startTimer(ui);
    state.abort = new AbortController();
    var finished = false, stopped = false, failedCount = 0, startedAt = Date.now();
    return streamPost("/api/run", { doc: turn.doc, questions: turn.questions.slice(), only: only || null, force: $("force").checked },
      function (name, data) {
        if (name === "ingest") {
          if (data.stage === "embedding") setProgress(ui, 15 * data.done / data.total, "Reading the PDF: " + data.done + " of " + data.total + " chunks");
          else if (data.stage === "reuse") setProgress(ui, 0, "Using the saved index");
          else if (data.stage === "saved") setProgress(ui, 15, "Index saved (" + data.chunks + " chunks)");
        } else if (name === "question_start") {
          setProgress(ui, 15 + 85 * (data.position - 1) / data.total, "Answering question " + data.position + " of " + data.total + "...");
          setItem(turn, data.index, "running", [skeleton()]);
          scrollEnd(false);
        } else if (name === "question_done") {
          turn.results[data.index] = data.checked;
          delete turn.failed[data.index];
          renderAnswer(turn, data.index, data.checked, data.seconds);
          scrollEnd(false);
        } else if (name === "question_failed") {
          failedCount += 1;
          delete turn.results[data.index];
          turn.failed[data.index] = data.message;
          renderFailed(turn, data.index, data.message);
        } else if (name === "summary") {
          setProgress(ui, 100);
          turn.summary = data.text;
          renderSummary(turn);
          scrollEnd(false);
        } else if (name === "done") {
          finished = true;
        } else if (name === "error") {
          finished = true; stopped = true;
          showNotice($("notice"), data.message, false);
          ui.stext.textContent = "Stopped.";
          markPending(turn, data.message, true);
        }
      }, state.abort.signal).catch(function (e) {
      stopped = true;
      if (e.name === "AbortError") {
        ui.stext.textContent = "Stopped. Answers already written are kept.";
        markPending(turn, "Stopped before this question.", false);
      } else {
        showNotice($("notice"), e.message, false);
        ui.stext.textContent = "Stopped.";
        markPending(turn, e.message, true);
      }
    }).then(function () {
      var seconds = (Date.now() - startedAt) / 1000;
      stopTimer(ui);
      ui.stext.className = "stext";
      if (finished && !stopped) {
        ui.stext.textContent = failedCount ? "Done in " + fmtTime(seconds) + " (" + failedCount + " failed)" : "Done in " + fmtTime(seconds);
        ui.status.className = "run-status done";
        show(ui.bar, false);
      } else {
        ui.status.className = "run-status stopped";
      }
      state.abort = null;
      setBusy(false);
      touch(state.cur);
      loadDocuments();
      scrollEnd(false);
    });
  }
  function sendQa(text) {
    var doc = state.doc;
    var questions = text.split("\n").map(function (l) { return l.trim(); }).filter(Boolean);
    var conv = ensureConv();
    var user = { role: "user", text: questions.join("\n"), doc: doc.name };
    var bot = { role: "bot", kind: "qa", doc: doc.id, docName: doc.name, questions: questions, results: {}, failed: {}, summary: "" };
    conv.turns.push(user, bot);
    touch(conv, doc.name + ": " + questions[0]);
    setEmpty(false);
    renderUser(user);
    renderBot(bot);
    scrollEnd(true);
    return startQa(bot, null);
  }

  // ---------- chat ----------
  function chatHistory(conv) {
    var msgs = [];
    for (var i = 0; i + 1 < conv.turns.length; i++) {
      var u = conv.turns[i], b = conv.turns[i + 1];
      if (u.role === "user" && !u.doc && b.role === "bot" && b.kind === "chat") msgs.push({ role: "user", content: u.text }, { role: "assistant", content: b.text });
    }
    return msgs;
  }
  function resetMeter() {
    $("meter-fill").style.width = "0%";
    $("meter-fill").className = "";
    document.querySelector("#meter .bar").setAttribute("aria-valuenow", "0");
    $("meter-text").textContent = "nothing sent yet";
    $("meter").title = "How much of the model's context window this conversation uses";
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
  function sendChat(text) {
    var conv = ensureConv();
    var user = { role: "user", text: text, doc: null };
    conv.turns.push(user);
    touch(conv, text);
    setEmpty(false);
    renderUser(user);
    var messages = chatHistory(conv).concat([{ role: "user", content: text }]);
    streamBotTurn(conv, messages);
  }

  function streamBotTurn(conv, messages) {
    var s = botShell();
    var md = el("div", { class: "md caret" });
    var thinking = el("span", { class: "think" }, [el("span", { class: "shimmer", text: "Thinking..." })]);
    s.body.appendChild(thinking);
    s.body.appendChild(md);
    scrollEnd(true);
    var reply = "", tokens = 0, failed = false, frame = 0, usage = null;
    function paint() {
      frame = 0;
      if (thinking.parentNode) thinking.parentNode.removeChild(thinking);
      renderMarkdown(md, reply);
      scrollEnd(false);
    }
    setBusy(true);
    state.abort = new AbortController();
    streamPost("/api/chat", { messages: messages }, function (name, data) {
      if (name === "token") {
        tokens += 1; reply += data.text;
        if (!frame) frame = requestAnimationFrame(paint);
        $("meter-text").textContent = "reply so far: about " + tokens + " tokens";
      } else if (name === "done") {
        usage = data.usage;
      } else if (name === "error") {
        failed = true;
        s.node.classList.add("err");
        clear(s.body);
        s.body.textContent = data.message;
        conv.turns.push({ role: "bot", kind: "error", text: data.message });
      }
    }, state.abort.signal).catch(function (e) {
      failed = true;
      var message = e.name === "AbortError" ? "(reply cancelled)" : e.message;
      if (e.name === "AbortError" && reply) { failed = false; return; }
      s.node.classList.add("err");
      clear(s.body);
      s.body.textContent = message;
      conv.turns.push({ role: "bot", kind: "error", text: message });
    }).then(function () {
      if (frame) cancelAnimationFrame(frame);
      if (!failed) {
        if (thinking.parentNode) thinking.parentNode.removeChild(thinking);
        md.classList.remove("caret");
        renderMarkdown(md, reply);
        s.body.appendChild(el("div", { class: "msg-actions" }, [copyButton(function () { return reply; }, "Copy reply")]));
        conv.turns.push({ role: "bot", kind: "chat", text: reply });
        if (usage) { conv.usage = usage; updateMeter(usage); } else if (!reply) resetMeter();
      } else { resetMeter(); if (conv.usage) updateMeter(conv.usage); }
      state.abort = null;
      setBusy(false);
      touch(conv);
      scrollEnd(false);
      $("chat-input").focus({ preventScroll: true });
    });
  }

  // ---------- composer ----------
  function setBusy(on) {
    state.busy = on;
    show($("chat-stop"), on);
    show($("send"), !on);
    updateSend();
  }
  function updateSend() { $("send").disabled = state.busy || !$("chat-input").value.trim(); }
  function sendMessage() {
    if (state.busy) return;
    var input = $("chat-input");
    var text = input.value.trim();
    if (!text) return;
    showNotice($("notice"), "", true);
    input.value = "";
    autosize(input, 192);
    updateSend();
    if (state.doc) sendQa(text); else sendChat(text);
  }
  function renderAttached() {
    var doc = state.doc;
    show($("attached"), !!doc);
    if (doc) {
      $("attached-name").textContent = doc.name;
      $("attached-meta").textContent = doc.pages + " pages" + (doc.indexed ? ", indexed" : "");
    }
    $("chat-input").placeholder = doc ? "Ask about " + doc.name + " (one question per line)" : "Message SENSAI";
    buildMenu();
  }
  function attachDoc(doc) {
    state.doc = doc;
    renderAttached();
    $("chat-input").focus();
  }
  function closeMenu() { show($("plus-menu"), false); $("plus").setAttribute("aria-expanded", "false"); }
  function buildMenu() {
    var box = $("menu-docs");
    clear(box);
    state.docs.forEach(function (d) {
      var sel = state.doc && state.doc.id === d.id;
      var b = el("button", { type: "button", role: "menuitem", class: sel ? "sel" : "" },
        [icon(sel ? "check" : "file"), el("span", { text: d.name + (d.source === "builtin" ? " (demo)" : "") }), el("span", { class: "meta", text: d.pages + " p." })]);
      b.addEventListener("click", function () { closeMenu(); attachDoc(d); });
      box.appendChild(b);
    });
    show($("menu-docs-label"), state.docs.length > 0);
  }
  function loadDocuments(attachId) {
    return apiGet("/api/documents").then(function (data) {
      state.docs = data.documents;
      var keep = attachId || (state.doc && state.doc.id);
      state.doc = state.docs.filter(function (d) { return d.id === keep; })[0] || null;
      renderAttached();
      buildChips();
    });
  }
  function upload(file) {
    if (!file) return;
    showNotice($("notice"), "Checking " + file.name + "...", true);
    fetch("/api/upload?name=" + encodeURIComponent(file.name), { method: "POST", body: file })
      .then(readJson)
      .then(function (data) {
        showNotice($("notice"), data.document.name + " is ready (" + data.document.pages + " pages).", true);
        setTimeout(function () { if ($("notice").classList.contains("info")) showNotice($("notice"), "", true); }, 3500);
        return loadDocuments(data.document.id);
      })
      .catch(function (e) { showNotice($("notice"), "Upload failed: " + e.message, false); })
      .then(function () { $("upload").value = ""; });
  }
  function demoDoc() { return state.docs.filter(function (d) { return d.id === "builtin/demo.pdf"; })[0]; }
  function askDemo(all) {
    var demo = demoDoc();
    if (!demo) { toast("The demo document is not available on this server.", true); return; }
    if (guardBusy()) return;
    var ex = state.examples[demo.id] || {};
    var qs = (all ? ex.questions : ex.quick) || [];
    if (!qs.length) { toast("No example questions for this document.", true); return; }
    state.cur = null;
    renderConv();
    state.doc = demo;
    renderAttached();
    sendQa(qs.join("\n"));
  }
  function buildChips() {
    var box = $("chips");
    clear(box);
    var demo = demoDoc();
    if (demo) {
      var a = el("button", { type: "button", id: "try-demo" }, [icon("file"), "Try the demo PDF"]);
      a.addEventListener("click", function () { askDemo(false); });
      var b = el("button", { type: "button", id: "ask-all" }, [icon("sparkles"), "Ask all 9 demo questions"]);
      b.addEventListener("click", function () { askDemo(true); });
      box.appendChild(a); box.appendChild(b);
    }
    CHAT_CHIPS.forEach(function (text) {
      var chip = el("button", { type: "button" }, [icon("chat"), text]);
      chip.addEventListener("click", function () { if (!state.busy) { state.doc = null; renderAttached(); sendChat(text); } });
      box.appendChild(chip);
    });
  }

  // ---------- side panel (PDF page or answers file) ----------
  function openPanel(title, href) {
    state.lastFocus = document.activeElement;
    $("drawer-title").textContent = title;
    if (href) $("drawer-open").setAttribute("href", href);
    show($("drawer-open"), !!href);
    show($("drawer-backdrop"), true);
    show($("drawer"), true);
    $("drawer-close").focus();
  }
  function openDrawer(url, title) {
    show($("drawer-text"), false); show($("drawer-frame"), true);
    $("drawer-frame").setAttribute("src", url);
    openPanel(title, url);
  }
  function openText(title, text) {
    show($("drawer-frame"), false); show($("drawer-text"), true);
    $("drawer-frame").setAttribute("src", "about:blank");
    $("drawer-text").textContent = text;
    openPanel(title, null);
  }
  function closeDrawer() {
    if ($("drawer").hidden) return;
    show($("drawer"), false);
    show($("drawer-backdrop"), false);
    $("drawer-frame").setAttribute("src", "about:blank");
    if (state.lastFocus && state.lastFocus.focus) state.lastFocus.focus();
  }

  // ---------- settings dialog ----------
  function openSettings() {
    state.lastFocus = document.activeElement;
    buildSettings();
    show($("settings-modal"), true);
    $("settings-close").focus();
  }
  function closeSettings() {
    if ($("settings-modal").hidden) return;
    show($("settings-modal"), false);
    if (state.lastFocus && state.lastFocus.focus) state.lastFocus.focus();
  }
  function buildSettings() {
    var s = state.status;
    var form = $("settings-form");
    clear(form);
    if (!s) return;
    SETTING_GROUPS.forEach(function (group) {
      var keys = group.keys.filter(function (k) { return s.editable[k]; });
      if (!keys.length) return;
      var box = el("div", { class: "group" }, [el("h3", { text: group.title })]);
      keys.forEach(function (key) {
        var rule = s.editable[key], input, help = group.help[key] || "";
        if (rule[0] === "int") {
          input = el("input", { type: "number", id: "set-" + key, min: rule[1], max: rule[2], step: "1" });
          help += " (" + fmtInt(rule[1]) + " to " + fmtInt(rule[2]) + ")";
        } else {
          input = el("input", { type: "text", id: "set-" + key, list: "model-list", spellcheck: "false" });
        }
        input.value = s.config[key];
        box.appendChild(el("div", { class: "field" }, [
          el("div", {}, [el("label", { for: "set-" + key, text: SETTING_LABELS[key] || key }), el("div", { class: "help", text: help })]), input]));
      });
      form.appendChild(box);
    });
    if (s.editable.feature_flags) {
      var flags = s.config.feature_flags || {};
      var fbox = el("div", { class: "group" }, [el("h3", { text: "Features" })]);
      FEATURE_FLAGS.forEach(function (f) {
        var input = el("input", { type: "checkbox", id: "flag-" + f[0] });
        input.checked = flags[f[0]] !== false;
        fbox.appendChild(el("div", { class: "field" }, [
          el("div", {}, [el("label", { for: "flag-" + f[0], text: f[1] }), el("div", { class: "help", text: f[2] })]), input]));
      });
      form.appendChild(fbox);
    }
  }
  function applySettings() {
    var s = state.status, overrides = {};
    if (s.editable.feature_flags && $("flag-" + FEATURE_FLAGS[0][0])) {
      var current = s.config.feature_flags || {}, next = {}, changedFlag = false;
      FEATURE_FLAGS.forEach(function (f) {
        next[f[0]] = $("flag-" + f[0]).checked;
        if (next[f[0]] !== (current[f[0]] !== false)) changedFlag = true;
      });
      if (changedFlag) overrides.feature_flags = next;
    }
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
      showNotice($("settings-msg"), "Applied." + (stale ? " The index will be rebuilt on the next question about a PDF." : ""), true);
      toast("Settings applied");
      return refreshStatus().then(buildSettings);
    }).catch(function (e) { showNotice($("settings-msg"), e.message, false); });
  }
  function resetSettings() {
    apiPost("/api/config", { reset: true }).then(function () {
      toast("Settings reset");
      return refreshStatus().then(buildSettings);
    }).then(function () {
      // Only say so once the fields show the default values again.
      showNotice($("settings-msg"), "Back to the values of config.json.", true);
    }).catch(function (e) { showNotice($("settings-msg"), e.message, false); });
  }

  // ---------- wiring ----------
  function init() {
    applyIcons(document);
    if (location.protocol === "file:") {
      show($("needs-server"), true);
      show($("main"), false);
      setPill("bad", "Server not running");
      $("theme").addEventListener("click", toggleTheme);
      return;
    }
    state.convs = loadConvs();
    renderHistory();
    renderConv();
    $("theme").addEventListener("click", toggleTheme);
    $("side-open").addEventListener("click", openSidebar);
    $("side-close").addEventListener("click", closeSidebar);
    $("scrim").addEventListener("click", function () { $("app").classList.remove("side-open"); });
    $("new-chat").addEventListener("click", newConversation);
    $("try-demo-side").addEventListener("click", function () { askDemo(false); if (isMobile()) $("app").classList.remove("side-open"); });
    $("open-settings").addEventListener("click", openSettings);
    $("status-pill").addEventListener("click", openSettings);
    $("settings-close").addEventListener("click", closeSettings);
    $("settings-modal").addEventListener("mousedown", function (e) { if (e.target === $("settings-modal")) closeSettings(); });
    $("settings-apply").addEventListener("click", applySettings);
    $("settings-reset").addEventListener("click", resetSettings);

    var input = $("chat-input");
    $("composer").addEventListener("submit", function (e) { e.preventDefault(); sendMessage(); });
    input.addEventListener("input", function () { autosize(input, 192); updateSend(); });
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); sendMessage(); }
    });
    $("chat-stop").addEventListener("click", function () { if (state.abort) state.abort.abort(); });
    $("plus").addEventListener("click", function (e) {
      e.stopPropagation();
      var open = $("plus-menu").hidden;
      show($("plus-menu"), open);
      $("plus").setAttribute("aria-expanded", open ? "true" : "false");
    });
    $("menu-upload").addEventListener("click", function () { closeMenu(); $("upload").click(); });
    $("upload").addEventListener("change", function () { upload($("upload").files[0]); });
    $("detach").addEventListener("click", function () { state.doc = null; renderAttached(); input.focus(); });
    document.addEventListener("click", function (e) { if (!$("plus-menu").hidden && !$("plus-menu").contains(e.target)) closeMenu(); });

    // drag and drop anywhere on the page
    var depth = 0;
    function hasFiles(e) { return e.dataTransfer && Array.prototype.indexOf.call(e.dataTransfer.types || [], "Files") >= 0; }
    window.addEventListener("dragenter", function (e) { if (hasFiles(e)) { e.preventDefault(); depth += 1; show($("drop-veil"), true); } });
    window.addEventListener("dragover", function (e) { if (hasFiles(e)) e.preventDefault(); });
    window.addEventListener("dragleave", function (e) { if (hasFiles(e)) { depth = Math.max(0, depth - 1); if (!depth) show($("drop-veil"), false); } });
    window.addEventListener("drop", function (e) {
      if (!hasFiles(e)) return;
      e.preventDefault(); depth = 0; show($("drop-veil"), false);
      if (e.dataTransfer.files.length) upload(e.dataTransfer.files[0]);
    });

    $("chat-body").addEventListener("scroll", updateJump, { passive: true });
    $("jump-btn").addEventListener("click", function () { $("chat-body").scrollTo({ top: $("chat-body").scrollHeight, behavior: reduceMotion ? "auto" : "smooth" }); });
    $("drawer-close").addEventListener("click", closeDrawer);
    $("drawer-backdrop").addEventListener("click", closeDrawer);
    document.addEventListener("keydown", function (e) {
      if (e.key !== "Escape") return;
      if (!$("settings-modal").hidden) closeSettings();
      else if (!$("plus-menu").hidden) { closeMenu(); $("plus").focus(); }
      else if (!$("drawer").hidden) closeDrawer();
      else if ($("app").classList.contains("side-open")) $("app").classList.remove("side-open");
    });

    refreshStatus().then(function () {
      return apiGet("/api/examples").catch(function () { return {}; });
    }).then(function (ex) {
      state.examples = ex || {};
      return loadDocuments();
    });
    setInterval(function () { if (!state.busy) refreshStatus(); }, 15000);
    input.focus();
  }
  document.addEventListener("DOMContentLoaded", init);
})();
