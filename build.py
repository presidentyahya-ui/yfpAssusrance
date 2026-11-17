#!/usr/bin/env python3
"""
YFP Assurance: site builder
============================
Reads the editable content (the .json files in this folder) and produces the finished website in  dist/.
All project files sit in ONE flat folder. The editor creates two folders by itself later:
  listings/  (one file per machine)   and   uploads/  (photos you upload).
Cloudflare Pages runs this automatically every time content is published from /admin.

Run locally:   python3 build.py   then   python3 -m http.server 8000 -d dist
Requires only Python 3.8+ (standard library). No packages to install.
"""
import html
import json
import os
import re
import shutil
import sys
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")

# ==========================================================================
# 1. CONTENT MODEL (also generates the /admin editor forms)
# ==========================================================================
def S(name, label, required=True, hint=None, default=None):
    f = {"name": name, "label": label, "widget": "string", "required": required}
    if hint: f["hint"] = hint
    if default is not None: f["default"] = default
    return f

def T(name, label, required=True, hint=None):
    f = {"name": name, "label": label, "widget": "text", "required": required}
    if hint: f["hint"] = hint
    return f

def B(name, label, hint=None, default=False):
    f = {"name": name, "label": label, "widget": "boolean", "required": False, "default": default}
    if hint: f["hint"] = hint
    return f

def N(name, label, hint=None):
    f = {"name": name, "label": label, "widget": "number", "value_type": "float", "required": False}
    if hint: f["hint"] = hint
    return f

def SEL(name, label, options, required=True, hint=None, default=None):
    f = {"name": name, "label": label, "widget": "select", "options": options, "required": required}
    if hint: f["hint"] = hint
    if default is not None: f["default"] = default
    return f

def IMG(name="image", label="Image", required=False, hint="Upload a photo (JPG or WebP, about 1600px wide, under 400 KB)."):
    return {"name": name, "label": label, "widget": "image", "required": required, "hint": hint,
            "choose_url": False}

def LS(name, label, item_label="Item", hint=None, required=False):
    f = {"name": name, "label": label, "widget": "list", "required": required,
         "field": {"name": "item", "label": item_label, "widget": "string"}}
    if hint: f["hint"] = hint
    return f

def LO(name, label, fields, summary="{{fields.title}}", hint=None, collapsed=True, required=True):
    f = {"name": name, "label": label, "widget": "list", "fields": fields, "summary": summary,
         "collapsed": collapsed, "required": required}
    if hint: f["hint"] = hint
    return f

def O(name, label, fields, collapsed=True, hint=None):
    f = {"name": name, "label": label, "widget": "object", "fields": fields, "collapsed": collapsed}
    if hint: f["hint"] = hint
    return f

SEO = O("seo", "Search engine (Google) title & description", [
    S("title", "Page title (shown in Google and browser tab)", hint="Aim for under 65 characters."),
    T("description", "Page description (shown under the title in Google)", hint="Aim for 120–160 characters."),
])
def HERO(extra=(), image=True):
    f = [S("eyebrow", "Small label above the headline"), S("title", "Headline"), T("lead", "Introduction text")]
    f += list(extra)
    if image: f.append(IMG("image", "Banner image"))
    return O("hero", "Top of page (headline & banner)", f, collapsed=False)
def SECTION_HEAD(name, label, text=True, extra=()):
    f = [S("eyebrow", "Small label"), S("title", "Heading")]
    if text: f.append(T("text", "Text", required=False))
    return O(name, label, f + list(extra))
STEP_FIELDS = [S("title", "Step title"), T("text", "Step description")]
FORM_HEAD = [S("eyebrow", "Small label"), S("title", "Form heading"), T("intro", "Text above the form"), S("button", "Submit button text")]

PAGE_LINKS = ["Refurbished Machinery", "Skills Assurance", "Factory Direct", "Project Assurance", "About", "Contact"]

SCHEMA = {
    "home": [SEO,
        O("hero", "Top of page (headline)", [
            S("eyebrow", "Small label above the headline"), S("title", "Headline, first part"),
            S("title_accent", "Headline, second part (shown in gold italics)"), T("lead", "Introduction text"),
            S("button_primary", "Main button text"), S("button_secondary", "Second button text"),
            LS("points", "Short points under the buttons", "Point"),
            IMG("image", "Main image"), S("image_alt", "Image description (for accessibility)", required=False),
            S("badge_title", "Badge on image: title"), S("badge_text", "Badge on image: text")], collapsed=False),
        O("statement", "Statement band", [S("title", "Heading"), T("text", "Text")]),
        O("services", "Services cards", [S("eyebrow", "Small label"), S("title", "Heading"), T("text", "Text"),
            LO("cards", "Cards", [S("title", "Title"), T("text", "Text"), SEL("link", "Links to page", PAGE_LINKS), IMG()])]),
        O("process", "How it works", [S("eyebrow", "Small label"), S("title", "Heading"),
            LO("steps", "Steps", STEP_FIELDS), S("button", "Button text")]),
        O("model", "Our model", [S("eyebrow", "Small label"), S("title", "Heading"), T("text", "Text"),
            LS("points", "Tick-list points", "Point"), IMG()]),
        O("cta", "Closing call to action", [S("title", "Heading"), T("text", "Text"), S("button", "Button text")]),
    ],
    "machinery": [SEO, HERO(),
        O("categories", "Equipment categories", [S("eyebrow", "Small label"), S("title", "Heading"), T("text", "Text"),
            LO("items", "Categories", [S("title", "Category name"), T("text", "Description"), IMG()],
               hint="Category names also appear in the quote form and the listings category list.")]),
        O("sourcing", "How we source", [S("eyebrow", "Small label"), S("title", "Heading"),
            T("text", "Text", hint="Leave an empty line between paragraphs."), LO("steps", "Steps", STEP_FIELDS)]),
        O("documentation", "Documentation section", [S("eyebrow", "Small label"), S("title", "Heading"), T("intro", "Intro text"),
            LS("points", "What documentation can cover", "Point"), S("notice_title", "Notice heading"), T("notice_text", "Notice text"), IMG()]),
        O("available", "Available equipment section (shown when listings are published)",
            [S("eyebrow", "Small label"), S("title", "Heading"), T("text", "Text")]),
        O("no_stock_notice", "Notice shown when no listings are published", [S("title", "Heading"), T("text", "Text")]),
        O("form", "Quote form", FORM_HEAD + [LS("next_steps", "'What happens next' points", "Point")]),
    ],
    "skills": [SEO, HERO()] + [
        O(key, label, [S("label", "Small label"), S("title", "Heading"), S("tagline", "Tagline"), T("text", "Description"),
            LS("points", "Points", "Point")] + ([T("notice", "Notice")] if key == "digital_cv" else []) +
            [S("button", "Button text"), IMG()],
          hint=("Price and ordering are set in Settings → Prices." if key != "training" else None))
        for key, label in (("digital_cv", "A · Digital CV"), ("assessment", "B · Employer Skills Assessment"), ("training", "C · Training & Practical Learning"))
    ] + [
        O("industries", "Industries served", [S("eyebrow", "Small label"), S("title", "Heading"), LS("items", "Industries", "Industry")]),
        O("disclaimer", "Important notice", [S("title", "Heading"), T("text", "Text")]),
        O("form", "Inquiry form", FORM_HEAD),
        O("sidebar", "Text beside the form", [S("employers_title", "Employers heading"), T("employers_text", "Employers text"),
            S("professionals_title", "Professionals heading"), T("professionals_text", "Professionals text")]),
    ],
    "factory": [SEO, HERO(),
        O("how", "How it works", [S("eyebrow", "Small label"), S("title", "Heading"), LO("steps", "Steps", STEP_FIELDS)]),
        LO("categories", "Product categories", [
            S("title", "Category name"), B("featured", "Feature this category (large dark block at the top)"),
            T("description", "Description"), LS("applications", "Typical applications", "Application"), IMG()],
           hint="Drag to reorder. Each category gets its own section, a jump link and a quote-form option."),
        O("partner_notice", "Production partner notice", [S("title", "Heading"), T("text", "Text")]),
        O("form", "Quote form", FORM_HEAD + [LS("tips", "'Helpful to include' points", "Point")]),
    ],
    "project": [SEO, HERO(),
        O("categories", "Project categories", [S("eyebrow", "Small label"), S("title", "Heading"), T("text", "Text"),
            LO("items", "Categories", [S("title", "Name"), T("text", "Description"), IMG()])]),
        O("process", "Process", [S("eyebrow", "Small label"), S("title", "Heading"), LO("steps", "Steps", STEP_FIELDS)]),
        O("services", "Services & pricing table", [S("eyebrow", "Small label"), S("title", "Heading"),
            LO("rows", "Services", [S("name", "Service"), T("what", "What it is"), T("receive", "What you receive"), S("pricing", "Pricing")],
               summary="{{fields.name}}")]),
        O("scope", "Scope cards", [S("eyebrow", "Small label"), S("title", "Heading"),
            LO("cards", "Cards", [S("tag", "Tag"), S("title", "Title"), T("text", "Text")])]),
        O("form", "Monitoring form", FORM_HEAD + [LS("ideal_for", "'Ideal for' points", "Point")]),
    ],
    "about": [SEO, HERO(),
        O("who", "Who we are", [S("eyebrow", "Small label"), S("title", "Heading"),
            T("text", "Text", hint="Leave an empty line between paragraphs."), S("model_line", "Business model line")]),
        O("philosophy", "Philosophy", [S("eyebrow", "Small label"), S("title", "Heading"), LO("items", "Principles", STEP_FIELDS)]),
        S("skills_mirror_title", "Skills Mirror section heading on this page"),
        O("not_section", "'What we are not' cards", [S("eyebrow", "Small label"), S("title", "Heading"),
            LO("cards", "Cards", STEP_FIELDS)]),
        O("cta", "Closing call to action", [S("title", "Heading"), T("text", "Text")]),
    ],
    "contact": [SEO, HERO(image=False),
        LS("inquiry_types", "Inquiry types", "Inquiry type", required=True),
        T("no_direct_contact_text", "Text shown until email/phone/WhatsApp are added in Settings"),
    ],
    "privacy": [SEO, S("title", "Heading"), T("lead", "Introduction"),
        LO("sections", "Sections", [S("heading", "Heading"), T("text", "Text")], summary="{{fields.heading}}"),
        S("last_updated", "Last updated (date)"),
    ],
    "shared": [
        T("footer_tagline", "Footer tagline"),
        S("legal_line", "Legal line in footer (registered company name, trade licence no.)", required=False,
          hint="Optional. Example: YFP Assurance FZ-LLC · Trade Licence No. 000000"),
        O("skills_mirror", "Skills Mirror section (Home & About)", [S("eyebrow", "Small label"), S("title", "Heading (Home page)"),
            T("text", "Text"), LS("points", "Tick-list points", "Point"), T("note", "Note above the planned features"),
            LO("planned", "Planned features", STEP_FIELDS)]),
    ],
    "settings": [
        S("site_url", "Website address", hint="Your final domain, e.g. https://yfp-assurance.com (used for Google)."),
        O("contact", "Contact details", [
            S("email", "Email address", required=False, hint="Leave empty to hide."),
            S("phone", "Telephone", required=False, hint="Include country code, e.g. +971 4 000 0000. Leave empty to hide."),
            S("whatsapp", "WhatsApp number", required=False, hint="Digits only with country code, e.g. 971500000000. Leave empty to hide all WhatsApp buttons."),
            S("whatsapp_greeting", "WhatsApp opening message"),
            S("location", "Location"),
            S("hours", "Business hours", required=False, hint="e.g. Sunday–Thursday, 9:00–18:00 GST")], collapsed=False),
        O("forms", "Inquiry forms delivery", [
            SEL("provider", "Form service", ["none", "web3forms", "formspree", "custom"],
                hint="'none' = visitors are offered a prefilled email/WhatsApp message instead. 'web3forms' is free and recommended."),
            S("access_key", "Web3Forms access key", required=False),
            S("endpoint", "Formspree / custom endpoint URL", required=False),
            S("subject_prefix", "Email subject prefix"),
            S("redirect_on_success", "Thank-you page address (optional)", required=False)]),
        O("pricing", "Prices", [
            O("digital_cv", "Digital CV", [N("amount", "Price"), S("currency", "Currency"), B("show", "Show price on website", default=True),
                B("orders_open", "Orders open", hint="Keep OFF until regulatory compliance is confirmed. When OFF, the button only collects interest."),
                S("order_url", "Order / sign-up link (when orders are open)", required=False)]),
            O("employer_assessment", "Employer Skills Assessment", [N("amount", "Price"), S("currency", "Currency"),
                B("show", "Show price on website", default=True), S("unit", "Price description")])]),
        O("skills_mirror", "Skills Mirror links", [
            S("website_url", "Skills Mirror website", required=False),
            S("report_portal_url", "Report portal link", required=False, hint="When set, an 'Access a shared report' button appears.")]),
        O("analytics", "Analytics (optional)", [
            S("plausible_domain", "Plausible domain", required=False),
            S("ga_measurement_id", "Google Analytics ID (G-…)", required=False),
            S("cloudflare_token", "Cloudflare Web Analytics token", required=False)]),
    ],
}

