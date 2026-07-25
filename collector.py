#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
media-hub collector — runs headless (GitHub Actions / any machine with Python).
Two source types:
  1. SITES    — a writer/tag page is scraped directly for that writer's articles.
  2. SEARCHES — Google News RSS query (reliable from a cloud runner; replaced the
                old DuckDuckGo HTML endpoint, which datacenter IPs get blocked on).
Filters by keywords, dedupes (by normalized URL AND normalized title) against the
existing data.json, and rewrites data.json.

No Claude, no browser. X/Twitter is NOT collected here (needs the paid X API).

Run:  python collector.py
Deps: pip install requests beautifulsoup4        (XML parsing uses the stdlib)
"""

import json, re, sys, datetime, urllib.parse, pathlib
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
import requests
from bs4 import BeautifulSoup

HERE = pathlib.Path(__file__).parent
DATA = HERE / "data.json"
TODAY = datetime.date.today().isoformat()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "he-IL,he;q=0.9,en;q=0.8",
}

KEYWORDS = ["קשת 12","ערוץ 12","חדשות 12","ערוץ 14","כוח מאה","גיא פלג","דודי ורטהיים",
    "קוקה קולה","חרם ערוץ 12","שלמה קרעי","חוק התקשורת","חוק השידורים","רפורמת התקשורת",
    "שוק התקשורת","החוק להחלשת התקשורת","הרשות השנייה",
    "אבי ניר","ארץ נהדרת","עובדה","רייטינג","ניר ברקת","יואב קיש","יעקב ברדוגו","ינון מגל",
    "גוגל","יוטיוב","מטא","פייסבוק","רגולציה","תרעלה","תבהלה"]

# Writer / tag pages. `pattern` = regex an ARTICLE href must match on that domain.
SITES = [
    {"source":"כלכליסט · עומר כביר","base":"https://www.calcalist.co.il",
     "url":"https://www.calcalist.co.il/tags/%D7%A2%D7%95%D7%9E%D7%A8_%D7%9B%D7%91%D7%99%D7%A8",
     "pattern":r"/article/[A-Za-z0-9]+"},
    {"source":"גלובס · נבו טרבלסי","base":"https://www.globes.co.il",
     "url":"https://www.globes.co.il/news/%D7%A0%D7%91%D7%95_%D7%98%D7%A8%D7%91%D7%9C%D7%A1%D7%99.tag",
     "pattern":r"/news/article\.aspx\?did=\d+"},
    {"source":"גלובס · גלית חתן","base":"https://www.globes.co.il",
     "url":"https://www.globes.co.il/news/%D7%92%D7%9C%D7%99%D7%AA_%D7%97%D7%AA%D7%9F.tag",
     "pattern":r"/news/article\.aspx\?did=\d+"},
    {"source":"דה-מרקר · יסמין גואטה","base":"https://www.themarker.com",
     "url":"https://www.themarker.com/ty-WRITER/0000017f-da32-d42c-afff-dff2b5d20000",
     "pattern":r"/[a-z].*/ty-article"},
    {"source":"דה-מרקר · נתי טוקר","base":"https://www.themarker.com",
     "url":"https://www.themarker.com/ty-WRITER/0000017f-da30-d42c-afff-dff2b4680000",
     "pattern":r"/[a-z].*/ty-article"},
    {"source":"הארץ · עידו דוד כהן","base":"https://www.haaretz.co.il",
     "url":"https://www.haaretz.co.il/ty-WRITER/0000017f-da5b-d494-a17f-de5b31520000",
     "pattern":r"/[a-z].*/ty-article"},
]

# Google News RSS searches. Israel Hayom writers (blocked to direct fetch) via
# site: queries + the Google-query topics from the spec. `unconditional`=True →
# keep every result (spec: Google searches enter with no keyword condition).
SEARCHES = [
    {"source":"ישראל היום · אילי זילברברג","q":"site:israelhayom.co.il אילי זילברברג","unconditional":False},
    {"source":"ישראל היום · ביני אשכנזי","q":"site:israelhayom.co.il ביני אשכנזי","unconditional":False},
    {"source":"ישראל היום · אלינור שירקני קופמן","q":"site:israelhayom.co.il אלינור שירקני קופמן","unconditional":False},
    {"source":"חיפוש גוגל · שלמה קרעי","q":"שלמה קרעי חוק התקשורת","unconditional":True},
    {"source":"חיפוש גוגל · ערוץ 14 / ברדוגו / ערוץ 12","q":"ערוץ 14 ברדוגו ערוץ 12","unconditional":True},
    {"source":"חיפוש גוגל · ינון מגל","q":"ינון מגל ערוץ 14","unconditional":True},
    {"source":"חיפוש גוגל · גלית דיסטל","q":"גלית דיסטל אטבריאן","unconditional":True},
    {"source":"חיפוש גוגל · דודי ורטהיים","q":"דודי ורטהיים קשת","unconditional":True},
    {"source":"חיפוש גוגל · אבי ניר","q":"אבי ניר קשת ארץ נהדרת","unconditional":True},
    {"source":"חיפוש גוגל · פטריק דרהי","q":"פטריק דרהי","unconditional":True},
    {"source":"חיפוש גוגל · יפעת בן חי שגב","q":"יפעת בן חי שגב","unconditional":True},
]

def norm_url(u):
    return re.sub(r"^https?://(www\.)?", "https://", u or "").rstrip("/")

def norm_title(t):
    return " ".join((t or "").split())

def matched_keywords(text):
    t = text or ""
    return [k for k in KEYWORDS if k in t]

def get(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        if r.status_code != 200:
            print(f"  ! {url} -> HTTP {r.status_code}", file=sys.stderr)
            return None
        return r.text
    except Exception as e:
        print(f"  ! {url} -> {e}", file=sys.stderr)
        return None

def scrape_site(site):
    html = get(site["url"])
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    pat = re.compile(site["pattern"])
    out, local = [], set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not pat.search(href):
            continue
        title = norm_title(a.get_text(" ", strip=True))
        if len(title) < 15:            # skip nav/thumbnail links with no real title
            continue
        url = href if href.startswith("http") else site["base"] + href
        if url in local:
            continue
        local.add(url)
        kws = matched_keywords(title)
        if not kws:                    # site items require a keyword match
            continue
        out.append({"title":title,"url":url,"source":site["source"],
                    "type":"site","date":TODAY,"keywords":kws})
    print(f"    -> {len(out)} kept", file=sys.stderr)
    return out

def scrape_search(s):
    url = ("https://news.google.com/rss/search?q=" + urllib.parse.quote(s["q"])
           + "&hl=he&gl=IL&ceid=IL:he")
    xml = get(url)
    if not xml:
        return []
    try:
        root = ET.fromstring(xml)
    except Exception as e:
        print(f"    ! parse error: {e}", file=sys.stderr)
        return []
    out = []
    for item in root.findall(".//item"):
        title = norm_title(item.findtext("title"))
        link = (item.findtext("link") or "").strip()
        if len(title) < 10 or not link.startswith("http"):
            continue
        date = TODAY
        pd = item.findtext("pubDate")
        if pd:
            try:
                date = parsedate_to_datetime(pd).date().isoformat()
            except Exception:
                pass
        kws = matched_keywords(title)
        if not s["unconditional"] and not kws:
            continue
        out.append({"title":title,"url":link,"source":s["source"],
                    "type":"google","date":date,"keywords":kws})
    out = out[:8]                                   # cap per search
    print(f"    -> {len(out)} kept", file=sys.stderr)
    return out

def main():
    old = json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else {"items":[]}
    items = old.get("items", [])
    seen_urls   = {norm_url(i["url"]) for i in items}
    seen_titles = {norm_title(i["title"]) for i in items}

    found = []
    for site in SITES:
        print(f"site: {site['source']}", file=sys.stderr)
        found += scrape_site(site)
    for s in SEARCHES:
        print(f"search: {s['source']}", file=sys.stderr)
        found += scrape_search(s)

    new = []
    for i in found:
        u, t = norm_url(i["url"]), norm_title(i["title"])
        if u in seen_urls or t in seen_titles:      # dedup by URL and by title
            continue
        seen_urls.add(u); seen_titles.add(t); new.append(i)

    merged = new + items
    merged.sort(key=lambda i: str(i.get("date","")), reverse=True)   # newest first
    merged = merged[:400]                                            # hard cap

    out = {"updated": datetime.datetime.now().astimezone().isoformat(timespec="minutes"),
           "keywords": KEYWORDS, "items": merged}
    DATA.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"added {len(new)} new; total {len(merged)}", file=sys.stderr)

if __name__ == "__main__":
    main()
