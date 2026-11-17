"""多格式文件解析引擎：docx / pptx / pdf / txt / md / csv / xlsx / xls / json / html -> 纯文本"""
from pathlib import Path

from . import tabular

# 表格类文件送入模型的预览行数上限（超出部分交给大文件模式/分页明细）
PREVIEW_ROWS = 800


def parse_file(path: str) -> dict:
    """返回 {text, meta}，meta 含页数/段落数等统计"""
    p = Path(path)
    ext = p.suffix.lower()
    parsers = {
        ".docx": _parse_docx,
        ".pptx": _parse_pptx,
        ".pdf": _parse_pdf,
        ".txt": _parse_text, ".md": _parse_text, ".json": _parse_text,
        ".html": _parse_html, ".htm": _parse_html,
        ".csv": _parse_table, ".xlsx": _parse_table, ".xls": _parse_table,
    }
    if ext == ".doc":
        raise ValueError("暂不支持旧版 .doc：请在 Word/WPS 中另存为 .docx 或 PDF 后再上传")
    fn = parsers.get(ext)
    if not fn:
        raise ValueError(f"暂不支持解析的格式: {ext}")
    text, meta = fn(p)
    text = (text or "").strip()
    meta.update(file_name=p.name, ext=ext, size_kb=round(p.stat().st_size / 1024, 1),
                char_count=len(text))
    return {"text": text, "meta": meta}


def _parse_docx(p):
    from docx import Document
    doc = Document(str(p))
    parts = []
    for para in doc.paragraphs:
        t = para.text.strip()
        if t:
            style = para.style.name if para.style else ""
            low = style.lower()
            if low.startswith("heading") or "标题" in style:
                level = "".join(ch for ch in style if ch.isdigit()) or "2"
                parts.append("#" * min(4, int(level)) + " " + t)
            else:
                parts.append(t)
    for i, table in enumerate(doc.tables, 1):
        rows = [" | ".join(c.text.strip() for c in r.cells) for r in table.rows]
        if rows:
            parts.append(f"\n[表格{i}]\n" + "\n".join(rows))
    return "\n\n".join(parts), {"paragraphs": len(doc.paragraphs), "tables": len(doc.tables)}


def _parse_pptx(p):
    from pptx import Presentation
    prs = Presentation(str(p))
    parts = []
    for idx, slide in enumerate(prs.slides, 1):
        parts.append(f"\n===== 第 {idx} 页 =====")
        for shape in slide.shapes:
            if getattr(shape, "has_text_frame", False):
                for para in shape.text_frame.paragraphs:
                    t = "".join(run.text for run in para.runs).strip() or (para.text or "").strip()
                    if t:
                        parts.append(t)
            if getattr(shape, "has_table", False):
                for r in shape.table.rows:
                    parts.append(" | ".join(c.text.strip() for c in r.cells))
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
            note = slide.notes_slide.notes_text_frame.text.strip()
            if note:
                parts.append(f"[备注] {note}")
    return "\n".join(parts), {"slides": len(prs.slides)}


def _parse_pdf(p):
    import pdfplumber
    parts = []
    pages = 0
    with pdfplumber.open(str(p)) as pdf:
        pages = len(pdf.pages)
        for i, page in enumerate(pdf.pages, 1):
            parts.append(f"\n===== 第 {i} 页 =====")
            parts.append(page.extract_text() or "")
            for t in page.extract_tables():
                for r in t:
                    parts.append(" | ".join(str(c or "") for c in r))
    return "\n".join(parts), {"pages": pages}


def _parse_text(p):
    return p.read_text(encoding="utf-8", errors="ignore"), {}


def _parse_html(p):
    import re
    raw = p.read_text(encoding="utf-8", errors="ignore")
    raw = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", "", raw, flags=re.I)
    text = re.sub(r"<[^>]+>", "\n", raw)
    text = re.sub(r"\n{2,}", "\n", text)
    return text, {}


def _parse_table(p):
    """csv / xlsx / xls 统一走表格层，首行作为表头提示"""
    rows = tabular.read_rows(p, limit=PREVIEW_ROWS + 1)
    if not rows:
        raise ValueError("表格文件为空")
    lines = [" | ".join("" if c is None else str(c) for c in row) for row in rows[:PREVIEW_ROWS]]
    if len(rows) > PREVIEW_ROWS:
        lines.append(f"...(仅预览前 {PREVIEW_ROWS} 行，完整数据在生成时可分页查看)")
    meta = {"rows": max(0, len(rows) - 1), "cols": max(len(r) for r in rows),
            "headers": [("" if c is None else str(c)) for c in rows[0]]}
    return "\n".join(lines), meta