LISTING_FIELDS = [
    B("published", "Show on website", default=True, hint="Switch off to hide this machine without deleting it."),
    S("ref", "Reference", hint="Your own unique code, e.g. YFP-M-014"),
    S("title", "Machine name", hint="e.g. 10-tray combi oven"),
    None,  # category select: filled from machinery categories at build time
    S("make", "Make / brand", required=False), S("model", "Model", required=False), S("year", "Year", required=False),
    SEL("condition", "Condition", ["Refurbished", "Serviced", "Used – as seen", "New / unused"], default="Refurbished"),
    S("location", "Location", default="Dubai, UAE"),
    S("price", "Price", required=False, hint="e.g. AED 18,500. Leave empty to show 'Price on request'."),
    SEL("status", "Status", ["Available", "Reserved", "Sold"], default="Available"),
    {"name": "images", "label": "Photos", "widget": "list", "required": False, "hint": "First photo is the main one. Drag to reorder.",
     "field": {"name": "image", "label": "Photo", "widget": "image", "choose_url": False}},
    T("summary", "Short description", required=False),
    LS("specs", "Key details", "Detail", hint="e.g. Power: 400V / 3-phase"),
    LS("documentation", "Documentation available", "Documentation item", hint="Only list documentation that genuinely exists for this unit."),
    T("known_issues", "Known issues", required=False, hint="Be upfront, e.g. minor cosmetic marks."),
    S("report_url", "Skills Mirror report link", required=False),
]

PAGE_FILES = [  # (key, label, file)
    ("home", "Home", "page-home.json"),
    ("machinery", "Refurbished Machinery", "page-machinery.json"),
    ("skills", "Skills Assurance", "page-skills.json"),
    ("factory", "Factory Direct", "page-factory.json"),
    ("project", "Project Assurance", "page-project.json"),
    ("about", "About", "page-about.json"),
    ("contact", "Contact", "page-contact.json"),
    ("privacy", "Privacy Notice", "page-privacy.json"),
]

# ==========================================================================
# 2. LOAD + VALIDATE
# ==========================================================================
def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)

ERRORS = []
def check(data, fields, where):
    """Fill in anything missing with safe empty values, and report problems."""
    if not isinstance(data, dict):
        ERRORS.append("%s: expected an object" % where); return {}
    for f in fields:
        n, wdg = f["name"], f["widget"]
        v = data.get(n)
        if v is None:
            if f.get("required", True) and wdg not in ("boolean", "list", "image", "number"):
                ERRORS.append("%s.%s is missing" % (where, n))
            data[n] = {"object": {}, "list": [], "boolean": f.get("default", False), "number": None}.get(wdg, "")
            v = data[n]
        if wdg == "object":
            check(v, f["fields"], where + "." + n)
        elif wdg == "list" and "fields" in f:
            if not isinstance(v, list): data[n] = v = []
            for i, item in enumerate(v):
                check(item, f["fields"], "%s.%s[%d]" % (where, n, i))
        elif wdg == "list":
            if not isinstance(v, list): data[n] = [] if not v else [str(v)]
            data[n] = [x for x in data[n] if isinstance(x, str) and x.strip()]
        elif wdg in ("string", "text", "image", "select") and not isinstance(v, str):
            data[n] = "" if v is None else str(v)
    return data

C = {}
for key, _, rel in PAGE_FILES:
    C[key] = check(load(rel), SCHEMA[key], key)
C["shared"] = check(load("shared.json"), SCHEMA["shared"], "shared")
C["settings"] = check(load("settings.json"), SCHEMA["settings"], "settings")

MACH_CATS = [i["title"] for i in C["machinery"]["categories"]["items"] if i.get("title")]
LISTING_FIELDS[3] = SEL("category", "Equipment category", MACH_CATS + ["Other"],
                        hint="Categories come from the Refurbished Machinery page.")
