#!/bin/bash
# 批量抓取 GitHub 仓库最新 release 的下载直链（expanded_assets 端点，无 API 限流）
# 用法: bash scan_github_releases.sh owner/repo1 owner/repo2 ...
# 新版 GitHub release 页 asset 是懒加载(HTML 无直链)；GitHub API 无 token 易 403。
for repo in "$@"; do
  echo "===== $repo"
  tag=$(curl -sIL --connect-timeout 12 -o /dev/null -w "%{url_effective}" "https://github.com/$repo/releases/latest" | sed 's|.*/releases/tag/||')
  echo "  tag: $tag"
  if [ -n "$tag" ] && [ "$tag" != "https://github.com/$repo/releases/latest" ]; then
    curl -sL --connect-timeout 12 -A "Mozilla/5.0" "https://github.com/$repo/releases/expanded_assets/$tag" \
      | grep -oE 'releases/download/[^"<>]*' | sort -u | head -12
  fi
  sleep 1
done
