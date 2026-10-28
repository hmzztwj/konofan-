# -*- coding: utf-8 -*-
"""把已解出来的数据打包成一个可离线浏览的静态站点。

输入:  out/masterdata/*.json  (解密后的主数据)
       out/masterdata_csv/*.csv
       out/assets_sorted/**      (导出的图片)
       out/cri_manifest.csv      (CRI 明文名)
       out/story/*.md            (可读剧情脚本)
输出:  site/  (index / characters / story / gallery / tables/<表名>)

全部页面自带数据（不依赖 fetch，直接 file:// 打开即可用）。
"""
import csv
import glob
import html
import json
import os
import shutil

ROOT = r"F:\python_work\逆向"
OUT = os.path.join(ROOT, "out")
SITE = os.path.join(ROOT, "site")
MD = os.path.join(OUT, "masterdata")
CSVD = os.path.join(OUT, "masterdata_csv")
ASSETS = os.path.join(OUT, "assets_sorted")
IMG = os.path.join(SITE, "img")
TBL = os.path.join(SITE, "tables")

MAX_ROWS_PER_TABLE_PAGE = 2000


# ---------- 基础 ----------
def fmt(n):
    try:
        return f"{int(n):,}"
    except Exception:
        return str(n)


def load(name):
    p = os.path.join(MD, name + ".json")
    if not os.path.exists(p):
        return []
    return json.load(open(p, encoding="utf-8")).get("master", [])


def text_map():
    m = {}
    for t in ("assetname", "text", "clienttext"):
        for r in load(t):
            k = r.get("id")
            if k and k not in m:
                v = r.get("text_japanese") or r.get("text") or ""
                if v and v != "0":
                    m[k] = v
    return m


def build_image_index(wanted):
    idx = {}
    for dirpath, _dirs, files in os.walk(ASSETS):
        for f in files:
            if not f.endswith(".png"):
                continue
            parts = f[:-4].split("_")
            if len(parts) < 4:
                continue
            typ = parts[-2]
            name = parts[-1]
            # logo 之类名字里带下划线的，取最后一段即可（我们只查成员/立绘 id）
            if name not in wanted:
                continue
            p = os.path.join(dirpath, f)
            if name not in idx or typ == "Sprite":
                idx[name] = p
    return idx


def link_img(src, dst_name):
    dst = os.path.join(IMG, dst_name)
    os.makedirs(IMG, exist_ok=True)
    if os.path.exists(dst):
        return True
    try:
        os.link(src, dst)
        return True
    except OSError:
        try:
            shutil.copy2(src, dst)
            return True
        except OSError:
            return False