LISTINGS = []
ldir = os.path.join(ROOT, "listings")
for fn in sorted(os.listdir(ldir)) if os.path.isdir(ldir) else []:
    if fn.endswith(".json"):
        try:
            LISTINGS.append(check(load(os.path.join("listings", fn)), LISTING_FIELDS, "listing " + fn))
        except ValueError as ex:
            ERRORS.append("listing %s could not be read: %s" % (fn, ex))

if ERRORS:
    print("Content warnings (the site still builds; missing text is left blank):")
    for e_ in ERRORS: print("  - " + e_)

SET = C["settings"]
SHARED = C["shared"]
SITE = (SET.get("site_url") or "https://yfp-assurance.com").rstrip("/")
TODAY = date.today()

# ==========================================================================
# 3. HTML HELPERS
# ==========================================================================
def e(s): return html.escape(s or "", quote=True)

def asset(p):
    p = (p or "").strip()
    if re.match(r"^https?://", p): return p
    return p.lstrip("/")

DIMS = {}
def dims(path):
    if path in DIMS: return DIMS[path]
    d = None
    full = os.path.join(ROOT, os.path.basename(path)) if not path.startswith("images/uploads/") else os.path.join(ROOT, "uploads", os.path.basename(path))
    if path.endswith(".svg") and os.path.exists(full):
        with open(full, encoding="utf-8") as fh:
            m = re.search(r'width="(\d+)" height="(\d+)"', fh.read(2000))
            if m: d = (m.group(1), m.group(2))
    DIMS[path] = d
    return d

def img(src, alt, eager=False):
    if not src: return ""
    p = asset(src)
    d = dims(p)
    wh = ' width="%s" height="%s"' % d if d else ""
    load = ' fetchpriority="high"' if eager else ' loading="lazy" decoding="async"'
    return '<img src="%s" alt="%s"%s%s>' % (e(p), e(alt), wh, load)

def paras(text, cls="muted"):
    parts = [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]
    c = ' class="%s"' % cls if cls else ""
    return "".join("<p%s>%s</p>" % (c, e(p).replace("\n", "<br>")) for p in parts)

def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-") or "item"

ARROW = '<span class="arrow" aria-hidden="true">→</span>'
NAV = [("index.html", "Home"), ("refurbished-machinery.html", "Refurbished Machinery"), ("skills-assurance.html", "Skills Assurance"),
       ("factory-direct.html", "Factory Direct"), ("project-assurance.html", "Project Assurance"), ("about.html", "About"), ("contact.html", "Contact")]
LINK_TO_FILE = {t: h for h, t in NAV}

MARK = ('<svg class="brand-mark" viewBox="0 0 40 40" aria-hidden="true"><rect x="0.75" y="0.75" width="38.5" height="38.5" rx="3" fill="#14233a"/>'
        '<rect x="4.5" y="4.5" width="31" height="31" rx="1.5" fill="none" stroke="#c9a875" stroke-width="0.9"/>'
        '<path d="M12.5 11.5 L20 21 L27.5 11.5 M20 21 V29.5" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="square"/></svg>')

def brand():
    return ('<a class="brand" href="index.html" aria-label="YFP Assurance — home">' + MARK +
            '<span class="brand-text"><span class="brand-name">YFP</span><span class="brand-sub">Assurance</span></span></a>')

def header(active):
    def cur(h): return ' aria-current="page"' if h == active else ""
    links = "".join('<li><a href="%s"%s>%s</a></li>' % (h, cur(h), t) for h, t in NAV)
    mlinks = "".join('<li><a class="m-link" href="%s"%s>%s<span aria-hidden="true">→</span></a></li>' % (h, cur(h), t) for h, t in NAV)
    return ('<a class="skip-link" href="#main">Skip to content</a>\n<header class="site-header"><div class="wrap header-inner">' + brand() +
            '<nav class="nav" aria-label="Main"><ul>' + links + '</ul></nav>'
            '<a class="btn btn-primary btn-sm header-cta" href="contact.html">Get a Quote ' + ARROW + '</a>'
            '<button class="menu-toggle" type="button" aria-expanded="false" aria-controls="mobile-nav"><span class="bars" aria-hidden="true"></span><span class="label">Menu</span></button>'
            '</div></header>\n<div class="mobile-nav" id="mobile-nav" aria-hidden="true"><nav aria-label="Mobile"><ul>' + mlinks + '</ul></nav>'
            '<div class="m-actions"><a class="btn btn-primary" href="contact.html">Get a Quote ' + ARROW + '</a>'
            '<a class="btn btn-wa" href="#" data-cfg-show="contact.whatsapp" data-cfg-href="whatsapp" target="_blank" rel="noopener" hidden>WhatsApp inquiry</a></div></div>')

def footer():
    legal = e(SHARED.get("legal_line"))
    return ('<footer class="site-footer"><div class="wrap"><div class="footer-grid"><div>' + brand() +
            '<p class="footer-tag">' + e(SHARED["footer_tagline"]) + '</p></div>'
            '<div><h4>Services</h4><ul><li><a href="refurbished-machinery.html">Refurbished Machinery</a></li><li><a href="skills-assurance.html">Skills Assurance</a></li>'
            '<li><a href="factory-direct.html">Factory-Direct Services</a></li><li><a href="project-assurance.html">Project Assurance</a></li></ul></div>'
            '<div><h4>Company</h4><ul><li><a href="about.html">About YFP</a></li><li><a href="contact.html">Contact</a></li>'
            '<li><a href="contact.html">Request a Quote</a></li><li><a href="privacy.html">Privacy Notice</a></li></ul></div>'
            '<div><h4>Contact</h4><ul><li>' + e(SET["contact"]["location"]) + '</li>'
            '<li data-cfg-show="contact.email" hidden><a href="#" data-cfg-href="email" data-cfg-text="contact.email"></a></li>'
            '<li data-cfg-show="contact.phone" hidden><a href="#" data-cfg-href="phone" data-cfg-text="contact.phone"></a></li>'
            '<li data-cfg-show="contact.whatsapp" hidden><a href="#" data-cfg-href="whatsapp" target="_blank" rel="noopener">WhatsApp</a></li></ul></div></div>'
            '<div class="footer-bottom"><span>© <span data-year>' + str(TODAY.year) + '</span> YFP Assurance. ' + e(SET["contact"]["location"]) + '.' +
            (' ' + legal if legal else '') + '</span><span>Documentation technology: Skills Mirror</span></div></div></footer>')

PAGES_OUT = []
def page(fname, seo, body, active=None, schema=None, noindex=False, scripts=()):
    path = "" if fname == "index.html" else fname.replace(".html", "")
    canon = SITE + "/" + path
    title, desc = seo.get("title", "YFP Assurance"), seo.get("description", "")
    ld = '<script type="application/ld+json">%s</script>\n' % json.dumps(schema, ensure_ascii=False) if schema else ""
    extra = "".join('<script src="%s" defer></script>\n' % s for s in scripts)
    doc = ('<!DOCTYPE html>\n<html lang="en" class="no-js">\n<head>\n<meta charset="utf-8">\n'
           '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
           '<title>' + e(title) + '</title>\n<meta name="description" content="' + e(desc) + '">\n' +
           ('<meta name="robots" content="noindex">\n' if noindex else '') +
           '<link rel="canonical" href="' + canon + '">\n'
           '<meta property="og:type" content="website">\n<meta property="og:site_name" content="YFP Assurance">\n'
           '<meta property="og:title" content="' + e(title) + '">\n<meta property="og:description" content="' + e(desc) + '">\n'
           '<meta property="og:url" content="' + canon + '">\n<meta property="og:image" content="' + SITE + '/images/og-image.png">\n'
           '<meta name="twitter:card" content="summary_large_image">\n<meta name="theme-color" content="#14233a">\n'
           '<link rel="icon" href="favicon.svg" type="image/svg+xml">\n'
           '<link rel="preconnect" href="https://fonts.googleapis.com">\n<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
           '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500&family=Inter:wght@400;500;600&display=swap">\n'
           '<link rel="stylesheet" href="css/styles.css">\n<script src="js/config.js" defer></script>\n' + extra +
           '<script src="js/main.js" defer></script>\n' + ld + '</head>\n<body>\n' + header(active) +
           '\n<main id="main">\n' + body + '\n</main>\n' + footer() + '\n</body>\n</html>\n')
    with open(os.path.join(DIST, fname), "w", encoding="utf-8") as f:
        f.write(doc)
    if not noindex: PAGES_OUT.append(path)

