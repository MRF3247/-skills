# 原型分享链接的读取（墨刀 / SPA 原型）

原型工具（墨刀、Figma、摹客等）的分享页是 canvas / SPA 渲染，`browser_navigate` 返回的 snapshot 常为空，`web_extract` 也拿不到正文。

## 取文字：DOM 里其实全有

墨刀分享页把原型上所有控件文案、标注、批注都渲染成 DOM 文本节点，一行 JS 全拿到：

```js
// browser_console --expression
(() => { const t = document.body.innerText;
  return { len: t.length, text: t.slice(0, 3000),
           canvases: document.querySelectorAll('canvas').length }; })()
```

- `len` 上万说明内容齐全，再分段取（`slice(3000, 8000)`）。
- 批注区文本通常带「编号 + 提示内容 + 批注人姓名」，可直接当需求条目清单用。
- 这是提取全部文案，不是看图；图形（红框、箭头指向哪个控件）取不到，必须靠 vision。

## 看图：先切「演示」再截图

总览模式默认缩放约 4%，一屏缩成一个点，vision 读不出内容。切到单屏演示：

```js
(() => { const els=[...document.querySelectorAll('div,span,a,button,li')]
    .filter(e=>e.textContent.trim()==='演示' && e.children.length===0);
  if(!els.length) return 'not found';
  els[0].click(); return 'clicked'; })()
```

切换后缩放约 50%，`browser_vision` 能读出面包屑、表单、按钮、右侧帮助文案。要逐屏核规则时，改 URL 的 `screen=<id>` 参数逐张截图。

## 注意

- 未登录态会有登录横幅和「浏览器兼容性差」提示遮住底部内容；读文案不受影响，但别把被遮住的部分当依据。
- 判定顺序：先拿到文字清单（含全部阈值与批注），再用图确认「这条批注贴在哪一屏、哪个控件」。只看图会漏掉阈值和文案细节，只看文字会不知道位置。