# ---------- 页面模板 ----------
CSS = """
:root{--bg:#12141a;--card:#1b1f28;--line:#2a3040;--fg:#e6e9f0;--dim:#9aa4b8;--acc:#6aa6ff;--acc2:#ff8fb1}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.6 "Noto Sans JP","Microsoft YaHei",system-ui,sans-serif}
header{position:sticky;top:0;z-index:9;background:rgba(18,20,26,.92);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
header .in{max-width:1400px;margin:0 auto;display:flex;gap:18px;align-items:center;padding:12px 20px}
header a{color:var(--fg);text-decoration:none;padding:4px 10px;border-radius:8px}
header a:hover,header a.on{background:#242a38;color:var(--acc)}
h1{font-size:20px;margin:0 14px 0 0}
main{max-width:1400px;margin:0 auto;padding:22px 20px 80px}
.grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fill,minmax(190px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden;cursor:pointer;transition:.15s}
.card:hover{border-color:var(--acc);transform:translateY(-2px)}
.card img{width:100%;display:block;background:#0c0e12}
.card .cap{padding:8px 10px}
.card .cap b{display:block;font-size:14px}
.card .cap span{color:var(--dim);font-size:12px}
.cards{display:grid;gap:10px;grid-template-columns:repeat(auto-fill,minmax(110px,1fr))}
.tag{display:inline-block;padding:1px 7px;border:1px solid var(--line);border-radius:99px;color:var(--dim);font-size:11px;margin-right:4px}
input[type=search],select{background:#0f1218;color:var(--fg);border:1px solid var(--line);border-radius:9px;padding:8px 12px;font:inherit;min-width:240px}
table{width:max-content;min-width:100%;border-collapse:collapse;font-size:13px}
td{max-width:460px}
th,td{padding:6px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{position:sticky;top:0;background:#171b23;color:var(--dim);font-weight:600;cursor:pointer;white-space:nowrap}
tr:hover td{background:#1a1f2a}
.dim{color:var(--dim)}
.wrap{overflow:auto;max-height:72vh;border:1px solid var(--line);border-radius:12px}
.meta{color:var(--dim);font-size:12px}
.pill{background:#232a38;border:1px solid var(--line);border-radius:10px;padding:10px 14px;display:inline-block;margin:0 8px 8px 0}
.pill b{display:block;font-size:20px;color:var(--acc)}
a{color:var(--acc)}
.modal{position:fixed;inset:0;background:rgba(0,0,0,.75);display:none;align-items:center;justify-content:center;padding:24px;z-index:99}
.modal.on{display:flex}
.modal .box{background:var(--card);border:1px solid var(--line);border-radius:16px;max-width:900px;width:100%;max-height:86vh;overflow:auto;padding:20px}
.li{margin:0 0 6px}.who{color:var(--acc);min-width:7em;display:inline-block;vertical-align:top}.say{white-space:pre-wrap}.cue{color:#5c6478;font-size:11px;margin-left:8px}.script{white-space:pre-wrap;font-size:14px;background:#0f1218;border:1px solid var(--line);border-radius:12px;padding:14px;max-height:60vh;overflow:auto}
"""

JS = """
function byId(id){return document.getElementById(id)}
function fmt(n){return (n||0).toLocaleString('ja-JP')}
function filterRows(tbl,q){
  q=q.trim().toLowerCase(); var n=0;
  for(const tr of tbl.tBodies[0].rows){
    const hit=!q||tr.innerText.toLowerCase().includes(q);
    tr.style.display=hit?'':'none'; if(hit)n++;
  }
  const c=byId('cnt'); if(c)c.textContent=n;
}
"""

NAV = [("index.html", "总览"), ("characters.html", "角色"), ("story.html", "剧情"),
       ("gallery.html", "图鉴"), ("tables.html", "数据表")]


def page(title, body, active="", extra_head=""):
    navs = "".join(
        f'<a href="{h}" class="{"on" if h == active else ""}">{n}</a>' for h, n in NAV)
    return f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>{CSS}</style>{extra_head}</head><body>
<header><div class="in"><h1>この素晴らしい世界に祝福を！ファンタスティックデイズ</h1>{navs}</div></header>
<main>{body}</main><script>{JS}</script></body></html>"""


def write(path, s):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(s)


# ---------- 各页 ----------
def build_index(stats, tables):
    pills = "".join(f'<div class="pill"><b>{fmt(v)}</b>{k}</div>' for k, v in stats)
    body = f"""
