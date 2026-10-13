# tcm-wiki-mcp

基于 Obsidian 构建的中医知识库 MCP（Model Context Protocol）服务器。

知识库语料为五部古籍：**《丁甘仁医案》《傅青主女科》《傅青主男科》《医学衷中参西录》《针灸大成》**，在此基础上整理出三类结构化笔记：

| 目录 | 内容 | 数量 |
|---|---|---|
| `concept/` | 抽象概念：辨证体系、病机、证候、病因、治法、理论术语 | 47 |
| `entity/` | 具体事物：药物、方剂、腧穴、症状群、病名 | 613 |
| `source/` | 五部古籍全文 | 5 |
| `source_ref/` | 知识来源：被引用的古籍（books/）与医家（figures/） | 45 |

所有条目使用 `[[双链]]` 交叉引用，面向中医诊断 agent 的推理链组织：
症状（entity）→ 病机/证候（concept）→ 治法（concept）→ 方剂、药物（entity）。

## 提供的 MCP 工具

| 工具 | 说明 |
|---|---|
| `list_categories` | 列出知识库分类与条目数量 |
| `list_entries` | 列出某分类下的条目名，可按关键词过滤 |
| `get_entry` | 读取条目全文（同名条目跨分类时会全部返回） |
| `search` | 全文检索，多词空格分隔为 AND 语义，按命中次数排序，返回片段 |
| `get_links` | 查看条目的双链关系：出链与反链 |

## 安装与运行

需要 Python 3.10+（推荐使用 [uv](https://docs.astral.sh/uv/)）。

```bash
# 安装依赖（已配置清华 PyPI 镜像）
uv sync

# 启动 MCP 服务器（stdio 传输）
uv run tcm-wiki-mcp
```

知识库根目录默认为本仓库根目录；如需指向其他位置，设置环境变量 `TCM_WIKI_ROOT`。

## 在 MCP 客户端中配置

### Claude Desktop

在 `claude_desktop_config.json` 中添加（路径改为实际 clone 位置）：

```json
{
  "mcpServers": {
    "tcm-wiki": {
      "command": "uv",
      "args": ["run", "--directory", "K:/zhongyinWIKI/Wiki", "tcm-wiki-mcp"]
    }
  }
}
```

### 其他支持 MCP 的客户端

等价配置：命令 `uv run --directory <仓库路径> tcm-wiki-mcp`，stdio 传输。

## 推荐用法

1. `search` 定位关键词（如「血崩 补阴」）→ 2. `get_entry` 读取条目全文 → 3. `get_links` 沿双链扩展相关病机、方药。

## 许可

MIT
