# -*- coding: utf-8 -*-
"""知识库索引与检索核心。

负责扫描 wiki 目录、解析 ``[[双链]]``、提供条目读取与全文检索能力。
目录结构（知识库根目录下）：

- ``concept/``     抽象概念：辨证体系、病机、证候、病因、治法、理论术语
- ``entity/``      具体事物：药、方、穴、症状、病名
- ``source/``      五部古籍全文（丁甘仁医案、傅青主女科、傅青主男科、医学衷中参西录、针灸大成）
- ``source_ref/``  知识来源：被引用的古籍（books/）与医家（figures/）
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

# 各目录的中文说明，用于给 MCP 客户端展示
CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "concept": "抽象概念：辨证体系、病机、证候、病因、治法、理论术语",
    "entity": "具体事物：药物、方剂、腧穴、症状群、病名",
    "source": "五部古籍全文（语料库）",
    "source_ref": "知识来源：被引用的古籍与医家",
}

# 双链语法：[[名称]]，语料中不存在别名与锚点写法
_LINK_RE = re.compile(r"\[\[([^\[\]]+)\]\]")


@dataclass
class Entry:
    """一个 wiki 条目，对应一个 md 文件。"""

    name: str  # 条目名，即文件名去掉 .md
    category: str  # 所在目录名：concept / entity / source / source_ref
    path: Path  # 文件绝对路径

    def label(self) -> str:
        """返回「分类/条目名」形式的标识，用于展示。"""
        return f"{self.category}/{self.name}"


class WikiIndex:
    """知识库索引：扫描条目、建立双链图谱、提供检索。"""

    def __init__(self, root: Path | None = None):
        # 知识库根目录：优先取环境变量 TCM_WIKI_ROOT，否则默认为本包所在仓库的根目录
        if root is None:
            env_root = os.environ.get("TCM_WIKI_ROOT")
            if env_root:
                root = Path(env_root)
            else:
                # src/tcm_wiki_mcp/wiki.py -> 上溯两级到仓库根
                root = Path(__file__).resolve().parents[2]
        self.root = Path(root)
        if not self.root.is_dir():
            raise FileNotFoundError(f"知识库根目录不存在：{self.root}")

        # 扫描所有条目
        self._entries: list[Entry] = []
        for category in CATEGORY_DESCRIPTIONS:
            cat_dir = self.root / category
            if not cat_dir.is_dir():
                continue
            for md in cat_dir.rglob("*.md"):
                self._entries.append(Entry(md.stem, category, md))
        if not self._entries:
            raise FileNotFoundError(f"知识库根目录下未找到任何条目：{self.root}")

        # 条目名 -> 条目列表（同一名字可能存在于多个分类，如 六腑 同时有 concept 与 entity）
        self._by_name: dict[str, list[Entry]] = {}
        for entry in self._entries:
            self._by_name.setdefault(entry.name, []).append(entry)

        # 双链图谱：一次性读取全部文件并解析，出链与反链各建一张表
        self._outgoing: dict[str, set[str]] = {}  # 条目标识 -> 其引用的条目名集合
        self._backlinks: dict[str, set[str]] = {}  # 条目名 -> 引用它的条目标识集合
        for entry in self._entries:
            text = entry.path.read_text(encoding="utf-8")
            linked = {m.strip() for m in _LINK_RE.findall(text) if m.strip()}
            key = entry.label()
            self._outgoing[key] = linked
            for target in linked:
                self._backlinks.setdefault(target, set()).add(key)

    # ---------- 条目列举与查找 ----------

    def categories(self) -> dict[str, int]:
        """返回各分类及其条目数量。"""
        counts: dict[str, int] = {}
        for entry in self._entries:
            counts[entry.category] = counts.get(entry.category, 0) + 1
        return counts

    def list_entries(self, category: str, keyword: str | None = None) -> list[Entry]:
        """列出某分类下的条目，可按关键词过滤条目名。"""
        self._check_category(category)
        result = [e for e in self._entries if e.category == category]
        if keyword:
            result = [e for e in result if keyword in e.name]
        result.sort(key=lambda e: e.name)
        return result

    def find(self, name: str, category: str | None = None) -> list[Entry]:
        """按名称查找条目：先精确匹配文件名，再退化为名称包含。"""
        if category is not None:
            self._check_category(category)
        pool = self._entries if category is None else [e for e in self._entries if e.category == category]
        exact = [e for e in pool if e.name == name]
        if exact:
            return exact
        return [e for e in pool if name in e.name]

    def read(self, entry: Entry) -> str:
        """读取条目全文。"""
        return entry.path.read_text(encoding="utf-8")

    # ---------- 双链 ----------

    def links(self, name: str) -> dict:
        """返回条目的出链（它引用了谁）与反链（谁引用了它）。"""
        matches = self.find(name)
        if not matches:
            raise KeyError(f"未找到条目：{name}")
        result = []
        for entry in matches:
            key = entry.label()
            out = sorted(self._outgoing.get(key, set()))
            back = sorted(self._backlinks.get(entry.name, set()))
            result.append({"entry": key, "outgoing": out, "backlinks": back})
        return {"name": name, "results": result}

    # ---------- 全文检索 ----------

    def search(self, query: str, category: str | None = None, limit: int = 10) -> list[dict]:
        """全文检索：多个词以空格分隔时要求全部出现（AND），按出现次数排序。"""
        if category is not None:
            self._check_category(category)
        terms = [t for t in query.split() if t]
        if not terms:
            raise ValueError("检索词不能为空")
        pool = self._entries if category is None else [e for e in self._entries if e.category == category]

        scored: list[tuple[int, Entry, str]] = []
        for entry in pool:
            text = entry.path.read_text(encoding="utf-8")
            counts = [text.count(t) for t in terms]
            if all(c > 0 for c in counts):
                snippet = self._snippet(text, terms)
                scored.append((sum(counts), entry, snippet))
        scored.sort(key=lambda x: -x[0])

        return [
            {"entry": entry.label(), "hits": total, "snippet": snippet}
            for total, entry, snippet in scored[: max(1, limit)]
        ]

    @staticmethod
    def _snippet(text: str, terms: list[str], width: int = 120) -> str:
        """截取第一个命中词附近的上下文片段。"""
        positions = [text.find(t) for t in terms if text.find(t) >= 0]
        start = max(0, min(positions) - width // 2)
        end = min(len(text), min(positions) + width)
        prefix = "…" if start > 0 else ""
        suffix = "…" if end < len(text) else ""
        return prefix + text[start:end].replace("\n", " ") + suffix

    # ---------- 内部工具 ----------

    @staticmethod
    def _check_category(category: str) -> None:
        """校验分类名是否合法。"""
        if category not in CATEGORY_DESCRIPTIONS:
            valid = "、".join(CATEGORY_DESCRIPTIONS)
            raise ValueError(f"未知分类「{category}」，可用分类：{valid}")
