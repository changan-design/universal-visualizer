"""表格结构化数据层：为 csv/xlsx/xls 提供「数据不进 LLM 输出」的注入式供给

设计动机（真实缺陷驱动）：
    早期实现把整张表的逐行文本塞进 prompt，让模型把数据**逐行转写**成页面里的 JS 数组。
    一张 55 行 × 13 列的中文招投标表就有 1 万多字符，仅数据部分就吃掉上万 token，
    模型输出一旦触达 max_tokens 上限，HTML 会从中间被截断 —— 表现就是「页面只有标题，
    下面一片空白」（CSS 的 .reveal{opacity:0} 等不到 JS 来点亮）。

    改为：后端把真实数据以 window.UV_DATA 注入页面，模型只写框架与图表逻辑，
    数据一律从 UV_DATA 读取。这样模型输出体积与数据量解耦，且数据 100% 保持原值，
    不会被模型改写、错行或编造。
"""
import json
import math
import re
from pathlib import Path

from .. import config
from . import tabular

TABLE_DIR = config.DATA_DIR / "table"
TABLE_DIR.mkdir(parents=True, exist_ok=True)

# 注入到页面的最大行数；超过则只注入前 N 行并由页面提示（>1000 行本就走大文件分页模式）
MAX_INLINE_ROWS = 2000
# 单列最多保留的分类取值数量（避免高基数字段把注入体积撑爆）
MAX_TOP_VALUES = 12
_SAMPLE_SIZE = 3
_DATE_RE = re.compile(r"^\d{4}[-/年]\d{1,2}[-/月]\d{1,2}|^\d{1,2}:\d{2}(:\d{2})?$")


def _coerce(v):
    """单元格值类型化：数字转 number、空转 None、其余转去除首尾空白的字符串"""
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return int(v) if float(v).is_integer() else round(float(v), 6)
    s = str(v).strip()
    if not s:
        return None
    # 纯数字（含千分位、负号、小数）→ number，便于前端直接参与计算与格式化
    t = s.replace(",", "").replace("，", "")
    if re.fullmatch(r"-?\d+(\.\d+)?", t):
        try:
            f = float(t)
            return int(f) if f.is_integer() else round(f, 6)
        except ValueError:
            return s
    return s


def _col_profile(name: str, values: list) -> dict:
    """单列画像：类型判定 + 分布/极值统计（供模型直接构造图表，无需自己遍历数据）"""
    nonnull = [v for v in values if v is not None]
    total = len(nonnull)
    prof = {"name": name, "filled": total}
    if not total:
        prof.update(type="empty", distinct=0, top=[], sample=[])
        return prof

    nums = [v for v in nonnull if isinstance(v, (int, float)) and not isinstance(v, bool)]
    num_ratio = len(nums) / total
    distinct_vals = {}
    for v in nonnull:
        k = str(v)
        distinct_vals[k] = distinct_vals.get(k, 0) + 1
    distinct = len(distinct_vals)

    if num_ratio >= 0.8:
        prof.update(type="number", distinct=distinct,
                    min=min(nums), max=max(nums),
                    avg=round(sum(nums) / len(nums), 4) if nums else None,
                    sum=round(sum(nums), 4) if len(nums) <= 20000 else None,
                    sample=nums[:_SAMPLE_SIZE])
        return prof

    date_ratio = sum(1 for v in nonnull if isinstance(v, str) and _DATE_RE.match(v)) / total
    if date_ratio >= 0.6:
        strs = sorted(str(v) for v in nonnull)
        prof.update(type="date", distinct=distinct, min=strs[0], max=strs[-1],
                    sample=[str(v) for v in nonnull[:_SAMPLE_SIZE]])
        return prof

    top = sorted(distinct_vals.items(), key=lambda kv: -kv[1])[:MAX_TOP_VALUES]
    is_category = distinct <= max(2, min(50, int(total * 0.6)))
    prof.update(
        type="category" if is_category else "text",
        distinct=distinct,
        top=[{"v": k, "n": n} for k, n in top],
        sample=[str(v) for v in nonnull[:_SAMPLE_SIZE]],
    )
    return prof


def prepare(path: str, file_id: str = "") -> dict:
    """读取整表并生成注入包：headers / rows / total / profiles"""
    p = Path(path)
    all_rows = tabular.read_rows(p)
    if not all_rows:
        raise ValueError("表格文件为空")

    raw_headers = list(all_rows[0])
    headers = []
    for i, h in enumerate(raw_headers):
        name = ("" if h is None else str(h)).strip() or f"列{i + 1}"
        # 表头去重，避免下游按键取值时互相覆盖
        base, n = name, 2
        while name in headers:
            name = f"{base}({n})"
            n += 1
        headers.append(name)

    body = []
    for r in all_rows[1:]:
        if not any(v not in (None, "") for v in r):
            continue                      # 跳过整行空白
        row = [_coerce(v) for v in r]
        # 对齐到表头长度：短了补 None，长了截断
        if len(row) < len(headers):
            row += [None] * (len(headers) - len(row))
        elif len(row) > len(headers):
            row = row[:len(headers)]
        body.append(row)

    total = len(body)
    if total == 0:
        raise ValueError("表格只有表头，没有数据行")

    shown = body[:MAX_INLINE_ROWS]
    cols = [[row[i] for row in body] for i in range(len(headers))]
    profiles = [_col_profile(headers[i], cols[i]) for i in range(len(headers))]

    payload = {
        "headers": headers, "rows": shown, "total": total,
        "truncated": total > MAX_INLINE_ROWS, "profiles": profiles,
    }
    if file_id:
        (TABLE_DIR / f"{file_id}.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload


def get(file_id: str) -> dict | None:
    f = TABLE_DIR / f"{file_id}.json"
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def brief(payload: dict, max_chars: int = 4200) -> str:
    """给模型看的「结构 + 画像」摘要（不含逐行数据，体积稳定在 KB 级）"""
    lines = [f"总行数：{payload['total']}（页面中由 window.UV_DATA.rows 提供，共 {len(payload['rows'])} 行已注入）",
             f"列数：{len(payload['headers'])}",
             "列结构："]
    for i, (h, prof) in enumerate(zip(payload["headers"], payload["profiles"])):
        t = prof.get("type")
        desc = f"  [{i}] {h} | 类型:{t} | 去重:{prof.get('distinct')}"
        if t == "number":
            desc += f" | min:{prof.get('min')} max:{prof.get('max')} avg:{prof.get('avg')} sum:{prof.get('sum')}"
        elif t == "category":
            tops = "、".join(f"{x['v']}({x['n']})" for x in prof.get("top", [])[:8])
            desc += f" | 分布Top: {tops}"
        elif t == "date":
            desc += f" | {prof.get('min')} ~ {prof.get('max')}"
        lines.append(desc)
    out = "\n".join(lines)
    return out[:max_chars]
