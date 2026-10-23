# -*- coding: utf-8 -*-
"""今日热榜快览 建页脚本：读 data JSON -> 替换模板 index.html 的 DATA/FETCH_TIME/历史栏 -> 存当天快照并清理 15 天前。"""
import json, re, os, shutil, datetime, zoneinfo

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HTML = os.path.join(ROOT, "index.html")
HIST = os.path.join(ROOT, "history")
DATA = os.path.join(ROOT, "data")
os.makedirs(HIST, exist_ok=True)

now = datetime.datetime.now(zoneinfo.ZoneInfo('Asia/Shanghai'))  # 北京时间
FETCH = now.strftime("%Y-%m-%d %H:%M")
TODAY = now.strftime("%Y-%m-%d")

raw = json.load(open(os.path.join(DATA, "tophub_raw.json"), encoding="utf-8"))
med = json.load(open(os.path.join(DATA, "med_raw.json"), encoding="utf-8"))

def clean(s):
    s = re.sub(r'[\uD800-\uDFFF]', '', s)
    s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', s)
    s = s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ').replace('\r', ' ').strip()
    return s

def clean_t(s):
    s = re.sub(r'\s+\d{4}-\d{2}-\d{2}', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return clean(s)

SRC_META = {
    "微博热搜": {"color": "#e6162d", "icon": "微", "src": "https://s.weibo.com/top/summary"},
    "知乎热榜": {"color": "#0f6fea", "icon": "知", "src": "https://www.zhihu.com/hot"},
    "今日头条热榜": {"color": "#e82d2d", "icon": "头", "src": "https://www.toutiao.com/trending/"},
    "澎湃热榜": {"color": "#0072bc", "icon": "澎", "src": "https://www.thepaper.cn/"},
    "抖音总榜": {"color": "#111", "icon": "抖", "src": "https://www.douyin.com/hot/"},
    "哔哩哔哩全站日榜": {"color": "#fb7299", "icon": "B", "src": "https://www.bilibili.com/v/popular/rank/all"},
    "36氪24小时热榜": {"color": "#2e6be6", "icon": "36", "src": "https://36kr.com/hot-list/catalog"},
    "果壳科学人": {"color": "#137752", "icon": "果", "src": "https://www.guokr.com/"},
    "医学界": {"color": "#0e8f6a", "icon": "医", "src": "https://www.yxj.org.cn/"},
}
CATS = {
    "全网热搜": ["微博热搜", "知乎热榜", "今日头条热榜", "澎湃热榜"],
    "视频热榜": ["抖音总榜", "哔哩哔哩全站日榜"],
    "科技与AI": ["36氪24小时热榜", "果壳科学人"],
    "医药健康": ["医学界"],
}

def heat_fmt(h, src):
    h = clean(h)
    if "次播放" in h:
        m = re.match(r'(\d+)', h)
        if m: return f"{int(m.group(1)) / 10000:.0f}万"
    return h

blocks = []
for cat, names in CATS.items():
    items = []
    for name in names:
        rows = raw.get(name) or med.get(name) or []
        rows = rows[:10]
        meta = SRC_META[name]
        item_rows = []
        for r in rows:
            t = clean_t(r["t"]); u = r["u"].replace('&', '&')
            h = heat_fmt(r.get("h", ""), name)
            item_rows.append(f'{{t:"{t}", u:"{u}", h:"{h}"}}')
        items.append(f'  {{ name:"{name}", color:"{meta["color"]}", icon:"{meta["icon"]}", src:"{meta["src"]}", rows:[\n    '
                     + ",\n    ".join(item_rows) + "\n  ]}")
    blocks.append(f'{{ cat:"{cat}", items:[\n' + ",\n".join(items) + "\n]}")
data_js = "const DATA = [\n" + ",\n".join(blocks) + "\n];"

# 历史栏：扫描 history/ 现有快照，最近 15 天（含今天）
existing = {f[:-5] for f in os.listdir(HIST) if f.endswith('.html') and len(f) == 15}
dates = sorted(({TODAY} | existing))[-15:]
hist_links = "".join(f'<a class="hist-link" href="history/{d}.html">{d}</a>' for d in dates)
hist_bar = ('<div class="hist-bar"><span class="hist-tag">历史数据</span>'
            f'<div class="hist-links">{hist_links}</div></div>')
hist_bar = hist_bar.replace(f'history/{TODAY}.html', f'history/{TODAY}.html" class="hist-link cur"')

html = open(HTML, encoding='utf-8').read()
html = re.sub(r'const FETCH_TIME = "[^"]*";', f'const FETCH_TIME = "{FETCH}";', html)
start = html.index('const DATA = [')
end = html.index('const catOrder')
html = html[:start] + data_js + "\n\n" + html[end:]
assert '<!-- HIST_BAR -->' in html
html = html.replace('<!-- HIST_BAR -->', hist_bar, 1)

open(HTML, 'w', encoding='utf-8').write(html)
print("HTML updated | entries:", data_js.count('{t:"'), "| cats:", len(blocks), "| FETCH:", FETCH)

snap = os.path.join(HIST, f'{TODAY}.html')
shutil.copy(HTML, snap)
kept = set(dates)
for f in os.listdir(HIST):
    if f.endswith('.html') and f[:-5] not in kept:
        os.remove(os.path.join(HIST, f))
print("snapshot:", snap, "| history:", sorted(os.listdir(HIST)))
