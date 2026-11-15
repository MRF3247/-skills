#!/bin/bash
# 批量抓取 GitHub 仓库最新 release 的下载链接（expanded_assets 端点，无 API 限流）
# 用法: bash scan_github_releases.sh owner/repo1 owner/repo2 ...
# 输出: 每个仓库的 tag + releases/download/... 直链列表
for repo in "$@"; do
  echo "===== $repo"
  # 最新 tag: releases/latest 会 302 到 /releases/tag/xxx；无 latest 的仓库留在原 URL
  tag=$(curl -sIL --connect-timeout 15 -o /dev/null -w "%{url_effective}" "https://github.com/$repo/releases/latest" | sed 's|.*/releases/tag/||')
  if [ -z "$tag" ] || [ "$tag" = "https://github.com/$repo/releases/latest" ]; then
    echo "  (无 latest 页，从 Releases 列表找 tag)"
    tag=$(curl -sL --connect-timeout 15 -A "Mozilla/5.0" "https://github.com/$repo/releases" \
      | grep -oE "/$repo/releases/tag/[A-Za-z0-9_.\-]*" | sed 's|.*tag/||' | sort -u | head -1)
  fi
  echo "  tag: $tag"
  if [ -n "$tag" ]; then
    curl -sL --connect-timeout 15 -A "Mozilla/5.0" "https://github.com/$repo/releases/expanded_assets/$tag" \
      | grep -oE 'releases/download/[^"<>]*' | sort -u | head -14
  fi
  sleep 1
done
