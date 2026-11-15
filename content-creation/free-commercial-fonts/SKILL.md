---
name: free-commercial-fonts
description: Use when 查找/下载/整理免费可商用字体，或确认某字体能否商用。含中文字体选型、官网直链挖掘、批量下载整理流程。
---

# 免费商用字体（Free Commercial Fonts）

## 触发场景
- 用户要「免费/无版权/可商用字体」、批量下载字体、整理字体库、海报/视频/PPT 选字体、确认某字体授权。
- 2026-08 已在 /Users/Jin/Documents/Hermes/免费商用字体库 建好 23 组字体库（~183 文件 / 1.4GB），README.md 有完整清单与许可，字体网站导航.md 是 13 个免费字体站索引；已全部安装到 ~/Library/Fonts/free-commercial-fonts/（CoreText 递归扫描子目录，卸载=删文件夹）。**用户默认期望：下载完自动装进系统**（说过「你先把你下下来的这些字体安装一下吧」）。
- 用户 2026-08-05 纠正过「搜得不全」：找字体要系统搜 GitHub（不止知名清单），且**简体中文优先**；清单交付禁止「等N个」省略。

## 主流免费商用字体速查（2026-08 验证）
- 思源黑体/思源宋体 Source Han Sans/Serif SC：SIL OFL 1.1，可商用可改可再分发；GitHub adobe-fonts/source-han-sans、source-han-serif（SC 子集 zip 90~132MB，7 字重 OTF）
- 得意黑 Smiley Sans：OFL，单字重斜体，海报/标题神器；GitHub atelier-anchor/smiley-sans
- 霞鹜文楷 LXGW WenKai：OFL，手写/楷体，字幕文艺风；GitHub lxgw/LxgwWenKai（单文件 TTF ~24MB）
- Fira Code / JetBrains Mono / Inter：OFL 西文/代码字体，GitHub 官方 release
- MiSans：免费商用但**禁改编**、需注明来源；小米官网 hyperos.mi.com（10 字重+VF）
- OPPO Sans：免费商用**禁改编**；OPPO 官网（3.0 为 3 字重）
- 阿里巴巴普惠体 3.0：免费商用**禁改编**；阿里官网（10 字重）
- HarmonyOS Sans：免费商用；华为开发者联盟下载需登录（未自动收录）
- 站酷系列/阿里妈妈方圆体/更纱黑体/江城圆体：免费商用，见 maoken.com 猫啃网

许可速记：OFL 系可改可再分发（分发须保留版权声明）；大厂系（阿里/MiSans/OPPO/华为）免费商用但禁改编、禁单独售卖字体文件；**IPA Font License 1.0**（一点明体 I.Ming、霞鹜铭心宋等日系衍生）可商用可改但衍生须继承 IPA、**与 OFL 不兼容**；CC0（汇文明朝体修正版）最干净。字魂扁桃体 = 得意黑二创、OFL 开源（字魂首款开源字体，勿与其他字魂付费字体混淆）。用字体做的海报/视频/文档本身商用无忧。

### 2026-08-06 追加验证仓库（宋体专题/热门字体/日文，详见 references/font-sources.md 第四批表）
- 一点明体 ichitenfont/I.Ming（IPA 1.0，8.10）；源云明朝 ButTaiwan/genwan-font（OFL，v2.100，同作者还有 genyo/genryu 源样/源流）
- 汇文明朝体修正 bosswnx/huiwenmincho-improved（CC0，raw main 分支直接下 ttf）；霞鹜铭心宋 lxgw/LxgwHeartSerif（IPA 1.0，**已停止维护**但 release 可用）；寒蝉端黑宋 Warren2060/ChillDuanHeiSong（OFL，14 变体）
- Nom Na Tong 喃那宋 nomfoundation/font（MIT）；ひな明朝 → google/fonts 仓库 ofl/hinamincho/（OFL）
- 热门款合集：dxinef/freefonts（80 个文件，含优设字由棒棒体/字由文艺黑/沐瑶软笔手写体/胡晓波骚包体）；**沐瑶软笔手写体旧版 v2.20 有 FlexiFont 商用隐患，务必用 2021 v1.00 重做版**
- 网盘发布（只记链接）：字魂扁桃体（OFL，夸克/百度 pwd=6666）、猴尊宋体（抖音博主，短视频字幕）、Minglish（明朝风西文，100font 夸克）、优设鲨鱼菲特健康体（百度 pwd=sxir）——具体链接在字体库 README.md

