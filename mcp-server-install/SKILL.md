---
name: mcp-server-install
description: "Use when 装第三方 MCP server 接入 Hermes（uv venv+stdio 握手验证）."
version: 1.0.0
metadata:
  hermes:
    tags: [mcp, install, uv, venv, stdio, integration]
---

# 第三方 MCP server 安装与接入（PyPI/GitHub）

Use when 用户要求「装一个 MCP 工具 / 从 GitHub 装 xx-mcp」并希望能在会话里调用。覆盖选型 → 安装 → 配置 → 验证全流程。config.yaml 的 mcp_servers 细节见受保护的 hermes-mcp-integration skill；本 skill 补 venv 安装与握手验证部分。

## 流程

1. **选型**：同名多仓库时 `git clone --depth 1` 到 /tmp 看 README（web_extract 在本机常被墙）。对比：平台覆盖是否够用、是否需付费 API key、编译成本（TypeScript 版要 npm+tsc，Python 版 uv 一行装，优先 Python）
2. **隔离安装**（不污染 Hermes venv）：
   ```bash
   mkdir -p ~/.hermes/mcp-servers/<name> && cd ~/.hermes/mcp-servers/<name>
   uv venv --python 3.11
   uv pip install --python .venv/bin/python <pypi包名>
   ```
3. **配置** `~/.hermes/config.yaml` → `mcp_servers.<name>`：`command: <venv 绝对路径 python>` + `args: ["-m", "<模块>"]`（stdio 传输）。dict 键必须用 python 精确行替换直改文件（patch 工具拒绝写 config.yaml；`hermes config set` 会把 dict 存成字符串），改前备份，改后 `yaml.safe_load` 验证结构
4. **握手验证**（不必等重启）：python 子进程向 server stdin 发 initialize JSON-RPC，20s 内收到 serverInfo 即通：
   ```python
   proc = subprocess.Popen([".venv/bin/python","-m","<模块>"], stdin=PIPE, stdout=PIPE, stderr=PIPE)
   out,_ = proc.communicate(input=(json.dumps({"jsonrpc":"2.0","id":1,"method":"initialize",
       "params":{"protocolVersion":"2024-11-05","capabilities":{},
                 "clientInfo":{"name":"t","version":"1"}}})+'\n').encode(), timeout=20)
   ```
5. **重启 Hermes 会话**才注入工具（无热加载）；重启前向用户说明「重启后可用 mcp_<name>_* 工具」
6. **功能实测**：MCP 注入前可用 venv python 直接 import 库函数验证——注意看源码确认方法是同步还是 async、返回值是自定义对象还是 dict

## 陷阱

- macOS 无 `timeout` 命令：用 python subprocess 测，别用 `timeout 20 cmd`
- 包的 search 方法可能是**同步**的（`await` 报 TypeError）；返回**自定义对象**（属性访问，无 `.get()`）
- 启动模块名以安装后的实际为准（如 `python -m paper_search_mcp.server`）
- 安装后把 venv 路径记下来，重启前的临时验证和后续排查都要用它

## 参考

- `references/paper-search-mcp.md` — paper-search-mcp 实例记录（PubMed/arXiv/medRxiv 论文检索）
