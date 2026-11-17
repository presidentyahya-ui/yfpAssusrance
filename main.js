/* ==========================================================================
   YFP Assurance — Site behaviour
   Navigation, configuration binding, inquiry forms, WhatsApp, analytics hooks.
   You normally do NOT need to edit this file. Settings live in js/config.js.
   ========================================================================== */
(function () {
  "use strict";

  var CFG = window.YFP_CONFIG || {};
  var doc = document;
  doc.documentElement.classList.remove("no-js");

  /* ---------- Helpers ---------- */
  function get(path) {
    return path.split(".").reduce(function (o, k) { return o && o[k] !== undefined ? o[k] : undefined; }, CFG);
  }
  function has(path) { var v = get(path); return v !== undefined && v !== null && v !== "" && v !== false; }
  function $(sel, root) { return (root || doc).querySelector(sel); }
  function $all(sel, root) { return Array.prototype.slice.call((root || doc).querySelectorAll(sel)); }
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }

  var contact = CFG.contact || {};
  function waLink(text) {
    if (!contact.whatsapp) return "";
    return "https://wa.me/" + String(contact.whatsapp).replace(/\D/g, "") + "?text=" + encodeURIComponent(text || contact.whatsappGreeting || "");
  }
  function mailLink(subject, body) {
    if (!contact.email) return "";
    return "mailto:" + contact.email + "?subject=" + encodeURIComponent(subject || "") + "&body=" + encodeURIComponent(body || "");
  }

  /* ---------- Analytics hook ----------
     Call window.yfpTrack("event_name", { key: "value" }) from anywhere.
     Forwards to Plausible / GA4 / dataLayer if present, and always fires a
     DOM event "yfp:track" that any future integration can listen for. */
  window.dataLayer = window.dataLayer || [];
  window.yfpTrack = function (name, props) {
    props = props || {};
    try {
      if (typeof window.plausible === "function") window.plausible(name, { props: props });
      if (typeof window.gtag === "function") window.gtag("event", name, props);
      window.dataLayer.push(Object.assign({ event: name }, props));
      doc.dispatchEvent(new CustomEvent("yfp:track", { detail: { name: name, props: props } }));
    } catch (e) { /* never break the page for analytics */ }
  };
  (function loadAnalytics() {
    var a = CFG.analytics || {};
    function add(src, attrs) {
      var s = doc.createElement("script"); s.defer = true; s.src = src;
      Object.keys(attrs || {}).forEach(function (k) { s.setAttribute(k, attrs[k]); });
      doc.head.appendChild(s);
    }
    if (a.plausibleDomain) add("https://plausible.io/js/script.js", { "data-domain": a.plausibleDomain });
    if (a.gaMeasurementId) {
      add("https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(a.gaMeasurementId));
      window.gtag = function () { window.dataLayer.push(arguments); };
      window.gtag("js", new Date()); window.gtag("config", a.gaMeasurementId);
    }
    if (a.cloudflareToken) add("https://static.cloudflareinsights.com/beacon.min.js", { "data-cf-beacon": JSON.stringify({ token: a.cloudflareToken }) });
  })();

  /* ---------- Bind configuration to the page ---------- */
  function bindConfig() {
    // Show elements only when a config value exists: data-cfg-show="contact.email"
    $all("[data-cfg-show]").forEach(function (el) {
      var ok = el.getAttribute("data-cfg-show").split("|").some(has);
      el.hidden = !ok;
    });
    // Show elements only when NOTHING in the list is configured: data-cfg-empty="contact.email|contact.phone"
    $all("[data-cfg-empty]").forEach(function (el) {
      var any = el.getAttribute("data-cfg-empty").split("|").some(has);
      el.hidden = any;
    });
    $all("[data-cfg-text]").forEach(function (el) {
      var v = get(el.getAttribute("data-cfg-text"));
      if (v) el.textContent = v;
    });
    $all("[data-cfg-href]").forEach(function (el) {
      var t = el.getAttribute("data-cfg-href"), href = "";
      if (t === "email") href = contact.email ? "mailto:" + contact.email : "";
      else if (t === "phone") href = (contact.phoneHref || contact.phone) ? "tel:" + String(contact.phoneHref || contact.phone).replace(/[^\d+]/g, "") : "";
      else if (t === "whatsapp") href = waLink(el.getAttribute("data-wa-text") || contact.whatsappGreeting);
      else href = get(t) || "";
      if (href) el.setAttribute("href", href);
    });

    // Prices
    var pricing = CFG.pricing || {};
    $all("[data-price]").forEach(function (el) {
      var p = pricing[el.getAttribute("data-price")];
      if (p && p.amount !== undefined) el.textContent = (p.currency || "AED") + " " + p.amount;
    });
    $all("[data-price-block]").forEach(function (el) {
      var p = pricing[el.getAttribute("data-price-block")];
      el.hidden = !(p && p.show);
    });
    $all("[data-price-unit]").forEach(function (el) {
      var p = pricing[el.getAttribute("data-price-unit")];
      if (p && p.unit) el.textContent = p.unit;
    });

    // Digital CV ordering state
    var cv = pricing.digitalCv || {};
    var open = !!(cv.ordersOpen && cv.orderUrl);
    $all("[data-cv-status]").forEach(function (el) { el.textContent = open ? "Available now" : "Orders opening soon"; });
    $all("[data-cv-open]").forEach(function (el) { el.hidden = !open; });
    $all("[data-cv-closed]").forEach(function (el) { el.hidden = open; });
    $all("[data-cv-button]").forEach(function (el) {
      if (open) { el.setAttribute("href", cv.orderUrl); el.removeAttribute("data-prefill-value"); }
    });

    // Footer year
    $all("[data-year]").forEach(function (el) { el.textContent = new Date().getFullYear(); });
  }

  /* ---------- Header & navigation ---------- */
  function initNav() {
    var header = $(".site-header");
    var toggle = $(".menu-toggle");
    var panel = $("#mobile-nav");
    function onScroll() { if (header) header.classList.toggle("scrolled", window.scrollY > 8); }
    window.addEventListener("scroll", onScroll, { passive: true }); onScroll();

    if (!toggle || !panel) return;
    function setOpen(open) {
      toggle.setAttribute("aria-expanded", String(open));
      toggle.querySelector(".label").textContent = open ? "Close" : "Menu";
      panel.classList.toggle("open", open);
      panel.setAttribute("aria-hidden", String(!open));
      if ("inert" in panel) panel.inert = !open;
      doc.body.classList.toggle("nav-open", open);
      if (open) { var f = panel.querySelector("a"); if (f) f.focus(); }
    }
    if ("inert" in panel) panel.inert = true;
    toggle.addEventListener("click", function () { setOpen(toggle.getAttribute("aria-expanded") !== "true"); });
    panel.addEventListener("click", function (e) { if (e.target.closest("a")) setOpen(false); });
    doc.addEventListener("keydown", function (e) { if (e.key === "Escape" && panel.classList.contains("open")) { setOpen(false); toggle.focus(); } });
    window.addEventListener("resize", function () { if (window.innerWidth >= 1140) setOpen(false); });
  }

  /* ---------- WhatsApp floating button ---------- */
  var WA_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true" fill="currentColor"><path d="M12.04 2C6.58 2 2.13 6.45 2.13 11.91c0 1.75.46 3.45 1.32 4.95L2.05 22l5.25-1.38a9.9 9.9 0 0 0 4.74 1.21h.01c5.46 0 9.91-4.45 9.91-9.91A9.85 9.85 0 0 0 12.04 2Zm0 18.15h-.01a8.23 8.23 0 0 1-4.2-1.15l-.3-.18-3.12.82.83-3.04-.2-.31a8.2 8.2 0 0 1-1.26-4.38c0-4.54 3.7-8.24 8.25-8.24a8.24 8.24 0 0 1 8.24 8.25c0 4.54-3.7 8.23-8.23 8.23Zm4.52-6.16c-.25-.12-1.47-.72-1.69-.81-.23-.08-.39-.12-.56.13-.16.25-.64.81-.79.97-.14.17-.29.19-.54.06-.25-.12-1.05-.39-1.99-1.23-.74-.66-1.23-1.47-1.38-1.72-.14-.25-.01-.38.11-.51.11-.11.25-.29.37-.43.13-.15.17-.25.25-.42.08-.17.04-.31-.02-.43-.06-.13-.56-1.34-.76-1.84-.2-.48-.41-.42-.56-.43h-.48c-.17 0-.43.06-.66.31-.22.25-.86.85-.86 2.07 0 1.22.89 2.4 1.01 2.56.12.17 1.75 2.67 4.23 3.74.59.26 1.05.41 1.41.52.59.19 1.13.16 1.56.1.48-.07 1.47-.6 1.67-1.18.21-.58.21-1.07.15-1.18-.06-.1-.23-.16-.48-.29Z"/></svg>';
  function initWhatsApp() {
    if (!contact.whatsapp) return;
    var a = doc.createElement("a");
    a.className = "wa-float";
    a.href = waLink(contact.whatsappGreeting);
    a.target = "_blank"; a.rel = "noopener";
    a.setAttribute("aria-label", "Chat with YFP Assurance on WhatsApp");
    a.innerHTML = WA_ICON + '<span class="wa-label">WhatsApp us</span>';
    a.addEventListener("click", function () { window.yfpTrack("whatsapp_click", { location: "floating" }); });
    doc.body.appendChild(a);
    $all("[data-wa-icon]").forEach(function (el) { el.innerHTML = WA_ICON; });
  }

  /* ---------- Reveal on scroll ---------- */
  function initReveal() {
    var els = $all(".reveal");
    if (!("IntersectionObserver" in window)) { els.forEach(function (e) { e.classList.add("in"); }); return; }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); } });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
    els.forEach(function (e) { io.observe(e); });
  }

  /* ---------- Prefill selects from buttons and URL ---------- */
  function setSelect(form, name, value) {
    if (!form || !value) return false;
    var el = form.querySelector('[name="' + name + '"]');
    if (!el) return false;
    if (el.tagName === "SELECT") {
      var match = Array.prototype.find.call(el.options, function (o) { return o.value === value || o.text === value; });
      if (!match) return false;
      el.value = match.value;
    } else { el.value = value; }
    el.dispatchEvent(new Event("change", { bubbles: true }));
    syncTypeButtons(form);
    return true;
  }
  function initPrefill() {
    doc.addEventListener("click", function (e) {
      var btn = e.target.closest("[data-prefill-field]");
      if (!btn) return;
      var href = btn.getAttribute("href") || "";
      var target = href.charAt(0) === "#" ? doc.getElementById(href.slice(1)) : null;
      var form = target ? (target.matches("form") ? target : target.querySelector("form")) : null;
      if (form) setSelect(form, btn.getAttribute("data-prefill-field"), btn.getAttribute("data-prefill-value"));
      window.yfpTrack("cta_click", { cta: btn.textContent.trim(), value: btn.getAttribute("data-prefill-value") || "" });
    });
    // URL parameters, e.g. contact.html?type=Equipment%20sourcing or factory-direct.html?category=Joinery#quote
    var params;
    try { params = new URLSearchParams(window.location.search); } catch (e) { return; }
    $all("form[data-yfp-form]").forEach(function (form) {
      ["type", "category", "service", "equipment_category", "project_category", "inquiry_type"].forEach(function (k) {
        var v = params.get(k); if (!v) return;
        var map = { type: "inquiry_type" };
        setSelect(form, map[k] || k, v) || setSelect(form, "category", v) || setSelect(form, "service", v);
      });
    });
  }

  /* Contact page "inquiry type" tiles */
  function syncTypeButtons(form) {
    var sel = form && form.querySelector('[name="inquiry_type"]');
    if (!sel) return;
    $all(".type-grid button").forEach(function (b) { b.setAttribute("aria-pressed", String(b.getAttribute("data-type") === sel.value)); });
  }
  function initTypeTiles() {
    $all(".type-grid button").forEach(function (b) {
      b.addEventListener("click", function () {
        var form = doc.getElementById(b.closest(".type-grid").getAttribute("data-form"));
        setSelect(form, "inquiry_type", b.getAttribute("data-type"));
        var first = form && form.querySelector('[name="name"]'); if (first) first.focus({ preventScroll: false });
      });
    });
    $all("form[data-yfp-form]").forEach(function (f) {
      var sel = f.querySelector('[name="inquiry_type"]');
      if (sel) { sel.addEventListener("change", function () { syncTypeButtons(f); }); syncTypeButtons(f); }
    });
  }

  /* ---------- Forms ---------- */
  var MSG = {
    valueMissing: "This field is required.",
    typeMismatchEmail: "Please enter a valid email address.",
    patternMismatchPhone: "Please enter a valid phone number, including country code.",
    consent: "Please confirm you agree to be contacted about this inquiry."
  };

  function fieldLabel(el) {
    var id = el.id, lab = id ? doc.querySelector('label[for="' + id + '"]') : null;
    var t = lab ? lab.childNodes[0].textContent : (el.getAttribute("aria-label") || el.name);
    return String(t).replace(/\s+/g, " ").trim();
  }

  function validateField(el) {
    var wrap = el.closest(".field") || el.closest(".full");
    var errEl = wrap ? wrap.querySelector(".error") : null;
    var msg = "";
    var v = (el.value || "").trim();
    if (el.type === "checkbox") { if (el.required && !el.checked) msg = MSG.consent; }
    else if (el.required && !v) msg = MSG.valueMissing;
    else if (v && el.type === "email" && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v)) msg = MSG.typeMismatchEmail;
    else if (v && el.type === "tel" && !/^\+?[\d\s().-]{7,20}$/.test(v)) msg = MSG.patternMismatchPhone;
    if (wrap) wrap.classList.toggle("invalid", !!msg);
    if (errEl) errEl.textContent = msg;
    el.setAttribute("aria-invalid", msg ? "true" : "false");
    return !msg;
  }

  function collect(form) {
    var data = {}, lines = [];
    $all("input, select, textarea", form).forEach(function (el) {
      if (!el.name || el.classList.contains("hp-input") || el.type === "submit") return;
      if (el.type === "checkbox") { data[el.name] = el.checked ? "Yes" : "No"; return; }
      var v = (el.value || "").trim();
      data[el.name] = v;
      if (v) lines.push(fieldLabel(el) + ": " + v);
    });
    data.form = form.getAttribute("data-yfp-form");
    data.page = window.location.href;
    return { data: data, text: lines.join("\n") };
  }

  function subjectFor(form, data) {
    var base = (CFG.forms && CFG.forms.subjectPrefix) || "Website inquiry";
    var topic = data.inquiry_type || data.service || data.category || data.equipment_category || data.project_category || form.getAttribute("data-form-title") || "";
    return base + (topic ? " — " + topic : "") + (data.name ? " (" + data.name + ")" : "");
  }

  function send(form, payload, subject) {
    var f = CFG.forms || {};
    var p = (f.provider || "none").toLowerCase();
    var body = Object.assign({ subject: subject }, payload.data);
    if (p === "web3forms") {
      if (!f.accessKey) return Promise.reject(new Error("not-configured"));
      body.access_key = f.accessKey; body.from_name = "YFP Assurance website";
      return postJSON(f.endpoint || "https://api.web3forms.com/submit", body).then(function (r) {
        return r.json().then(function (j) { if (!r.ok || j.success === false) throw new Error("rejected"); return true; });
      });
    }
    if (p === "formspree" || p === "custom") {
      if (!f.endpoint) return Promise.reject(new Error("not-configured"));
      body._subject = subject;
      return postJSON(f.endpoint, body).then(function (r) { if (!r.ok) throw new Error("rejected"); return true; });
    }
    if (p === "netlify") {
      var fd = new URLSearchParams();
      fd.append("form-name", form.getAttribute("name") || form.getAttribute("data-yfp-form"));
      Object.keys(body).forEach(function (k) { fd.append(k, body[k]); });
      return fetch("/", { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: fd.toString() })
        .then(function (r) { if (!r.ok) throw new Error("rejected"); return true; });
    }
    return Promise.reject(new Error("not-configured"));
  }
  function postJSON(url, body) {
    return fetch(url, { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify(body) });
  }

  function fallbackButtons(subject, text) {
    var html = "", mail = mailLink(subject, text), wa = waLink(subject + "\n\n" + text);
    if (mail) html += '<a class="btn btn-primary btn-sm" href="' + esc(mail) + '" data-fb="email">Send by email</a>';
    if (wa) html += '<a class="btn btn-wa btn-sm" href="' + esc(wa) + '" target="_blank" rel="noopener" data-fb="whatsapp">Send on WhatsApp</a>';
    html += '<button type="button" class="btn btn-ghost btn-sm" data-copy>Copy inquiry text</button>';
    return html;
  }

  function showStatus(box, kind, title, bodyHtml) {
    box.className = "form-status show " + kind;
    box.innerHTML = "<h3>" + esc(title) + "</h3>" + bodyHtml;
    box.setAttribute("tabindex", "-1");
    box.focus({ preventScroll: true });
    box.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function wireStatusActions(box, subject, text, formName) {
    var copyBtn = box.querySelector("[data-copy]");
    var area = box.querySelector("textarea");
    if (copyBtn) copyBtn.addEventListener("click", function () {
      var full = subject + "\n\n" + text;
      function done() { copyBtn.textContent = "Copied"; }
      try {
        navigator.clipboard.writeText(full).then(done, function () { if (area) { area.hidden = false; area.select(); } });
      } catch (e) { if (area) { area.hidden = false; area.select(); } }
    });
    $all("[data-fb]", box).forEach(function (a) {
      a.addEventListener("click", function () { window.yfpTrack("inquiry_fallback_opened", { form: formName, channel: a.getAttribute("data-fb") }); });
    });
  }

  function initForms() {
    $all("form[data-yfp-form]").forEach(function (form) {
      var box = form.querySelector(".form-status") || (function () { var d = doc.createElement("div"); d.className = "form-status"; d.setAttribute("role", "status"); d.setAttribute("aria-live", "polite"); form.appendChild(d); return d; })();
      var btn = form.querySelector('[type="submit"]');
      var formName = form.getAttribute("data-yfp-form");
      var started = false;

      $all("input, select, textarea", form).forEach(function (el) {
        el.addEventListener("blur", function () { if (el.closest(".invalid") || el.value) validateField(el); });
        el.addEventListener("input", function () {
          if (!started) { started = true; window.yfpTrack("form_start", { form: formName }); }
          if (el.closest(".invalid")) validateField(el);
        });
      });

      form.addEventListener("submit", function (e) {
        e.preventDefault();
        var hp = form.querySelector(".hp-input");
        if (hp && hp.value) return; // spam trap: silently ignore

        var fields = $all("input, select, textarea", form).filter(function (el) { return el.name && !el.classList.contains("hp-input"); });
        var firstBad = null;
        fields.forEach(function (el) { if (!validateField(el) && !firstBad) firstBad = el; });
        if (firstBad) { firstBad.focus(); return; }

        var payload = collect(form);
        var subject = subjectFor(form, payload.data);
        var copyArea = '<textarea hidden readonly aria-label="Inquiry text">' + esc(subject + "\n\n" + payload.text) + "</textarea>";
        var f = CFG.forms || {};
        var configured = f.provider && f.provider !== "none";

        if (!configured) {
          var any = contact.email || contact.whatsapp;
          showStatus(box, "pending",
            any ? "Almost done — your inquiry has not been sent yet" : "Online inquiries are not connected yet",
            any
              ? "<p>Choose how you would like to send it. Your details will be prefilled in a new message — please press send in your email or WhatsApp app to complete your inquiry.</p><div class=\"btn-row\">" + fallbackButtons(subject, payload.text) + "</div>" + copyArea
              : "<p>This website is awaiting connection to its inquiry service, so your message <strong>has not been sent</strong>. Please copy your inquiry and keep it until contact details are published on this page.</p><div class=\"btn-row\"><button type=\"button\" class=\"btn btn-ghost btn-sm\" data-copy>Copy inquiry text</button></div>" + copyArea);
          wireStatusActions(box, subject, payload.text, formName);
          window.yfpTrack("inquiry_prepared", { form: formName });
          return;
        }

        btn.disabled = true; var label = btn.innerHTML; btn.innerHTML = "Sending…";
        send(form, payload, subject).then(function () {
          window.yfpTrack("inquiry_submitted", { form: formName });
          if (f.redirectOnSuccess) { window.location.href = f.redirectOnSuccess; return; }
          showStatus(box, "ok", "Thank you — your inquiry has been received",
            "<p>A member of the YFP Assurance team will review your requirements and respond to the contact details you provided. If your request is urgent, please mention it when we reply.</p>");
          form.reset(); syncTypeButtons(form);
        }).catch(function () {
          window.yfpTrack("inquiry_failed", { form: formName });
          showStatus(box, "err", "Your inquiry could not be sent",
            "<p>Something went wrong and your message <strong>was not delivered</strong>. Your details are still in the form. Please try again, or use one of the options below.</p><div class=\"btn-row\">" + fallbackButtons(subject, payload.text) + "</div>" + copyArea);
          wireStatusActions(box, subject, payload.text, formName);
        }).then(function () { btn.disabled = false; btn.innerHTML = label; });
      });
    });
  }

  /* ---------- Generic click tracking for WhatsApp/email/phone links ---------- */
  function initLinkTracking() {
    doc.addEventListener("click", function (e) {
      var a = e.target.closest("a[href]"); if (!a) return;
      var h = a.getAttribute("href");
      if (/^https:\/\/wa\.me/.test(h) && !a.classList.contains("wa-float")) window.yfpTrack("whatsapp_click", { location: "inline" });
      else if (/^mailto:/.test(h) && !a.hasAttribute("data-fb")) window.yfpTrack("email_click", {});
      else if (/^tel:/.test(h)) window.yfpTrack("phone_click", {});
    });
  }

  /* ---------- Equipment listings (data in js/listings.js) ---------- */
  function initListings() {
    var section = $("[data-listings-section]");
    if (!section) return;
    var items = (window.YFP_LISTINGS || []).filter(function (x) { return x && x.published; });
    var empty = $("[data-listings-empty]");
    if (!items.length) { section.hidden = true; if (empty) empty.hidden = false; return; }
    section.hidden = false; if (empty) empty.hidden = true;

    var order = { Available: 0, Reserved: 1, Sold: 2 };
    items.sort(function (a, b) { return (order[a.status] || 0) - (order[b.status] || 0); });

    var grid = $("#listings-grid", section);
    var filters = $("#listings-filter", section);

    function card(x) {
      var imgs = (x.images || []).filter(Boolean);
      var status = x.status || "Available";
      var sold = status === "Sold";
      var meta = [x.make, x.model, x.year].filter(Boolean).join(" · ");
      var list = function (arr) { return "<ul class=\"dash-list small\">" + arr.map(function (s) { return "<li>" + esc(s) + "</li>"; }).join("") + "</ul>"; };
      var media = imgs.length
        ? '<img src="' + esc(imgs[0]) + '" alt="' + esc(x.title) + '" loading="lazy" decoding="async">' +
          (imgs.length > 1 ? '<span class="photo-count">' + imgs.length + " photos</span>" : "")
        : '<div class="no-photo">Photos on request</div>';
      var details = "";
      if ((x.specs || []).length) details += '<h4>Key details</h4>' + list(x.specs);
      if ((x.documentation || []).length) details += '<h4>Documentation available</h4>' + list(x.documentation);
      if (x.knownIssues) details += '<h4>Known issues</h4><p class="small muted">' + esc(x.knownIssues) + "</p>";
      if (imgs.length > 1) details += '<div class="thumbs">' + imgs.slice(1).map(function (s) { return '<img src="' + esc(s) + '" alt="' + esc(x.title) + ' — additional photo" loading="lazy">'; }).join("") + "</div>";
      if (x.reportUrl) details += '<p><a class="link-arrow" href="' + esc(x.reportUrl) + '" target="_blank" rel="noopener">View documentation report →</a></p>';

      return '<article class="card listing' + (sold ? " is-sold" : "") + '" data-cat="' + esc(x.category || "") + '" id="' + esc(x.ref || "") + '">' +
        '<div class="media">' + media + '<span class="status s-' + esc(status.toLowerCase()) + '">' + esc(status) + "</span></div>" +
        '<div class="body">' +
          '<p class="ref">' + esc(x.ref || "") + (x.category ? " · " + esc(x.category) : "") + "</p>" +
          "<h3>" + esc(x.title || "") + "</h3>" +
          (meta ? '<p class="meta">' + esc(meta) + "</p>" : "") +
          '<p class="meta">' + esc([x.condition, x.location].filter(Boolean).join(" · ")) + "</p>" +
          (x.summary ? '<p class="small muted">' + esc(x.summary) + "</p>" : "") +
          (details ? '<details><summary>Details &amp; documentation</summary>' + details + "</details>" : "") +
          '<div class="foot"><span class="price">' + esc(x.price || "Price on request") + "</span>" +
          (sold ? '<span class="small muted">No longer available</span>'
                : '<a class="btn btn-primary btn-sm" href="#quote" data-listing="' + esc(x.ref || "") + '">Enquire</a>') +
          "</div></div></article>";
    }

    grid.innerHTML = items.map(card).join("");

    // Category filter (only if more than one category is present)
    var cats = items.map(function (x) { return x.category; }).filter(function (c, i, a) { return c && a.indexOf(c) === i; });
    if (filters && cats.length > 1) {
      filters.hidden = false;
      filters.innerHTML = ['All'].concat(cats).map(function (c, i) {
        return '<button type="button" aria-pressed="' + (i === 0) + '" data-filter="' + esc(c) + '">' + esc(c) + "</button>";
      }).join("");
      filters.addEventListener("click", function (e) {
        var b = e.target.closest("button"); if (!b) return;
        $all("button", filters).forEach(function (x) { x.setAttribute("aria-pressed", String(x === b)); });
        var f = b.getAttribute("data-filter");
        $all(".listing", grid).forEach(function (c) { c.hidden = f !== "All" && c.getAttribute("data-cat") !== f; });
      });
    }

    // "Enquire" fills the equipment form with the item's reference
    grid.addEventListener("click", function (e) {
      var b = e.target.closest("[data-listing]"); if (!b) return;
      var ref = b.getAttribute("data-listing");
      var x = items.filter(function (i) { return i.ref === ref; })[0]; if (!x) return;
      var form = doc.getElementById("machinery-form"); if (!form) return;
      setSelect(form, "equipment_category", x.category);
      var req = form.querySelector('[name="equipment_required"]');
      if (req) req.value = x.ref + " — " + x.title;
      var qty = form.querySelector('[name="quantity"]');
      if (qty && !qty.value) qty.value = 1;
      window.yfpTrack("listing_enquire", { ref: x.ref, category: x.category || "" });
    });
  }

  function init() {
    initListings();
    bindConfig(); initNav(); initWhatsApp(); initReveal(); initPrefill(); initTypeTiles(); initForms(); initLinkTracking();
  }
  if (doc.readyState === "loading") doc.addEventListener("DOMContentLoaded", init); else init();
})();
