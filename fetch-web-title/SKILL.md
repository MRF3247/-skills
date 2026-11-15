---
name: fetch-web-title
description: 从 URL 抓取网页/视频/文章原标题。Use when 要按原稿标题重命名链接、取网页标题。
---

# 网页原标题抓取（curl + og:title）

从任意 URL（B站视频、公众号、知乎、新闻站等）获取**原稿件标题**。典型场景：链接收藏重命名、素材库 URL 归档补标题、把 AI 总结标题替换为原稿标题。

## 核心方法（2026-08-05 实测）

```python
import subprocess, re

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

def curl_title(url, timeout=10):
    """抓原网页标题；失败返回 None（不抛异常，调用方自行降级）"""
    try:
        r = subprocess.run(
            ["curl", "-sL", "--compressed", "--max-time", str(timeout),
             "-A", UA, "-H", "Accept-Language: zh-CN,zh;q=0.9", url],
            capture_output=True, timeout=timeout + 5)
        html = r.stdout.decode("utf-8", errors="ignore")
    except Exception:
        return None
    # 优先 og:title（两种属性顺序都要试）
    m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html)
    if not m:
        m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title["\']', html)
    if m:
        t = m.group(1).strip()
    else:
        m = re.search(r'<title[^>]*>(.*?)</title>', html, re.S)
        if not m:
            return None
        t = re.sub(r'\s+', ' ', m.group(1)).strip()
    # 清理站点后缀
    t = re.sub(r'_哔哩哔哩_bilibili$| - 哔哩哔哩$|_知乎$| - 知乎$| - 微信公众号文章$', '', t).strip()
    return t or None
```

## 关键坑（全部实测）

- **必须 `curl -sL --compressed`**：urllib 直接请求 B站会拿到 gzip 压缩的二进制流（`\x1f\x08` 开头）且不解压，标题解析必然失败；`--compressed` 让 curl 自动解压。urllib 方案直接弃用
- **完整浏览器 UA**：裸 UA 会被部分站点（B站等）反爬拒绝；用 Chrome/126 完整 UA 串
- **解析顺序**：og:title 优先于 `<title>`（og:title 更干净）；meta 标签 property 和 content 的前后顺序有两种写法都要匹配
- **站点后缀清理**：og:title 常带站点尾巴（B站 `_哔哩哔哩_bilibili`、知乎 ` - 知乎`、公众号 ` - 微信公众号文章`），统一正则剥掉，否则标题污染
- **JS 渲染站抓不到**：抖音（douyin.com）标题在 JS 数据里，静态 HTML 无 og:title/title；B站 OK、公众号/知乎 OK。遇到抓不到的站点：**保留原标题不动**（不要编造），统计跳过数量汇报
- **失效/404/登录墙**：一律返回 None，不阻塞批量流程；单请求超时 8-12s
- ⚠️ **失效页面会返回 200 + 错误页标题**（不是 None）：小红书被删文章返回「小红书 - 你访问的页面不见了」、B站被删视频返回「视频去哪了呢？」——curl 跟随重定向后 200 正常返回，og:title 解析到的是错误页文案。必须加黑名单检测：标题含「页面不见了/视频去哪了/404/不存在/无法访问」等词 → 视为抓取失败，恢复原标题
- **恢复机制**：重命名时把原 AI 总结标题写入内容第一行（`一句话总结：XXX`），标题抓错/失效时可从第一行提取恢复原标题
- **标题长度校验**：抓到的标题 <2 字符或 >150 字符视为异常丢弃

## 批量应用模式

- 重命名工作流（如链接笔记）：详情接口拿 url → 逐条 curl_title → 成功则 update 标题、把原 AI 总结放内容第一行；跳过内部链接（无原稿件概念的站内短链）
- 断点续跑：处理状态写 state JSON（每篇 renamed/skipped/failed），中断后跳过已处理的
- 先小样验证（3-5 篇）再全量：确认目标站点能抓到、后缀清理符合预期
- 相关场景：得到大脑（Get 笔记）link 笔记重命名，见 skill `getnote-api`（其 scripts/retitle_links.py 完整实现）
