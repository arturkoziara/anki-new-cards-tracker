/* New Cards Tracker — year of squares, same shape as Review Heatmap */
(function () {
  "use strict";

  function $(sel, root) {
    return (root || document).querySelector(sel);
  }

  function readData() {
    var el = $("#ncat-data");
    if (!el) return null;
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      return null;
    }
  }

  function pycmd(cmd) {
    if (typeof window.pycmd === "function") {
      window.pycmd(cmd);
    }
  }

  function bindControls(root) {
    root.querySelectorAll("[data-ncat]").forEach(function (btn) {
      btn.addEventListener("click", function (ev) {
        ev.preventDefault();
        if (btn.disabled) return;
        var action = btn.getAttribute("data-ncat");
        if (action) pycmd("ncat:" + action);
      });
    });
  }

  function tone(day, target) {
    if (day.isFuture) return "is-future";
    if (!day.count) return "is-none";
    if (day.count >= target) return "is-met";
    return "is-under";
  }

  function weeksOf(days) {
    var cells = [];
    if (days.length) {
      var lead = days[0].weekday; // Monday = 0
      for (var i = 0; i < lead; i++) cells.push(null);
    }
    days.forEach(function (day) {
      cells.push(day);
    });
    var columns = [];
    for (var c = 0; c < cells.length; c += 7) {
      var col = cells.slice(c, c + 7);
      while (col.length < 7) col.push(null);
      columns.push(col);
    }
    return columns;
  }

  function formatDate(iso) {
    var parts = iso.split("-");
    var d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
    return d.toLocaleDateString(undefined, {
      weekday: "short",
      month: "short",
      day: "numeric",
    });
  }

  function renderGrid(root, data) {
    var grid = $("#ncat-grid", root);
    if (!grid) return;
    var target = data.dailyTarget || 10;
    grid.textContent = "";

    var tip = document.createElement("div");
    tip.className = "ncat-tooltip";
    tip.style.display = "none";
    root.appendChild(tip);

    weeksOf(data.days || []).forEach(function (week) {
      var col = document.createElement("div");
      col.className = "ncat-week";
      week.forEach(function (day) {
        var cell = document.createElement("div");
        cell.className = "ncat-cell";
        if (!day) {
          cell.style.visibility = "hidden";
          cell.tabIndex = -1;
          col.appendChild(cell);
          return;
        }
        cell.classList.add(tone(day, target));
        cell.setAttribute("aria-label", day.isoDate + ", " + day.count + " cards");
        if (day.isToday) cell.classList.add("is-today");
        if (!day.isFuture) {
          cell.classList.add("is-past");
          cell.setAttribute("role", "button");
          cell.addEventListener("click", function () {
            pycmd("ncat:browse:" + day.isoDate);
          });
          cell.addEventListener("mouseenter", function (ev) {
            var noun = day.count === 1 ? "card" : "cards";
            var status = !day.count
              ? "none added"
              : day.count >= target
                ? "on target"
                : "under target";
            tip.textContent =
              day.count + " " + noun + " on " + formatDate(day.isoDate) + " (" + status + ")";
            var rect = cell.getBoundingClientRect();
            var host = root.getBoundingClientRect();
            tip.style.left = rect.left - host.left + rect.width / 2 + "px";
            tip.style.top = rect.top - host.top + "px";
            tip.style.display = "block";
          });
          cell.addEventListener("mouseleave", function () {
            tip.style.display = "none";
          });
        } else {
          cell.tabIndex = -1;
        }
        col.appendChild(cell);
      });
      grid.appendChild(col);
    });
  }

  function init() {
    var root = $("#ncat-root");
    if (!root) return;
    var data = readData();
    if (!data) return;
    bindControls(root);
    renderGrid(root, data);
  }

  function boot() {
    if ($("#ncat-root") && !$("#ncat-root").dataset.ncatReady) {
      $("#ncat-root").dataset.ncatReady = "1";
      init();
      return;
    }
    var tries = 0;
    var t = setInterval(function () {
      tries += 1;
      var root = $("#ncat-root");
      if (root && !root.dataset.ncatReady) {
        root.dataset.ncatReady = "1";
        clearInterval(t);
        init();
      } else if (tries > 40) {
        clearInterval(t);
      }
    }, 50);
  }

  window.ncatBoot = boot;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