# ---- forms ----
def field(name, label, kind="text", required=False, options=None, full=False, hint="", placeholder="", ac="", rows=5):
    fid = "f-" + name
    req = ' required aria-required="true"' if required else ""
    mark = ' <span class="req" aria-hidden="true">*</span>' if required else ' <span class="opt">(optional)</span>'
    ph = ' placeholder="%s"' % e(placeholder) if placeholder else ""
    a = ' autocomplete="%s"' % ac if ac else ""
    desc = ' aria-describedby="%s-err%s"' % (fid, (" " + fid + "-hint") if hint else "")
    if kind == "select":
        opts = '<option value="">Please select</option>' + "".join("<option>%s</option>" % e(o) for o in options)
        ctl = '<select id="%s" name="%s"%s%s>%s</select>' % (fid, name, req, desc, opts)
    elif kind == "textarea":
        ctl = '<textarea id="%s" name="%s" rows="%d"%s%s%s></textarea>' % (fid, name, rows, req, ph, desc)
    else:
        extra = ' inputmode="tel"' if kind == "tel" else ""
        ctl = '<input id="%s" name="%s" type="%s"%s%s%s%s%s>' % (fid, name, kind, req, ph, a, extra, desc)
    h = '<span class="hint" id="%s-hint">%s</span>' % (fid, e(hint)) if hint else ""
    return '<div class="field%s"><label for="%s">%s%s</label>%s%s<span class="error" id="%s-err" role="alert"></span></div>' % (
        " full" if full else "", fid, e(label), mark, ctl, h, fid)

def form(form_id, form_name, title, fields_html, submit):
    return ('<form id="' + form_id + '" name="' + form_name + '" data-yfp-form="' + form_name + '" data-form-title="' + e(title) + '" novalidate>'
            '<div class="hp" aria-hidden="true"><label for="' + form_id + '-website">Leave this field empty</label>'
            '<input class="hp-input" id="' + form_id + '-website" name="website" type="text" tabindex="-1" autocomplete="off"></div>'
            '<div class="form-grid">' + fields_html +
            '<div class="full"><label class="consent"><input type="checkbox" name="consent" required aria-required="true"> '
            '<span>I agree that YFP Assurance may contact me about this inquiry, as described in the <a href="privacy.html">privacy notice</a>.</span></label>'
            '<span class="error" role="alert"></span></div></div>'
            '<div class="form-actions mt-m"><button class="btn btn-bronze" type="submit">' + e(submit) + ' ' + ARROW + '</button>'
            '<span class="small">No obligation. We review every requirement before quoting.</span></div>'
            '<div class="form-status" role="status" aria-live="polite"></div></form>')

def contact_fields():
    return (field("name", "Your name", required=True, ac="name") + field("company", "Company", ac="organization") +
            field("country", "Country", required=True, ac="country-name") + field("email", "Email", "email", required=True, ac="email") +
            field("phone", "Phone / WhatsApp", "tel", required=True, ac="tel", hint="Include country code, e.g. +971"))

def form_shell(fm, form_html):
    return ('<div class="form-shell reveal"><p class="eyebrow">' + e(fm["eyebrow"]) + '</p>'
            '<h2 style="font-size:clamp(1.8rem,3vw,2.4rem)">' + e(fm["title"]) + '</h2>'
            '<p class="muted mb-m">' + e(fm["intro"]) + '</p>' + form_html + '</div>')

# ---- blocks ----
def steps_html(items, horizontal=True):
    cls = "steps h" if horizontal else "steps"
    out = ['<div class="%s" style="--n:%d">' % (cls, max(1, len(items)))]
    for i, s in enumerate(items):
        out.append('<div class="step reveal"><span class="n">%02d</span><div><h3>%s</h3><p>%s</p></div></div>' % (i + 1, e(s["title"]), e(s["text"])))
    return "".join(out) + "</div>"

def check_list(points, style=""):
    st = ' style="%s"' % style if style else ""
    return '<ul class="check-list"%s>' % st + "".join("<li>%s</li>" % e(p) for p in points) + "</ul>"

def dash_list(points):
    return '<ul class="dash-list mt-s">' + "".join("<li>%s</li>" % e(p) for p in points) + "</ul>"

def chips(points):
    return '<ul class="chip-list">' + "".join("<li>%s</li>" % e(p) for p in points) + "</ul>"

def grid_cls(n):
    return "g4" if n % 4 == 0 else ("g3" if n >= 3 else "g2")

def section_head_split(eyebrow, title, text):
    return ('<div class="section-head split"><div class="reveal"><p class="eyebrow">' + e(eyebrow) + '</p><h2 style="margin:0">' + e(title) +
            '</h2></div><p class="muted reveal" style="margin:0">' + e(text) + '</p></div>')

def wa_button(cls, label, text):
    return ('<a class="btn %s" href="#" data-cfg-show="contact.whatsapp" data-cfg-href="whatsapp" data-wa-text="%s" target="_blank" rel="noopener" hidden>%s</a>'
            % (cls, e(text), e(label)))

def cta_band(title, text, button="Request a Quote"):
    return ('<section class="section tight"><div class="wrap"><div class="cta-band reveal"><div><h2>' + e(title) + '</h2><p>' + e(text) + '</p></div>'
            '<div class="btn-row"><a class="btn btn-light" href="contact.html">' + e(button) + ' ' + ARROW + '</a>' +
            wa_button("btn-ghost-light", "WhatsApp us", "Hello YFP Assurance, I would like to request a quotation.") + '</div></div></div></section>')

def page_hero(crumb, hero, buttons="", show_image=True):
    media = ('<div class="page-hero-media reveal">' + img(hero.get("image"), "", eager=True) + '</div>') if show_image and hero.get("image") else ""
    return ('<section class="page-hero"><div class="wrap"><p class="breadcrumb"><a href="index.html">Home</a> &nbsp;/&nbsp; ' + crumb + '</p>'
            '<p class="eyebrow">' + e(hero["eyebrow"]) + '</p><h1>' + e(hero["title"]) + '</h1><p class="lead">' + e(hero["lead"]) + '</p>' +
            ('<div class="btn-row">' + buttons + '</div>' if buttons else "") + media + '</div></section>')

def skills_mirror_section(title=None):
    sm = SHARED["skills_mirror"]
    planned = "".join('<div><h3>%s</h3><p>%s</p><span class="pill">Planned</span></div>' % (e(p["title"]), e(p["text"])) for p in sm["planned"])
    return ('<section class="section dark" id="skills-mirror"><div class="wrap"><div class="split wide-left"><div class="reveal">'
            '<p class="eyebrow">' + e(sm["eyebrow"]) + '</p><h2>' + e(title or sm["title"]) + '</h2><p class="lead">' + e(sm["text"]) + '</p></div>'
            '<div class="reveal">' + check_list(sm["points"], "color:#dcd8d0") +
            '<div class="btn-row mt-m"><a class="btn btn-ghost-light btn-sm" href="#" data-cfg-show="skillsMirror.websiteUrl" data-cfg-href="skillsMirror.websiteUrl" target="_blank" rel="noopener" hidden>Visit Skills Mirror</a>'
            '<a class="btn btn-light btn-sm" href="#" data-cfg-show="skillsMirror.reportPortalUrl" data-cfg-href="skillsMirror.reportPortalUrl" target="_blank" rel="noopener" hidden>Access a shared report</a></div></div></div>' +
            ('<div class="mt-l"><p class="small" style="color:#a9b0bc;margin-bottom:16px">' + e(sm["note"]) + '</p><div class="future-grid reveal">' + planned + '</div></div>' if sm["planned"] else "") +
            '</div></section>')

ORG = {"@type": "Organization", "name": "YFP Assurance", "url": SITE + "/"}
def service_schema(name, desc, area="United Arab Emirates and international markets"):
    return {"@context": "https://schema.org", "@type": "Service", "name": name, "description": desc, "provider": ORG, "areaServed": area}

