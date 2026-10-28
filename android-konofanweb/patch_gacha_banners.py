"""给「卡池一览」生成带池名的横幅图，并把它写进本地站点。

背景：这个单机版站点里 37 个卡池的 banner 全指向同一张占位图
(`yuanban/sprite/webp/TitleBG__13d146.webp`，画面上印着「ゲームタイトル配置」)，
而卡池一览的格子是**纯图片**（没有文字），所以整列看起来是空的。

做法：
1. 用 Pillow 按卡池 id/名字/开放时间画 801x481 的横幅（深色渐变 + 中文/日文名）；
2. 输出到 `site/yuanban/gacha/banner/pool_<id>.webp`；
3. 把 `site/assets/gacha*.js` 里那条数据补丁的 banner 字段按 id 改成本地图片。

用法：
  python tools/patch_gacha_banners.py --site ../../sqweb_offline/site --pools out/pools.json
  python tools/patch_gacha_banners.py --restore          # 从 .bak 还原
"""
import argparse
import io
import json
import os
import re
import sys

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\meiryo.ttc",
]

PALETTES = [
    ((28, 36, 66), (86, 60, 128)),
    ((22, 44, 48), (52, 106, 96)),
    ((52, 32, 40), (132, 66, 74)),
    ((32, 32, 48), (96, 84, 132)),
    ((38, 30, 24), (120, 92, 56)),
]


def load_font(size):
    from PIL import ImageFont
    for p in FONT_CANDIDATES:
        if os.path.isfile(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def wrap(draw, text, font, max_w):
    lines, cur = [], ""
    for ch in text:
        trial = cur + ch
        if draw.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def render(pool, out_path, w=801, h=481):
    from PIL import Image, ImageDraw
    idx = int(pool.get("id", "0")) % len(PALETTES)
    c1, c2 = PALETTES[idx]
    img = Image.new("RGB", (w, h), c1)
    d = ImageDraw.Draw(img)
    # 斜向渐变
    for y in range(h):
        t = y / (h - 1)
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        d.line([(0, y), (w, y)], fill=(r, g, b))
    # 右下角高光
    for i in range(240):
        a = int(30 * (1 - i / 240))
        d.ellipse([w - 320 + i, h - 260 + i, w + 120 - i, h + 120 - i],
                  outline=(255, 255, 255)) if False else None
    # 顶部细线
    d.rectangle([0, 0, w, 6], fill=(255, 255, 255))

    name = (pool.get("name") or pool.get("nameJa") or pool.get("id") or "").strip()
    sub = (pool.get("schedule") or "").strip()
    font_big = load_font(64)
    font_small = load_font(26)

    lines = wrap(d, name, font_big, w - 120)[:3]
    total_h = len(lines) * 78
    y = (h - total_h) // 2 - 20
    for ln in lines:
        tw = d.textlength(ln, font=font_big)
        x = (w - tw) / 2
        d.text((x + 3, y + 3), ln, font=font_big, fill=(0, 0, 0))
        d.text((x, y), ln, font=font_big, fill=(255, 255, 255))
        y += 78

    if sub:
        tw = d.textlength(sub, font=font_small)
        d.text(((w - tw) / 2, h - 74), sub, font=font_small, fill=(226, 232, 240))

    pid = str(pool.get("id", ""))
    d.text((26, h - 46), "ID " + pid, font=font_small, fill=(200, 206, 220))

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path, "WEBP", quality=92, method=4)


BANNER_KEYS = ("banner", "bannerJa")


def patch_js(path, mapping):
    """把数据补丁里每个卡池的 banner 换成我们生成的图片。"""
    src = io.open(path, encoding="utf-8", errors="surrogateescape").read()
    orig = src
    hits = 0
    for pid, rel in mapping.items():
        # 匹配 "id":"<pid>" 到下一个 "banner":"..."，只替换该对象内的 banner
        pat = re.compile(r'("id":\s*"%s"[^{}]*?"banner":\s*")([^"]*)(")' % re.escape(pid))
        src, n = pat.subn(lambda m: m.group(1) + rel + m.group(3), src, count=1)
        hits += n
    if src != orig:
        bak = path + ".bak"
        if not os.path.exists(bak):
            io.open(bak, "w", encoding="utf-8", errors="surrogateescape").write(orig)
        io.open(path, "w", encoding="utf-8", errors="surrogateescape").write(src)
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default=os.path.join(os.path.dirname(__file__), "..", "..", "sqweb_offline", "site"))
    ap.add_argument("--pools", default=os.path.join(os.path.dirname(__file__), "out", "pools.json"))
    ap.add_argument("--restore", action="store_true")
    args = ap.parse_args()

    site = os.path.abspath(args.site)
    assets = os.path.join(site, "assets")

    if args.restore:
        n = 0
        for f in os.listdir(assets):
            if f.endswith(".js.bak"):
                os.replace(os.path.join(assets, f), os.path.join(assets, f[:-4]))
                n += 1
        print("restored", n)
        return

    pools = json.load(io.open(args.pools, encoding="utf-8"))
    out_dir = os.path.join(site, "yuanban", "gacha", "banner")
    mapping = {}
    for p in pools:
        pid = str(p.get("id"))
        name = out_dir + os.sep + ("pool_%s.webp" % pid)
        render(p, name)
        # 数据补丁里的路径相对于 yuanban/
        mapping[pid] = "gacha/banner/pool_%s.webp" % pid
    print("rendered", len(mapping), "banners ->", out_dir)

    total = 0
    for f in sorted(os.listdir(assets)):
        if re.match(r"gacha.*\.js$", f):
            total += patch_js(os.path.join(assets, f), mapping)
    print("patched banner fields:", total)


if __name__ == "__main__":
    main()
