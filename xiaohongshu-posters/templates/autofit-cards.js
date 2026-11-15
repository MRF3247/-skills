/* 文字卡字号处理（两种模式，二选一）
 *
 * MODE A「统一字号 + 只测量」——**本用户的定案，默认用这个**
 *   给 <div class="body" data-fixed="40"> 写上固定字号，脚本不再改字号，
 *   只把 used / avail / fill% 写进 <title>。渲染后逐页回读，一次拿到「哪张溢出」「哪张太空」。
 *   为什么：逐卡适配会让相邻卡 40↔58 跳变，用户读到的不是「有节奏」而是「不统一」；
 *   他的口径是「以最满那一页的字号为准，全篇统一」。空页用重新分卡解决，不靠缩字。
 *
 * MODE B「逐卡自动适配」——只在用户明确要求「每页各自填满」时用
 *   不给 data-fixed，脚本在 data-maxfit（默认 46，独立节拍卡 52-56）与下限 40
 *   之间二分搜索最大可容纳字号。
 *
 * 所需 HTML 结构：
 *   <div class="page">
 *     <div class="brand">…</div><div class="hr"></div>
 *     <div class="stack">                       <-- flex:1，可居中
 *       <div class="kicker">…</div>              <-- 章节头（可以是复合块：日期+标签+标题）
 *       <div class="body" data-maxfit="46">      <-- MODE B：限定本卡字号上限
 *         <!-- 或 MODE A：<div class="body" data-fixed="40"> 全篇统一字号 -->
 *         <p class="p">正文</p>
 *         <p class="cite">小字引用</p>
 *       </div>
 *     </div>
 *     [可选 .idx 等页脚之上的块]
 *     <div class="foot">…</div>
 *   </div>
 *
 * 取数：Chrome --headless --virtual-time-budget=6000 --dump-dom file:///page.html | grep '<title>'
 *       输出 FIT=<字号> used=<已用高> avail=<可用高> fill=<填充率>
 *
 * 注意：必须给 --virtual-time-budget（>=4000），否则 JS 还没跑完就截图/导出，拿到的是默认字号。
 */
(function () {
  var body = document.querySelector('.body');
  var stack = document.querySelector('.stack');
  if (!body || !stack) return;
  var ps = body.querySelectorAll('p.p');
  if (!ps.length) return;
  var cites = body.querySelectorAll('p.cite');

  // 上限：正文卡 46，封面/序/结语这类独立节拍卡可放到 52-56
  var mx = parseFloat(body.getAttribute('data-maxfit') || '46');
  // 下限即分卡报警线：需要低于 40 才放得下的卡，应该多分一张卡而不是继续缩字
  var mn = 40;
  // MODE A：有 data-fixed = 全篇统一字号，只测量不改字号（本用户默认）
  var fixed = parseFloat(body.getAttribute('data-fixed') || '0');

  function outerH(el) {
    var r = el.getBoundingClientRect(), cs = getComputedStyle(el);
    return r.height + parseFloat(cs.marginTop || 0) + parseFloat(cs.marginBottom || 0);
  }

  // 可用高度 = 容器高 − body 之上【所有】兄弟节点外高 − 安全余量。
  // 只减紧邻的章节头会漏掉复合头部块（日期/标签/标题），DOM 以为放得下、实际溢出到页脚。
  var above = 0, el = body.previousElementSibling;
  while (el) { above += outerH(el); el = el.previousElementSibling; }
  var avail = stack.clientHeight - above - 120;  // 120 = 页脚内边距 + 居中块的上下留白

  var gap = parseFloat(getComputedStyle(body).rowGap || 30) || 30;

  function apply(sz) {
    ps.forEach(function (p) { p.style.fontSize = sz + 'px'; });
    // 引用小字跟随正文缩放（0.55×，不低于 19px）——小是层级，不是不可读
    cites.forEach(function (c) { c.style.fontSize = Math.max(19, Math.round(sz * 0.55)) + 'px'; });
    var h = 0, k = 0;
    Array.prototype.forEach.call(body.children, function (ch) {
      h += ch.getBoundingClientRect().height; k++;
    });
    return h + (k - 1) * gap;
  }

  var best;
  if (fixed) {
    best = fixed;                       // MODE A：统一字号，不搜索
  } else {
    best = mn;                          // MODE B：逐卡搜最大可容纳字号
    for (var s = mx; s >= mn; s -= 0.5) { if (apply(s) <= avail) { best = s; break; } }
  }
  var used = apply(best);  // 最后再 apply 一次，避免留下探测过程中的过大字号
  document.title = (fixed ? 'FIXED=' : 'FIT=') + best
                 + ' used=' + Math.round(used) + ' avail=' + Math.round(avail)
                 + ' fill=' + Math.round(used / avail * 100) + '%'
                 + (used > avail ? ' OVERFLOW' : '');
})();
