/* この素晴らしい世界に祝福を！ ローカル版 — 战斗/养成核心
 * 数据来自 tools/build_webapp.py 生成的 data.js (window.KD)
 * 数值公式说明见 README：伤害/命中为「按 MasterData 复元的近似式」，非原客户端逐位一致。
 */
(() => {
const KD = window.KD;
const $app = document.getElementById('app');
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const rnd = (a, b) => a + Math.random() * (b - a);

const MAXLV = { 4: 60, 3: 50, 2: 40, 1: 30 };
const PLV = 24;           // 玩家等级（暂定；后续接养成系统）
const SP_MAX = 10;
const COST = { sk: 2, sp: 5 };

const S = {
  screen: 'home',
  party: JSON.parse(localStorage.getItem('kd_party') || 'null'),
  cleared: new Set(JSON.parse(localStorage.getItem('kd_cleared') || '[]')),
  stage: null, battle: null, member: null, area: null, tab: 4,
};

/* ---------------- 数据访问 ---------------- */
const M = {}; KD.members.forEach(m => M[m.id] = m);
const EN = KD.enemies;
const memImg = id => `img/m_${id}.png`;
const enemyImg = e => e.img ? `img/${e.img}` : null;

function statAt(m, lv) {
  const max = MAXLV[m.rare] || 50, t = clamp((lv - 1) / (max - 1), 0, 1);
  const out = {};
  for (const k of ['hp', 'atk', 'def', 'matk', 'mdef', 'agi'])
    out[k] = Math.round(m.min[k] + (m.max[k] - m.min[k]) * t);
  return out;
}
function saveProgress() {
  localStorage.setItem('kd_cleared', JSON.stringify([...S.cleared]));
  if (S.party) localStorage.setItem('kd_party', JSON.stringify(S.party));
}

/* ---------------- 战斗引擎 ---------------- */
function mkAlly(mid, idx) {
  const m = M[mid], st = statAt(m, PLV);
  return {
    uid: 'a' + idx, side: 'ally', id: m.id, name: m.cname, sub: m.name, img: memImg(m.id),
    lv: PLV, hp: st.hp, maxhp: st.hp, atk: st.atk, def: st.def, matk: st.matk, mdef: st.mdef, agi: st.agi,
    skills: m.skills, sp: m.sp, alive: true,
  };
}
function mkEnemy(eid, idx) {
  const e = EN[eid];
  return {
    uid: 'e' + idx, side: 'enemy', id: e.id, name: e.name, img: enemyImg(e), shape: e.shape,
    lv: e.lv, hp: e.hp, maxhp: e.hp, atk: e.atk, def: e.def, matk: e.matk, mdef: e.mdef, agi: e.agi,
    skills: e.skills, ai: e.ai, alive: true, boss: e.boss,
  };
}

function damage(a, d, power, kind) {
  const atk = kind === 'magic' ? a.matk : a.atk;
  const def = kind === 'magic' ? d.mdef : d.def;
  const base = atk * (power / 100);
  const dmg = base * (420 / (420 + def));
  const crit = Math.random() < 0.08;
  const v = 0.95 + Math.random() * 0.1;
  return { n: Math.max(1, Math.round(dmg * v * (crit ? 1.6 : 1))), crit };
}
const kindOf = t => (String(t).indexOf('magic') >= 0 ? 'magic' : 'phys');

function startBattle(stage) {
  const b = {
    stage, waveIdx: 0, round: 0, sp: 3, allies: [], enemies: [],
    log: [], over: null, queue: [], qi: 0, waiting: false, busy: false, popups: [],
  };
  S.battle = b;
  (S.party || []).forEach((mid, i) => { if (mid) b.allies.push(mkAlly(mid, i)); });
  loadWave(b);
  S.screen = 'battle';
  render();
  next();
}
function loadWave(b) {
  const ids = b.stage.waves[b.waveIdx] || [];
  b.enemies = ids.map((eid, i) => mkEnemy(eid, i));
  b.round = 0;
  if (b.waveIdx > 0) b.log.push(`<b>WAVE ${b.waveIdx + 1}</b> が出現した`);
  buildQueue(b);
}
function aliveOf(list) { return list.filter(u => u.alive); }
function buildQueue(b) {
  b.queue = [...b.allies, ...b.enemies].filter(u => u.alive)
    .sort((x, y) => (y.agi - x.agi) || (Math.random() - .5));
  b.qi = 0;
  b.round++;
}
function pushLog(b, html) {
  b.log.push(html);
  if (b.log.length > 80) b.log.shift();
}

function next() {
  const b = S.battle;
  if (!b || b.over) return;
  if (b.busy) return;
  if (!aliveOf(b.allies).length) return finish(b, false);
  if (!aliveOf(b.enemies).length) {
    if (b.waveIdx + 1 < b.stage.waves.length) {
      b.waveIdx++; b.enemies = []; b.queue = [];
      loadWave(b); render(); return setTimeout(next, 700);
    }
    return finish(b, true);
  }
  if (b.qi >= b.queue.length) { buildQueue(b); render(); return setTimeout(next, 260); }

  const u = b.queue[b.qi];
  if (!u.alive) { b.qi++; return next(); }

  if (u.side === 'ally') {
    b.waiting = true; render();
    if (window.__auto) setTimeout(() => {
      if (S.battle && S.battle.waiting) {
        const ok = b.sp >= COST.sp && Math.random() < .35;
        ok ? playerAction('sp') : (b.sp >= COST.sk && Math.random() < .5 ? playerAction('sk', Math.floor(Math.random() * 2)) : playerAction('atk'));
      }
    }, 260);
  } else {
    b.waiting = false; render();
    setTimeout(() => enemyTurn(b, u), 480);
  }
}
function advance(b) { b.qi++; b.waiting = false; setTimeout(next, 220); }

function hit(b, target, res, heal) {
  if (heal) {
    target.hp = Math.min(target.maxhp, target.hp + res.n);
    target.pop = { txt: '+' + res.n, cls: 'heal' };
    return;
  }
  target.hp = Math.max(0, target.hp - res.n);
  target.pop = { txt: res.n, cls: res.crit ? 'crit' : '' };
  target.shake = true;
  if (target.hp <= 0 && target.alive) {
    target.alive = false;
    pushLog(b, `${target.side === 'ally' ? '<b>' + esc(target.name) + '</b>' : esc(target.name)} は倒れた`);
  }
}

function playerAction(kind, skillIdx) {
  const b = S.battle;
  if (!b || b.busy || b.over || !b.waiting) return;
  const u = b.queue[b.qi];
  if (!u || u.side !== 'ally' || !u.alive) return;
  const foes = aliveOf(b.enemies);
  if (!foes.length) return;

  b.busy = true; render();
  let power = 100, kindD = 'phys', label = '通常攻撃', cost = 0, hits = [], multi = 1;

  if (kind === 'sk') {
    const sk = u.skills[skillIdx];
    if (!sk || b.sp < COST.sk) { b.busy = false; return; }
    cost = COST.sk; power = sk.vmax || sk.vmin || 100; kindD = kindOf(sk.type);
    label = sk.name; multi = Math.min(sk.num || 1, foes.length);
  } else if (kind === 'sp') {
    const sk = u.sp;
    if (!sk || b.sp < COST.sp) { b.busy = false; return; }
    cost = COST.sp; power = sk.vmax || 250; kindD = kindOf(sk.type);
    label = sk.name || '必殺技'; multi = Math.min(sk.num || 1, foes.length);
  }
  b.sp = clamp(b.sp - cost, 0, SP_MAX);
  if (kind === 'atk') b.sp = clamp(b.sp + 1, 0, SP_MAX);

  pushLog(b, `<b>${esc(u.name)}</b> の ${esc(label)}`);
  for (let i = 0; i < multi; i++) hits.push(foes[i % foes.length]);

  hits.forEach((t, i) => setTimeout(() => {
    const r = damage(u, t, power, kindD);
    hit(b, t, r);
    render();
  }, i * 130));

  setTimeout(() => {
    b.busy = false; b.waiting = false;
    if (!aliveOf(b.enemies).length) { render(); return next(); }
    advance(b);
  }, 200 + hits.length * 130 + 260);
}

function enemyTurn(b, u) {
  const foes = aliveOf(b.allies);
  if (!foes.length) { b.busy = false; return next(); }
  // AI：按 weight 选技能，无权重时用 100% 普攻
  let pick = null;
  const pool = (u.ai || []).filter(a => a.w > 0);
  if (pool.length) {
    const total = pool.reduce((s, a) => s + a.w, 0);
    let r = Math.random() * total;
    for (const a of pool) { r -= a.w; if (r <= 0) { pick = u.skills.find(s => s.id === a.skill) || null; break; } }
  }
  if (!pick && u.skills.length) pick = u.skills[0];

  if (pick && pick.type === 'escape') {
    pushLog(b, `${esc(u.name)} は逃げ出した`);
    u.alive = false; render(); return advance(b);
  }
  const tgt = foes[Math.floor(Math.random() * foes.length)];
  const isHeal = pick && /heal/.test(pick.type);
  if (isHeal) {
    hit(b, u, { n: Math.round(u.maxhp * 0.08) }, true);
    pushLog(b, `${esc(u.name)} は回復した`);
  } else {
    const power = pick ? (pick.value || 100) : 100;
    const kd = kindOf(pick ? pick.type : 'atk_physics');
    pushLog(b, `<b>${esc(u.name)}</b> の攻撃`);
    const r = damage(u, tgt, power, kd);
    hit(b, tgt, r);
  }
  render();
  setTimeout(() => advance(b), 420);
}

function finish(b, win) {
  b.over = win ? 'win' : 'lose';
  if (win) { S.cleared.add(b.stage.id); saveProgress(); }
  render();
}

/* ---------------- 渲染 ---------------- */
function nav() {
  const items = [
    ['home', 'ホーム'], ['adventure', '冒険'], ['members', 'メンバー'],
    ['party', '編成'], ['data', '資料庫'],
  ];
  return `<div class="top">
    <div class="logo">この素晴らしい世界に祝福を！<small>ローカル版</small></div>
    <div class="nav">${items.map(([k, t]) =>
      `<button data-nav="${k}" class="${S.screen === k || (k === 'adventure' && S.screen === 'stages') ? 'on' : ''}">${t}</button>`).join('')}</div>
  </div>`;
}

function render() {
  let body = '';
  switch (S.screen) {
    case 'home': body = viewHome(); break;
    case 'adventure': body = viewAreas(); break;
    case 'stages': body = viewStages(); break;
    case 'party': body = viewParty(); break;
    case 'members': body = viewMembers(); break;
    case 'member': body = viewMember(); break;
    case 'battle': body = viewBattle(); break;
  }
  $app.innerHTML = (S.screen === 'battle' ? '' : nav()) + body;
  bind();
  if (S.screen === 'battle') { flushPops(); scrollLog(); }
}

function flushPops() {
  const b = S.battle; if (!b) return;
  for (const u of [...b.allies, ...b.enemies]) {
    const el = document.querySelector(`[data-uid="${u.uid}"]`);
    if (!el) continue;
    if (u.pop) {
      const d = document.createElement('div');
      d.className = 'dmg ' + (u.pop.cls || '');
      d.textContent = u.pop.txt;
      el.appendChild(d);
      u.pop = null;
    }
    if (u.shake) { el.classList.add('hit'); u.shake = false; setTimeout(() => el.classList.remove('hit'), 300); }
  }
}
function scrollLog() {
  const l = document.querySelector('.log');
  if (l) l.scrollTop = l.scrollHeight;
}

/* --------- 首页 --------- */
function viewHome() {
  const n = S.cleared.size;
  return `<div class="hero">
    <h1>この素晴らしい世界に祝福を！ ローカル版</h1>
    <p>MasterData 全 279 表 / メンバー ${KD.members.length} / クエスト ${KD.stages.length} / 敵 ${Object.keys(KD.enemies).length}</p>
  </div>
  <div class="grid menu">
    <div class="card" data-nav="adventure"><div class="ic">⚔️</div><div class="t">冒険</div><div class="d">メインクエストを進める</div></div>
    <div class="card" data-nav="party"><div class="ic">🛡️</div><div class="t">編成</div><div class="d">パーティを組む（3人）</div></div>
    <div class="card" data-nav="members"><div class="ic">👥</div><div class="t">メンバー</div><div class="d">${KD.members.length} 枚のカード</div></div>
    <div class="card" data-act="data"><div class="ic">📚</div><div class="t">資料庫</div><div class="d">データ/CG/シナリオ</div></div>
  </div>
  <div class="stats">
    <div>クリア <b>${n}</b></div>
    <div>編成 <b>${(S.party || []).filter(Boolean).length}/3</b></div>
    <div>プレイヤーLv <b>${PLV}</b></div>
  </div>`;
}

/* --------- 冒险：区域 --------- */
function viewAreas() {
  const parts = {};
  for (const s of KD.stages) {
    const a = KD.areas[s.area] || { part: 1, title: 'AREA ' + s.area };
    const k = a.part;
    (parts[k] = parts[k] || []).push({ area: s.area, title: a.title, n: 0 });
  }
  for (const s of KD.stages) ((parts[(KD.areas[s.area] || {}).part || 1] || []).find(x => x.area === s.area) || {}).n++;
  const out = Object.keys(parts).sort((x, y) => x - y).map(p => {
    const seen = {};
    const list = parts[p].filter(a => (seen[a.area] ? false : (seen[a.area] = 1)));
    return `<h3>第 ${p} 部</h3><div class="grid areas">${list.map(a => {
      const cnt = KD.stages.filter(s => s.area === a.area).length;
      const cl = KD.stages.filter(s => s.area === a.area && S.cleared.has(s.id)).length;
      return `<div class="card area" data-area="${a.area}">
        <div class="p">AREA ${a.area}</div>
        <div class="t">${esc(a.title)}</div>
        <div class="hint">${cl} / ${cnt} クリア</div></div>`;
    }).join('')}</div>`;
  }).join('');
  return `<h2>冒険 — メインクエスト</h2><p class="hint">クリアすると次のステージが開放されます（進行状況はブラウザに保存）。</p>${out}`;
}

function stageOpen(s) {
  if (!s.unlock || s.unlock === '0') return true;
  if (S.cleared.has(s.unlock)) return true;
  return false;
}
function viewStages() {
  const list = KD.stages.filter(s => s.area === S.area);
  const rows = list.map(s => {
    const open = stageOpen(s);
    const done = S.cleared.has(s.id);
    return `<div class="row ${open ? '' : 'lock'}" ${open ? `data-stage="${s.id}"` : ''}>
      <div class="id">${s.area}-${s.stage}</div>
      <div class="ttl">${esc(s.title)} ${done ? '<span class="badge" style="color:#7ef0a8;border-color:#7ef0a8">クリア</span>' : ''}
        ${s.boss ? '<span class="badge">BOSS</span>' : ''}</div>
      <div class="st">WAVE ${s.waves.length} ・ 消費 ${s.stamina}</div>
      <div>${open ? '<span class="btn">挑戦</span>' : '<span class="hint">未開放</span>'}</div>
    </div>`;
  }).join('');
  const a = KD.areas[S.area] || {};
  return `<h2>${esc(a.title || 'エリア ' + S.area)}</h2>
    <p class="hint"><a href="#" data-nav="adventure">← エリア一覧</a></p>
    <div class="stagelist">${rows}</div>`;
}

/* --------- 编成 --------- */
function viewParty() {
  const p = S.party || [null, null, null];
  const slots = [0, 1, 2].map(i => {
    const mid = p[i];
    if (!mid) return `<div class="slot" data-slot="${i}">＋<div class="hint">タップして選択</div></div>`;
    const m = M[mid], st = statAt(m, PLV);
    return `<div class="slot filled" data-slot="${i}">
      <img src="${memImg(mid)}" onerror="this.style.opacity=.15">
      <div><b>${esc(m.cname)}</b><div class="hint">${esc(m.name)}</div></div>
      <div class="hint">HP ${st.hp} / ATK ${st.atk} / AGI ${st.agi}</div>
    </div>`;
  }).join('');
  const roster = KD.members.slice(0, 400).map(m =>
    `<div class="rc r${m.rare} ${(S.party || []).includes(m.id) ? 'sel' : ''}" data-pick="${m.id}">
      <img src="${memImg(m.id)}" loading="lazy" onerror="this.style.opacity=.1">
      <span class="r">${'★'.repeat(m.rare)}</span></div>`).join('');
  return `<h2>編成</h2>
    <p class="hint">スロットを選んでからメンバーをタップ。Lv ${PLV} 時点のステータスを表示。</p>
    <div class="grid party">${slots}</div>
    <h3>メンバー（★4 優先 / 上位 400 枚）</h3>
    <div class="roster">${roster}</div>`;
}

/* --------- 成员 --------- */
function viewMembers() {
  const tabs = [4, 3, 2].map(r =>
    `<button class="btn ${S.tab === r ? 'primary' : ''}" data-tab="${r}">★${r} (${KD.members.filter(m => m.rare === r).length})</button>`).join('');
  const list = KD.members.filter(m => m.rare === S.tab);
  const cards = list.map(m => `<div class="mc" data-member="${m.id}" title="${esc(m.cname)} ${esc(m.name)}">
    <img src="${memImg(m.id)}" loading="lazy" onerror="this.style.opacity=.1"></div>`).join('');
  return `<h2>メンバー</h2><div style="display:flex;gap:8px;margin:12px 0">${tabs}</div>
    <div class="grid mlist">${cards}</div>`;
}
function viewMember() {
  const m = M[S.member];
  if (!m) return '<p>?</p>';
  const st = statAt(m, PLV);
  const kv = Object.entries({ HP: st.hp, 'ATK': st.atk, 'M.ATK': st.matk, DEF: st.def, 'M.DEF': st.mdef, AGI: st.agi })
    .map(([k, v]) => `<div><span>${k}</span>${v}</div>`).join('');
  const sks = m.skills.map((s, i) => `<div class="sk">
      <div class="t">${esc(s.name)} <span class="badge">${esc(s.type)}</span>${s.num > 1 ? `<span class="badge">${s.num}体</span>` : ''}</div>
      <div class="d">威力 ${s.vmin}〜${s.vmax}% ・ 命中 ${s.prob}% ${s.desc ? '・ ' + esc(s.desc) : ''}</div>
    </div>`).join('');
  const sp = m.sp ? `<div class="sk"><div class="t">${esc(m.sp.name)} <span class="badge">SP</span></div>
      <div class="d">威力 ${m.sp.vmin}〜${m.sp.vmax}% ・ ${esc(m.sp.type)}</div></div>` : '';
  return `<h2>${esc(m.cname)} — ${esc(m.name)}</h2>
    <p class="hint"><a href="#" data-nav="members">← メンバー一覧</a> ・ ★${m.rare} ・ ${esc(m.weapon)}</p>
    <div class="detail">
      <img src="${memImg(m.id)}" onerror="this.style.opacity=.15">
      <div><div class="kv">${kv}</div>${sks}${sp}
      <div class="hint">パッシブ ${esc(m.passive)}</div></div>
    </div>`;
}

/* --------- 战斗 --------- */
function cleanName(n) { return (!n || /^ASSET_/.test(n)) ? '必殺技' : n; }

function viewBattle() {
  const b = S.battle;
  if (!b) return '<p class="hint" style="padding:40px">バトルがありません</p>';
  const bg = b.stage.bg ? `style="background-image:url('img/${b.stage.bg}')"` : '';
  const en = b.enemies.map(e => unitHtml(e, true)).join('');
  const al = b.allies.map(u => unitHtml(u, false)).join('');
  const actor = b.waiting ? b.queue[b.qi] : null;
  const canSk = k => b.sp >= (k === 'sp' ? COST.sp : COST.sk);
  let acts = '<span class="hint">敵の行動中…</span>';
  if (actor) {
    acts = `<button class="btn primary" data-act="atk">通常攻撃<small>SP +1</small></button>`;
    (actor.skills || []).forEach((s, i) => {
      acts += `<button class="btn" data-act="sk" data-i="${i}" ${canSk('sk') ? '' : 'disabled'}>
        ${esc(cleanName(s.name).slice(0, 10))}<small>SP ${COST.sk} ・ ${s.vmax}%</small></button>`;
    });
    if (actor.sp) acts += `<button class="btn" data-act="sp" ${canSk('sp') ? '' : 'disabled'}>
      ${esc(cleanName(actor.sp.name || '必殺技').slice(0, 10))}<small>SP ${COST.sp} ・ ${actor.sp.vmax}%</small></button>`;
  }
  const spDots = Array.from({ length: SP_MAX }, (_, i) => `<i class="${i < b.sp ? 'on' : ''}"></i>`).join('');
  let overlay = '';
  if (b.over) {
    overlay = `<div class="result">
      <h3>${b.over === 'win' ? 'VICTORY' : 'DEFEAT'}</h3>
      <p class="hint">${esc(b.stage.title)} ・ WAVE ${b.waveIdx + 1}/${b.stage.waves.length}</p>
      <div style="display:flex;gap:10px">
        <button class="btn primary" data-nav="adventure">ステージ一覧へ</button>
        ${b.over === 'win' ? `<button class="btn" data-retry="1">もう一度</button>` : `<button class="btn" data-retry="1">再挑戦</button>`}
      </div></div>`;
  }
  return `<div class="battle">
    <div class="bstage ${b.stage.bg ? '' : 'noimg'}" ${bg}>
      <div class="wavebar">WAVE <b>${b.waveIdx + 1}</b> / ${b.stage.waves.length}
        <span style="margin-left:8px">ROUND ${b.round}</span></div>
      <div class="enemies">${en}</div>
      <div class="allys">${al}</div>
    </div>
    <div class="hud">
      <div class="sp">${spDots}</div>
      <span class="hint">SP ${b.sp}/${SP_MAX}</span>
      <div class="acts">${acts}</div>
    </div>
    <div class="log">${b.log.slice(-40).map(l => `<div>${l}</div>`).join('')}</div>
    ${overlay}
  </div>`;
}
function unitHtml(u, enemy) {
  const pct = Math.round(u.hp / u.maxhp * 100);
  const img = u.img ? `<img src="${u.img}" onerror="this.style.display='none'">`
    : `<div style="width:104px;height:104px;border-radius:50%;background:#2a3145;display:flex;align-items:center;justify-content:center;font-size:30px">👹</div>`;
  return `<div class="unit ${u.alive ? '' : 'dead'} ${(S.battle && S.battle.waiting && S.battle.queue[S.battle.qi] === u) ? 'acting' : ''}" data-uid="${u.uid}">
    ${img}
    <div class="nm">${esc(u.name)}</div>
    <div class="bar"><i style="width:${pct}%"></i></div>
    <div class="hint" style="font-size:10px">${u.hp}/${u.maxhp}</div>
  </div>`;
}

/* ---------------- 事件 ---------------- */
function bind() {
  document.querySelectorAll('[data-nav]').forEach(el => el.onclick = e => {
    e.preventDefault();
    const k = el.dataset.nav;
    if (k === 'data') { location.href = '../site/index.html'; return; }
    S.screen = k; render(); window.scrollTo(0, 0);
  });
  document.querySelectorAll('[data-act="data"]').forEach(el => el.onclick = () => location.href = '../site/index.html');
  document.querySelectorAll('[data-area]').forEach(el => el.onclick = () => { S.area = el.dataset.area; S.screen = 'stages'; render(); });
  document.querySelectorAll('[data-stage]').forEach(el => el.onclick = () => {
    const st = KD.stages.find(s => s.id === el.dataset.stage);
    if (!st) return;
    if (!S.party || !S.party.filter(Boolean).length) {
      alert('先に編成でパーティを組んでください'); S.screen = 'party'; render(); return;
    }
    S.stage = st; startBattle(st);
  });
  document.querySelectorAll('[data-slot]').forEach(el => el.onclick = () => {
    S.slot = +el.dataset.slot; render();
  });
  document.querySelectorAll('[data-pick]').forEach(el => el.onclick = () => {
    const id = el.dataset.pick;
    const p = S.party ? [...S.party] : [null, null, null];
    const i = S.slot == null ? p.findIndex(x => !x) : S.slot;
    const at = p.indexOf(id);
    if (at >= 0) p[at] = null;
    p[i < 0 ? 0 : i] = id;
    S.party = p.filter((x, k) => k < 3);
    saveProgress(); render();
  });
  document.querySelectorAll('[data-tab]').forEach(el => el.onclick = () => { S.tab = +el.dataset.tab; render(); });
  document.querySelectorAll('[data-member]').forEach(el => el.onclick = () => { S.member = el.dataset.member; S.screen = 'member'; render(); });
  document.querySelectorAll('[data-act="atk"]').forEach(el => el.onclick = () => playerAction('atk'));
  document.querySelectorAll('[data-act="sk"]').forEach(el => el.onclick = () => playerAction('sk', +el.dataset.i));
  document.querySelectorAll('[data-act="sp"]').forEach(el => el.onclick = () => playerAction('sp'));
  document.querySelectorAll('[data-retry]').forEach(el => el.onclick = () => startBattle(S.stage));
}

/* 默认编成：最强的 3 张 ★4 */
if (!S.party || !S.party.filter(Boolean).length) {
  // 默认编成：不同キャラの★4を3枚
  const seen = new Set(), pick = [];
  for (const m of KD.members) {
    if (seen.has(m.char)) continue;
    seen.add(m.char); pick.push(m.id);
    if (pick.length === 3) break;
  }
  S.party = pick; saveProgress();
}

/* 简易 hash 路由：#/stages/1  #/battle/101011  #/members  #/party  #/adventure */
function applyHash() {
  const h = (location.hash || '').replace(/^#\/?/, '').split('/');
  if (!h[0]) return false;
  if (h[0] === 'stages') { S.screen = 'stages'; S.area = h[1] || '1'; return true; }
  if (h[0] === 'battle') {
    const st = KD.stages.find(s => s.id === h[1]);
    if (st) { window.__auto = h[2] === 'auto'; S.stage = st; startBattle(st); return true; }
  }
  if (h[0] === 'member' && M[h[1]]) { S.member = h[1]; S.screen = 'member'; return true; }
  if (['home', 'adventure', 'party', 'members'].includes(h[0])) { S.screen = h[0]; return true; }
  return false;
}
if (applyHash()) { if (S.screen !== 'battle') render(); } else render();
window.addEventListener('hashchange', () => { if (applyHash()) { if (S.screen !== 'battle') render(); } });
})();
