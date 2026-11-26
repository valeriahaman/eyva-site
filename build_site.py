#!/usr/bin/env python3
"""Build the public EYVA site (eyva.me) from the reference landing page.

Source of truth for words and design: Brand/reference-briefs/eyva-landing-founder-preview.html
(edited by Val and Claude Code). This script does not change that file; it reads it and writes
public/ (index.html, terms.html, privacy.html, assets, robots.txt, llms.txt, sitemap.xml).

Run from eyva-site/:  python3 build_site.py [path-to-reference-briefs]
Then commit public/ and push; Cloudflare builds and deploys the Worker.
"""
import re, sys, shutil, pathlib, datetime

HERE = pathlib.Path(__file__).resolve().parent
SRC = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / "Brand" / "reference-briefs"
OUT = HERE / "public"
REF = SRC / "eyva-landing-founder-preview.html"

COMPANY = "EYVA Concepts FZ-LLC"
ADDRESS = "FDBC5419, Compass Building, Al Shohada Road, Al Hamra Industrial Zone-FZ, Ras Al Khaimah, United Arab Emirates"
LICENCE = "45040421"
EMAIL = "val@eyva.me"
UPDATED = "26 November 2026"

html = REF.read_text(encoding="utf-8")

def must(pattern, repl, text, flags=0, count=1):
    # Replacement strings are literal unless they use \1-style back-references.
    fn = repl if (callable(repl) or "\\1" in repl) else (lambda m, r=repl: r)
    new, n = re.subn(pattern, fn, text, count=count, flags=flags)
    if n == 0:
        raise SystemExit(f"build_site: pattern not found: {pattern[:80]}")
    return new

# ---------------------------------------------------------------- index.html
index = html

# Head comment: say what this file is.
index = must(r"<!--.*?-->", "<!-- eyva.me — built by eyva-site/build_site.py from Brand/reference-briefs/eyva-landing-founder-preview.html. Edit the reference, not this file. -->", index, flags=re.S)

# Canonical + description for search.
index = must(r"<title>", '<link rel="canonical" href="https://eyva.me/">\n<meta name="description" content="EYVA is a shower filter head for Dubai and the UAE: seven layers — carbon, sediment, vitamin C — designed in Dubai, made in Korea. The step before your shampoo. Join the waitlist and hear from Val first.">\n<meta name="keywords" content="shower filter Dubai, shower filter head, filtered shower head, vitamin C shower head, vitamin C shower filter, shower head filter UAE, hard water shower filter Dubai, EYVA">\n<title>', index)

# Search data: the names people use for this category, so engines and assistants can match them.
index = must(r'"name": "EYVA vitamin C shower head",',
             '"name": "EYVA shower filter head",\n   "alternateName": ["EYVA vitamin C shower head", "EYVA shower filter", "EYVA filtered shower head", "EYVA seven-layer shower head"],\n   "keywords": "shower filter, shower filter head, filtered shower head, vitamin C shower head, vitamin C shower filter, shower head filter, hard water shower filter, Dubai, UAE",',
             index)
index = must(r'"category": "Vitamin C shower head",', '"category": "Shower filters",\n   "areaServed": "AE",', index)

# Footer: legal line, Terms and Privacy.
index = must(
    r'<div class="base"><span>© 2026 EYVA</span><span>Feel it, or send it back\.</span></div>',
    '<div class="base"><span>© 2026 ' + COMPANY + ' · Feel it, or send it back.</span>'
    '<span><a href="/terms">Terms</a> · <a href="/privacy">Privacy</a></span></div>'
    '<p class="legal">' + COMPANY + ' · ' + ADDRESS + ' · Licence ' + LICENCE + '</p>',
    index)
index = must(r"(footer \.about\{[^}]*\})",
             r"\1\nfooter .base a{display:inline;margin:0;color:#bcb7ae}\nfooter .legal{grid-column:1/-1;margin-top:10px;font-size:13px;line-height:1.5;color:#8d8982}",
             index)

