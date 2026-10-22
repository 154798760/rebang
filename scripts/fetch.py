# -*- coding: utf-8 -*-
"""今日热榜快览 抓取脚本：9 源（4 官网直连 + 5 tophub 中转），纯标准库。"""
import re, json, os, html as htmlmod, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(HERE), "data")
os.makedirs(DATA_DIR, exist_ok=True)
OUT = os.path.join(DATA_DIR, "tophub_raw.json")
MED_OUT = os.path.join(DATA_DIR, "med_raw.json")

def get(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "ignore")

def parse_tophub(h):
    rows = []
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', h, re.S):
        rm = re.search(r'<td[^>]*align="center"[^>]*>\s*(\d+)\.?', tr) or re.search(r'<td[^>]*>\s*(\d+)\.?\s*</td>', tr)
        if not rm: continue
        rank = int(rm.group(1))
        anchors = re.findall(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', tr, re.S)
        best = None
        for url, inner in anchors:
            text = htmlmod.unescape(re.sub(r'<[^>]+>', '', inner)).strip()
            if not text or len(text) < 3: continue
            if best is None or len(text) > len(best[0]): best = (text, url)
        if not best: continue
        title, url = best
        heat = ""
        for cls in ['item-extra', 'item-desc']:
            m = re.search(cls + r'">([^<]+)</div>', tr)
            if m: heat = m.group(1).strip(); break
        if not heat:
            m = re.search(r'class="ws"[^>]*>\s*([^<]{1,30})\s*<', tr)
            if m: heat = m.group(1).strip()
        rows.append({"r": rank, "t": title, "u": url, "h": heat})
    return rows

def fmt_wan(n, dec=1):
    return f"{float(n) / 10000:.{dec}f}万"

def fetch_toutiao():
    d = json.loads(get("https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"))
    return [{"r": i, "t": it['Title'].strip(), "u": it.get('Url', ''), "h": fmt_wan(it.get('HotValue', 0))}
            for i, it in enumerate(d.get('data', [])[:10], 1)]

def fetch_bili():
    d = json.loads(get("https://api.bilibili.com/x/web-interface/popular?ps=20&pn=1"))
    return [{"r": i, "t": v['title'].strip(), "u": f"https://www.bilibili.com/video/{v['bvid']}", "h": fmt_wan(v['stat']['view'])}
            for i, v in enumerate(d['data']['list'][:10], 1)]

def fetch_guokr():
    h = get("https://www.guokr.com/")
    m = re.search(r'window\.INITIAL_STORE\s*=\s*(\{.*?\});?\s*</script>', h, re.S)
    arts = json.loads(m.group(1))['articleListStore']['articleList'][:10]
    return [{"r": i, "t": a['title'].strip(), "u": f"https://www.guokr.com/article/{a['id']}/", "h": ""}
            for i, a in enumerate(arts, 1)]

def fetch_med():
    h = get("https://www.yxj.org.cn/")
    idx = h.find('24h最热')
    seg = h[idx:idx + 8000] if idx > 0 else h
    items = []
    for m in re.finditer(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', seg, re.S):
        text = htmlmod.unescape(re.sub(r'<[^>]+>', '', m.group(2))).strip()
        url = m.group(1)
        if text and len(text) >= 8 and not any(k in url for k in ['javascript', '#']) \
                and not any(k in text for k in ['登录', '注册', '更多', '查看全部', '下载']):
            items.append({"t": text, "u": url if url.startswith('http') else 'https://www.yxj.org.cn' + url})
    seen, dedup = set(), []
    for it in items:
        if it['t'] not in seen:
            seen.add(it['t']); dedup.append(it)
    return [{"r": i + 1, **it} for i, it in enumerate(dedup[:10])]

TOPHUB_SOURCES = [
    ("微博热搜", "https://tophub.today/n/KqndgxeLl9"),
    ("知乎热榜", "https://tophub.today/n/mproPpoq6O"),
    ("澎湃热榜", "https://tophub.today/n/wWmoO5Rd4E"),
    ("抖音总榜", "https://tophub.today/n/DpQvNABoNE"),
    ("36氪24小时热榜", "https://tophub.today/n/Q1Vd5Ko85R"),
]

out = {}
for name, url in TOPHUB_SOURCES:
    try:
        rows = parse_tophub(get(url)); out[name] = rows
        f = rows[0] if rows else {}
        print(f"[tophub] {name}: {len(rows)} | 1.{f.get('t','')[:20]} | [{f.get('h','')[:10]}]")
    except Exception as e:
        print(f"[tophub] {name}: ERR {e}"); out[name] = []

for name, fn in [("今日头条热榜", fetch_toutiao), ("哔哩哔哩全站日榜", fetch_bili), ("果壳科学人", fetch_guokr)]:
    try:
        rows = fn(); out[name] = rows
        f = rows[0] if rows else {}
        print(f"[direct] {name}: {len(rows)} | 1.{f.get('t','')[:20]} | [{f.get('h','')[:10]}]")
    except Exception as e:
        print(f"[direct] {name}: ERR {e}"); out[name] = []

try:
    med = fetch_med(); out["医学界"] = med
    json.dump({"医学界": med}, open(MED_OUT, 'w'), ensure_ascii=False, indent=1)
    print(f"[direct] 医学界: {len(med)} | 1.{med[0]['t'][:20] if med else ''}")
except Exception as e:
    print(f"[direct] 医学界: ERR {e}"); out["医学界"] = []

json.dump(out, open(OUT, 'w'), ensure_ascii=False, indent=1)
print("SAVED")