# ==========================================================================
# 4. PAGES
# ==========================================================================
def build_home():
    c = C["home"]; h = c["hero"]
    cards = ""
    for i, k in enumerate(c["services"]["cards"]):
        cards += ('<a class="card hover pillar-card reveal" href="' + LINK_TO_FILE.get(k["link"], "contact.html") + '"><div class="media">' + img(k["image"], "") +
                  '</div><div class="body"><span class="num">%02d</span><h3>' % (i + 1) + e(k["title"]) + '</h3><p>' + e(k["text"]) +
                  '</p><span class="link-arrow">Explore ' + ARROW + '</span></div></a>')
    meta = "".join("<span>%s</span>" % e(p) for p in h["points"])
    body = (
        '<section class="hero"><div class="wrap hero-grid"><div class="reveal"><p class="eyebrow">' + e(h["eyebrow"]) + '</p>'
        '<h1>' + e(h["title"]) + (' <em>' + e(h["title_accent"]) + '</em>' if h["title_accent"] else "") + '</h1>'
        '<p class="lead">' + e(h["lead"]) + '</p><div class="btn-row"><a class="btn btn-primary" href="#services">' + e(h["button_primary"]) + ' ' + ARROW +
        '</a><a class="btn btn-ghost" href="contact.html">' + e(h["button_secondary"]) + '</a></div>' +
        ('<div class="hero-meta">' + meta + '</div>' if meta else "") + '</div>'
        '<div class="hero-figure reveal"><div class="frame">' + img(h["image"], h["image_alt"], eager=True) + '</div>' +
        ('<div class="badge"><strong>' + e(h["badge_title"]) + '</strong><span>' + e(h["badge_text"]) + '</span></div>' if h["badge_title"] else "") +
        '</div></div></section>'
        '<section class="section tight surface"><div class="wrap"><div class="section-head split mb-0"><h2 class="reveal" style="margin:0">' + e(c["statement"]["title"]) +
        '</h2><p class="lead reveal" style="margin:0">' + e(c["statement"]["text"]) + '</p></div></div></section>'
        '<section class="section" id="services"><div class="wrap">' + section_head_split(c["services"]["eyebrow"], c["services"]["title"], c["services"]["text"]) +
        '<div class="grid ' + grid_cls(len(c["services"]["cards"])) + '">' + cards + '</div></div></section>'
        '<section class="section alt" id="process"><div class="wrap"><div class="section-head reveal"><p class="eyebrow">' + e(c["process"]["eyebrow"]) +
        '</p><h2>' + e(c["process"]["title"]) + '</h2></div>' + steps_html(c["process"]["steps"]) +
        '<div class="btn-row mt-l reveal"><a class="btn btn-primary" href="contact.html">' + e(c["process"]["button"]) + ' ' + ARROW + '</a></div></div></section>'
        '<section class="section"><div class="wrap split"><div class="figure reveal">' + img(c["model"]["image"], "") + '</div><div class="reveal">'
        '<p class="eyebrow">' + e(c["model"]["eyebrow"]) + '</p><h2>' + e(c["model"]["title"]) + '</h2>' + paras(c["model"]["text"]) +
        '<div class="mt-m">' + check_list(c["model"]["points"]) + '</div></div></div></section>' +
        skills_mirror_section() + cta_band(c["cta"]["title"], c["cta"]["text"], c["cta"]["button"]))
    schema = {"@context": "https://schema.org", "@type": "Organization", "name": "YFP Assurance", "url": SITE + "/",
              "logo": SITE + "/favicon.svg", "image": SITE + "/images/og-image.png",
              "description": c["seo"]["description"],
              "address": {"@type": "PostalAddress", "addressLocality": "Dubai", "addressCountry": "AE"},
              "areaServed": "United Arab Emirates and international markets"}
    page("index.html", c["seo"], body, "index.html", schema)

def build_machinery():
    c = C["machinery"]; cats = c["categories"]["items"]
    cards = "".join(
        '<article class="card cat-card reveal" id="' + slug(it["title"]) + '"><div class="media">' + img(it["image"], "") + '</div><div class="body">'
        '<span class="tag">Category %02d</span><h3>' % (i + 1) + e(it["title"]) + '</h3><p>' + e(it["text"]) + '</p>'
        '<a class="link-arrow" href="#quote" data-prefill-field="equipment_category" data-prefill-value="' + e(it["title"]) + '">Request a quote ' + ARROW + '</a></div></article>'
        for i, it in enumerate(cats))
    d = c["documentation"]; fm = c["form"]
    mform = form("machinery-form", "equipment-quote", "Equipment quote",
        field("name", "Customer name", required=True, ac="name") + field("company", "Company name", ac="organization") +
        field("country", "Country", required=True, ac="country-name", hint="Where the equipment will be delivered or used") +
        field("equipment_category", "Equipment category", "select", required=True, options=MACH_CATS + ["Other commercial equipment"]) +
        field("equipment_required", "Equipment required", required=True, full=True, placeholder="e.g. 10-tray combi oven, 2 × commercial treadmills") +
        field("quantity", "Quantity", "number", required=True) + field("budget", "Budget", placeholder="e.g. AED 40,000 or USD 10,000") +
        field("email", "Email", "email", required=True, ac="email") + field("phone", "Phone / WhatsApp", "tel", required=True, ac="tel", hint="Include country code") +
        field("additional", "Additional requirements", "textarea", full=True, placeholder="Preferred brands, power supply (voltage/phase), condition expectations, delivery timeline, export needs…"),
        fm["button"])
    body = (
        page_hero("Refurbished Machinery", c["hero"], '<a class="btn btn-primary" href="#quote">' + e(fm["button"]) + ' ' + ARROW + '</a>'
                  '<a class="btn btn-ghost" href="#documentation">How we document equipment</a>') +
        '<section class="section"><div class="wrap">' + section_head_split(c["categories"]["eyebrow"], c["categories"]["title"], c["categories"]["text"]) +
        '<div class="grid ' + grid_cls(len(cats)) + '">' + cards + '</div></div></section>'
        '<section class="section alt"><div class="wrap split"><div class="reveal"><p class="eyebrow">' + e(c["sourcing"]["eyebrow"]) + '</p><h2>' + e(c["sourcing"]["title"]) +
        '</h2>' + paras(c["sourcing"]["text"]) + '</div><div class="reveal">' + steps_html(c["sourcing"]["steps"], horizontal=False) + '</div></div></section>'
        '<section class="section" id="documentation"><div class="wrap split reverse"><div class="figure tall reveal">' + img(d["image"], "") + '</div><div class="reveal">'
        '<p class="eyebrow">' + e(d["eyebrow"]) + '</p><h2>' + e(d["title"]) + '</h2><p class="muted">' + e(d["intro"]) + '</p>'
        '<div class="mt-m mb-m">' + check_list(d["points"]) + '</div><div class="notice"><p><strong>' + e(d["notice_title"]) + '</strong> ' + e(d["notice_text"]) +
        '</p></div></div></div></section>'
        '<section class="section alt" id="available" data-listings-section hidden><div class="wrap">' +
        section_head_split(c["available"]["eyebrow"], c["available"]["title"], c["available"]["text"]).replace(" reveal", "") +
        '<div class="listing-filter" id="listings-filter" role="group" aria-label="Filter by category" hidden></div><div class="grid g3" id="listings-grid"></div>'
        '<p class="small muted mt-m">Don\'t see what you need? <a href="#quote">Tell us your requirement</a> and we will source it.</p></div></section>'
        '<section class="section tight alt" data-listings-empty><div class="wrap"><div class="notice reveal" style="max-width:820px"><p><strong>' +
        e(c["no_stock_notice"]["title"]) + '</strong> ' + e(c["no_stock_notice"]["text"]) + '</p></div></div></section>'
        '<section class="section" id="quote"><div class="wrap split wide-left" style="align-items:start">' + form_shell(fm, mform) +
        '<aside class="reveal"><h3 class="h3-sans">What happens next</h3>' + dash_list(fm["next_steps"]) +
        '<div class="mt-m" data-cfg-show="contact.whatsapp" hidden><p class="small muted">Prefer to message us with photos or a spec sheet?</p>' +
        '<a class="btn btn-wa btn-sm" href="#" data-cfg-href="whatsapp" data-wa-text="Hello YFP Assurance, I am looking for refurbished equipment." target="_blank" rel="noopener">WhatsApp an equipment inquiry</a></div>'
        '</aside></div></section>')
    page("refurbished-machinery.html", c["seo"], body, "refurbished-machinery.html",
         service_schema("Refurbished commercial machinery sourcing", c["seo"]["description"], "United Arab Emirates, Africa and South Asia"),
         scripts=("js/listings.js",))

