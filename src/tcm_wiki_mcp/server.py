# -*- coding: utf-8 -*-
"""MCP 服务器定义：将知识库能力暴露为 MCP 工具。

提供五个工具：

- ``list_categories``  列出知识库分类与条目数量
- ``list_entries``     列出某分类下的条目名，可按关键词过滤
- ``get_entry``        读取条目全文
- ``search``           全文检索并返回命中片段
- ``get_links``        查看条目的 [[双链]] 出链与反链
"""

from __future__ import annotations

import json

from mcp.server.mcpserver import MCPServer

from .wiki import CATEGORY_DESCRIPTIONS, WikiIndex

mcp = MCPServer("tcm-wiki", instructions="中医知识库（丁甘仁医案、傅青主女科/男科、医学衷中参西录、针灸大成语料的结构化笔记）。先用 search 定位条目，再用 get_entry 读取全文，用 get_links 沿双链扩展相关知识。")

# 全局共享一个索引实例，启动时完成扫描
_index = WikiIndex()


@mcp.tool()
def list_categories() -> str:
    """列出知识库的分类目录及各分类条目数量。"""
    lines = ["知识库根目录：" + str(_index.root), ""]
    for category, count in _index.categories().items():
        desc = CATEGORY_DESCRIPTIONS.get(category, "")
        lines.append(f"- {category}（{count} 条）：{desc}")
    return "\n".join(lines)


@mcp.tool()
def list_entries(category: str, keyword: str | None = None) -> str:
    """列出某分类下的条目名，可按关键词过滤条目名。

    Args:
        category: 分类名，取值 concept / entity / source / source_ref
        keyword: 可选，过滤条目名中包含该关键词的条目
    """
    try:
        entries = _index.list_entries(category, keyword)
    except ValueError as exc:
        # 分类名非法时返回可读提示，避免异常被框架吞掉后客户端拿不到可用分类
        return str(exc)
    if not entries:
        return f"分类 {category} 下没有匹配的条目。"
    suffix = f"（名称含「{keyword}」）" if keyword else ""
    lines = [f"分类 {category}{suffix} 共 {len(entries)} 条：", ""]
    lines += [f"- {e.name}" for e in entries]
    return "\n".join(lines)


@mcp.tool()
def get_entry(name: str, category: str | None = None) -> str:
    """读取条目全文。同名条目存在于多个分类时会全部返回。

    Args:
        name: 条目名，如「人参」「六经辨证」
        category: 可选，限定分类以精确查找
    """
    try:
        matches = _index.find(name, category)
    except ValueError as exc:
        return str(exc)
    if not matches:
        return f"未找到条目「{name}」。可先用 search 全文检索，或用 list_entries 查看条目列表。"
    parts = []
    for entry in matches:
        parts.append(f"## {entry.label()}\n\n" + _index.read(entry))
    return "\n\n---\n\n".join(parts)


@mcp.tool()
def search(query: str, category: str | None = None, limit: int = 10) -> str:
    """全文检索知识库。多个词用空格分隔表示同时包含（AND），结果按命中次数排序。

    Args:
        query: 检索词，如「血崩 补阴」
        category: 可选，限定分类范围
        limit: 最多返回条数，默认 10
    """
    try:
        results = _index.search(query, category, limit)
    except ValueError as exc:
        # 覆盖空检索词与非法分类两种情况
        return str(exc)
    if not results:
        return f"知识库中没有同时包含这些词的条目：{query}"
    lines = [f"检索「{query}」命中 {len(results)} 条（按命中次数排序）：", ""]
    for r in results:
        lines.append(f"### {r['entry']}（命中 {r['hits']} 次）")
        lines.append(r["snippet"])
        lines.append("")
    return "\n".join(lines)


@mcp.tool()
def get_links(name: str) -> str:
    """查看条目的双链关系：出链（该条目引用了谁）与反链（谁引用了该条目）。

    Args:
        name: 条目名，如「痰」「六腑」
    """
    try:
        data = _index.links(name)
    except KeyError:
        return f"未找到条目「{name}」。"
    return json.dumps(data, ensure_ascii=False, indent=2)


def main() -> None:
    """启动 MCP 服务器（stdio 传输）。"""
    mcp.run(transport="stdio")
