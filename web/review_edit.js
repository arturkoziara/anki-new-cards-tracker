/* Click a piece of card text while reviewing and edit that field in place. */
(function () {
  if (window.__ncatEditBound) return;
  window.__ncatEditBound = true;

  function live() {
    return window.NCAT_EDIT || { note: 0, side: "", fields: [] };
  }

  var style = document.createElement("style");
  style.textContent = [
    ".ncat-hot { outline: 1px dashed rgba(122,162,255,.9); outline-offset: 3px; border-radius: 4px; cursor: text; }",
    ".ncat-editing { outline: 1px solid #7aa2ff; outline-offset: 3px; border-radius: 4px; background: rgba(122,162,255,.14); cursor: text; }",
    ".ncat-saved { outline: 1px solid #3fb950; outline-offset: 3px; border-radius: 4px; }"
  ].join("\n");
  document.head.appendChild(style);

  var hot = null;

  function norm(s) {
    return (s || "").replace(/\u00a0/g, " ").replace(/\s+/g, " ").trim();
  }

  function interactive(el) {
    return !!(el && el.closest && el.closest("a, button, audio, video, iframe, input, textarea, .yt-box, .yt-restart, .play"));
  }

  function matchField(el) {
    if (!el || el.nodeType !== 1) return null;
    if (interactive(el)) return null;
    if (el.querySelector && el.querySelector("iframe, audio, video, button, a")) return null;
    var t = norm(el.innerText);
    if (!t) return null;
    var pool = live().fields || [];
    var hinted = el.closest && el.closest("[data-edit]");
    if (hinted) {
      var name = hinted.getAttribute("data-edit");
      var scoped = pool.filter(function (f) { return f.name === name; });
      if (scoped.length) pool = scoped;
    }
    var exact = pool.filter(function (f) { return norm(f.value) === t || norm(f.plain) === t; });
    if (exact.length === 1) {
      var hit = exact[0];
      if (hit.value.indexOf("<") !== -1 && norm(hit.value) !== t) {
        if (hit.value.indexOf(t) === -1) return null;
        return { field: hit, old: t, whole: false, showRaw: false };
      }
      return { field: hit, old: hit.value, whole: true, showRaw: false };
    }
    var parts = pool.filter(function (f) { return f.value.indexOf(t) !== -1; });
    if (parts.length === 1) {
      return { field: parts[0], old: t, whole: norm(parts[0].value) === t, showRaw: false };
    }
    return null;
  }

  function rawFallback(node) {
    if (!/Answer$/.test(live().side || "")) return null;
    var root = node.closest && node.closest("[data-edit]");
    if (!root || interactive(root)) return null;
    if (root.querySelector && root.querySelector("iframe, audio, video, button")) return null;
    var name = root.getAttribute("data-edit");
    var field = null;
    (live().fields || []).forEach(function (f) { if (f.name === name) field = f; });
    if (!field || field.value.indexOf("<") !== -1) return null;
    return { el: root, m: { field: field, old: field.value, whole: true, showRaw: norm(root.innerText) !== norm(field.value) } };
  }

  function locate(node) {
    if (!node || interactive(node)) return null;
    var el = node.nodeType === 1 ? node : node.parentElement;
    while (el && el !== document.body && el !== document.documentElement) {
      var m = matchField(el);
      if (m) return { el: el, m: m };
      el = el.parentElement;
    }
    return rawFallback(node.nodeType === 1 ? node : node.parentElement);
  }

  function clearHot() {
    if (hot) {
      hot.classList.remove("ncat-hot");
      hot = null;
    }
  }

  function send(field, old, now, whole) {
    var msg = "ncat:setfield:" + JSON.stringify({
      note: live().note,
      field: field,
      old: old,
      value: now,
      whole: !!whole
    });
    if (typeof pycmd === "function") pycmd(msg);
    else if (typeof bridgeCommand === "function") bridgeCommand(msg);
  }

  function finish(el, cancel) {
    if (!el || el.getAttribute("contenteditable") !== "true") return;
    var old = el.getAttribute("data-ncat-old") || "";
    var field = el.getAttribute("data-ncat-field") || "";
    var whole = el.getAttribute("data-ncat-whole") === "1";
    var html = el.getAttribute("data-ncat-html");
    el.removeAttribute("contenteditable");
    el.classList.remove("ncat-editing");
    if (cancel) {
      if (html != null) el.innerHTML = html;
      el.removeAttribute("data-ncat-html");
      return;
    }
    var now = norm(el.innerText);
    el.removeAttribute("data-ncat-html");
    if (!field || now === norm(old)) return;
    send(field, old, now, whole);
    var stored = null;
    (live().fields || []).forEach(function (f) { if (f.name === field) stored = f; });
    if (stored) {
      if (whole && stored.value === old) stored.value = now;
      else if (stored.value.indexOf(old) !== -1) stored.value = stored.value.replace(old, now);
      stored.plain = norm(stored.value.replace(/<[^>]+>/g, " "));
    }
    el.classList.add("ncat-saved");
    setTimeout(function () { el.classList.remove("ncat-saved"); }, 700);
  }

  function placeCaret(el, x, y) {
    var range = null;
    if (document.caretRangeFromPoint) range = document.caretRangeFromPoint(x, y);
    if (!range && document.caretPositionFromPoint) {
      var pos = document.caretPositionFromPoint(x, y);
      if (pos) {
        range = document.createRange();
        range.setStart(pos.offsetNode, pos.offset);
        range.collapse(true);
      }
    }
    if (!range) return;
    var sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
  }

  function begin(found, x, y) {
    var el = found.el;
    var m = found.m;
    if (el.getAttribute("contenteditable") === "true") return;
    var open = document.querySelector("[contenteditable='true']");
    if (open && open !== el) finish(open, false);
    el.setAttribute("data-ncat-html", el.innerHTML);
    el.setAttribute("data-ncat-old", m.old);
    el.setAttribute("data-ncat-field", m.field.name);
    el.setAttribute("data-ncat-whole", m.whole ? "1" : "0");
    el.contentEditable = "true";
    el.classList.add("ncat-editing");
    clearHot();
    if (m.showRaw) el.textContent = m.field.value;
    el.focus();
    if (m.showRaw) {
      var sel = window.getSelection();
      var range = document.createRange();
      range.selectNodeContents(el);
      sel.removeAllRanges();
      sel.addRange(range);
    } else {
      placeCaret(el, x, y);
    }
  }

  document.addEventListener("mouseover", function (ev) {
    var open = document.querySelector("[contenteditable='true']");
    if (open) return;
    var found = locate(ev.target);
    var next = found ? found.el : null;
    if (next === hot) return;
    clearHot();
    if (next) {
      next.classList.add("ncat-hot");
      hot = next;
    }
  });

  document.addEventListener("mouseout", function (ev) {
    if (!hot) return;
    if (ev.relatedTarget && hot.contains(ev.relatedTarget)) return;
    clearHot();
  });

  document.addEventListener("click", function (ev) {
    if (ev.button !== 0 || ev.shiftKey || ev.metaKey || ev.ctrlKey || ev.altKey) return;
    var sel = window.getSelection();
    if (sel && !sel.isCollapsed && norm(sel.toString())) return;
    var found = locate(ev.target);
    if (!found) return;
    if (found.el.getAttribute("contenteditable") === "true") return;
    ev.preventDefault();
    begin(found, ev.clientX, ev.clientY);
  });

  document.addEventListener("keydown", function (ev) {
    var el = ev.target && ev.target.getAttribute && ev.target.getAttribute("contenteditable") === "true"
      ? ev.target
      : document.activeElement;
    if (!el || !el.getAttribute || el.getAttribute("contenteditable") !== "true") return;
    ev.stopPropagation();
    if (ev.key === "Escape") {
      ev.preventDefault();
      finish(el, true);
      return;
    }
    if (ev.key === "Enter" && !ev.shiftKey) {
      ev.preventDefault();
      finish(el, false);
    }
  }, true);

  document.addEventListener("focusout", function (ev) {
    var el = ev.target;
    if (!el || el.getAttribute && el.getAttribute("contenteditable") !== "true") return;
    setTimeout(function () {
      if (document.activeElement === el) return;
      finish(el, false);
    }, 0);
  });
})();