def build_skills():
    c = C["skills"]
    def service(key, anchor, extra_top="", extra_bottom="", prefill=""):
        s = c[key]
        return ('<article class="service" id="' + anchor + '"><div class="reveal"><p class="label">' + e(s["label"]) + '</p><h2>' + e(s["title"]) + '</h2>'
                '<p class="display" style="font-size:1.5rem;color:var(--bronze);font-style:italic">“' + e(s["tagline"]) + '”</p>' + extra_top +
                '<a class="btn btn-primary mt-s" href="#enquire" ' + prefill + '>' + e(s["button"]) + ' ' + ARROW + '</a>' + extra_bottom + '</div>'
                '<div class="reveal"><div class="figure mb-m">' + img(s["image"], "") + '</div>' + paras(s["text"]) +
                '<div class="mt-s">' + check_list(s["points"]) + '</div>' +
                ('<div class="notice mt-m"><p>' + e(s["notice"]) + '</p></div>' if s.get("notice") else "") + '</div></article>')
    cv_price = ('<div class="price-box" data-price-block="digitalCv"><span class="amt" data-price="digitalCv"></span><span class="per">one-time portfolio fee</span>'
                '<span class="status" data-cv-status>Orders opening soon</span></div>')
    as_price = ('<div class="price-box" data-price-block="employerAssessment"><span class="amt" data-price="employerAssessment"></span>'
                '<span class="per" data-price-unit="employerAssessment"></span></div>')
    cv_note = '<p class="small muted mt-s" data-cv-closed>Digital CV orders are not open yet. Register your interest and we will contact you when they are. No payment is taken now.</p>'
    ind = c["industries"]; fm = c["form"]; sb = c["sidebar"]
    sform = form("skills-form", "skills-inquiry", "Skills Assurance",
        field("service", "Service", "select", required=True, options=["Digital CV — register interest", "Employer skills assessment", "Training & practical learning"]) +
        field("industry", "Industry", "select", required=True, options=ind["items"] + ["Other"]) + contact_fields() +
        field("role", "Role or skills", full=True, placeholder="e.g. Barista, tile installer, AV technician, joiner") +
        field("candidates", "Number of candidates / learners", "number", hint="For employer assessments and group training") +
        field("message", "Message", "textarea", full=True, placeholder="Tell us what you would like to demonstrate, assess or learn."), fm["button"])
    body = (
        page_hero("Skills Assurance", c["hero"], '<a class="btn btn-primary" href="#digital-cv">' + e(c["digital_cv"]["title"]) + '</a>'
                  '<a class="btn btn-ghost" href="#assessment">' + e(c["assessment"]["title"]) + '</a><a class="btn btn-ghost" href="#training">Training</a>') +
        '<section class="wrap" aria-label="Skills Assurance services">' +
        service("digital_cv", "digital-cv", cv_price, cv_note, 'data-cv-button data-prefill-field="service" data-prefill-value="Digital CV — register interest"') +
        service("assessment", "assessment", as_price, "", 'data-prefill-field="service" data-prefill-value="Employer skills assessment"') +
        service("training", "training", "", "", 'data-prefill-field="service" data-prefill-value="Training &amp; practical learning"') +
        '</section><section class="section alt"><div class="wrap split"><div class="reveal"><p class="eyebrow">' + e(ind["eyebrow"]) + '</p><h2>' + e(ind["title"]) +
        '</h2><div class="mt-m">' + chips(ind["items"]) + '</div></div><div class="notice reveal"><p><strong>' + e(c["disclaimer"]["title"]) + '</strong> ' +
        e(c["disclaimer"]["text"]) + '</p></div></div></section>'
        '<section class="section" id="enquire"><div class="wrap split wide-left" style="align-items:start">' + form_shell(fm, sform) +
        '<aside class="reveal"><h3 class="h3-sans">' + e(sb["employers_title"]) + '</h3><p class="muted small">' + e(sb["employers_text"]) + '</p>'
        '<h3 class="h3-sans mt-m">' + e(sb["professionals_title"]) + '</h3><p class="muted small">' + e(sb["professionals_text"]) + '</p></aside></div></section>')
    page("skills-assurance.html", c["seo"], body, "skills-assurance.html",
         service_schema("Skills assurance", c["seo"]["description"]))

def build_factory():
    c = C["factory"]; cats = [x for x in c["categories"] if x.get("title")]
    featured = [x for x in cats if x.get("featured")][:1]
    others = [x for x in cats if x not in featured]
    def quote_btn(t, light=False):
        return ('<a class="btn %s" href="#quote" data-prefill-field="category" data-prefill-value="%s">Request a Quote %s</a>'
                % ("btn-light" if light else "btn-primary", e(t), ARROW))
    anchors = "".join('<a href="#%s"%s>%s</a>' % (slug(x["title"]), ' class="featured"' if x in featured else "", e(x["title"])) for x in featured + others)
    feat_html = ""
    for x in featured:
        feat_html = ('<section class="detail" id="' + slug(x["title"]) + '" style="border-top:0"><div class="wrap"><div class="feature reveal"><div class="media">' + img(x["image"], "") +
                     '</div><div class="body"><p class="eyebrow">Featured category</p><h2>' + e(x["title"]) + '</h2>' + paras(x["description"], "") +
                     '<h3 class="h3-sans" style="color:#fff;margin-top:28px">Typical applications</h3><div class="mt-s">' + chips(x["applications"]) + '</div>'
                     '<div class="btn-row mt-m">' + quote_btn(x["title"], True) +
                     wa_button("btn-ghost-light", "Send details on WhatsApp", "Hello YFP Assurance, I would like a quotation for " + x["title"] + ".") +
                     '</div></div></div></div></section>')
    details = ""
    for i, x in enumerate(others):
        details += ('<section class="detail" id="' + slug(x["title"]) + '"><div class="wrap split' + (" reverse" if i % 2 else "") + '"><div class="figure reveal">' +
                    img(x["image"], "") + '</div><div class="reveal"><p class="num">%02d</p><h2>' % (i + 1) + e(x["title"]) + '</h2>' + paras(x["description"]) +
                    '<h3 class="sub">Typical applications</h3>' + chips(x["applications"]) + '<div class="btn-row mt-m">' + quote_btn(x["title"]) + '</div></div></div></section>')
    fm = c["form"]
    fform = form("factory-form", "factory-quote", "Factory-direct quotation",
        field("category", "Product category", "select", required=True, options=[x["title"] for x in featured + others] + ["Other"]) +
        field("project_location", "Project location (city)", required=True, placeholder="e.g. Dubai Marina") + contact_fields() +
        field("quantity", "Quantity / size", placeholder="e.g. 6 windows, 3.2m countertop, 1 shopfront sign") +
        field("timeline", "Required timeline", "select", options=["As soon as possible", "Within 1 month", "1–3 months", "3+ months", "Flexible"]) +
        field("budget", "Budget", placeholder="Approximate, if known") +
        field("installation", "Installation needed?", "select", options=["Yes, supply and install", "Supply only", "Not sure"]) +
        field("message", "Describe your requirement", "textarea", required=True, full=True,
              placeholder="Dimensions, materials, finishes and any references. After we reply, you can send drawings, artwork or photos by email or WhatsApp."),
        fm["button"])
    first = featured[0]["title"] if featured else (others[0]["title"] if others else "")
    body = (
        page_hero("Factory Direct", c["hero"], '<a class="btn btn-primary" href="#quote">' + e(fm["button"]) + ' ' + ARROW + '</a>' +
                  ('<a class="btn btn-ghost" href="#' + slug(first) + '">' + e(first) + '</a>' if first else "")) +
        '<section class="section tight alt"><div class="wrap"><p class="small muted" style="margin-bottom:4px">Jump to a category</p>'
        '<nav class="anchor-nav" aria-label="Factory-direct categories" style="margin-top:8px">' + anchors + '</nav></div></section>'
        '<section class="section"><div class="wrap"><div class="section-head reveal"><p class="eyebrow">' + e(c["how"]["eyebrow"]) + '</p><h2>' + e(c["how"]["title"]) +
        '</h2></div>' + steps_html(c["how"]["steps"]) + '</div></section>' + feat_html + details +
        '<section class="section tight"><div class="wrap"><div class="notice reveal" style="max-width:860px"><p><strong>' + e(c["partner_notice"]["title"]) + '</strong> ' +
        e(c["partner_notice"]["text"]) + '</p></div></div></section>'
        '<section class="section alt" id="quote"><div class="wrap split wide-left" style="align-items:start">' + form_shell(fm, fform) +
        '<aside class="reveal"><h3 class="h3-sans">Helpful to include</h3>' + dash_list(fm["tips"]) + '</aside></div></section>')
    page("factory-direct.html", c["seo"], body, "factory-direct.html",
         service_schema("Factory-direct custom products and installation", c["seo"]["description"]))

