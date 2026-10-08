#!/usr/bin/env python3
"""Build the LDA website from the approved copy in content/.

    python3 build.py

Writes index.html plus one page per section into this folder. Copy is taken
word for word from the .md files; edit those, then re-run this script.
Square-bracket text such as [TOOL NAME] is shown as a visible placeholder.
"""
import html
import re
from pathlib import Path

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"

NAV_LEFT = [("New curriculum", "new-curriculum.html"), ("Creative", "creative.html")]
NAV_RIGHT = [("Consulting", "consulting.html"), ("About", "about.html"), ("Contact", "contact.html")]
CONTACT = "contact.html"

# Section pages built from the shared template: (content file, page file, section label)
SECTION_PAGES = [
    ("new-curriculum.md", "new-curriculum.html", "New curriculum"),
    ("creative.md", "creative.html", "LDA Creative"),
    ("consulting.md", "consulting.html", "LDA Consulting"),
]

# Sections whose notes are internal (e.g. pricing still being decided):
# only their [placeholders] are shown on the page.
INTERNAL_ONLY = {"Pricing and demo"}

TEMPLATE_HEADINGS = {"Headline", "Intro", "How we work", "Call to action"}


# ---------- Markdown helpers (just what the content files use) ----------

def inline(text):
    text = html.escape(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    return re.sub(r"\[([^\]]+)\]", r'<span class="ph">[\1]</span>', text)


def is_placeholder(text):
    return bool(re.fullmatch(r"\[[^\]]+\]", text.strip()))


def parse(md_file):
    """Return (title, {heading: [paragraph, ...]}) keeping heading order.

    A paragraph is a list of its lines. ### headings are folded in as 'parent / child'.
    """
    title, sections, current, parent = "", {}, None, None
    for line in (CONTENT / md_file).read_text(encoding="utf-8").splitlines():
        if line.startswith("> ") or line.strip() == "---":
            continue
        if line.startswith("# "):
            title = line[2:].strip()
        elif line.startswith("## "):
            parent = current = line[3:].strip()
            sections[current] = [[]]
        elif line.startswith("### "):
            current = f"{parent} / {line[4:].strip()}"
            sections[current] = [[]]
        elif current is not None:
            if line.strip():
                sections[current][-1].append(line.strip())
            elif sections[current][-1]:
                sections[current].append([])
    return title, {k: [p for p in v if p] for k, v in sections.items()}


def split_button(paras):
    """Pull a 'Button: **Label**' line out of the paragraphs."""
    text, button = [], None
    for para in paras:
        keep = []
        for line in para:
            m = re.fullmatch(r"Button:\s*\*\*(.+?)\*\*", line)
            if m:
                button = m.group(1)
            else:
                keep.append(line)
        if keep:
            text.append(" ".join(keep))
    return text, button


def paras_html(paras, cls=None):
    out = []
    for p in paras:
        text = " ".join(p) if isinstance(p, list) else p
        c = "ph-only" if is_placeholder(text) else cls
        out.append(f'<p{f" class=\"{c}\"" if c else ""}>{inline(text)}</p>')
    return "\n".join(out)


# ---------- Shared page parts ----------

def nav(current):
    def links(items):
        return "\n".join(
            f'      <a href="{href}"{" aria-current=\"page\"" if href == current else ""}>{label}</a>'
            for label, href in items)
    return f"""<nav class="site-nav" aria-label="Main">
    <div class="side">
{links(NAV_LEFT)}
    </div>
    <a href="index.html" class="nav-bolt" aria-label="Learning Design Aotearoa home"><img src="assets/nav-bolt.svg" alt=""></a>
    <div class="side">
{links(NAV_RIGHT)}
    </div>
  </nav>"""


def footer():
    links = "\n".join(f'        <a href="{h}">{l}</a>' for l, h in [("Home", "index.html")] + NAV_LEFT + NAV_RIGHT)
    return f"""<footer class="site-foot dark">
    <div class="wrap">
      <nav aria-label="Footer">
{links}
      </nav>
      <p class="soon">Coming soon: LDA Leadership</p>
    </div>
  </footer>"""


def page(title, current, body, script=""):
    return f"""<!doctype html>
<html lang="en-NZ">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <!-- Built by build.py from content/ — edit the .md files, not this page. -->
{body}
  {footer()}
{script}</body>
</html>
"""


def cta(paras, button):
    return f"""<section class="cta dark">
    <div class="wrap">
      {paras_html(paras)}
      <a class="button" href="{CONTACT}">{inline(button)}</a>
    </div>
  </section>"""


# ---------- Section pages (New curriculum, Creative, Consulting) ----------

def service_block(heading, paras):
    paras = [" ".join(p) for p in paras]
    if heading in INTERNAL_ONLY:
        paras = [p for p in paras if is_placeholder(p)]
    tag = ""
    if paras and not is_placeholder(paras[0]) and not paras[0].startswith("**Ideal for:**"):
        tag = f'<p class="tag">{inline(paras.pop(0))}</p>'
    body = []
    for p in paras:
        if p.startswith("- "):
            continue  # internal bullet notes are never published
        body.append(paras_html([p], "ideal" if p.startswith("**Ideal for:**") else None))
    return f"""<article class="service">
        <header>
          <h2>{inline(heading)}</h2>
          {tag}
        </header>
        <div class="body">
          {"".join(body)}
        </div>
      </article>"""


def section_page(md_file, out_file, label):
    title, s = parse(md_file)
    services = [service_block(h, p) for h, p in s.items() if h not in TEMPLATE_HEADINGS]
    cta_paras, button = split_button(s["Call to action"])
    how = ""
    if "How we work" in s:
        how = f"""<section class="how light">
      <div class="wrap">
        <p class="label"><img src="assets/nav-bolt.svg" alt="">How we work</p>
        {paras_html(s["How we work"])}
      </div>
    </section>"""
    body = f"""  <header class="dark">
  {nav(out_file)}
    <div class="page-head wrap">
      <p class="label"><img src="assets/nav-bolt.svg" alt="">{html.escape(label)}</p>
      <h1>{inline(" ".join(s["Headline"][0]))}</h1>
    </div>
  </header>
  <main>
    <section class="page-intro light">
      <div class="wrap">{paras_html(s["Intro"])}</div>
    </section>
    <section class="light">
      <div class="wrap">
      {"".join(services)}
      </div>
    </section>
    {how}
  </main>
  {cta(cta_paras, button)}"""
    (ROOT / out_file).write_text(page(f"{title} | Learning Design Aotearoa", out_file, body), encoding="utf-8")


# ---------- Home ----------

FLICKER_SCRIPT = """  <script>
    // Switch the bolt on when the page opens, and again whenever the visitor
    // scrolls back up to the landing screen.
    const badge = document.getElementById('badge');
    new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        badge.classList.remove('lit');
        void badge.offsetWidth; // restart the animation
        badge.classList.add('lit');
      }
    }, { threshold: 0.6 }).observe(badge);
  </script>
"""


def short_block(s, key):
    for para in s[key]:
        if para[0] == "**Short:**":
            return " ".join(para[1:])
    raise ValueError(f"No short version under {key}")


def home():
    _, s = parse("home.md")
    badge = (ROOT / "assets/badge.svg").read_text(encoding="utf-8").strip()
    banner, banner_button = split_button(s["New curriculum banner"])
    contact, contact_button = split_button(s["Contact prompt"])

    card_links = {"New curriculum": "new-curriculum.html", "LDA Creative": "creative.html", "LDA Consulting": "consulting.html"}
    cards = []
    for line in s["Three cards"][0]:
        m = re.fullmatch(r"- \*\*(.+?)\*\* — (.+)", line)
        name, text = m.groups()
        cards.append(f"""<li><a href="{card_links[name]}">
          <img src="assets/nav-bolt.svg" alt="">
          <h3>{inline(name)}</h3>
          <p>{inline(text)}</p>
        </a></li>""")

    body = f"""  <section class="hero dark" id="home">
  {nav("index.html")}
    <div class="badge-wrap">
      <div class="badge" id="badge">
        {badge}
      </div>
      <img class="tagline" src="assets/tagline.png" alt="Ideas · People · Organisations">
    </div>
  </section>
  <main>
    <section class="intro light">
      <div class="block left">
        <p>{inline(short_block(s, "Hero / Left block — Creative"))}</p>
        <a href="creative.html">LDA Creative</a>
      </div>
      <img class="mark" src="assets/wordmark.svg" alt="Learning Design Aotearoa">
      <div class="block right">
        <p>{inline(short_block(s, "Hero / Right block — Consulting"))}</p>
        <a href="consulting.html">LDA Consulting</a>
      </div>
    </section>
    <section class="banner dark">
      <div class="wrap">
        {paras_html(banner)}
        <a class="button" href="{CONTACT}">{inline(banner_button)}</a>
      </div>
    </section>
    <section class="cards light">
      <div class="wrap">
        <ul>
        {"".join(cards)}
        </ul>
      </div>
    </section>
    <section class="why light">
      <div class="wrap">
        <p class="label">Why LDA</p>
        {paras_html(s["Why LDA"])}
      </div>
    </section>
    <section class="proof light">
      <div class="wrap">
        {paras_html(s["Proof"])}
      </div>
    </section>
  </main>
  {cta(contact, contact_button)}"""
    (ROOT / "index.html").write_text(page("Learning Design Aotearoa", "index.html", body, FLICKER_SCRIPT), encoding="utf-8")
    return contact


# ---------- About and Contact (copy still to come) ----------

def simple_page(out_file, label, paras):
    body = f"""  <header class="dark">
  {nav(out_file)}
    <div class="page-head wrap">
      <p class="label"><img src="assets/nav-bolt.svg" alt="">{label}</p>
    </div>
  </header>
  <main>
    <section class="page-intro light" style="padding-bottom:88px">
      <div class="wrap">{paras_html(paras)}</div>
    </section>
  </main>"""
    (ROOT / out_file).write_text(page(f"{label} | Learning Design Aotearoa", out_file, body), encoding="utf-8")


if __name__ == "__main__":
    contact_text = home()
    for args in SECTION_PAGES:
        section_page(*args)
    simple_page("about.html", "About", ["[About copy — to come]"])
    simple_page("contact.html", "Contact", contact_text + ["[Contact form or email address — to come]"])
    print("Built index.html, " + ", ".join(p for _, p, _ in SECTION_PAGES) + ", about.html, contact.html")
