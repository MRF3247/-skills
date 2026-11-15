#!/bin/bash
# GitHub 官方 release 批量下载字体模板
# 用法: 改 BASE 和 dl 列表后 bash download_fonts.sh（可后台 + notify_on_complete）
set -u
BASE="/Users/Jin/Documents/Hermes/免费商用字体库"
mkdir -p "$BASE/_压缩包暂存"
cd "$BASE/_压缩包暂存"

dl() { # dl 输出文件名 URL
  curl -sL --retry 4 --retry-delay 3 --connect-timeout 20 -o "$1" "$2" \
    && echo "OK   $1 ($(du -h "$1" | cut -f1))" \
    || echo "FAIL $1"
}

echo "=== 开始下载 $(date '+%H:%M:%S') ==="
dl smiley-sans-v2.0.1.zip "https://github.com/atelier-anchor/smiley-sans/releases/download/v2.0.1/smiley-sans-v2.0.1.zip" &
dl 09_SourceHanSansSC.zip "https://github.com/adobe-fonts/source-han-sans/releases/download/2.005R/09_SourceHanSansSC.zip" &
dl 09_SourceHanSerifSC.zip "https://github.com/adobe-fonts/source-han-serif/releases/download/2.003R/09_SourceHanSerifSC.zip" &
wait
echo "=== 完成 $(date '+%H:%M:%S') ==="
ls -lh

# 官网直链示例（防盗链需带头）:
# curl -sL -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36" \
#      -H "Referer: https://www.alibabafonts.com/" -o AlibabaPuHuiTi-3.zip \
#      "https://fonts.alibabadesign.com/AlibabaPuHuiTi-3.zip"
# 校验: shasum -a 256 AlibabaPuHuiTi-3.zip（对照 AUR 的 sha256sums）
