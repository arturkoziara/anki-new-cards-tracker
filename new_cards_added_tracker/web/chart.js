/* New Cards Tracker — lightweight canvas bar chart (no CDN) */
(function () {
  "use strict";

  var COLOR_MET = "#2da44e";
  var COLOR_UNDER = "#d4a72c";
  var COLOR_TODAY_STROKE = "#0969da";

  function isNightMode() {
    var b = document.body;
    if (!b) return false;
    return (
      b.classList.contains("nightMode") ||
      b.classList.contains("night-mode") ||
      b.classList.contains("night_mode")
    );
  }

  function themeColors() {
    if (isNightMode()) {
      return {
        grid: "rgba(255,255,255,0.22)",
        label: "rgba(220,220,220,0.85)",
        todayStroke: "#6cb6ff",
      };
    }
    return {
      grid: "rgba(80,80,80,0.28)",
      label: "rgba(60,60,60,0.85)",
      todayStroke: COLOR_TODAY_STROKE,
    };
  }

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

  function layout(canvas, days) {
    var dpr = window.devicePixelRatio || 1;
    var cssW = canvas.clientWidth || 600;
    var cssH = canvas.clientHeight || 200;
    canvas.width = Math.floor(cssW * dpr);
    canvas.height = Math.floor(cssH * dpr);
    var ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    var pad = { top: 28, right: 12, bottom: 42, left: 36 };
    var plotW = cssW - pad.left - pad.right;
    var plotH = cssH - pad.top - pad.bottom;
    var n = Math.max(days.length, 1);
    var gap = Math.min(12, Math.max(6, plotW / n / 3.5));
    var barW = Math.max(6, (plotW - gap * (n - 1)) / n);

    return { ctx: ctx, cssW: cssW, cssH: cssH, pad: pad, plotW: plotW, plotH: plotH, barW: barW, gap: gap };
  }

  function draw(canvas, data, tooltip) {
    var days = data.days || [];
    var target = data.dailyTarget || 10;
    var colors = themeColors();
    var L = layout(canvas, days);
    var ctx = L.ctx;
    ctx.clearRect(0, 0, L.cssW, L.cssH);

    var maxCount = target;
    days.forEach(function (d) {
      if (d.count > maxCount) maxCount = d.count;
    });
    maxCount = Math.max(maxCount, 1);
    // headroom so count labels clear the plot top
    var yMax = maxCount * 1.28;

    // target line
    var targetY = L.pad.top + L.plotH * (1 - target / yMax);
    ctx.save();
    ctx.strokeStyle = colors.grid;
    ctx.setLineDash([4, 3]);
    ctx.beginPath();
    ctx.moveTo(L.pad.left, targetY);
    ctx.lineTo(L.pad.left + L.plotW, targetY);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = colors.label;
    ctx.font = "11px system-ui, sans-serif";
    ctx.textAlign = "left";
    ctx.fillText("target " + target, L.pad.left + 2, Math.max(12, targetY - 8));
    ctx.restore();

    var hitBoxes = [];

    days.forEach(function (day, i) {
      var x = L.pad.left + i * (L.barW + L.gap);
      var h = (day.count / yMax) * L.plotH;
      // zero days: tiny stub so the day is clickable
      var drawH = day.count === 0 ? 3 : Math.max(h, 3);
      var y = L.pad.top + L.plotH - drawH;

      ctx.fillStyle = day.met ? COLOR_MET : COLOR_UNDER;
      // slightly rounded look via clip isn't needed; keep simple rects
      ctx.fillRect(x, y, L.barW, drawH);

      if (day.isToday) {
        ctx.strokeStyle = colors.todayStroke;
        ctx.lineWidth = 2;
        ctx.strokeRect(x + 0.5, y + 0.5, L.barW - 1, drawH - 1);
      }

      // count above bar
      ctx.fillStyle = colors.label;
      ctx.font = "11px system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(String(day.count), x + L.barW / 2, y - 8);

      // x label
      ctx.save();
      ctx.translate(x + L.barW / 2, L.pad.top + L.plotH + 16);
      var label = day.label;
      if (days.length > 14) {
        // month view: show day number only for readability
        var parts = label.split(" ");
        label = parts[parts.length - 1];
      }
      ctx.fillText(label, 0, 0);
      ctx.restore();

      hitBoxes.push({
        x: x,
        y: L.pad.top,
        w: L.barW,
        h: L.plotH,
        day: day,
      });
    });

    canvas._ncatHits = hitBoxes;

    function findHit(clientX, clientY) {
      var rect = canvas.getBoundingClientRect();
      var x = clientX - rect.left;
      var y = clientY - rect.top;
      for (var i = 0; i < hitBoxes.length; i++) {
        var b = hitBoxes[i];
        if (x >= b.x && x <= b.x + b.w && y >= b.y && y <= b.y + b.h) {
          return b;
        }
      }
      return null;
    }

    canvas.onmousemove = function (ev) {
      var hit = findHit(ev.clientX, ev.clientY);
      if (!hit || !tooltip) {
        if (tooltip) tooltip.classList.remove("is-visible");
        return;
      }
      var day = hit.day;
      var status = day.met
        ? "target met"
        : "under by " + Math.max(0, target - day.count);
      tooltip.textContent =
        day.isoDate + " — " + day.count + " card" + (day.count === 1 ? "" : "s") + " (" + status + ")";
      var rect = canvas.getBoundingClientRect();
      var wrap = canvas.parentElement;
      var wrapRect = wrap.getBoundingClientRect();
      tooltip.style.left = ev.clientX - wrapRect.left + "px";
      tooltip.style.top = ev.clientY - wrapRect.top + "px";
      tooltip.classList.add("is-visible");
    };

    canvas.onmouseleave = function () {
      if (tooltip) tooltip.classList.remove("is-visible");
    };

    canvas.onclick = function (ev) {
      var hit = findHit(ev.clientX, ev.clientY);
      if (hit) pycmd("ncat:browse:" + hit.day.isoDate);
    };
  }

  function init() {
    var root = $("#ncat-root");
    if (!root) return;
    var data = readData();
    if (!data) return;

    bindControls(root);

    var canvas = $("#ncat-chart", root);
    if (!canvas) return;

    var wrap = $(".ncat-chart-wrap", root);
    var tooltip = document.createElement("div");
    tooltip.className = "ncat-tooltip";
    wrap.appendChild(tooltip);

    function redraw() {
      draw(canvas, data, tooltip);
    }
    redraw();
    window.addEventListener("resize", redraw);
  }

  // Deck browser may inject HTML after scripts load; retry briefly
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