## 下载工作流（GitHub 官方源，优先）
1. 找候选仓库：GitHub 搜索 `/search/repositories?q=chinese+font` 按 stars 排序（再搜 `中文字体`、`simplified chinese font`）；也翻组织/作者主页列仓库（实测 maoken-fonts 组织 8 个字体仓库、Warren2060 寒蝉系列 20 个）。**license 字段可能为 null，取值必须判空**（`lic = it.get("license"); lic.get("spdx_id") if lic else None`）。无 token 限流 10 req/min，请求间 sleep 7s。
2. 抓 asset 直链：**新版 GitHub release 页 asset 是懒加载，HTML 无直链；GitHub API 又易 403 限流** → 用无 API 限流的 HTML 端点 `https://github.com/{owner}/{repo}/releases/expanded_assets/{tag}`（tag 从 `releases/latest` 的 302 `url_effective` 取；无 latest 的仓库从 releases 列表页抓 tag），grep `releases/download/[^"<>]*`。脚本：scripts/scan_github_releases.sh。
3. release 直链模式：`https://github.com/{owner}/{repo}/releases/download/{tag}/{asset}`
4. 并行下载：多条 `curl -sL --retry 4 --retry-delay 3 -o <file> <url>` 加 `&` 与 `wait`，大文件后台跑 notify_on_complete
5. 校验：`file -b` 结果须含 TrueType/OpenType；有官方 sha256 就 `shasum -a 256` 对比（AUR PKGBUILD 常带 sha256sums，可作权威校验）

## 官网字体直链挖掘（官网 JS 下载页无静态 href 时）
1. **AUR 金矿（首选）**：`https://aur.archlinux.org/cgit/aur.git/plain/PKGBUILD?h=<包名>`，包名猜 `ttf-<字体>` / `<字体>-fonts`；source= 段直接给出官方 zip 直链 + sha256。实测：MiSans（ttf-misans）、阿里普惠体 3.0（alibabasans-puhuiti3-fonts）。
2. **JS 渲染官网**：browser 打开下载页 → console 列 script[src] 找 `pages/*/download-*.js` → curl 抓 bundle → grep `font-download|\.zip` 找 URL 拼接逻辑（实测 MiSans：`window.location.origin + "/font-download" + 文件名`，注意是 font-**download** 不是 font/download）。browser_console 表达式要小（大 JSON 会 400），分步查询。
3. **防盗链**：阿里系等需 `-H "Referer: <官网>"` + 浏览器 UA；403 先加头重试，勿判死。
4. 命名试探效率低，最后用：常见 zip 名逐一 `curl -sIL -w "%{http_code}"`。

## GBK 文件名 zip 坑（OPPO 官方包实测）
- macOS unzip 对 GBK 中文文件名 zip 解压会失败（目录空或乱码路径），但 zip 本身完好。
- 修复：Python `zipfile` + `info.filename.encode("cp437", errors="replace").decode("gbk", errors="replace")` 逐个提取。
- 先 `unzip -t` 确认 zip 完好，别把编码问题误判成下载损坏。

## 特殊下载源（实测）
- **Google Fonts 字体**：`fonts.google.com/download?family=` 接口现在返回 HTML 网页，别用 → 直链走 GitHub 镜像 `raw.githubusercontent.com/google/fonts/main/ofl/<family>/<file>`（实测 HinaMincho-Regular.ttf）。日文免费字体很多在 Google Fonts（ひな明朝等）。
- **已关闭/失效的配布站**：用 Wayback Machine 救援，`web.archive.org/web/<时间戳>id_/<原始URL>`（**id_ 后缀**拿原始文件防 JS 重写，zip 也能整包下）。流程：goodfreefonts 等字体导航页会给存档链接 → 抓存档 HTML 找 zip 路径 → 拼 id_ 直链（实测あおぞら明朝 7 字重 + IPA_PMincho 从 blueskis.wktk.so 2020 存档全部救回）。
- 网盘发布的（字魂扁桃体/猴尊宋体/Minglish/优设鲨鱼菲特健康体/江西拙楷）：无法自动下载，README 记录 夸克/百度 链接+提取码+版本提示（详见 references/font-sources.md）。