index = must(r'(<a href="https://instagram.com/valeryhaman">Val @valeryhaman</a>)',
             r'\1\n      <a href="mailto:' + EMAIL + '">' + EMAIL + '</a>', index)

# Hero capture form: give it an id so the script below can find it.
index = must(r'<form class="capture" onsubmit="return false">', '<form class="capture" id="heroJoin" novalidate>', index)
# Salon form: same.
index = must(r'<form class="full" onsubmit="return false">', '<form class="full" id="salon" novalidate>', index)

# Waitlist form: send before showing the thank-you panel.
index = must(
    r"    err\.textContent='';\n    showThanks\(nameIn\.value\.trim\(\)\.split\(/\\s\+/\)\[0\]\);",
    "    err.textContent='';\n"
    "    var chosen=form.querySelector('.sw[aria-pressed=\"true\"]');\n"
    "    var friend=document.getElementById('fFriend');\n"
    "    var btn=form.querySelector('button[type=submit]'); btn.disabled=true;\n"
    "    window.eyvaSend('/api/join',{name:nameIn.value.trim(),email:contact.value.trim(),colour:chosen?chosen.textContent.trim():'',friend:friend?friend.value.trim():'',consent:true,source:'form'})\n"
    "      .then(function(){ showThanks(nameIn.value.trim().split(/\\s+/)[0]); })\n"
    "      .catch(function(){ btn.disabled=false; err.textContent='Something went wrong on our side. Please email ' + 'val@eyva.me' + ' and Val adds you by hand.'; });",
    index)
index = must(r"// Nothing is sent or stored\. The panel's words live here, not in the page, until she joins\.",
             "// The entry is sent to /api/join (saved, and emailed to Val) before the panel shows.", index)

SEND_SCRIPT = r"""
<script>
// Sending: every form posts JSON to the site's own /api/… (a Cloudflare Worker beside these files).
(function(){
  window.eyvaSend=function(path,data){
    data.page=location.pathname; data.hp=(document.getElementById('hpField')||{}).value||'';
    return fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)})
      .then(function(r){ if(!r.ok) throw new Error('bad status '+r.status); return r.json(); });
  };
  var EMAIL_RE=/^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  // Hero: email only. Afterwards the small line under the box carries the thank-you.
  var hero=document.getElementById('heroJoin');
  if(hero){
    var inp=hero.querySelector('input'), note=hero.nextElementSibling, hb=hero.querySelector('button');
    hero.addEventListener('submit',function(e){
      e.preventDefault();
      var v=inp.value.trim();
      if(!EMAIL_RE.test(v)){ inp.setAttribute('aria-invalid','true'); inp.focus(); note.textContent='Please add an email Val can write to.'; return; }
      inp.removeAttribute('aria-invalid'); hb.disabled=true;
      window.eyvaSend('/api/join',{email:v,consent:true,source:'hero'}).then(function(){
        hero.style.display='none'; note.textContent='You’re on the waitlist. Val writes.';
      }).catch(function(){ hb.disabled=false; note.textContent='Something went wrong on our side. Please email val@eyva.me.'; });
    });
  }

  // Salon.
  var salon=document.getElementById('salon');
  if(salon){
    salon.addEventListener('submit',function(e){
      e.preventDefault();
      var n=document.getElementById('sName'), s=document.getElementById('sSalon'), c=document.getElementById('sContact'), sb=salon.querySelector('button');
      if(!n.value.trim()){ n.focus(); return; }
      if(!c.value.trim()){ c.focus(); return; }
      sb.disabled=true;
      window.eyvaSend('/api/salon',{name:n.value.trim(),salon:s.value.trim(),contact:c.value.trim(),source:'salon'}).then(function(){
        var p=document.createElement('p'); p.className='letter'; p.innerHTML='<h3>Thank you.</h3><p style="margin-top:12px">Val will write when the first units exist.</p>';
        salon.style.display='none'; salon.parentNode.insertBefore(p, salon.nextSibling);
      }).catch(function(){ sb.disabled=false; c.setAttribute('aria-invalid','true'); });
    });
  }

  // Question box.
  var ask=document.getElementById('ask');
  if(ask){
    ask.addEventListener('submit',function(e){
      e.preventDefault();
      var n=document.getElementById('qName'), m=document.getElementById('qEmail'), t=document.getElementById('qMsg'), er=document.getElementById('qErr'), ab=ask.querySelector('button');
      if(!n.value.trim()){ er.textContent='Please add your name.'; n.focus(); return; }
      if(!EMAIL_RE.test(m.value.trim())){ er.textContent='Please add an email Val can reply to.'; m.focus(); return; }
      if(!t.value.trim()){ er.textContent='Please write your message.'; t.focus(); return; }
      er.textContent=''; ab.disabled=true;
      window.eyvaSend('/api/ask',{name:n.value.trim(),email:m.value.trim(),message:t.value.trim(),source:'ask'}).then(function(){
        var p=document.createElement('div'); p.className='letter'; p.innerHTML='<h3>Thank you.</h3><p style="margin-top:12px">Val reads every message herself and writes back.</p>';
        ask.style.display='none'; ask.parentNode.insertBefore(p, ask.nextSibling);
      }).catch(function(){ ab.disabled=false; er.textContent='Something went wrong on our side. Please email val@eyva.me.'; });
    });
  }
})();
</script>
</body>"""
index = must(r"</body>", SEND_SCRIPT, index)

