/* ===== 彩票本地化补丁（前置 IIFE，先于主桥接执行） ===== */
(function () {
  try {
    var SAVE = 'oldui59.save', PRICE = 100000;
    function rd() { try { return JSON.parse(localStorage.getItem(SAVE)) || {}; } catch (e) { return {}; } }
    function wr(s) { try { localStorage.setItem(SAVE, JSON.stringify(s)); } catch (e) {} }
    function day() { var d = new Date(); return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2); }
    function six() { return ('000000' + Math.floor(Math.random() * 1000000)).slice(-6); }
    var TIER_HIT = [6, 5, 4, 3];                 // 对中位数 → 一/二/三/四等奖
    var TIER_CASH = [1000000, 500000, 1000000, 500000];   // 每张现金
    var TIER_SHARD = [100, 30, 1, 0];            // 每张碎片
    function pad2(n) { return ('0' + n).slice(-2); }
    function dayOf(d) { return d.getFullYear() + '-' + pad2(d.getMonth() + 1) + '-' + pad2(d.getDate()); }
    function drawAt(dd) { return dd + 'T20:00:00+08:00'; }
    function winNo(dd) {
      var h = 2166136261, i;
      for (i = 0; i < dd.length; i++) { h ^= dd.charCodeAt(i); h = (h * 16777619) >>> 0; }
      h ^= 0x5bf03635; h = (h * 16777619) >>> 0;
      return ('000000' + (h % 1000000)).slice(-6);
    }
    function hitCount(no, w) {
      var n = 0, i;
      for (i = 0; i < 6 && i < no.length; i++) if (no.charAt(i) === w.charAt(i)) n++;
      return n;
    }
    function roundIdOf(dd) {                     // 2026-10-24 为第 1 期，每天一期
      var t0 = Date.parse('2026-10-24T00:00:00+08:00'), t = Date.parse(dd + 'T00:00:00+08:00');
      var n = Math.floor((t - t0) / 86400000) + 1;
      return n < 1 ? 1 : n;
    }
    function mineOf(s) {                         // 按天汇总，返回 {mine:[...], tickets:[今日号码]}
      var tk = (s.x && s.x.lotteryTickets) || [], byDay = {}, order = [], i;
      for (i = 0; i < tk.length; i++) {
        var d0 = tk[i].day || day();
        if (!byDay[d0]) { byDay[d0] = []; order.push(d0); }
        byDay[d0].push(tk[i]);
      }
      order.sort().reverse();
      var now = Date.now(), mine = [];
      for (i = 0; i < order.length; i++) {
        var dd = order[i], list = byDay[dd], at = Date.parse(drawAt(dd));
        var open = now < at, hits = [0, 0, 0, 0], money = 0, shards = 0, w = winNo(dd);
        for (var j = 0; j < list.length; j++) {
          if (open) break;
          var c = hitCount(list[j].no || '', w);
          for (var k = 0; k < 4; k++) {
            if (c === TIER_HIT[k]) { hits[k]++; money += TIER_CASH[k]; shards += TIER_SHARD[k]; }
          }
        }
        var e = {
          roundId: roundIdOf(dd), qty: list.length, spent: list.length * PRICE, drawAt: drawAt(dd),
          status: open ? 'open' : 'settled', winNo: open ? '' : w, money: money, shards: shards
        };
        if (!open) e.hits = hits;
        mine.push(e);
      }
      var cur = byDay[day()] || [];
      return {
        mine: mine,
        tickets: cur.map(function (t) { return t.no; })
      };
    }
    function home() {
      var s = rd(), r = mineOf(s);
      return {
        now: new Date().toISOString(),
        round: {
          id: roundIdOf(day()), pot: 500000000, participants: 12,
          totalTickets: 88 + r.tickets.length, myTickets: r.tickets.length,
          drawAt: drawAt(day()),
          estimate: [1000000, 500000, 5000000], carry: [0, 0, 0]
        },
        results: [], mine: r.mine, tickets: r.tickets
      };
    }
    function buy(qty) {
      var s = rd(); s.items = s.items || {}; s.x = s.x || {};
      var gold = s.items['1:1'] || 0, cost = PRICE * qty;
      if (gold < cost) return { error: '艾莉丝不足，需要 ' + cost.toLocaleString() };
      s.items['1:1'] = gold - cost;
      s.x.lotteryTickets = s.x.lotteryTickets || [];
      var made = [];
      for (var i = 0; i < qty; i++) { var t = { no: six(), day: day(), ts: Date.now() }; s.x.lotteryTickets.push(t); made.push(t.no); }
      wr(s);
      return { data: { ok: true, qty: qty, numbers: made, gold: s.items['1:1'] } };
    }
    function wrap(u) {
      var url = String((u && u.url) || u);
      if (url.indexOf('/api/lottery/home') >= 0) {
        return new Response(JSON.stringify({ data: home() }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }
      return null;
    }
    var origFetch = window.fetch;
    window.fetch = function (u, o) {
      try {
        var url = String((u && u.url) || u);
        if (url.indexOf('/api/lottery/home') >= 0) return Promise.resolve(wrap(u));
        if (url.indexOf('/api/lottery/buy') >= 0) {
          var qty = 1;
          try { var b = JSON.parse((o && o.body) || '{}'); qty = Number(b.qty || 1) || 1; } catch (e) {}
          var r = buy(qty);
          return Promise.resolve(new Response(JSON.stringify(r.error ? { error: r.error } : r), { status: 200, headers: { 'Content-Type': 'application/json' } }));
        }
      } catch (e) {}
      return origFetch.apply(window, arguments);
    };
    window.__KF_LOTTERY = { home: home, buy: buy };
  } catch (e) {}
})();
if (window.__KONOFAN_BRIDGE__) { /* already */ } else {
window.__KONOFAN_BRIDGE__ = true;
// 素晴管理器 ←→ 游戏 的桥
// 由 MainActivity 在页面加载完成后注入；通过本地 MiniServer 的 /__mgr/* 读命令、上报存档快照。
(function () {
  if (window.__kfmgr) return;
  window.__kfmgr = 1;

  var SAVE = 'oldui59.save';
  var CFG = {};        // 管理器下发的配置
  var logbox = [];

  function log(s) { logbox.push(String(s)); if (logbox.length > 50) logbox.shift(); }

  function readSave() {
    try { return JSON.parse(localStorage.getItem(SAVE)) || {}; } catch (e) { return {}; }
  }
  function writeSave(s) {
    try { localStorage.setItem(SAVE, JSON.stringify(s)); return true; } catch (e) { return false; }
  }

  // ---------- 礼物：一律写进游戏内礼物箱，由玩家手动领取 ----------
  // gifts.json 里每条形如 {"seq":1,"type":"item|member","id":"1:1","count":7777,"msg":"自定义文案"}
  // 类型 → 礼物箱类别码（客户端 B 枚举）：item 用 "类别:编号" 的类别；member = 4（MEMBER）
  var MEMBER_TYPE = 4;
  var DAY = 86400000;

  function presentEntry(s, cat, iid, n, msg, fixedId) {
    s.x = s.x || {};
    s.x.presents = s.x.presents || [];
    s.x.pseq = Number(s.x.pseq || 1);
    s.x.presents.unshift({
      id: fixedId || (s.x.pseq++),
      t: cat,
      iid: String(iid),
      n: n,
      msg: msg || '管理员发放',
      sent: Date.now(),
      exp: Date.now() + 90 * DAY,
      gm: true
    });
  }

  function recallEntry(s, cat, iid, need) {
    var left = need;
    var list = (s.x && s.x.presents) || [];
    for (var i = 0; i < list.length && left > 0; i++) {
      var pz = list[i];
      if (String(pz.t) === String(cat) && String(pz.iid) === String(iid)) {
        var take = Math.min(Number(pz.n || 0), left);
        pz.n = Number(pz.n || 0) - take;
        left -= take;
        if (pz.n <= 0) { list.splice(i, 1); i--; }
      }
    }
    if (left > 0) {
      if (String(cat) === String(MEMBER_TYPE)) {
        var have = Number((s.members || {})[String(iid)] || 0);
        s.members = s.members || {};
        s.members[String(iid)] = Math.max(0, have - left);
        if (s.members[String(iid)] === 0) delete s.members[String(iid)];
      } else {
        var key = cat + ':' + iid;
        s.items = s.items || {};
        s.items[key] = Math.max(0, Number(s.items[key] || 0) - left);
      }
    }
  }

  function applyGifts(payload) {
    var list = (payload && payload.gifts) || [];
    if (!list.length) return false;
    var s = readSave();
    s.items = s.items || {};
    s.members = s.members || {};
    var applied = [];

    list.forEach(function (g) {
      var seq = g.seq;
      var n = Number(g.count || 0);
      var cat, iid;
      if (g.type === 'reset') {
        try { localStorage.removeItem(SAVE); } catch (e) {}
        applied.push(seq);
        return;
      }
      if (g.type === 'member') {
        cat = MEMBER_TYPE;
        iid = String(g.id);
      } else if (g.type === 'weapon') {
        cat = 5;
        iid = String(g.id);
      } else if (g.type === 'accessory') {
        cat = 6;
        iid = String(g.id);
      } else {
        var parts = String(g.id).split(':');
        cat = parseInt(parts[0], 10);
        iid = parts[1] || '0';
      }
      if (!(cat > 0) || !iid) return;
      if (n > 0) presentEntry(s, cat, iid, n, g.msg, 900000 + Number(seq % 99999));
      else recallEntry(s, cat, iid, -n);
      applied.push(seq);
    });

    // 游戏会周期性自动存档（写回它内存里的旧副本），所以连续写几遍再刷新，
    // 用确定性 id（900000+seq）保证重复写不会产生重复条目。
    var tries = 0;
    (function beat() {
      var cur = readSave();
      cur.x = cur.x || {};
      cur.x.presents = (cur.x.presents || []).filter(function (p) {
        return !(p && p.id >= 900000 && p.gm && p.id < 1000000);
      });
      // 把我们这批再塞回去
      var tmp = { items: {}, members: {} };
      (payload.gifts || []).forEach(function (g) {
        if (Number(g.count) <= 0 || g.type === 'reset') return;
        var TYPEMAP = { member: 4, weapon: 5, accessory: 6 };
        var cat = TYPEMAP[g.type] || parseInt(String(g.id).split(':')[0], 10);
        var iid = TYPEMAP[g.type] ? String(g.id) : (String(g.id).split(':')[1] || '0');
        if (!(cat > 0)) return;
        presentEntry(cur, cat, iid, Number(g.count), g.msg, 900000 + Number(g.seq % 99999));
      });
      writeSave(cur);
      if (++tries < 12) setTimeout(beat, 150);
      else {
        log('gifts applied ' + applied.join(','));
        fetch('/__mgr/ack', { method: 'POST', body: JSON.stringify({ seqs: applied }) })
          .catch(function () {});
        setTimeout(function () { try { location.hash = '#/home'; } catch (e) {} }, 200);
      }
    })();
    return true;
  }

  // ---------- 卡池轮换：包一层 __localRpc ----------
  function wrapRpc() {
    var f = window.__localRpc;
    if (!f || f.__kfwrapped) return;
    var g = function (name, args, ctx) {
      if (ctx && ctx.W && ctx.gd) window.__kfctx = ctx;   // 拿到游戏自己的存档读写器
      var p = f.call(this, name, args, ctx);
      return Promise.resolve(p).then(function (res) {
        try {
          if (name === 'releasedGachaPools' && CFG && CFG.activePools && CFG.activePools.length) {
            var allow = {};
            CFG.activePools.forEach(function (id) { allow[String(id)] = 1; });
            var arr = (res && res.pools) ? res.pools : res;
            if (Array.isArray(arr)) {
              var filtered = arr.filter(function (p) { return allow[String(p.id)]; });
              if (filtered.length) {
                return (res && res.pools) ? Object.assign({}, res, { pools: filtered }) : filtered;
              }
            }
          }
        } catch (e) {}
        return res;
      });
    };
    g.__kfwrapped = 1;
    window.__localRpc = g;
    log('rpc wrapped');
  }

  // ---------- 事件/首领：挂在全局，供页面内模块参考 ----------
  var bootTs = null, reloaded = 0;
  function applyConfig(cfg) {
    CFG = cfg || {};
    if (cfg && cfg.ts) {
      if (bootTs === null) bootTs = cfg.ts;
      else if (cfg.ts !== bootTs && !reloaded) { reloaded = 1; setTimeout(function () { location.reload(); }, 300); }
    }
/* ===== 首次启动自动导入最新备份（放在最前，保证一定执行） ===== */
(function(){
  function tryRestore(){
    try{
      if(localStorage.getItem('kf_restored_ok')) return;
      fetch('/__mgr/save-latest',{cache:'no-store'}).then(function(r){return r.text()}).then(function(t){
        try{
          var o=JSON.parse(t);
          if(!o||!o.uid||!(o.rank>0)) return;
          localStorage.setItem('oldui59.save',t);
          localStorage.removeItem('oldui59.localProfile');
          localStorage.removeItem('oldui59.device');
          localStorage.setItem('kf_restored_ok','1');
          location.reload();
        }catch(e){}
      }).catch(function(){});
    }catch(e){}
  }
  if(document.readyState==='complete') setTimeout(tryRestore,1200);
  else window.addEventListener('load',function(){ setTimeout(tryRestore,1200); });
})();

    window.__KONOFAN_MGR__ = CFG;
    try { if (window.kfApplyBoss) window.kfApplyBoss(CFG); } catch (e) {}
    document.documentElement.setAttribute('data-kf-events',
      (CFG.enabledEvents || []).join(','));
  }

  function poll() {
    fetch('/__mgr/config.json?t=' + Date.now())
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (c) { if (c) applyConfig(c); })
      .catch(function () {});
    fetch('/__mgr/gifts.json?t=' + Date.now())
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (g) {
        if (g && g.gifts && g.gifts.length) { applyGifts(g); }
      })
      .catch(function () {});
  }

  // ---------- 上报快照 ----------
  var POOLS = [], EVENTS = [];
  function refreshPools() {
    var f = window.__localRpc;
    if (!f) return;
    Promise.resolve(f('releasedGachaPools', [], {})).then(function (res) {
      var arr = (res && res.pools) ? res.pools : res;
      if (Array.isArray(arr)) {
        POOLS = arr.map(function (p) { return { id: String(p.id), name: p.name || p.nameJa || '' }; });
      }
    }).catch(function () {});
  }
  function refreshEvents() {
    fetch('/__mgr/events').then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) {
        if (Array.isArray(j)) {
          EVENTS = j.map(function (e) { return { id: String(e.id), name: e.name || '' }; });
        }
      }).catch(function () {});
  }

  function snapshot() {
    var s = readSave();
    fetch('/__mgr/state', {
      method: 'POST',
      body: JSON.stringify({
        ts: Date.now(),
        rank: s.rank, exp: s.exp, party: s.party, uid: s.uid,
        items: s.items || {},
        members: s.members || [],
        chars: Object.keys(s.chars || {}).length,
        pools: POOLS, events: EVENTS, lottery: LOTTERY,
        gachaActive: (window.__KONOFAN_MGR__ || {}).activePools || null,
        log: logbox.slice(-10)
      })
    }).catch(function () {});
  }

  applyConfig({});
  wrapRpc();
  setTimeout(refreshPools, 1500);
  setTimeout(refreshEvents, 2000);
  poll();
  setInterval(poll, 2000);
  setInterval(wrapRpc, 1500);
  snapshot();
  setInterval(snapshot, 6000);
  setInterval(snapshot, 5000);
  log('bridge ready');
})();

