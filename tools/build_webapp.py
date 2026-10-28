# -*- coding: utf-8 -*-
"""把解密后的 MasterData + 导出的美术资源，打包成本地 Web 客户端用的数据/图片。

产物:
  F:\\python_work\\逆向\\webapp\\data.js     window.KD = {...}  (普通 script, file:// 可用)
  F:\\python_work\\逆向\\webapp\\img\\*.png   硬链接到 out/assets_sorted 里的素材

用法: python tools\\build_webapp.py
"""
import json, os, re, glob, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "out", "masterdata")
A = os.path.join(ROOT, "out", "assets_sorted")
W = os.path.join(ROOT, "webapp")
IMG = os.path.join(W, "img")


def load(name):
    p = os.path.join(D, name + ".json")
    if not os.path.exists(p):
        return []
    return json.load(open(p, encoding="utf-8")).get("master") or []


def i(v, d=0):
    try:
        return int(float(v))
    except Exception:
        return d


def f(v, d=0.0):
    try:
        return float(v)
    except Exception:
        return d


def main():
    os.makedirs(IMG, exist_ok=True)

    # ---------- 文本 ----------
    text = {}
    for t in ("text", "assetname", "clienttext"):
        for r in load(t):
            k = r.get("id")
            v = (r.get("text_japanese") or "").strip()
            if k and v and v != "0":
                text[k] = v

    # ---------- 角色 / 成员 ----------
    chars = {c["id"]: c for c in load("character")}
    member_raw = load("member")

    # ---------- 技能 ----------
    ac = {r["skill_id"]: r for r in load("skill_ac")}
    ac_det = {}
    for r in load("skill_ac_details"):
        ac_det.setdefault(r["skill_id"], r)      # 每个技能取第一条（lv1）
    sp = {}
    for r in load("skill_sp_details"):
        sp.setdefault(r["skill_id"], r)

    def skill_pack(sid, kind="ac"):
        r = ac.get(sid) if kind == "ac" else None
        det = ac_det.get(sid) if kind == "ac" else sp.get(sid)
        if not det:
            return None
        return {
            "id": sid,
            "name": text.get(det.get("skill_name", ""), det.get("skill_name", "")) or ("スキル " + sid),
            "desc": text.get(det.get("skill_flavor_text", ""), "") or "",
            "type": det.get("type", "atk_physics"),
            "attr": det.get("attribute", "0"),
            "target": det.get("target", "enemy_aiming"),
            "num": i(det.get("target_num"), 1),
            "vmin": i(det.get("value_min", det.get("value", 0))),
            "vmax": i(det.get("value_max", det.get("value", 0))),
            "v2min": i(det.get("value2_min", det.get("value2", 0))),
            "v2max": i(det.get("value2_max", det.get("value2", 0))),
            "prob": i(det.get("probability"), 100),
            "unlock": i(det.get("unlock_lv"), 1),
            "icon": str(r.get("skill_icon", "0")) if r else "0",
        }

    # ---------- 敌人 ----------
    e_det = {}
    for r in load("skill_enemy_details"):
        e_det.setdefault(r["skill_id"], r)
    enemy_ai = {}
    for r in load("battle_enemy_ai"):
        enemy_ai.setdefault(r["ai_id"], []).append(r)

    enemies = {}
    for e in load("battle_enemy"):
        eid = e["id"]
        skills = []
        for k in ("skill_id1", "skill_id2", "skill_id3"):
            sid = e.get(k, "0")
            if sid in ("0", ""):
                continue
            d = e_det.get(sid)
            if not d:
                continue
            skills.append({
                "id": sid,
                "name": text.get(d.get("skill_name", ""), d.get("skill_name", "")) or sid,
                "type": d.get("type", "atk_physics"),
                "target": d.get("target", "enemy_aiming"),
                "num": i(d.get("target_num"), 1),
                "value": i(d.get("value"), 100),
                "v2": i(d.get("value2"), 0),
                "prob": i(d.get("probability"), 100),
            })
        enemies[eid] = {
            "id": eid, "name": text.get(e.get("name", ""), e.get("name", "")) or ("敵 " + eid),
            "shape": e.get("shape", "0"), "lv": i(e["lv"], 1),
            "hp": i(e["hp"], 100), "atk": i(e["attack"], 10), "def": i(e["defense"], 10),
            "matk": i(e["magicattak"], 10), "mdef": i(e["magicdefence"], 10),
            "agi": i(e["agility"], 10), "sp": i(e.get("sp_up"), 0), "spTime": i(e.get("sp_up_time"), 0),
            "boss": i(e.get("boss_flag"), 0), "skills": skills,
            "ai": [{"skill": r["skill_id_1"], "w": i(r["weight_1"])} for r in enemy_ai.get(e.get("enemy_ai_id", "0"), [])][:3],
        }

    # ---------- 波次 / 关卡 ----------
    waves = {}
    for w in load("battle_wave"):
        ids = [w.get("enemy_id%d" % n, "0") for n in range(1, 6)]
        waves[w["wave_id"]] = [x for x in ids if x != "0" and x in enemies]

    areas = {}
    for a in load("mainquest_area"):
        areas[a["id"]] = {"id": a["id"], "part": i(a.get("part_id"), 1),
                          "title": text.get(a.get("title", ""), a.get("title", "")) or ("エリア " + a["id"])}

    stages = []
    for s in load("mainquest_stage"):
        wid = [s.get("wave_id%d" % n, "0") for n in (1, 2, 3)]
        wv = [waves.get(x) for x in wid if x != "0"]
        wv = [x for x in wv if x]
        if not wv:
            continue
        stages.append({
            "id": s["id"], "area": s.get("area_id", "1"), "stage": i(s.get("stage_id"), 0),
            "title": text.get(s.get("title", ""), s.get("title", "")) or ("ステージ " + s["id"]),
            "stamina": i(s.get("stamina"), 1), "graphic": s.get("graphic", "0"),
            "bgm": s.get("bgm", "0"), "boss": i(s.get("boss"), 0),
            "unlock": s.get("unlock_clearstage", "0"),
            "waves": wv,
        })
    stages.sort(key=lambda x: (i(x["area"]), x["stage"]))

    # ---------- 成员 ----------
    members = []
    for m in member_raw:
        cid = m.get("character_id", "0")
        sk = []
        for k in ("activeskill1", "activeskill2", "activeskill3"):
            p = skill_pack(m.get(k, "0"))
            if p:
                sk.append(p)
        sps = chars.get(cid, {}).get("specialattack", "0")
        members.append({
            "id": m["id"], "char": cid, "rare": i(m.get("rare"), 3),
            "name": text.get(m.get("name", ""), "") or ("メンバー " + m["id"]),
            "cname": text.get(chars.get(cid, {}).get("name", ""), "") or ("キャラ " + cid),
            "weapon": chars.get(cid, {}).get("weapon_type", ""),
            "min": {"hp": i(m["min_hp"], 100), "atk": i(m["min_attack"], 10), "def": i(m["min_defense"], 10),
                    "matk": i(m["min_magicattak"], 10), "mdef": i(m["min_magicdefence"], 10),
                    "agi": i(m["min_agility"], 10)},
            "max": {"hp": i(m["max_hp"], 100), "atk": i(m["max_attack"], 10), "def": i(m["max_defense"], 10),
                    "matk": i(m["max_magicattak"], 10), "mdef": i(m["max_magicdefence"], 10),
                    "agi": i(m["max_agility"], 10)},
            "skills": sk,
            "sp": (skill_pack(sps, "sp") or None),
            "passive": m.get("passiveskill1", "0"),
        })
    members.sort(key=lambda x: (-x["rare"], x["char"], x["id"]))

    # ---------- 图片索引（硬链接） ----------
    def link(src, dst):
        if not src or not os.path.exists(src):
            return None
        if os.path.exists(dst):
            try:
                os.unlink(dst)
            except OSError:
                return os.path.basename(dst)
        try:
            os.link(src, dst)
        except OSError:
            shutil.copyfile(src, dst)
        return os.path.basename(dst)

    # 成员立绘/头像
    icon_map = {}
    for p in glob.glob(os.path.join(A, "Common", "Images", "IconMember", "*_Sprite_*.png")):
        m = re.search(r"_Sprite_([^\\/]+)\.png$", p)
        if not m:
            continue
        mid = m.group(1)
        # 优先 Sprite（头像），同名多个时取第一张
        icon_map.setdefault(mid, p)
    for mid, p in icon_map.items():
        if link(p, os.path.join(IMG, "m_%s.png" % mid)):
            pass
    # 敌人
    enemy_img = {}
    for p in glob.glob(os.path.join(A, "Battle", "Unit", "EnemyUnit", "*Texture2D_*.png")):
        m = re.search(r"Texture2D_([^\\/]+)\.png$", p)
        if not m:
            continue
        eid = m.group(1)
        if eid.startswith("Default"):
            continue
        enemy_img.setdefault(eid, p)
    for sid, p in enemy_img.items():
        link(p, os.path.join(IMG, "e_%s.png" % sid))
    for e in enemies.values():
        e["img"] = ("e_%s.png" % e["shape"]) if ("e_%s.png" % e["shape"]) in os.listdir(IMG) or e["shape"] in enemy_img else None
    # 战斗背景
    bgs = {}
    for p in glob.glob(os.path.join(A, "Battle", "BackGround", "BG01", "*_Sprite_bg_battle_*.png")):
        m = re.search(r"_Sprite_(bg_battle_\d+_\d+)\.png$", p)
        if m:
            bgs.setdefault(m.group(1), p)
    for k, p in bgs.items():
        link(p, os.path.join(IMG, "%s.png" % k))
    for s in stages:
        cands = [k for k in bgs if k.startswith("bg_battle_%s_" % s["graphic"])]
        s["bg"] = (cands[0] + ".png") if cands else None
    # 技能图标
    sic = {}
    for p in glob.glob(os.path.join(A, "Common", "Images", "IconSkill", "*_Sprite_*.png")):
        m = re.search(r"_Sprite_([^\\/]+)\.png$", p)
        if m:
            sic.setdefault(m.group(1), p)
    used_icons = set()
    for mem in members:
        for s in mem["skills"] + ([mem["sp"]] if mem["sp"] else []):
            used_icons.add(s["icon"])
    for ic in used_icons:
        if ic in sic:
            link(sic[ic], os.path.join(IMG, "s_%s.png" % ic))

    # ---------- 写 data.js ----------
    payload = {
        "text": text, "members": members, "enemies": enemies,
        "stages": stages, "areas": areas,
    }
    js = "window.KD=" + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n"
    out = os.path.join(W, "data.js")
    open(out, "w", encoding="utf-8").write(js)

    print("[+] 文本 %d 条" % len(text))
    print("[+] 成员 %d / 敌人 %d / 关卡 %d / 区域 %d" % (len(members), len(enemies), len(stages), len(areas)))
    print("[+] 图片 %d 张" % len(os.listdir(IMG)))
    print("[+] data.js %.2f MB -> %s" % (len(js.encode()) / 1048576, out))


if __name__ == "__main__":
    main()