# Instagram line under the founder's signature.
index = must(r'(<p class="sig">Val, founder</p>)',
             r'\1\n      <p class="follow">Follow along on Instagram, <a href="https://instagram.com/eyva.me" target="_blank" rel="noopener">@eyva.me</a>.</p>',
             index)
index = must(r"(/\* salon \*/)", "\n.follow{margin-top:14px;color:var(--muted)}\n.follow a{color:var(--charcoal)}\n.ask{margin-top:80px}\n.ask .split{align-items:start}\n.ask .mail{margin-top:18px;color:var(--muted);font-size:17px}\n.ask .mail a{color:var(--charcoal)}\n\\1", index)

# Question box after the FAQ list.
ASK = """    </div>
    <div class="ask split">
      <div class="reveal">
        <span class="eyebrow">Something else?</span>
        <h2 style="margin:16px 0 22px">Write to Val, she answers herself.</h2>
        <p class="mail">Or from your own mail: <a href="mailto:val@eyva.me">val@eyva.me</a></p>
      </div>
      <div>
        <form class="full" id="ask" novalidate>
          <div class="field"><label for="qName">Your name</label><input id="qName" autocomplete="given-name"></div>
          <div class="field"><label for="qEmail">Your email</label><input id="qEmail" type="email" autocomplete="email"></div>
          <div class="field"><label for="qMsg">Your message</label><textarea id="qMsg" rows="5"></textarea></div>
          <p class="err" id="qErr" role="alert"></p>
          <div><button class="btn" type="submit">Send</button></div>
        </form>
      </div>
    </div>
  </div>
</section>

<section class="salon">"""
index = must(r"    </div>\n  </div>\n</section>\n\n<section class=\"salon\">", ASK, index)

# Honeypot: an unlabelled field bots fill and people never see.
index = must(r'(<form class="full" id="waitlist" novalidate>)',
             r'\1\n        <input id="hpField" name="website" tabindex="-1" autocomplete="off" aria-hidden="true" style="position:absolute;left:-9999px;width:1px;height:1px;opacity:0">',
             index)

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "index.html").write_text(index, encoding="utf-8")

