/* 彩票本地化：在模块加载前接管 fetch，处理 /api/lottery/* */
window.__KFL=5;
(function () {
  try {
    window.__reqs = window.__reqs || [];
    var __f0 = window.fetch;
    window.fetch = function (u, o) {
      try { window.__reqs.push(String(u).slice(0, 120)); if (window.__reqs.length > 400) window.__reqs.shift(); } catch (e) {}
      return __f0.apply(this, arguments);
    };
    var SAVE = 'oldui59.save';
    function readSave() { try { return JSON.parse(localStorage.getItem(SAVE)); } catch (e) { return null; } }
    function writeSave(s) {
      var txt = JSON.stringify(s);
      for (var i = 0; i < 10; i++) localStorage.setItem(SAVE, txt);
    }
    function rand6() { return String(Math.floor(Math.random() * 900000) + 100000); }
    function json(obj, code) {
      return new Response(JSON.stringify(obj), {
        status: code || 200, headers: { 'Content-Type': 'application/json' }
      });
    }

    /* ---- 开奖与发奖：到期未结算的票，比对当日中奖号，中奖写礼物箱 ---- */
    var PRIZE = { 1: [10000000, 100], 2: [5000000, 30], 3: [1000000, 1], 4: [500000, 0] };
    function h32(str) {
      var h = 2166136261 >>> 0;
      for (var i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; }
      return h >>> 0;
    }
    function six(n) { return String(n % 1000000).padStart(6, '0'); }
    function drawNo(day) { return six(h32('konofan-win-' + day)); }
    function settle() {
      var s = readSave(); if (!s || !s.x) return;
      var tk = s.x.lotteryTickets || []; if (!tk.length) return;
      var now = Date.now(), changed = false;
      s.x.presents = s.x.presents || [];
      if (s.x.pseq == null) s.x.pseq = 1;
      tk.forEach(function (t) {
        if (t.settled) return;
        var due = t.due || (t.ts + 24 * 3600 * 1000);
        if (now < due) return;
        t.settled = 1; changed = true;
        var day = new Date(due).toISOString().slice(0, 10);
        var win = t.win || drawNo(day);
        t.win = win;
        var a = String(t.no), b = String(win);
        var hit = (a === b) ? 6 : (a.slice(-5) === b.slice(-5) ? 5 : (a.slice(-4) === b.slice(-4) ? 4 : (a.slice(-3) === b.slice(-3) ? 3 : 0)));
        t.hit = hit;
        var lvl = hit === 6 ? 1 : hit === 5 ? 2 : hit === 4 ? 3 : hit === 3 ? 4 : 0;
        t.level = lvl;
        if (lvl) {
          var pr = PRIZE[lvl], exp = now + 90 * 86400000;
          s.x.presents.unshift({ id: s.x.pseq++, t: 1, iid: '1', n: pr[0],
            msg: '彩票' + lvl + '等奖·艾莉丝（' + win + '）', sent: now, exp: exp, gm: true });
          if (pr[1] > 0) s.x.presents.unshift({ id: s.x.pseq++, t: 39, iid: '1', n: pr[1],
            msg: '彩票' + lvl + '等奖·万能碎片（' + win + '）', sent: now, exp: exp, gm: true });
        }
      });
      if (changed) { writeSave(s); }
    }
    setTimeout(function () { try { settle(); } catch (e) {} }, 3000);

    /* ---- 教团：本地无教团服务，统一返回“未加入”的静态数据，避免招募卡片取值报错 ---- */
    var ADS_CFG = { adsOpen: false, adsDaySlots: 2, adsPersonSlots: 1, adsRotateSec: 5,
      adsRefundPct: 90, adsSettleHour: 21, adsClickLimit: 20, adsBadWords: [],
      adsDayMinBid: 100000000, adsPersonMinBid: 1000000,
      adsPersonCapDefault: 20000000, adsPersonCapMax: 1000000000 };
    function guildHome() {
      return {
        guild: null, joined: false,
        config: { ads: ADS_CFG, rejoinHours: 24, foundRefundPct: 50, donateCost: 10000,
                  donateContrib: 10, duelStartHour: 20, duelEndHour: 21, duelOpen: false,
                  createCost: 50000, applyCooldownHours: 24 }
      };
    }
    function guildPayload(ep) {
      var base = { status: 0, joined: false, list: [], rows: [], more: false, faith: 0,
                   found: false, lands: [], open: false, board: [], data: {}, code: '',
                   view: { slots: [], rotateSec: 5, adsOpen: false } };
      if (ep === 'home' || ep === 'deposit' || ep === 'depositTicket') base.home = guildHome();
      return base;
    }
    /* 下一期开奖时间：设备本地时区每天 20:00 */
    function nextDraw() {
      var d = new Date(), p = function (n) { return (n < 10 ? '0' : '') + n; };
      d.setHours(20, 0, 0, 0);
      if (d.getTime() <= Date.now()) d.setDate(d.getDate() + 1);
      return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()) + 'T20:00:00+08:00';
    }
    var orig = window.fetch ? window.fetch.bind(window) : null;
    window.fetch = function (input, init) {
      var url = (typeof input === 'string') ? input : (input && input.url) || '';
      var gm = url.match(/\/api\/guild\/([A-Za-z0-9_\-\/]+)/);
      if (gm) {
        try { (window.__glog = window.__glog || []).push(gm[1]); } catch (e) {}
        return Promise.resolve(json(guildPayload(gm[1])));
      }
      var m = url.match(/\/lottery\/(buy|home)/);
      if (!m) return orig ? orig(input, init) : Promise.reject(new Error('no fetch'));
      try {
        var s = readSave() || {};
        s.x = s.x || {};
        if (m[1] === 'buy') {
          var body = {};
          try { body = JSON.parse((init && init.body) || '{}'); } catch (e) {}
          var qty = Math.max(1, Math.min(100, parseInt(body.qty || 1, 10) || 1));
          var price = 100000, cost = price * qty;
          s.items = s.items || {};
          var gold = parseInt(s.items['1:1'] || 0, 10);
          if (gold < cost) return Promise.resolve(json({ error: '金币不足' }, 400));
          s.items['1:1'] = gold - cost;
          s.x.lotteryTickets = s.x.lotteryTickets || [];
          var roundId = body.roundId || 1, now = Date.now(), made = [];
          for (var i = 0; i < qty; i++) {
            var t = { no: rand6(), round: String(roundId), ts: now };
            s.x.lotteryTickets.push(t); made.push(t);
          }
          writeSave(s);
          setTimeout(function () { location.hash = '#/home'; location.reload(); }, 400);
          return Promise.resolve(json({ data: { ok: true, qty: qty, tickets: made, gold: s.items['1:1'] } }));
        }
        try { settle(); s = readSave() || s; } catch (e) {}
        var tk = (s.x && s.x.lotteryTickets) || [];
        var draw = nextDraw();
        var mine = tk.map(function (t) {
          var lvl = t.level || 0;
          var hits = null;
          if (t.settled) {
            hits = [0, 0, 0, 0];
            if (lvl >= 1 && lvl <= 4) hits[lvl - 1] = 1;
          }
          return {
            roundId: Number(t.round || 7), qty: 1, spent: 100000,
            drawAt: t.drawAt || draw, winNo: t.win || '',
            status: t.settled ? 'settled' : 'open', hits: hits,
            money: lvl && PRIZE[lvl] ? PRIZE[lvl][0] : 0,
            shards: lvl && PRIZE[lvl] ? PRIZE[lvl][1] : 0
          };
        });
        return Promise.resolve(json({ data: {
          now: new Date().toISOString(),
          round: { id: 7, pot: 500000000, participants: 12, totalTickets: 88 + tk.length,
                   myTickets: tk.length, drawAt: draw,
                   estimate: [7777777, 5000000, 1000000], carry: [0, 0, 0] },
          results: [], mine: mine, tickets: tk
        } }));
      } catch (e) {
        return Promise.resolve(json({ error: String(e) }, 500));
      }
    };
  } catch (e) { /* 静默失败，不影响游戏 */ }
})();
