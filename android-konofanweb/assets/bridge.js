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
        var cat = g.type === 'member' ? 4 : parseInt(String(g.id).split(':')[0], 10);
        var iid = g.type === 'member' ? String(g.id) : (String(g.id).split(':')[1] || '0');
        if (!(cat > 0)) return;
        presentEntry(cur, cat, iid, Number(g.count), g.msg, 900000 + Number(g.seq % 99999));
      });
      writeSave(cur);
      if (++tries < 12) setTimeout(beat, 150);
      else {
        log('gifts applied ' + applied.join(','));
        fetch('/__mgr/ack', { method: 'POST', body: JSON.stringify({ seqs: applied }) })
          .catch(function () {});
        setTimeout(function () { location.reload(); }, 200);
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
  function applyConfig(cfg) {
    CFG = cfg || {};
    window.__KONOFAN_MGR__ = CFG;
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
    fetch('/yuanban/master/eventcfg59.json').then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) { if (j) EVENTS = Object.keys(j); }).catch(function () {});
  }

  function snapshot() {
    var s = readSave();
    fetch('/__mgr/state', {
      method: 'POST',
      body: JSON.stringify({
        ts: Date.now(),
        rank: s.rank, exp: s.exp, party: s.party,
        items: s.items || {},
        members: s.members || [],
        chars: Object.keys(s.chars || {}).length,
        pools: POOLS, events: EVENTS,
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
  setInterval(snapshot, 5000);
  log('bridge ready');
})();