# ------------------------------------------------------ terms.html / privacy.html
head_fonts = re.search(r'(<link rel="preconnect".*?</style>)', index, re.S).group(1)
symbol = re.search(r'(<svg width="0" height="0" style="position:absolute">.*?</svg>\n)', html, re.S).group(1)
nav = re.search(r'(<nav>.*?</nav>)', html, re.S).group(1)
footer = re.search(r'(<footer>.*?</footer>)', index, re.S).group(1)
nav = re.sub(r'(<a [^>]*?href=")#', r'\1/#', nav)
footer = re.sub(r'(<a [^>]*?href=")#', r'\1/#', footer)

LEGAL_CSS = """
<style>
.legal-page{padding:80px 0 110px}
.legal-page .wrap{max-width:760px}
.legal-page h1{font-size:clamp(36px,4.5vw,56px);margin:14px 0 10px}
.legal-page .updated{color:var(--muted);font-size:16px;margin-bottom:44px}
.legal-page h2{font-size:28px;margin:44px 0 10px}
.legal-page p{margin-top:.6em}
</style>
"""

def page(title, slug, description, body):
    return f"""<!DOCTYPE html>
<!-- eyva.me/{slug} — built by eyva-site/build_site.py; the words live in that script. -->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="canonical" href="https://eyva.me/{slug}">
<meta name="description" content="{description}">
<title>{title} — EYVA</title>
{head_fonts}
{LEGAL_CSS}
</head>
<body>
{symbol}
{nav}
<main>
<section class="legal-page">
  <div class="wrap">
    <span class="eyebrow">EYVA</span>
    <h1>{title}</h1>
    <p class="updated">Last updated {UPDATED}.</p>
{body}
  </div>
</section>
</main>
{footer}
</body>
</html>
"""

TERMS = f"""
    <h2>Who we are</h2>
    <p>EYVA is a brand of {COMPANY}, a company registered in Ras Al Khaimah Economic Zone, United Arab Emirates, licence {LICENCE}, at {ADDRESS}. You can write to us at <a href="mailto:{EMAIL}">{EMAIL}</a>.</p>

    <h2>What this site does today</h2>
    <p>EYVA is not on sale yet. This site tells you what EYVA is and lets you join the waitlist. Joining the waitlist costs nothing and commits you to nothing. When EYVA goes on sale, people on the waitlist hear first, and the launch price of AED 549 is held for them for fourteen days from the first day of sale. After that the price is AED 599.</p>

    <h2>When EYVA is on sale</h2>
    <p>Prices are in UAE dirhams and include VAT where it applies. Delivery anywhere in the UAE is included. These terms will be updated with delivery times and payment details on the day sales open, and you will see them before you pay.</p>

    <h2>Sixty days</h2>
    <p>Every EYVA comes with sixty days. If you feel no difference, send it back within sixty days of receiving it, used, and we refund the full price you paid. You pay the return postage; that is the only cost. Reply to your order email or message us and we tell you where to send it. Refunds go to the payment method you used, within fourteen days of the return reaching us.</p>

    <h2>Refills</h2>
    <p>EYVA Purify and EYVA Care are designed for sixty days of use. Refills are AED 95 a pair. Refill plans can be stopped at any time by replying to any email from us.</p>

    <h2>What EYVA is not</h2>
    <p>EYVA is a shower head with filtration layers. It is not a medical device and does not treat any condition. What you feel in your hair and skin is yours to judge; that is what the sixty days are for.</p>

    <h2>Law</h2>
    <p>These terms are governed by the laws of the United Arab Emirates and the regulations of Ras Al Khaimah Economic Zone. Nothing here removes rights you have under UAE consumer protection law.</p>
"""