def build_project():
    c = C["project"]; items = c["categories"]["items"]
    cards = "".join('<article class="card cat-card reveal"><div class="media">' + img(it["image"], "") + '</div><div class="body"><h3>' + e(it["title"]) +
                    '</h3><p>' + e(it["text"]) + '</p><a class="link-arrow" href="#monitor" data-prefill-field="project_category" data-prefill-value="' + e(it["title"]) +
                    '">Monitor this type of project ' + ARROW + '</a></div></article>' for it in items)
    rows = "".join('<tr><th scope="row">' + e(r["name"]) + '</th><td data-label="What it is">' + e(r["what"]) + '</td><td data-label="What you receive">' +
                   e(r["receive"]) + '</td><td data-label="Pricing">' + e(r["pricing"]) + '</td></tr>' for r in c["services"]["rows"])
    scards = "".join('<div class="card reveal"><span class="pill light">' + e(k["tag"]) + '</span><h3 class="mt-s">' + e(k["title"]) + '</h3><p class="muted">' +
                     e(k["text"]) + '</p></div>' for k in c["scope"]["cards"])
    fm = c["form"]
    pform = form("project-form", "project-monitoring", "Project monitoring",
        field("project_category", "Project category", "select", required=True, options=[i["title"] for i in items] + ["Other"]) +
        field("service", "Service of interest", "select", required=True, options=[r["name"] for r in c["services"]["rows"]] + ["Not sure yet"]) +
        field("project_location", "Project location", required=True, placeholder="City and country") +
        field("project_stage", "Project stage", "select", options=["Planning", "Contractor selected", "In progress", "Near completion"]) + contact_fields() +
        field("reporting", "Preferred reporting frequency", "select", options=["Weekly", "Fortnightly", "At each milestone", "Not sure"]) +
        field("message", "Project description", "textarea", required=True, full=True,
              placeholder="Scope, contractor or workshop involved, timeline and what you most want visibility on."), fm["button"])
    body = (
        page_hero("Project Assurance", c["hero"], '<a class="btn btn-primary" href="#monitor">' + e(fm["button"]) + ' ' + ARROW + '</a>'
                  '<a class="btn btn-ghost" href="#scope">What is and isn’t included</a>') +
        '<section class="section"><div class="wrap">' + section_head_split(c["categories"]["eyebrow"], c["categories"]["title"], c["categories"]["text"]) +
        '<div class="grid ' + grid_cls(len(items)) + '">' + cards + '</div></div></section>'
        '<section class="section dark"><div class="wrap"><div class="section-head reveal"><p class="eyebrow">' + e(c["process"]["eyebrow"]) + '</p><h2>' +
        e(c["process"]["title"]) + '</h2></div>' + steps_html(c["process"]["steps"]) + '</div></section>'
        '<section class="section" id="services"><div class="wrap"><div class="section-head reveal"><p class="eyebrow">' + e(c["services"]["eyebrow"]) + '</p><h2>' +
        e(c["services"]["title"]) + '</h2></div><div class="table-scroll reveal"><table class="compare stack"><thead><tr><th scope="col">Service</th>'
        '<th scope="col">What it is</th><th scope="col">What you receive</th><th scope="col">Pricing</th></tr></thead><tbody>' + rows + '</tbody></table></div></div></section>'
        '<section class="section alt" id="scope"><div class="wrap"><div class="section-head reveal"><p class="eyebrow">' + e(c["scope"]["eyebrow"]) + '</p><h2>' +
        e(c["scope"]["title"]) + '</h2></div><div class="grid ' + grid_cls(len(c["scope"]["cards"])) + '">' + scards + '</div></div></section>'
        '<section class="section" id="monitor"><div class="wrap split wide-left" style="align-items:start">' + form_shell(fm, pform) +
        '<aside class="reveal"><h3 class="h3-sans">Ideal for</h3>' + dash_list(fm["ideal_for"]) + '</aside></div></section>')
    page("project-assurance.html", c["seo"], body, "project-assurance.html",
         service_schema("Project assurance and progress reporting", c["seo"]["description"]))

def build_about():
    c = C["about"]
    princ = "".join('<li class="reveal"><span class="n">%02d</span><div><h3>%s</h3><p>%s</p></div></li>' % (i + 1, e(p["title"]), e(p["text"]))
                    for i, p in enumerate(c["philosophy"]["items"]))
    nots = "".join('<div class="card reveal"><h3>' + e(k["title"]) + '</h3><p class="muted">' + e(k["text"]) + '</p></div>' for k in c["not_section"]["cards"])
    body = (
        page_hero("About", c["hero"]) +
        '<section class="section"><div class="wrap split" style="align-items:start"><div class="reveal"><p class="eyebrow">' + e(c["who"]["eyebrow"]) + '</p><h2>' +
        e(c["who"]["title"]) + '</h2></div><div class="reveal">' + paras(c["who"]["text"]) +
        ('<div class="notice mt-m"><p><strong>Our model:</strong> ' + e(c["who"]["model_line"]) + '</p></div>' if c["who"]["model_line"] else "") + '</div></div></section>'
        '<section class="section alt"><div class="wrap split" style="align-items:start"><div class="reveal"><p class="eyebrow">' + e(c["philosophy"]["eyebrow"]) +
        '</p><h2>' + e(c["philosophy"]["title"]) + '</h2></div><ul class="principles">' + princ + '</ul></div></section>' +
        skills_mirror_section(c["skills_mirror_title"]) +
        '<section class="section"><div class="wrap"><div class="section-head reveal"><p class="eyebrow">' + e(c["not_section"]["eyebrow"]) + '</p><h2>' +
        e(c["not_section"]["title"]) + '</h2></div><div class="grid ' + grid_cls(len(c["not_section"]["cards"])) + '">' + nots + '</div></div></section>' +
        cta_band(c["cta"]["title"], c["cta"]["text"]))
    page("about.html", c["seo"], body, "about.html")

def build_contact():
    c = C["contact"]; types = c["inquiry_types"] or ["General inquiry"]
    tiles = "".join('<button type="button" data-type="%s" aria-pressed="false">%s</button>' % (e(t), e(t)) for t in types)
    cform = form("contact-form", "contact", "Contact",
        field("inquiry_type", "Inquiry type", "select", required=True, options=types, full=True) + contact_fields() +
        field("message", "Message", "textarea", required=True, full=True, rows=6, placeholder="Tell us about your requirement."), "Send inquiry")
    body = (
        page_hero("Contact", c["hero"], show_image=False) +
        '<section class="section"><div class="wrap split wide-left" style="align-items:start"><div class="reveal"><p class="small muted" style="margin-bottom:12px">What can we help with?</p>'
        '<div class="type-grid mb-m" data-form="contact-form" role="group" aria-label="Choose an inquiry type">' + tiles + '</div><div class="form-shell">' + cform + '</div></div>'
        '<aside class="contact-aside reveal"><div class="contact-item"><p class="k">Location</p><p class="v">' + e(SET["contact"]["location"]) + '</p></div>'
        '<div class="contact-item" data-cfg-show="contact.email" hidden><p class="k">Email</p><a class="v" href="#" data-cfg-href="email" data-cfg-text="contact.email"></a></div>'
        '<div class="contact-item" data-cfg-show="contact.phone" hidden><p class="k">Telephone</p><a class="v" href="#" data-cfg-href="phone" data-cfg-text="contact.phone"></a></div>'
        '<div class="contact-item" data-cfg-show="contact.hours" hidden><p class="k">Hours</p><p class="v" style="font-size:1.1rem" data-cfg-text="contact.hours"></p></div>'
        '<div class="contact-item" data-cfg-show="contact.whatsapp" hidden><p class="k">WhatsApp</p><p class="small muted">Quick questions, photos or documents. Message us directly.</p>'
        '<a class="btn btn-wa" href="#" data-cfg-href="whatsapp" target="_blank" rel="noopener"><span data-wa-icon style="width:20px;height:20px;display:inline-flex"></span> Chat on WhatsApp</a></div>'
        '<div class="contact-item" data-cfg-empty="contact.email|contact.phone|contact.whatsapp"><p class="k">Direct contact</p><p class="small muted">' +
        e(c["no_direct_contact_text"]) + '</p></div></aside></div></section>')
    page("contact.html", c["seo"], body, "contact.html")

def build_privacy():
    c = C["privacy"]
    secs = "".join('<h2 style="font-size:1.8rem" class="mt-m">' + e(s["heading"]) + '</h2>' + paras(s["text"]) for s in c["sections"])
    body = ('<section class="page-hero"><div class="wrap"><p class="breadcrumb"><a href="index.html">Home</a> &nbsp;/&nbsp; Privacy</p><h1>' + e(c["title"]) +
            '</h1><p class="lead">' + e(c["lead"]) + '</p></div></section><section class="section"><div class="wrap" style="max-width:760px">' + secs +
            '<p class="small muted mt-m">Last updated: ' + e(c["last_updated"]) + '</p></div></section>')
    page("privacy.html", c["seo"], body)

def build_404():
    body = ('<section class="page-hero" style="border:0"><div class="wrap"><p class="eyebrow">404</p><h1>This page could not be found.</h1>'
            '<p class="lead">The page may have moved. Explore our services or get in touch.</p><div class="btn-row"><a class="btn btn-primary" href="index.html">Back to home ' +
            ARROW + '</a><a class="btn btn-ghost" href="contact.html">Contact us</a></div></div></section>')
    page("404.html", {"title": "Page not found | YFP Assurance", "description": "Page not found."}, body, noindex=True)

