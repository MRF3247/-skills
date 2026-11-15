# 免费商用中文（简体）字体源名录

收集时间 2026-08-05。全部为 GitHub 官方 release 或官网直链。字体库成品位于
/Users/Jin/Documents/Hermes/免费商用字体库/（18 组、125 文件、~790MB）。

## GitHub 仓库（有 release 可自动下载）
| 字体 | 仓库 | 许可 | 要点 |
|---|---|---|---|
| 思源黑体 | adobe-fonts/source-han-sans | OFL | 2.005R；SC 包 asset 名 09_SourceHanSansSC.zip ~91MB |
| 思源宋体 | adobe-fonts/source-han-serif | OFL | 2.003R；09_SourceHanSerifSC.zip ~132MB |
| 得意黑 | atelier-anchor/smiley-sans | OFL | v2.0.1 单字重斜体 5.5MB，标题/海报利器 |
| 霞鹜文楷 | lxgw/LxgwWenKai | OFL | v1.522，TTF ~24MB/字重 |
| 霞鹜文楷GB | lxgw/LxgwWenkaiGB | OFL | v1.522，简体 GB2312 优化版 |
| 霞鹜新晰黑 | lxgw/LxgwNeoXiHei | OFL | v1.304，TTF + Plus（补字库版） |
| 霞鹜新致宋 | lxgw/LxgwNeoZhiSong | OFL | v1.066，TTF + Plus |
| 小赖字体 | lxgw/kose-font | OFL | v3.126，Xiaolai-Regular.ttf（濑户简体补全） |
| 悠哉字体 | lxgw/yozai-font | OFL | v0.868，Regular/Medium |
| 朱雀仿宋 | TrionesType/zhuque | OFL | v0.210；**无 latest 页**，从 /releases 列表页找 tag |
| 方舟像素 | TakWolf/ark-pixel-font | MIT | 2026.07.20；16px 只在 ark（fusion 仅 10px） |
| 融合像素 | TakWolf/fusion-pixel-font | MIT | 只有 10px 发布 |
| Maple Mono | subframe7536/maple-font | OFL | v7.9；MapleMono-CN.zip 145MB 全格式，解压后只留 ttf 精简到 ~90MB |
| Fira Code | tonsky/FiraCode | OFL | 6.2 |
| JetBrains Mono | JetBrains/JetBrainsMono | OFL | v2.304 |
| Inter | rsms/inter | OFL | v4.1，32MB zip，保留 Variable + static 常用字重 |

## 官网直链（无 GitHub 仓库）
| 字体 | URL | 要点 |
|---|---|---|
| MiSans | https://hyperos.mi.com/font-download/MiSans.zip | 简体 10 字重+VF 225MB；MiSans_L3.zip 生僻字 25MB；全语言 MiSans_Global_ALL.zip 397MB 慎用；许可要求注明来源 |
| 阿里普惠体 3.0 | https://fonts.alibabadesign.com/AlibabaPuHuiTi-3.zip | 273MB；需 Referer: https://www.alibabafonts.com/ + 浏览器 UA 防 403；sha256 f25f730b6a7661bcd5b9764dc98f05d3ac25ee771977cf04b31ed5fba9f496a7（对 AUR 记录） |
| OPPO Sans 3.0 | https://coloros-website-cn.allawnfs.com/font/OPPOSans3.0.zip | 49MB；zip 内文件名 GBK 编码，macOS unzip 解不出，Python zipfile cp437→gbk 解码提取 |
| 江西拙楷 2.0 | 夸克 https://pan.quark.cn/s/0ccadb77af13；百度 https://pan.baidu.com/s/1soyvHGAB_u8ufN3TfPoYzQ?pwd=6666 | **2.0 免费商用，3.0 大字库版收费**；网盘需手动下载；猫啃页 https://www.maoken.com/freefonts/1438.html |
| HarmonyOS Sans | https://developer.huawei.com/consumer/cn/design/resource-V1 | 免费商用，需登录 |
| 站酷系列 | https://www.zcool.com.cn | 免费商用（高端黑/快乐体/仓耳渔阳体等） |
| 阿里妈妈方圆体/刀隶体 | https://www.alibabafonts.com | 免费商用 |
| 更纱黑体 | be5invis/Sarasa-Gothic | OFL，单包 >300MB 未收 |
| 猫啃网 | https://www.maoken.com | 无 GitHub 仓库字体的汇总站，网盘下载 |

## 未收录原因备忘
- 齐伋体 qiji-font、粉圆体 open-huninn-font: 繁体为主，简体场景用不上
- 更纱黑体: 体积过大；江城圆体/字制区喜脉体: 仅网盘，未主动收

## AUR PKGBUILD 直链挖掘法
包名示例: ttf-misans（MiSans）、alibabasans-puhuiti3-fonts（阿里普惠体 3.0）
URL: https://aur.archlinux.org/cgit/aur.git/plain/PKGBUILD?h=<包名>
PKGBUILD 的 source=() 段含真实下载 URL 和 sha256 校验值；AUR 评论常提示防盗链细节（需 Referer 等）。
