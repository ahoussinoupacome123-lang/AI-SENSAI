/* Defense kit: theme toggle, top navigation, table of contents with scroll spy. */
(function () {
  "use strict";
  var root = document.documentElement;
  function get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* private mode: ignore */ } }

  var saved = get("defense-theme");
  if (saved === "light" || saved === "dark") root.setAttribute("data-theme", saved);

  var PAGES = [["index.html", "Start here"], ["guide.html", "Study guide"], ["files.html", "Every file"], ["quiz.html", "Quiz"]];
  var here = location.pathname.split("/").pop() || "index.html";
  var bar = document.getElementById("bar");
  if (bar) {
    var html = '<div class="bar-in"><a class="brand" href="index.html">SENSAI &middot; defense kit</a>';
    PAGES.forEach(function (p) { html += '<a class="nav' + (p[0] === here ? " on" : "") + '" href="' + p[0] + '">' + p[1] + "</a>"; });
    html += '<span class="sp"></span><button class="tbtn" id="theme" type="button">Dark / light</button></div>';
    bar.innerHTML = html;
    document.getElementById("theme").addEventListener("click", function () {
      var dark = root.getAttribute("data-theme") === "dark" ||
        (!root.getAttribute("data-theme") && matchMedia("(prefers-color-scheme: dark)").matches);
      var next = dark ? "light" : "dark";
      root.setAttribute("data-theme", next); set("defense-theme", next);
    });
  }

  // Table of contents: every <h2 id data-toc="Short name"> becomes a link; data-group starts a group.
  var toc = document.getElementById("toc");
  if (toc) {
    var heads = Array.prototype.slice.call(document.querySelectorAll("main h2[id]"));
    var out = "";
    heads.forEach(function (h) {
      if (h.dataset.group) out += '<div class="grp">' + h.dataset.group + "</div>";
      out += '<a href="#' + h.id + '">' + (h.dataset.toc || h.textContent) + "</a>";
    });
    toc.innerHTML = out;
    var links = Array.prototype.slice.call(toc.querySelectorAll("a"));
    var spy = function () {
      var current = heads[0], y = window.scrollY + 110;
      heads.forEach(function (h) { if (h.getBoundingClientRect().top + window.scrollY <= y) current = h; });
      links.forEach(function (a) { a.classList.toggle("on", !!current && a.getAttribute("href") === "#" + current.id); });
    };
    window.addEventListener("scroll", spy, { passive: true }); spy();
  }

  // "Open all / Close all" buttons for the collapsible cards.
  document.querySelectorAll("[data-toggle-all]").forEach(function (b) {
    b.addEventListener("click", function () {
      var open = b.dataset.state !== "open";
      document.querySelectorAll("details").forEach(function (d) { d.open = open; });
      b.dataset.state = open ? "open" : "closed";
      b.textContent = open ? "Close all" : "Open all";
    });
  });
})();