PRIVACY = f"""
    <h2>The short version</h2>
    <p>We keep what you give us on the waitlist form, we use it to write to you about EYVA, and we don't sell it or share it with anyone else. Reply to any email and we stop.</p>

    <h2>What we collect</h2>
    <p>When you join the waitlist: your name, your email address, the colour you'd choose, and, if you add one, the first name of a friend who might want to hear about EYVA. We don't contact the friend; that name is only so we can ask you to pass the word when the time comes. When you fill in the salon form: your name, your salon and its area, and how to reach you.</p>

    <h2>What we use it for</h2>
    <p>To tell you when EYVA goes on sale, to hold the launch price for you, and to send you the short notes Val writes along the way. That's all.</p>

    <h2>Where it lives</h2>
    <p>Your entry is stored by {COMPANY} on Cloudflare's servers, and a copy arrives in our mailbox at <a href="mailto:{EMAIL}">{EMAIL}</a>. When the shop opens, the waitlist moves to our shop platform so your launch price can be applied to your order. Nobody else has access.</p>

    <h2>Cookies</h2>
    <p>This site sets no tracking cookies and runs no advertising pixels. If that changes, this page will say so before it does.</p>

    <h2>Your choices</h2>
    <p>Write to <a href="mailto:{EMAIL}">{EMAIL}</a> at any time to see what we hold about you, change it, or have it deleted. To stop hearing from us, reply to any email with a word.</p>

    <h2>Law</h2>
    <p>We handle personal data under the UAE Personal Data Protection Law (Federal Decree-Law No. 45 of 2021).</p>
"""

(OUT / "terms.html").write_text(page("Terms", "terms", "EYVA terms: who we are, the waitlist, the launch price, sixty days, refills.", TERMS), encoding="utf-8")
(OUT / "privacy.html").write_text(page("Privacy", "privacy", "EYVA privacy: what the waitlist form collects, what it is used for, where it lives, your choices.", PRIVACY), encoding="utf-8")

# ------------------------------------------------------------------- assets
(OUT / "assets").mkdir(exist_ok=True)
used = set(re.findall(r'assets/([\w.\-]+)', html))
for name in sorted(used):
    src = SRC / "assets" / name
    if src.exists():
        shutil.copy2(src, OUT / "assets" / name)
    else:
        print("missing asset:", name)

robots = (SRC / "robots.txt").read_text(encoding="utf-8")
robots = "\n".join(l for l in robots.splitlines() if "Kept beside" not in l and "moves to the Shopify" not in l)
robots = robots.rstrip() + "\n\nSitemap: https://eyva.me/sitemap.xml\n"
(OUT / "robots.txt").write_text(robots, encoding="utf-8")
llms = (SRC / "llms.txt").read_text(encoding="utf-8").rstrip() + """

## What people call it
EYVA is a shower filter, a shower filter head, a filtered shower head, a vitamin C shower head and a vitamin C shower filter, sold in Dubai and across the UAE. It is a handheld shower head with the filter built in: EYVA Purify (sediment and activated carbon fibre) in the handle and EYVA Care (carbon, sediment, mesh and a vitamin C disc) in the head. It does not soften water or change dissolved minerals; it makes the water feel softer on hair and skin.

## Pages
- https://eyva.me/ — the product, the water story, the price, the FAQ and the waitlist
- https://eyva.me/terms — terms, the sixty-day return
- https://eyva.me/privacy — privacy
"""
(OUT / "llms.txt").write_text(llms, encoding="utf-8")

today = datetime.date.today().isoformat()
(OUT / "sitemap.xml").write_text(
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + "".join(f"  <url><loc>https://eyva.me/{p}</loc><lastmod>{today}</lastmod></url>\n" for p in ("", "terms", "privacy"))
    + "</urlset>\n", encoding="utf-8")

print("built", OUT, "assets:", len(used))

# IndexNow key file (Bing, Yandex, etc.): keeps the key published at /<key>.txt across rebuilds.
_k = HERE / ".indexnow-key"
if _k.exists():
    key = _k.read_text().strip()
    (OUT / f"{key}.txt").write_text(key + "\n", encoding="utf-8")