# ==========================================================================
# 5. GENERATED SCRIPTS (site settings + listings)
# ==========================================================================
def js_config():
    s = SET; ct = s["contact"]; f = s["forms"]; p = s["pricing"]
    def num(v, default):
        try: return int(v) if float(v).is_integer() else float(v)
        except (TypeError, ValueError): return default
    cfg = {
        "contact": {"email": ct["email"].strip(), "phone": ct["phone"].strip(), "phoneHref": "",
                    "whatsapp": re.sub(r"\D", "", ct["whatsapp"]), "whatsappGreeting": ct["whatsapp_greeting"],
                    "location": ct["location"], "hours": ct["hours"]},
        "forms": {"provider": f["provider"] or "none", "endpoint": f["endpoint"], "accessKey": f["access_key"],
                  "subjectPrefix": f["subject_prefix"], "redirectOnSuccess": f["redirect_on_success"]},
        "pricing": {
            "digitalCv": {"amount": num(p["digital_cv"]["amount"], 25), "currency": p["digital_cv"]["currency"] or "AED",
                          "show": bool(p["digital_cv"]["show"]), "ordersOpen": bool(p["digital_cv"]["orders_open"]), "orderUrl": p["digital_cv"]["order_url"]},
            "employerAssessment": {"amount": num(p["employer_assessment"]["amount"], 75), "currency": p["employer_assessment"]["currency"] or "AED",
                                   "show": bool(p["employer_assessment"]["show"]), "unit": p["employer_assessment"]["unit"]}},
        "skillsMirror": {"websiteUrl": s["skills_mirror"]["website_url"], "reportPortalUrl": s["skills_mirror"]["report_portal_url"]},
        "analytics": {"plausibleDomain": s["analytics"]["plausible_domain"], "gaMeasurementId": s["analytics"]["ga_measurement_id"],
                      "cloudflareToken": s["analytics"]["cloudflare_token"]},
    }
    return ("/* Generated by build.py from settings.json. Edit settings in /admin, not here. */\n"
            "window.YFP_CONFIG = " + json.dumps(cfg, ensure_ascii=False, indent=2) + ";\n")

def js_listings():
    out = []
    for x in LISTINGS:
        if not x.get("published"): continue
        out.append({"published": True, "ref": x["ref"], "title": x["title"], "category": x["category"], "make": x["make"], "model": x["model"],
                    "year": x["year"], "condition": x["condition"], "location": x["location"], "price": x["price"], "status": x["status"] or "Available",
                    "images": [asset(i) for i in x["images"]], "summary": x["summary"], "specs": x["specs"], "documentation": x["documentation"],
                    "knownIssues": x["known_issues"], "reportUrl": x["report_url"]})
    return ("/* Generated by build.py from the listings/ folder. Manage listings in /admin. */\n"
            "window.YFP_LISTINGS = " + json.dumps(out, ensure_ascii=False, indent=2) + ";\n")

# ==========================================================================
# 6. ADMIN (Decap CMS) CONFIGURATION
# ==========================================================================
def cms_config():
    repo = os.environ.get("CMS_REPO", "").strip() or "presidentyahya-ui/yfpAssusrance"
    branch = os.environ.get("CMS_BRANCH", "").strip() or os.environ.get("CF_PAGES_BRANCH", "").strip() or "main"
    pages = [{"name": k, "label": lbl, "file": f, "fields": SCHEMA[k]} for k, lbl, f in PAGE_FILES]
    return {
        "load_config_file": False,
        "backend": {"name": "github", "repo": repo, "branch": branch, "auth_endpoint": "api/auth",
                    "commit_messages": {"create": "Add {{collection}} “{{slug}}”", "update": "Update {{collection}} “{{slug}}”",
                                        "delete": "Delete {{collection}} “{{slug}}”", "uploadMedia": "Upload “{{path}}”", "deleteMedia": "Delete “{{path}}”"}},
        "media_folder": "uploads",
        "public_folder": "/images/uploads",
        "logo_url": "/favicon.svg",
        "display_url": SITE,
        "collections": [
            {"name": "listings", "label": "Equipment Listings", "label_singular": "Machine", "folder": "listings",
             "create": True, "delete": True, "extension": "json", "format": "json", "identifier_field": "ref", "slug": "{{slug}}",
             "summary": "{{ref}} · {{title}} · {{status}}", "sortable_fields": ["ref", "title", "status"],
             "description": "Machines YFP is offering for sale. They appear on the Refurbished Machinery page. Use 'Show on website' to hide one without deleting it.",
             "editor": {"preview": False}, "fields": LISTING_FIELDS},
            {"name": "pages", "label": "Website Pages", "editor": {"preview": False}, "files": pages},
            {"name": "site", "label": "Settings & Contact", "editor": {"preview": False}, "files": [
                {"name": "settings", "label": "Contact details, forms, prices & analytics", "file": "settings.json", "fields": SCHEMA["settings"]},
                {"name": "shared", "label": "Footer & Skills Mirror section", "file": "shared.json", "fields": SCHEMA["shared"]}]},
        ],
    }

ADMIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>YFP Assurance | Website Editor</title>
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<script>window.CMS_MANUAL_INIT = true;</script>
<script src="https://unpkg.com/decap-cms@^3.0.0/dist/decap-cms.js"></script>
<script src="cms-config.js"></script>
</head>
<body>
<script>
  (function () {
    var cfg = window.YFP_CMS_CONFIG;
    cfg.backend.base_url = window.location.origin;   // login runs on this same website (/api/auth)
    cfg.site_url = window.location.origin;
    if (/^(localhost|127\\.0\\.0\\.1)$/.test(window.location.hostname)) cfg.local_backend = true;
    var init = window.initCMS || (window.CMS && window.CMS.init);
    init({ config: cfg });
  })();
</script>
</body>
</html>
"""

# ==========================================================================
# 7. WRITE dist/
# ==========================================================================
def main():
    if os.path.isdir(DIST): shutil.rmtree(DIST)
    # Arrange the flat project files into the website's folder structure
    for sub in ("css", "js", "images", "admin"):
        os.makedirs(os.path.join(DIST, sub), exist_ok=True)
    for fn in sorted(os.listdir(ROOT)):
        src = os.path.join(ROOT, fn)
        if not os.path.isfile(src): continue
        low = fn.lower()
        if low.endswith(".css"): shutil.copy2(src, os.path.join(DIST, "css", fn))
        elif fn == "main.js": shutil.copy2(src, os.path.join(DIST, "js", fn))
        elif fn == "worker.js": shutil.copy2(src, os.path.join(DIST, "_worker.js"))
        elif fn == "favicon.svg": shutil.copy2(src, os.path.join(DIST, fn))
        elif low.endswith((".svg", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif")): shutil.copy2(src, os.path.join(DIST, "images", fn))
    up = os.path.join(ROOT, "uploads")
    if os.path.isdir(up):
        shutil.copytree(up, os.path.join(DIST, "images", "uploads"), ignore=shutil.ignore_patterns(".gitkeep", ".DS_Store"))
    build_home(); build_machinery(); build_skills(); build_factory(); build_project(); build_about(); build_contact(); build_privacy(); build_404()
    with open(os.path.join(DIST, "js", "config.js"), "w", encoding="utf-8") as f: f.write(js_config())
    with open(os.path.join(DIST, "js", "listings.js"), "w", encoding="utf-8") as f: f.write(js_listings())
    with open(os.path.join(DIST, "admin", "index.html"), "w", encoding="utf-8") as f: f.write(ADMIN_HTML)
    with open(os.path.join(DIST, "admin", "cms-config.js"), "w", encoding="utf-8") as f:
        f.write("/* Generated by build.py. Do not edit. */\nwindow.YFP_CMS_CONFIG = " + json.dumps(cms_config(), ensure_ascii=False, indent=1) + ";\n")
    with open(os.path.join(DIST, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for p in PAGES_OUT:
            f.write("  <url><loc>%s/%s</loc><lastmod>%s</lastmod></url>\n" % (SITE, p, TODAY.isoformat()))
        f.write("</urlset>\n")
    with open(os.path.join(DIST, "robots.txt"), "w", encoding="utf-8") as f:
        f.write("User-agent: *\nAllow: /\nDisallow: /admin/\n\nSitemap: %s/sitemap.xml\n" % SITE)
    print("Built %d pages, %d published listing(s) -> dist/" % (len(PAGES_OUT) + 1, sum(1 for x in LISTINGS if x.get("published"))))

if __name__ == "__main__":
    main()
