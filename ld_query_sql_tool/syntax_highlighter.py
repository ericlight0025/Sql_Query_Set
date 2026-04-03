from __future__ import annotations

import re
import tkinter as tk
from typing import Mapping

# 專注常見 SQL 關鍵字，先滿足 GUI 可讀性，不把高亮邏輯做成大型解析器。
SQL_KEYWORDS = (
    "SELECT",
    "FROM",
    "WHERE",
    "AND",
    "OR",
    "NOT",
    "NULL",
    "IS",
    "IN",
    "EXISTS",
    "LIKE",
    "BETWEEN",
    "JOIN",
    "INNER",
    "LEFT",
    "RIGHT",
    "FULL",
    "OUTER",
    "ON",
    "AS",
    "GROUP",
    "BY",
    "ORDER",
    "HAVING",
    "UNION",
    "ALL",
    "DISTINCT",
    "CASE",
    "WHEN",
    "THEN",
    "ELSE",
    "END",
    "INSERT",
    "INTO",
    "VALUES",
    "UPDATE",
    "SET",
    "DELETE",
    "CREATE",
    "ALTER",
    "DROP",
    "TABLE",
    "VIEW",
    "INDEX",
    "WITH",
    "OVER",
    "PARTITION",
    "ROWNUM",
    "ROW_NUMBER",
    "COUNT",
    "SUM",
    "AVG",
    "MIN",
    "MAX",
    "TO_DATE",
    "TO_CHAR",
    "TO_CLOB",
    "SYSDATE",
    "COMMIT",
    "ROLLBACK",
)

SQL_HIGHLIGHT_TAG_NAMES = (
    "sql_keyword",
    "sql_string",
    "sql_comment",
    "sql_number",
    "sql_placeholder",
    "sql_bind_variable",
)

SQL_TOKEN_PATTERN = re.compile(
    rf"""
    (?P<comment>/\*[\s\S]*?\*/|--[^\n]*)
    |(?P<string>'(?:''|[^'])*')
    |(?P<placeholder>\$\{{[A-Za-z_][A-Za-z0-9_]*\}})
    |(?P<bind_variable>:[A-Za-z_][A-Za-z0-9_]*)
    |(?P<number>\b\d+(?:\.\d+)?\b)
    |(?P<keyword>\b(?:{"|".join(SQL_KEYWORDS)})\b)
    """,
    re.IGNORECASE | re.VERBOSE,
)

TAG_TO_THEME_KEY = {
    "sql_keyword": "keyword",
    "sql_string": "string",
    "sql_comment": "comment",
    "sql_number": "number",
    "sql_placeholder": "placeholder",
    "sql_bind_variable": "bind_variable",
}

MATCH_GROUP_TO_TAG = {
    "keyword": "sql_keyword",
    "string": "sql_string",
    "comment": "sql_comment",
    "number": "sql_number",
    "placeholder": "sql_placeholder",
    "bind_variable": "sql_bind_variable",
}


def collect_sql_highlight_tokens(sql_text: str) -> list[tuple[str, int, int]]:
    """回傳要套用到 tk.Text 的 tag 與字元區間。"""

    tokens: list[tuple[str, int, int]] = []
    for match in SQL_TOKEN_PATTERN.finditer(sql_text):
        token_group = match.lastgroup
        if token_group is None:
            continue
        tag_name = MATCH_GROUP_TO_TAG[token_group]
        start, end = match.span()
        if start == end:
            continue
        tokens.append((tag_name, start, end))
    return tokens


def apply_sql_syntax_highlighting(widget: tk.Text, theme: Mapping[str, str]) -> None:
    """在現有 tk.Text 上重新套用 SQL 高亮，不改動文字內容。"""

    _configure_sql_tags(widget, theme)
    for tag_name in SQL_HIGHLIGHT_TAG_NAMES:
        widget.tag_remove(tag_name, "1.0", "end")

    sql_text = widget.get("1.0", "end-1c")
    for tag_name, start, end in collect_sql_highlight_tokens(sql_text):
        widget.tag_add(tag_name, _offset_to_index(start), _offset_to_index(end))

    # 確保選取色不會被語法 tag 蓋掉。
    widget.tag_raise("sel")


def _configure_sql_tags(widget: tk.Text, theme: Mapping[str, str]) -> None:
    for tag_name in SQL_HIGHLIGHT_TAG_NAMES:
        widget.tag_configure(tag_name, foreground=theme[TAG_TO_THEME_KEY[tag_name]])


def _offset_to_index(offset: int) -> str:
    return f"1.0+{offset}c"
