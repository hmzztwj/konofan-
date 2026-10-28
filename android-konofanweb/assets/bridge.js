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

  // ---------- 礼物：一次性消费 ----------
  function applyGifts(payload) {
    var list = (payload && payload.gifts) || [];
    if (!list.length) return false;
    var ctx = window.__kfctx;
    var s = (ctx && ctx.W) ? ctx.W() : readSave();
    if (!s || typeof s !== 'object') s = readSave();
    s.items = s.items || {};
    s.members = s.members || [];
    var applied = [];
    s.x = s.x || {};
    s.x.presents = s.x.presents || [];
    s.x.pseq = Number(s.x.pseq || 1);
    var DAY = 86400000;

    list.forEach(function (g) {
      var seq = g.seq, done = false;
      if (g.type === 'item') {
        var k = String(g.id);                    // 形如 "1:1" → 类别 1、编号 1
        var parts = k.split(':');
        var cat = parseInt(parts[0], 10), iid = parts[1] || '0';
        var n = Number(g.count || 0);
        if (!(cat > 0)) { done = false; }
        else if (n > 0) {
          // 走游戏自己的礼物箱：x.presents 里插一条，玩家在首页「礼物」里领取
          s.x.presents.unshift({
            id: s.x.pseq++,
            t: cat,
            iid: String(iid),
            n: n,
            msg: (g.msg || '管理员发放'),
            sent: Date.now(),
            exp: Date.now() + 90 * DAY,
            gm: true
          });
          done = true;
        } else {
          // 收回：先扣未领取的礼物箱条目，再扣背包
          var need = -n;
          for (var i = 0; i < s.x.presents.length && need > 0; i++) {
            var pz = s.x.presents[i];
            if (String(pz.t) === String(cat) && String(pz.iid) === String(iid)) {
              var take = Math.min(Number(pz.n || 0), need);
              pz.n = Number(pz.n || 0) - take;
              need -= take;
              if (pz.n <= 0) { s.x.presents.splice(i, 1); i--; }
            }
          }
          if (need > 0) {
            var cur = Number(s.items[k] || 0);
            s.items[k] = Math.max(0, cur - need);
          }
          done = true;
        }
      } else if (g.type === 'member') {
        var mid = String(g.id);
        var isMap = !Array.isArray(s.members) && typeof s.members === 'object';
        if (Number(g.count || 0) > 0) {
          if (isMap) s.members[mid] = (Number(s.members[mid] || 0) || 1);
          else if (s.members.indexOf(mid) < 0) s.members.push(mid);
          done = true;
        } else {
          if (isMap) delete s.members[mid];
          else s.members = s.members.filter(function (v) { return String(v) !== mid; });
          done = true;
        }
      } else if (g.type === 'reset') {
        // 清空存档（危险操作，管理器里要二次确认）
        try { localStorage.removeItem(SAVE); } catch (e) {}
        return true;
      }
      if (done) applied.push(seq);
    });
    var okLive = false;
    try {
      if (ctx && ctx.gd) { ctx.gd(s); okLive = true; }
      if (okLive && ctx.Xm) ctx.Xm();
    } catch (e) { okLive = false; }
    if (!okLive) writeSave(s);
    log('gifts applied ' + applied.join(',') + (okLive ? ' (live)' : ' (ls)'));
    // 立刻刷新：拖太久游戏会把它内存里的旧存档写回 localStorage，把礼物覆盖掉
    fetch('/__mgr/ack', { method: 'POST', body: JSON.stringify({ seqs: applied }) })
      .catch(function () {})
      .then(function () { setTimeout(function () { location.reload(); }, 50); });
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