## macOS 安装与验证

- 安装：`mkdir -p ~/Library/Fonts/<子目录>` + `find <字体库> \( -iname '*.ttf' -o -iname '*.otf' \) -exec cp {} <子目录>/ \;`。用户级免 sudo；已开应用需重启才刷新字体列表。
- **验证别用 system_profiler SPFontsDataType**：它有缓存，刚装完查不到 ≠ 没装上（本会话 18 组全部误报 0，实际已注册）。用 CoreText Swift 查 `CTFontManagerCopyAvailableFontFamilyNames`（scripts/verify_fonts.swift）。
- `CTFontManagerRegisterFontsForURL` 返回 OSStatus -50 = 已注册（重复注册的正常信号，不是文件损坏）。
- **家族名可能和文件名/直觉不一致**（实测：Huiwen-mincho 全小写、`Nom Na Tong` 带空格、寒蝉端黑宋 是中文家族名）——CoreText 关键词查不到 ≠ 没装上，用 `CTFontManagerCreateFontDescriptorsFromURL` 读文件真实 family name（kCTFontFamilyNameAttribute）确认。
- 大厂 zip 解压后常有 `__MACOSX` 和 `.textClipping` 打包垃圾，一并清理。

## 其他坑（实测）

- macOS BSD grep：字符类 `[A-Za-z0-9_\-./]` 报 `invalid character range` → 模式简化为 `releases/download/[^"<>]*`。
- shell cwd 卡死：脚本删除自己所在目录后，后续命令报 `getcwd: cannot access parent directories` → 每条命令开头先 `cd` 到有效路径。
- web_extract 会误拦部分国内站点（误判私有网络地址）→ 改用 curl 或 browser。
- 江西拙楷（用户点名过的知名开源楷体）：GitHub 无官方仓库，只网盘发布（夸克/百度）；**2.0 及以前免费商用，3.0 大字库版收费**——收录时务必注明版本。
- 官方组织/作者仓库比杂牌镜像可靠：优先收 `maoken-fonts/*`、`Warren2060/*`（寒蝉）、`lxgw/*`、`TakWolf/*`、`adobe-fonts/*` 等官方源。

## 整理规范
- 每字体一个文件夹，数字前缀编号；保留一种主格式（OTF/TTF 二选一，macOS 通用选 TTF，官方主格式是 OTF 则留 OTF）
- 删 __MACOSX 目录、woff/woff2/eot（网页格式）、重复格式副本、`.textClipping` 等打包垃圾、空目录
- **许可证文件绝不能删**（OFL/LICENSE 是 OFL 再分发的法律要求；曾误删后从 GitHub raw 补回——检查 `find <dir> -iname "*licen*"`）
- 全部文件校验：`file -b` 扫一遍统计异常
- 写 README：完整清单逐条列出（用户偏好：禁止「等N个」省略）、每款许可类型、来源、安装方法（macOS 双击或复制到 ~/Library/Fonts）
- 产物放用户工作目录 /Users/Jin/Documents/Hermes 下，压缩包清理掉省空间

## 支持文件
- references/font-sources.md：已验证直链/版本/大小快照（2026-08，20 组全量）
- scripts/download_fonts.sh：GitHub 源批量下载脚本模板（改 BASE 即可用）
- scripts/scan_github_releases.sh：expanded_assets 批量抓 release 直链（避 API 限流）
- scripts/verify_fonts.swift：CoreText 字体注册验证（system_profiler 有缓存不可靠）

---

## 已合并的同类技能（2026-09-23 归并）

以下技能内容已并入本技能，原文存档在 `references/`，脚本/模板在 `scripts/<名称>/`、`templates/<名称>/`。技能清单里不再单独出现它们；需要时读对应文件。

| 原技能 | 适用范围 | 原文 |
|---|---|---|
| `font-library` | 收集/下载免费商用中文字体、搭建字体库、查字体许可。含 GitHub release 抓取与整理校验。 | `references/merged-font-library.md` |
| `free-font-collection` | 搜集/下载/整理/安装免费商用字体时使用。GitHub 官方源→官网直链→网盘；校验、规范命名、装系统、入素材库。 | `references/merged-free-font-collection.md` |