<h2>离线资料库</h2>
<p class="meta">数据来源：<code>files/Data/MasterData/*.data</code>（AES-256-CBC 解密）+ 
<code>UnityCache</code> 里 2,228 个 UnityFS bundle（21,790 张图）+ <code>bundles/Cri</code>（7,658 个 cpk/usm，已按明文名还原）。</p>
<div>{pills}</div>
<h3 style="margin-top:28px">入口</h3>
<div class="grid">
  <a class="card" href="characters.html" style="text-decoration:none;color:inherit"><div class="cap"><b>角色图鉴</b><span>{stats[0][1]} 名角色 / 全部卡面与语音计数</span></div></a>
  <a class="card" href="story.html" style="text-decoration:none;color:inherit"><div class="cap"><b>剧情目录</b><span>主线 / 活动 / 角色剧情标题与梗概</span></div></a>
  <a class="card" href="gallery.html" style="text-decoration:none;color:inherit"><div class="cap"><b>回忆图鉴</b><span>CG 立绘与剧情影片</span></div></a>
  <a class="card" href="tables.html" style="text-decoration:none;color:inherit"><div class="cap"><b>数据表</b><span>{len(tables)} 张表，支持搜索</span></div></a>
</div>
<h3 style="margin-top:28px">关于这份副本</h3>
<p class="meta">本机数据是部分缓存：catalog 共 23,069 个 bundle，本地仅 2,228 个（剧情文本因此只有 5 章可读）。
MasterData 279 个文件全部完整。密钥与算法见仓库里的分析报告。</p>
"""
    write(os.path.join(SITE, "index.html"), page("总览", body, "index.html"))


def build_characters(chars, tmap):
    js = json.dumps(chars, ensure_ascii=False)
    body = f"""
<h2>角色 <span class="meta" id="cnt">{len(chars)}</span></h2>
<p><input type="search" id="q" placeholder="搜索角色名 / 武器 / 卡名"></p>
<div class="grid" id="g"></div>
<div class="modal" id="m"><div class="box" id="mb"></div></div>
<script>
const DATA = {js};
const TMAP = {json.dumps(tmap, ensure_ascii=False)};
function t(k){{return TMAP[k]||k||''}}
function render(q){{
  q=(q||'').toLowerCase();
  const g=document.getElementById('g'); g.innerHTML='';
  let n=0;
  for(const c of DATA){{
    const hay=(c.name+' '+c.weapon+' '+c.members.map(m=>m.name).join(' ')).toLowerCase();
    if(q&&!hay.includes(q))continue; n++;
    const d=document.createElement('div'); d.className='card';
    d.innerHTML=`<img loading="lazy" src="${{c.icon||''}}" onerror="this.style.display='none'">
      <div class="cap"><b>${{c.name}}</b><span>${{c.weapon}} · 卡 ${{c.members.length}} · 语音 ${{c.voices}}</span></div>`;
    d.onclick=()=>open(c); g.appendChild(d);
  }}
  document.getElementById('cnt').textContent=n;
}}
function open(c){{
  const b=document.getElementById('mb');
  b.innerHTML=`<h2 style="margin-top:0">${{c.name}} <span class="tag">${{c.weapon}}</span></h2>
    <p class="meta">${{c.members.length}} 张卡 · ${{c.voices}} 条语音 · ${{c.stories}} 段角色剧情</p>
    <div class="cards">` + c.members.map(m=>`<div class="card"><img loading="lazy" src="${{m.icon}}" onerror="this.style.display='none'">
      <div class="cap"><b style="font-size:12px">${{m.name}}</b><span>★${{m.rare}}</span></div></div>`).join('') + `</div>`;
  document.getElementById('m').classList.add('on');
}}
document.getElementById('m').onclick=e=>{{if(e.target.id==='m')e.currentTarget.classList.remove('on')}};
document.getElementById('q').oninput=e=>render(e.target.value);
render('');
</script>
"""
    write(os.path.join(SITE, "characters.html"), page("角色", body, "characters.html"))


def build_script_pages():
    """把 out/story/*.md 渲染成 site/script_*.html，并在 story 页给出链接。"""
    import re as _re
    line_re = _re.compile(r"^\*\*(.+?)\*\*\s*[:：]\s*(.*?)\s*(?:<!--\s*(.*?)\s*-->)?$")
    links = []
    for p in sorted(glob.glob(os.path.join(OUT, "story", "*.md"))):
        base = os.path.splitext(os.path.basename(p))[0]
        txt = open(p, encoding="utf-8").read()
        out, n = [], 0
        for ln in txt.splitlines():
            m = line_re.match(ln.strip())
            if m:
                who, say, cue = m.group(1), m.group(2), m.group(3) or ""
                n += 1
                out.append(
                    '<p class="li"><b class="who">' + html.escape(who) + '</b>'
                    '<span class="say">' + html.escape(say) + '</span>'
                    + (f'<span class="cue">{html.escape(cue)}</span>' if cue else "") + "</p>")
            elif ln.startswith("## "):
                out.append(f"<h3>{html.escape(ln[3:])}</h3>")
            elif ln.strip():
                out.append(f'<p class="dim">{html.escape(ln)}</p>')
        body = (f'<h2>{html.escape(base)}</h2>'
                f'<p class="meta">{n} 句台词 · <a href="story.html">返回剧情目录</a>'
                f' · <a href="../out/story/{html.escape(os.path.basename(p))}">原始 md</a></p>'
                f'<div class="script">{"".join(out)}</div>')
        write(os.path.join(SITE, f"script_{base}.html"), page(base, body, "story.html"))
        links.append((f"script_{base}.html", base, n))
    return links


def build_story(main, event, member, scripts):
    def rows(lst, kind):
        out = []
        for r in lst:
            out.append({"id": r.get("id"), "title": r.get("title", ""), "short": r.get("short", ""),
                        "chapter": r.get("chapter", ""), "part": r.get("part", ""),
                        "summary": r.get("summary", ""), "kind": kind})
        return out
    data = rows(main, "主线") + rows(event, "活动") + rows(member, "角色")
    script_links = "".join(
        f'<a href="{h}">{html.escape(n)}（{c} 句）</a> ' for h, n, c in scripts)
    body = f"""
<h2>剧情 <span class="meta" id="cnt">{len(data)}</span></h2>
<p class="meta">本地缓存里可读的完整剧本：{script_links or '（无）'}</p>
<p><input type="search" id="q" placeholder="搜索标题 / 梗概"> <select id="k">
  <option value="">全部</option><option>主线</option><option>活动</option><option>角色</option></select></p>
<div class="wrap"><table id="t"><thead><tr><th>类型</th><th>ID</th><th>标题</th><th>梗概</th></tr></thead><tbody></tbody></table></div>
<script>
const DATA = {json.dumps(data, ensure_ascii=False)};
function render(){{
  const q=document.getElementById('q').value.toLowerCase().trim();
  const k=document.getElementById('k').value;
  const tb=document.querySelector('#t tbody'); tb.innerHTML='';
  let n=0;
  for(const r of DATA){{
    if(k&&r.kind!==k)continue;
    const hay=(r.title+' '+r.summary+' '+r.id).toLowerCase();
    if(q&&!hay.includes(q))continue;
    n++;
    const tr=document.createElement('tr');
    tr.innerHTML=`<td><span class="tag">${{r.kind}}</span></td><td class="dim">${{r.id}}</td>
      <td>${{r.title||r.short||''}}</td><td class="dim">${{r.summary||''}}</td>`;
    tb.appendChild(tr);
  }}
  document.getElementById('cnt').textContent=n;
}}
document.getElementById('q').oninput=render; document.getElementById('k').onchange=render; render();
</script>
"""
    write(os.path.join(SITE, "story.html"), page("剧情", body, "story.html"))


def build_gallery(stills, movies, backgrounds=None):
    backgrounds = backgrounds or []
    bgcards = "".join(
        f'<div class="card"><img loading="lazy" src="{b["img"]}">'
        f'<div class="cap"><b>背景 {b["id"]}</b><span>{b["size"]}</span></div></div>'
        for b in backgrounds)
    cards = []
    have = miss = 0
    for s in stills:
        if s["img"]:
            have += 1
            cards.append(f'<div class="card"><img loading="lazy" src="{s["img"]}">'
                         f'<div class="cap"><b>{s["title"]}</b><span>still {s["id"]}</span></div></div>')
        else:
            miss += 1
            cards.append(f'<div class="card" style="opacity:.45"><div class="cap" style="height:96px">'
                         f'<b>{s["title"]}</b><span>still {s["id"]} · 本副本未缓存</span></div></div>')
    mv = "".join(f'<tr><td>{html.escape(m["title"])}</td><td class="dim">{html.escape(m["artist"])}</td>'
                 f'<td><code>{html.escape(m["usm"])}</code></td></tr>' for m in movies)
    body = f"""
<h2>回忆图鉴</h2>
<h3>CG / 立绘（{len(stills)}，其中 {have} 张本地有图）</h3>
<div class="grid">{''.join(cards) or '<p class="meta">没有找到对应图片</p>'}</div>
<h3 style="margin-top:26px">剧情背景（{len(backgrounds)} 张，本地缓存）</h3>
<div class="grid">{bgcards}</div>
<h3 style="margin-top:26px">剧情影片（{len(movies)}）</h3>
<div class="wrap"><table><thead><tr><th>标题</th><th>歌手/署名</th><th>对应视频文件</th></tr></thead><tbody>{mv}</tbody></table></div>
"""
    write(os.path.join(SITE, "gallery.html"), page("图鉴", body, "gallery.html"))


def build_tables(tables):
    rows = "".join(
        f'<tr><td><a href="tables/{html.escape(t["name"])}.html">{html.escape(t["name"])}</a></td>'
        f'<td class="dim">{fmt(t["rows"])}</td><td class="dim">{t["cols"]}</td>'
        f'<td><a href="../{html.escape(t["csv"])}">CSV</a></td></tr>'
        for t in tables)
    body = f"""
<h2>数据表 <span class="meta" id="cnt">{len(tables)}</span></h2>
<p><input type="search" id="q" placeholder="搜索表名"></p>
<div class="wrap"><table id="t"><thead><tr><th>表</th><th>行数</th><th>列数</th><th>下载</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<script>document.getElementById('q').oninput=e=>filterRows(document.getElementById('t'),e.target.value);</script>
"""
    write(os.path.join(SITE, "tables.html"), page("数据表", body, "tables.html"))


def build_table_page(name, header, rows, total, csvrel, tmap=None):
    tmap = tmap or {}
    data = [[r.get(h, "") for h in header] for r in rows]
    used = {}
    for row in data:
        for v in row:
            if v and v in tmap:
                used[v] = tmap[v]
    head = "".join(f"<th>{html.escape(h)}</th>" for h in header)
    js = """
const D = %s;
const MAP = %s;
const tb=document.getElementById('tb');
const esc=s=>String(s==null?'':s).replace(/[<>&]/g,x=>({'<':'&lt;','>':'&gt;','&':'&amp;'}[x]));
tb.innerHTML = D.map(r=>'<tr>'+r.map(c=>{const v=esc(c); const m=MAP[c];
  return m?('<td title="'+v+'">'+esc(m)+'</td>'):('<td>'+v+'</td>')}).join('')+'</tr>').join('');
document.getElementById('q').oninput=e=>filterRows(document.getElementById('t'),e.target.value);
""" % (json.dumps(data, ensure_ascii=False), json.dumps(used, ensure_ascii=False))
    body = f"""
<h2>{html.escape(name)} <span class="meta">共 {fmt(total)} 行，这里显示前 {fmt(len(rows))} 行</span></h2>
<p><input type="search" id="q" placeholder="在本表内搜索"> <span class="meta">匹配 <b id="cnt">{len(rows)}</b> 行</span>
 · <a href="../{html.escape(csvrel)}">下载完整 CSV</a> · <a href="../tables.html">返回列表</a></p>
<div class="wrap"><table id="t"><thead><tr>{head}</tr></thead><tbody id="tb"></tbody></table></div>
<script>{js}</script>
"""
    write(os.path.join(TBL, name + ".html"), page(name, body, "tables.html"))


# ---------- 组装 ----------
def main():
    os.makedirs(SITE, exist_ok=True)
    tmap = text_map()
    for k in list(tmap):
        if isinstance(tmap[k], str) and (tmap[k].startswith("ASSET_") or tmap[k].startswith("STORY_")
                                         or tmap[k].startswith("TEXT_") or tmap[k].startswith("GALLERY_")):
            tmap.pop(k)

    def t(k):
        if not k or k == "0":
            return ""
        return tmap.get(k, "")
    chars_raw = load("character")
    members = load("member")
    voices = load("voice")
    stories_m = load("story_member")
    charmembers = {}
    for m in members:
        charmembers.setdefault(m.get("character_id", ""), []).append(m)
    vcount = {}
    for v in voices:
        vcount[v.get("chara_id", "")] = vcount.get(v.get("chara_id", ""), 0) + 1
    scount = {}
    for s in stories_m:
        scount[s.get("chara_id", "")] = scount.get(s.get("chara_id", ""), 0) + 1

    stills_raw = load("gallery_still")
    want = set()
    for m in members:
        want.add(m.get("id", ""))
    for s in stills_raw:
        want.add(s.get("still", ""))
    imgidx = build_image_index(want)
    print(f"[+] 图片索引命中 {len(imgidx)}/{len(want)}")

    chars = []
    for c in chars_raw:
        cid = c.get("id", "")
        ms = charmembers.get(cid, [])
        items = []
        for m in ms:
            mid = m.get("id", "")
            src = imgidx.get(mid)
            rel = ""
            if src and link_img(src, f"mem_{mid}.png"):
                rel = f"img/mem_{mid}.png"
            items.append({"id": mid, "name": t(m.get("name")) or mid,
                          "rare": m.get("rare", "?"), "icon": rel})
        icon = next((m["icon"] for m in items if m["icon"]), "")
        chars.append({"id": cid, "name": t(c.get("name")) or cid,
                      "weapon": c.get("weapon_type", ""), "icon": icon,
                      "members": items, "voices": vcount.get(cid, 0),
                      "stories": scount.get(cid, 0)})
    chars.sort(key=lambda x: (x["id"] or "999"))
    build_characters(chars, {})

    def srows(lst):
        out = []
        for r in lst:
            out.append({"id": r.get("id", ""), "title": t(r.get("title_text")),
                        "short": t(r.get("short_title_text")), "part": r.get("part", ""),
                        "chapter": t(r.get("chapter_text")),
                        "summary": t(r.get("summary_text"))})
        return out
    build_story(srows(load("story_main")), srows(load("story_event")), srows(stories_m), build_script_pages())

    # 图鉴：still -> 图 / 剧情标题
    story_title = {}
    for r in load("story_main"):
        story_title[r.get("id", "")] = t(r.get("title_text")) or r.get("id", "")
    stills = []
    for s in stills_raw:
        sid = s.get("still", "")
        src = imgidx.get(sid)
        rel = ""
        if src and link_img(src, f"still_{sid}.png"):
            rel = f"img/still_{sid}.png"
        stills.append({"id": sid, "img": rel,
                       "title": story_title.get(s.get("story_id", ""), "") or f"still {sid}"})
    movies = []
    for m in load("gallery_movie"):
        raw = m.get("movie", "")
        usm = raw.split("\u2015")[-1].split("—")[-1]
        if "movie_" in raw:
            usm = "movie_" + raw.split("movie_", 1)[1]
        movies.append({"title": t(m.get("title")), "artist": t(m.get("artist_name")),
                       "usm": usm + ".usm"})
    backgrounds = []
    bgdir = os.path.join(ASSETS, "Story", "Prefab", "Background")
    for f in sorted(os.listdir(bgdir)) if os.path.isdir(bgdir) else []:
        if not (f.endswith(".png") and "_Sprite_" in f):
            continue
        bid = f.split("_Sprite_")[1][:-4]
        src = os.path.join(bgdir, f)
        if link_img(src, f"bg_{bid}.png"):
            sz = os.path.getsize(src)
            backgrounds.append({"id": bid, "img": f"img/bg_{bid}.png",
                                "size": f"{sz/1024:.0f} KB"})
    build_gallery(stills, movies, backgrounds)

    # 数据表
    tables = []
    for p in sorted(glob.glob(os.path.join(CSVD, "*.csv"))):
        name = os.path.splitext(os.path.basename(p))[0]
        with open(p, encoding="utf-8-sig", newline="") as f:
            rd = csv.DictReader(f)
            header = rd.fieldnames or []
            allrows = list(rd)
        build_table_page(name, header, allrows[:MAX_ROWS_PER_TABLE_PAGE], len(allrows),
                         os.path.relpath(p, ROOT).replace("\\", "/"), tmap)
        tables.append({"name": name, "rows": len(allrows), "cols": len(header),
                       "csv": os.path.relpath(p, ROOT).replace("\\", "/")})
    build_tables(tables)

    stats = [("角色", len(chars)), ("卡（成员）", len(members)), ("数据表", len(tables)),
             ("数据行", sum(x["rows"] for x in tables)), ("文本条目", len(tmap)),
             ("CG/立绘", len(stills)), ("剧情条目", len(load("story_main")) + len(load("story_event")) + len(stories_m))]
    build_index(stats, tables)
    print(f"[+] site -> {SITE}  页面 {3 + 1 + len(tables) + 1}")


if __name__ == "__main__":
    main()