// ==== 存档备份 / 还原 / 礼物角标 ====
(function () {
  var SAVE = 'oldui59.save';
  function readSaveText() { try { return localStorage.getItem(SAVE); } catch (e) { return null; } }
  window.__konofanBackupNow = function () {
    var t = readSaveText();
    if (!t) return false;
    fetch('/__mgr/backup', { method: 'POST', body: t }).catch(function () {});
    return true;
  };
  var lastToken = null;
  function pollRestore() {
    fetch('/__mgr/restore.json?t=' + Date.now()).then(function (r) {
      return r.ok ? r.json() : null;
    }).then(function (j) {
      if (!j || !j.token || j.token === lastToken) return;
      lastToken = j.token;
      function apply(txt) {
        if (!txt || txt.length < 20) return;
        localStorage.setItem(SAVE, txt);
        fetch('/__mgr/ack-restore', { method: 'POST', body: j.token }).catch(function () {});
        setTimeout(function () { location.reload(); }, 300);
      }
      if (j.data) { apply(j.data); return; }
      fetch('/__mgr/restore/' + encodeURIComponent(j.file)).then(function (r) {
        return r.text();
      }).then(apply);
    }).catch(function () {});
  }
  function pollCmd() {
    fetch('/__mgr/cmd.json?t=' + Date.now()).then(function (r) {
      return r.ok ? r.json() : null;
    }).then(function (c) {
      if (!c) return;
      if (c.backup) {
        window.__konofanBackupNow();
        fetch('/__mgr/ack-cmd', { method: 'POST' }).catch(function () {});
      }
    }).catch(function () {});
  }
  // ---------- 彩票 ----------
  var LOTTERY = null;
  function dayStr() {
    var d = new Date();
    return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2);
  }
  function h32(str) {
    var h = 2166136261;
    for (var i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = (h * 16777619) >>> 0; }
    return h >>> 0;
  }
  function six(n) { return ('000000' + n).slice(-6); }

  function drawLottery() {
    var s = readSave();
    if (!s || !s.x || typeof s.uid === 'undefined') return;
    var cfg = window.__KONOFAN_MGR__ || {};
    var today = dayStr();
    var win;
    var c = cfg.lottery || {};
    if (/^[0-9]{6}$/.test(c.number || '') && c.date === today) win = c.number;
    else win = six(h32('konofan-win-' + today) % 1000000);
    var player = six(h32('konofan-ticket-' + (s.uid || 0) + '-' + today) % 1000000);
    var lvl = 0;
    if (player === win) lvl = 1;
    else if (player.slice(1) === win.slice(1)) lvl = 2;
    else if (player.slice(2) === win.slice(2)) lvl = 3;
    s.x = s.x || {};
    var claimed = s.x.lotteryClaim === today;
    LOTTERY = { day: today, win: win, player: player, level: lvl, claimed: claimed };
    try { window.__KONOFAN_LOTTERY = LOTTERY; } catch (e0) {}
    log('lottery ' + today + ' win=' + win + ' me=' + player + ' lvl=' + lvl);
    if (lvl > 0 && !claimed) {
      var P = { 1: [1000000, 10], 2: [500000, 5], 3: [200000, 2] }[lvl];
      var name = { 1: '一等奖', 2: '二等奖', 3: '三等奖' }[lvl];
      s.x.presents = s.x.presents || [];
      s.x.presents.unshift(presentEntry(s, 1, '1', P[0], '彩票' + name + '·艾莉丝'));
      s.x.presents.unshift(presentEntry(s, 39, '1', P[1], '彩票' + name + '·万能碎片'));
      s.x.lotteryClaim = today;
      var n = 0;
      (function beat() { writeSave(s); if (++n < 10) setTimeout(beat, 150); else log('lottery prize queued L' + lvl); })();
    }
  }
  try { window.__KF_DRAW = drawLottery; setTimeout(drawLottery, 2500); setInterval(drawLottery, 8000); } catch (eL0) {}

  setTimeout(pollRestore, 2500);
  setInterval(pollRestore, 3000);
  setInterval(pollCmd, 4000);
  setInterval(function () { window.__konofanBackupNow(); }, 120000);
})();

}

/* ===== 世界BOSS 切换 ===== */
window.kfApplyBoss = function (cfg) {
  try {
    if (!cfg || !cfg.boss || !cfg.boss.key) return false;
    if (window.__kfBossKey === cfg.boss.key) return false;
    var raw = localStorage.getItem('oldui59.worldboss');
    var st = raw ? JSON.parse(raw) : {};
    var b = cfg.boss;
    st.cfg = Object.assign({}, (st.cfg || {}), {
      id: b.key + '-1', name: b.name, art: b.art || b.key,
      enemy: b.enemy, minions: b.minions || [],
      hp: b.hp || 500000000, hpMax: b.hp || 500000000,
      bossAtk: b.bossAtk || 130, bossDef: b.bossDef || 120, bossAgi: b.bossAgi || 125,
      bossScale: b.bossScale || 240, minionAtk: b.minionAtk || 40, minionScale: b.minionScale || 70
    });
    window.__kfBossKey = b.key;
    localStorage.setItem('oldui59.worldboss', JSON.stringify(st));
    setTimeout(function () { try { location.reload(); } catch (e) {} }, 400);
    return true;
  } catch (e) { return false; }
};

