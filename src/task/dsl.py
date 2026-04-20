"""
任务 budget / reward DSL 解析器

格式（设计文档 §3.3）：
    类型:数值                            单一项, 例 "MONEY:300"
    类型:数值;类型:数值                   多项以 `;` 分隔
    ITEM:<物品名>:<数量>                  物品带数量

支持的类型: MONEY / FAME / MERIT / ITEM:<物品名>

返回结构：list[dict]，每条形如：
    {'kind': 'MONEY', 'amount': 300}
    {'kind': 'FAME', 'amount': 10}
    {'kind': 'MERIT', 'amount': 5}
    {'kind': 'ITEM', 'name': '生鱼', 'amount': 3}

非法/未知项打印告警并跳过；空字符串返回 []。
"""

from typing import List, Dict, Any


SCALAR_KINDS = ('MONEY', 'FAME', 'MERIT')


def parse_dsl(s: str) -> List[Dict[str, Any]]:
    if not s:
        return []
    out: List[Dict[str, Any]] = []
    for raw in s.split(';'):
        entry = raw.strip()
        if not entry:
            continue
        parts = entry.split(':')
        kind = parts[0].strip().upper()

        if kind in SCALAR_KINDS:
            if len(parts) != 2:
                print(f"[DSL] 格式错误（{kind} 需 1 个参数）: {entry!r}")
                continue
            try:
                out.append({'kind': kind, 'amount': int(parts[1].strip())})
            except ValueError:
                print(f"[DSL] 数值解析失败: {entry!r}")
        elif kind == 'ITEM':
            if len(parts) != 3:
                print(f"[DSL] 格式错误（ITEM 需 名称+数量）: {entry!r}")
                continue
            name = parts[1].strip()
            try:
                amount = int(parts[2].strip())
            except ValueError:
                print(f"[DSL] ITEM 数量解析失败: {entry!r}")
                continue
            out.append({'kind': 'ITEM', 'name': name, 'amount': amount})
        else:
            print(f"[DSL] 未知类型: {entry!r}")
    return out


def format_dsl(entries: List[Dict[str, Any]]) -> str:
    """把解析后的条目转回人类可读文本，用于结算 / 接取面板。
    例: [{'kind':'MONEY','amount':200}, {'kind':'FAME','amount':10}] -> "铜钱 200、声望 10"
    """
    if not entries:
        return ""
    label = {'MONEY': '铜钱', 'FAME': '声望', 'MERIT': '功勋'}
    pieces = []
    for e in entries:
        if e['kind'] in label:
            pieces.append(f"{label[e['kind']]} {e['amount']}")
        elif e['kind'] == 'ITEM':
            pieces.append(f"{e['name']} ×{e['amount']}")
    return '、'.join(pieces)
