# 已验证下载源快照（2026-08-05/06，macOS 实测，20 组全量）

## GitHub 官方 release（直链模式 https://github.com/{owner}/{repo}/releases/download/{tag}/{asset}）

### 第一批（01-10）
| 字体 | 仓库 | 版本 | 关键 asset | 大小 |
|---|---|---|---|---|
| 思源黑体 SC | adobe-fonts/source-han-sans | 2.005R | 09_SourceHanSansSC.zip（7 字重 OTF） | 91MB |
| 思源宋体 SC | adobe-fonts/source-han-serif | 2.003R | 09_SourceHanSerifSC.zip（7 字重 OTF） | 132MB |
| 得意黑 | atelier-anchor/smiley-sans | v2.0.1 | smiley-sans-v2.0.1.zip | 5.5MB |
| 霞鹜文楷 | lxgw/LxgwWenKai | v1.522 | LXGWWenKai-Regular.ttf / -Medium.ttf | 各 ~24MB |
| Fira Code | tonsky/FiraCode | 6.2 | Fira_Code_v6.2.zip | 2.3MB |
| JetBrains Mono | JetBrains/JetBrainsMono | v2.304 | JetBrainsMono-2.304.zip | 5.4MB |
| Inter | rsms/inter | v4.1 | Inter-4.1.zip | 32MB |

注意：思源 SC zip 的 01~12 编号对应 全语言ttc/VF/OTC/OTF/Subset/Resources/JP/K/SC/TC/HC 等，09 才是简体 SC。

### 第二批（11-18，2026-08-05）
| 字体 | 仓库 | 版本 | 关键 asset | 大小 |
|---|---|---|---|---|
| 霞鹜新晰黑 | lxgw/LxgwNeoXiHei | v1.304 | LXGWNeoXiHei.ttf + Plus.ttf | 8.1M + 9.2M |
| 霞鹜新致宋 | lxgw/LxgwNeoZhiSong | v1.066 | LXGWNeoZhiSong.ttf + Plus.ttf | 11M + 13M |
| 朱雀仿宋 | TrionesType/zhuque | v0.210 | ZhuqueFangsong-v0.210.zip（无 latest 页，从 releases 列表抓 tag） | 5.9MB |
| 霞鹜文楷 GB 版 | lxgw/LxgwWenkaiGB | v1.522 | LXGWWenKaiGB-Regular/Medium.ttf | 各 ~25MB |
| 小赖字体 | lxgw/kose-font | v3.126 | Xiaolai-Regular.ttf | 22MB |
| 悠哉字体 | lxgw/yozai-font | v0.868 | Yozai-Regular/Medium.ttf | 各 15MB |
| 方舟像素字体 | TakWolf/ark-pixel-font | 2026.07.20 | ark-pixel-font-16px-proportional-otf-*.zip（MIT） | 2.3MB |
| Maple Mono CN | subframe7536/maple-font | v7.9 | MapleMono-CN.zip（解压后只留 6 个 ttf ~89M） | 134MB |

注：TakWolf/fusion-pixel-font 是 ark 的继任但只发 10px；16px 用 ark。lxgw 系全部 OFL。

### 第三批（19-20，2026-08-06，从小红书 13 站线索挖出）
| 字体 | 仓库 | 版本 | 关键 asset | 大小 |
|---|---|---|---|---|
| 猫啃什锦黑 | maoken-fonts/MaokenAssortedSans | v1.70 | MaokenAssortedSans.ttf | 13MB |
| 猫啃硬笔楷书 | maoken-fonts/MaokenYingBiKaiShuJ | 0.10 | MaokenYingBiKaiShuJ_0.10.zip | 3.7MB |
| 猫啃王风雅宋 | maoken-fonts/fengyasong | v1.30 | MaoKenWangFengYaSong.ttf | 17MB |
| 猫啃圆磨体 | maoken-fonts/KNYuanmo | v0.74 | KNYuanmo-Regular.ttf | 3.9MB |
| 寒蝉圆黑体 | Warren2060/ChillRoundGothic | v3.750 | ChillRoundGothic.v3.75.zip | 51MB |
| 寒蝉手拙体 | Warren2060/ChillShouZhuo | v2.500 | ChillZhuo_v2.500.zip | 13MB |
| 寒蝉炭黑体 | Warren2060/ChillTanHei | v1.00 | ChillTanHei_v1.00.zip（含有机/无机×宽窄多变体 8 个 otf） | 59MB |

