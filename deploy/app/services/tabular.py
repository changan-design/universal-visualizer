"""表格读取统一层：csv / xlsx / xls 三种来源统一为「行列表」

- xlsx/xls 用 openpyxl（xlsx）与 xlrd（xls）分别读取，缺依赖时给出明确中文提示；
- 所有读取都设行数上限，避免超大文件把内存打满；
- 供 parser / convert / bigdata 复用，避免三处各写一份导致的格式支持不一致。
"""
import csv
from pathlib import Path


def _read_csv(path: Path, limit: int | None) -> list:
    rows = []
    with open(path, "r", encoding="utf-8-sig", errors="ignore", newline="") as f:
        for i, row in enumerate(csv.reader(f)):
            rows.append(row)
            if limit and i + 1 >= limit:
                break
    return rows


def _read_xlsx(path: Path, limit: int | None) -> list:
    from openpyxl import load_workbook
    wb = load_workbook(str(path), read_only=True, data_only=True)
    try:
        ws = wb.worksheets[0]
        rows = []
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            rows.append(["" if c is None else c for c in row])
            if limit and i + 1 >= limit:
                break
        return rows
    finally:
        wb.close()


def _read_xls(path: Path, limit: int | None) -> list:
    try:
        import xlrd
    except ImportError as e:  # pragma: no cover - 依赖缺失时的明确提示
        raise ValueError("读取旧版 .xls 需要 xlrd，请执行 pip install xlrd，或将文件另存为 .xlsx") from e
    book = xlrd.open_workbook(str(path))
    sheet = book.sheet_by_index(0)
    rows = []
    for r in range(sheet.nrows):
        if limit and r >= limit:
            break
        rows.append([sheet.cell_value(r, c) for c in range(sheet.ncols)])
    return rows


def read_rows(src, limit: int | None = 2000) -> list:
    """读取工作表首个 sheet（或 CSV 全表）为二维列表，limit 为行数上限（None 表示不限）"""
    p = Path(src)
    ext = p.suffix.lower()
    if ext == ".csv":
        return _read_csv(p, limit)
    if ext == ".xlsx":
        return _read_xlsx(p, limit)
    if ext == ".xls":
        return _read_xls(p, limit)
    raise ValueError(f"格式 {ext or '未知'} 不是表格文件")


def count_rows(path, ext: str) -> int:
    """统计数据行数（不含表头）；失败时返回 0，避免影响上传主流程"""
    try:
        if ext == ".csv":
            with open(path, "rb") as f:
                return max(0, sum(1 for _ in f) - 1)
        if ext == ".xlsx":
            from openpyxl import load_workbook
            wb = load_workbook(str(path), read_only=True)
            try:
                return max(0, (wb.worksheets[0].max_row or 1) - 1)
            finally:
                wb.close()
        if ext == ".xls":
            import xlrd
            return max(0, xlrd.open_workbook(str(path)).sheet_by_index(0).nrows - 1)
    except Exception:
        return 0
    return 0


def iter_rows(path, ext: str, limit: int | None = None):
    """流式迭代数据行（xlsx/csv 逐行读取；xls 一次性载入后迭代）"""
    p = Path(path)
    if ext == ".csv":
        with open(p, "r", encoding="utf-8-sig", errors="ignore", newline="") as f:
            for i, row in enumerate(csv.reader(f)):
                if limit and i >= limit:
                    break
                yield [("" if c is None else str(c).strip()) for c in row]
    elif ext == ".xlsx":
        from openpyxl import load_workbook
        wb = load_workbook(str(p), read_only=True, data_only=True)
        try:
            for i, row in enumerate(wb.worksheets[0].iter_rows(values_only=True)):
                if limit and i >= limit:
                    break
                yield [("" if c is None else str(c).strip()) for c in row]
        finally:
            wb.close()
    elif ext == ".xls":
        for i, row in enumerate(_read_xls(p, limit)):
            yield [("" if c is None else str(c).strip()) for c in row]
    else:
        raise ValueError(f"大文件模式仅支持 xlsx / xls / csv，当前 {ext}")