- maoken-fonts 组织共 8 个字体仓库（含 KNBobohei、LongZhuTi 等未收）；Warren2060 寒蝉 Chill 系列 20 个仓库（ChillGSans/ChillRound/Chillkai 等）。
- maoken-fonts/slidefont（演示系列：演示秋鸿楷等）：**无 release 直链**，只能从优设字体频道/猫啃网下载。
- 演示系列/站酷系列/江城系列：无 GitHub 官方源。

## 官网直链（AUR PKGBUILD 挖出 / bundle 挖出）

- MiSans 简体中文：`https://hyperos.mi.com/font-download/MiSans.zip`（10 字重 ttf + VF，225MB）
- MiSans 生僻字 L3：`https://hyperos.mi.com/font-download/MiSans_L3.zip`（24MB）
- MiSans 全语言：`https://hyperos.mi.com/font-download/MiSans_Global_ALL.zip`（397MB，太大一般不收）
  - 路径是 font-**download**；官网下载页为 Next.js 渲染，URL 拼接逻辑在 `_next/static/chunks/pages/[locale]/download-*.js` 里（URL = origin + "/font-download" + 文件名）
- 阿里巴巴普惠体 3.0：`https://fonts.alibabadesign.com/AlibabaPuHuiTi-3.zip`（273MB，10 字重 OTF；**需 Referer: https://www.alibabafonts.com/ + 浏览器 UA**；sha256=f25f730b6a7661bcd5b9764dc98f05d3ac25ee771977cf04b31ed5fba9f496a7）
- OPPO Sans 3.0：`https://coloros-website-cn.allawnfs.com/font/OPPOSans3.0.zip`（49MB，3 字重；**zip 内文件名 GBK 编码**，见 SKILL.md 处理法；4.0 直链未找到，官网页面提供）

## AUR 包名索引（直链金矿）

- MiSans：`ttf-misans`（source 含 MiSans_Global_ALL.zip）
- 阿里普惠体 3.0：`alibabasans-puhuiti3-fonts`（source 含 AlibabaPuHuiTi-3.zip + sha256）
- 查法：`curl -sL "https://aur.archlinux.org/cgit/aur.git/plain/PKGBUILD?h=<包名>"`，看 source= 段

## 免费字体站导航（小红书 13 站，2026-08-06 整理，详见字体库/字体网站导航.md）

字库星球 zikuxq.com｜猫啃网 maoken.com（可生成授权证书）｜优设字体 hao.uisdc.com/font｜字体天下 fonts.net.cn｜100FONT 100font.com｜字体搬运工 font.sucai999.com｜字由 hellofont.cn（客户端）｜Fontshare fontshare.com（英文）｜洋芋田 potatofield.cn/fontlibrary｜自由字体 ziyouziti.com｜求字体 qiuziti.com（识别工具）｜站长字体 font.chinaz.com｜光合字体天下（fonts.net.cn 板块）

## 网盘发布（无法自动下载，给链接+版本提示）

- 江西拙楷（楷体，站酷设计师 Fontree）：夸克 https://pan.quark.cn/s/0ccadb77af13；百度 https://pan.baidu.com/s/1soyvHGAB_u8ufN3TfPoYzQ?pwd=6666；**2.0 免费商用，3.0 大字库收费**
- HarmonyOS Sans：华为开发者联盟 https://developer.huawei.com/consumer/cn/design/resource-V1（需登录）
- 站酷系列：https://www.zcool.com.cn
- 阿里妈妈方圆体/刀隶体：https://www.alibabafonts.com
- 更纱黑体 Sarasa Gothic：GitHub be5invis/Sarasa-Gothic（单包 >300MB）
- 汇总站：https://www.maoken.com（猫啃网）
