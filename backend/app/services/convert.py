"""格式转换引擎 v3：布局感知转换（无系统字体依赖）

设计标准：
- 转换结果必须尽量保留源文档的结构信息 —— 段落分组、标题层级、表格结构、图片、加粗/斜体；
- 生成 PDF 一律走 PyMuPDF(Story / insert_htmlbox) 的 HTML 排版管线：
  内置 CJK 字体（Droid Sans Fallback），Windows / macOS / Linux / 容器内行为一致，
  彻底避免 fpdf2「未注册字体 → Undefined font / UnicodeEncodeError」导致的 400。

支持矩阵（见 TARGETS）：
- PDF→DOCX：PyMuPDF span 级字体信息（字号/粗斜体）+ find_tables 表格 + 图像区域渲染
- DOCX→PDF：python-docx 解析为语义 HTML，再排版为 PDF（标题层级 / 行内粗斜体 / 真实表格 / 图片）
- PPTX→PDF：逐页 HTML，自动等比缩放到单页（适合幻灯片的固定版面）
- PPTX→DOCX / MD→DOCX / 表格→PDF / 任意→TXT 等
"""
import base64
import csv
import hashlib
import html as _html
import re
import uuid
from pathlib import Path

from .. import config

# ---------------- 支持矩阵 ----------------

TARGETS = {
    ".docx": [".pdf", ".txt", ".xlsx", ".csv"],
    ".doc": [".pdf", ".txt"],
    ".pdf": [".docx", ".txt", ".xlsx", ".csv"],
    ".pptx": [".pdf", ".docx", ".txt", ".xlsx"],
    ".md": [".pdf", ".docx", ".txt"],
    ".markdown": [".pdf", ".docx", ".txt"],
    ".txt": [".pdf", ".docx"],
    ".json": [".pdf", ".docx", ".txt"],
    ".html": [".pdf", ".docx", ".txt"],
    ".htm": [".pdf", ".docx", ".txt"],
    ".csv": [".pdf", ".docx", ".xlsx", ".txt"],
    ".xlsx": [".pdf", ".docx", ".csv", ".txt"],
    ".xls": [".pdf", ".docx", ".csv", ".txt"],
}

# 目标格式的统一中文名，用于错误提示
EXT_LABEL = {".pdf": "PDF", ".docx": "Word", ".txt": "纯文本", ".xlsx": "Excel", ".csv": "CSV",
             ".md": "Markdown", ".pptx": "PPT"}


def supported_targets(ext: str) -> list:
    return TARGETS.get((ext or "").lower(), [])


# ---------------- 通用工具 ----------------

def _esc(s) -> str:
    return _html.escape(str(s or ""), quote=False)


def _tmp_png(out: Path) -> Path:
    """为图片渲染分配唯一临时文件，避免同一转换内多次覆盖"""
    return out.parent / f"_cvt_{uuid.uuid4().hex[:8]}.png"


def _img_data_uri(blob: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(blob).decode()


def _set_docx_base(doc):
    """Word 基础样式：中西文字体 + 页边距"""
    from docx.shared import Pt, Cm
    from docx.oxml.ns import qn
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    rpr = normal.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), "微软雅黑")
    for s in doc.sections:
        s.top_margin = s.bottom_margin = Cm(2)
        s.left_margin = s.right_margin = Cm(2)


def _docx_runs(p, runs):
    """把 [(text, bold, italic)] 写入段落，并保留行内样式"""
    for text, bold, italic in runs:
        if not text:
            continue
        r = p.add_run(text)
        r.bold = bold or None
        r.italic = italic or None


def _rect_hit(rect, items):
    """rect 是否与任一 (x0,y0,x1,y1) 有有效重叠"""
    for (x0, y0, x1, y1) in items:
        ox = min(rect[2], x1) - max(rect[0], x0)
        oy = min(rect[3], y1) - max(rect[1], y0)
        if ox > 4 and oy > 4:
            return True
    return False


# ---------------- HTML → PDF（统一排版管线） ----------------

_BASE_CSS = """
* { box-sizing: border-box; }
body { font-family: sans-serif; font-size: 11pt; line-height: 1.7; color: #1f2733; margin: 0; }
h1 { font-size: 20pt; margin: 14pt 0 8pt; color: #16344C; }
h2 { font-size: 15pt; margin: 12pt 0 6pt; color: #16344C; }
h3 { font-size: 13pt; margin: 10pt 0 5pt; color: #16344C; }
h4 { font-size: 11.5pt; margin: 8pt 0 4pt; color: #16344C; }
/* Word 的章节标题：加一条极淡分隔线，让分区在视觉上立起来（仅 .sec，不影响 Markdown/TXT 输出） */
h2.sec, h3.sec, h4.sec { border-bottom: 0.6pt solid #DCE3EE; padding-bottom: 3pt; margin-bottom: 7pt; }
h1:first-child, h2:first-child, h3:first-child { margin-top: 0; }
p { margin: 0 0 6pt; text-align: justify; }
ul, ol { margin: 2pt 0 6pt 16pt; padding: 0; }
li { margin: 0 0 2pt; text-align: justify; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 10pt; font-size: 9.5pt; }
th, td { border: 0.6pt solid #b9c2d0; padding: 3pt 5pt; vertical-align: top; text-align: left; }
th { background: #eef2f9; font-weight: bold; }
/* 版式表格（无边框）：简历头部等只作分栏排版的表格不应出现表格线 */
table.plain { margin: 0 0 6pt; font-size: 10.5pt; }
table.plain th, table.plain td { border: none; padding: 0 8pt 0 0; }
td p, th p { margin: 0 0 2pt; }
td p:last-child, th p:last-child { margin-bottom: 0; }
img { max-width: 100%; }
blockquote { margin: 6pt 0 6pt 12pt; padding-left: 8pt; border-left: 2pt solid #c9d3e3; color: #4a5568; }
pre { font-family: monospace; font-size: 9pt; background: #f5f7fb; padding: 6pt; }
.center { text-align: center; }
.right { text-align: right; }
"""


def _finalize_pdf(path: Path):
    """字体子集化 + 压缩：避免整份 CJK 回退字体被完整嵌入导致体积膨胀（3.5MB → ~10KB）"""
    import pymupdf
    tmp = path.with_name(path.stem + "_opt" + path.suffix)
    try:
        doc = pymupdf.open(str(path))
        try:
            doc.subset_fonts()
        except Exception:
            pass
        doc.save(str(tmp), garbage=4, deflate=True)
        doc.close()
        tmp.replace(path)
    except Exception:
        tmp.unlink(missing_ok=True)


def _story_pdf(html_body: str, out: Path, landscape: bool = False, margin: float = 42):
    """流式排版：适合连续文档（Word / Markdown / 纯文本 / 表格）"""
    import pymupdf

    html = f"<!DOCTYPE html><html><head><style>{_BASE_CSS}</style></head><body>{html_body}</body></html>"
    paper = "a4-l" if landscape else "a4"
    mediabox = pymupdf.paper_rect(paper)
    where = mediabox + (margin, margin, -margin, -margin)
    raw = out.with_name(out.stem + "_raw" + out.suffix)
    story = pymupdf.Story(html=html)
    writer = pymupdf.DocumentWriter(str(raw))
    more, guard = 1, 0
    while more:
        dev = writer.begin_page(mediabox)
        more, _ = story.place(where)
        story.draw(dev)
        writer.end_page()
        guard += 1
        if guard > 800:                      # 防御：异常 HTML 导致的死循环
            break
    writer.close()
    del writer, story                          # 释放文件句柄（Windows 下否则无法二次打开）
    _finalize_pdf(raw)
    raw.replace(out)


def _pages_pdf(page_bodies: list, out: Path, landscape: bool = False, footer: bool = False):
    """整页排版：适合幻灯片这类固定页面的内容（自动等比缩放保证不溢出）"""
    import pymupdf

    doc = pymupdf.open()
    paper = "a4-l" if landscape else "a4"
    total = len(page_bodies)
    for idx, body in enumerate(page_bodies, 1):
        page = doc.new_page(width=pymupdf.paper_rect(paper).width,
                            height=pymupdf.paper_rect(paper).height)
        rect = pymupdf.Rect(42, 42, page.rect.width - 42, page.rect.height - 42)
        html = f"<!DOCTYPE html><html><head><style>{_BASE_CSS}</style></head><body>{body}</body></html>"
        try:
            # scale_low 允许收缩到 25%，保证超长幻灯片内容仍能完整落在单页内
            page.insert_htmlbox(rect, html, scale_low=0.25)
        except Exception:
            # 极端情况下退化为纯文本插入，绝不因排版异常而整体失败
            plain = re.sub(r"<[^>]+>", " ", body)
            page.insert_textbox(rect, plain, fontname="china-s", fontsize=10)
        if footer and total > 1:
            # 幻灯片页脚：页码 + 细分隔线，更接近正式演示文稿
            h = page.rect.height
            page.draw_line(pymupdf.Point(42, h - 30), pymupdf.Point(page.rect.width - 42, h - 30),
                           color=(0.76, 0.81, 0.89), width=0.7)
            page.insert_textbox(pymupdf.Rect(42, h - 26, page.rect.width - 42, h - 12),
                                f"{idx} / {total}", fontname="china-s", fontsize=8.5,
                                align=pymupdf.TEXT_ALIGN_RIGHT, color=(0.42, 0.47, 0.55))
    doc.save(str(out), garbage=4, deflate=True)
    doc.close()
    del doc
    _finalize_pdf(out)


# ---------------- DOCX → PDF ----------------

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
EMU_PT = 12700.0          # 1pt = 12700 EMU
USABLE_PT = 511.0         # A4 宽 595pt 减去左右各 42pt 页边距


def _docx_run_html(run, doc, in_cell: bool = False, max_w: float = 480.0) -> str:
    """单个 run → HTML（保留字号/颜色/粗斜体/下划线 + 内嵌图片）

    图片按 Word 里记录的显示尺寸（wp:extent，EMU 换算成 pt）还原，
    超出所在栏宽时等比收敛——只写 max-width 百分比对图片不生效，会导致图片被放大到整栏。
    """
    parts = []
    ext = next(run._element.iter(_WP + "extent"), None)
    w_pt = h_pt = None
    if ext is not None:
        try:
            w_pt = int(ext.get("cx")) / EMU_PT
            h_pt = int(ext.get("cy")) / EMU_PT
        except Exception:
            w_pt = h_pt = None
    for blip in run._element.findall(".//a:blip", {"a": _A[1:-1], "r": _R[1:-1]}):
        rid = blip.get(_R + "embed")
        if not rid:
            continue
        try:
            blob = doc.part.related_parts[rid].blob
        except Exception:
            continue
        if w_pt and h_pt:
            w, h = w_pt, h_pt
            if max_w and w > max_w:
                h *= max_w / w
                w = max_w
            style = f"width:{w:.1f}pt;height:{h:.1f}pt"
        else:
            style = f"max-width:{max_w or 480:.0f}pt"
        img = f'<img src="{_img_data_uri(blob)}" style="{style}"/>'
        parts.append(img if in_cell else f"<p>{img}</p>")
    text = run.text or ""
    if text.strip():
        t = _esc(text).replace("\n", "<br/>").replace("\t", "&nbsp;&nbsp;&nbsp;&nbsp;")
        # 字号与颜色是版式层级的主要载体（姓名 22pt、联系方式 10pt 灰），丢失后整页会退化成同一字号
        styles = []
        try:
            if run.font.size is not None:
                styles.append(f"font-size:{run.font.size.pt:.1f}pt")
        except Exception:
            pass
        try:
            rgb = run.font.color.rgb if run.font.color is not None else None
            if rgb is not None:
                styles.append(f"color:#{rgb}")
        except Exception:
            pass
        if styles:
            t = f'<span style="{";".join(styles)}">{t}</span>'
        if run.bold:
            t = f"<b>{t}</b>"
        if run.italic:
            t = f"<i>{t}</i>"
        if run.underline:
            t = f"<u>{t}</u>"
        parts.append(t)
    return "".join(parts)


def _table_has_border(tbl_el, table) -> bool:
    """判断源表格是否真的带边框：显式 tblBorders 优先，其次看表格样式是否自带网格线。

    Word 里大量表格只用于分栏排版（简历头部、图字混排），本身没有边框；
    若无条件描边，导出后会出现一个突兀的方框把这些内容圈起来。
    """
    tbl_pr = tbl_el.find(_W + "tblPr")
    if tbl_pr is not None:
        borders = tbl_pr.find(_W + "tblBorders")
        if borders is not None:
            for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
                e = borders.find(_W + edge)
                if e is None:
                    continue
                val = e.get(_W + "val")
                if val and val not in ("none", "nil", "0"):
                    return True
            return False  # 明确声明了边框但全为 none
    try:
        name = (table.style.name or "") if table is not None and table.style is not None else ""
    except Exception:
        name = ""
    low = name.lower()
    return "grid" in low or "网格" in name


def _col_percents(table) -> list:
    """把 Word 的列宽换算成百分比，供 HTML 表格还原比例（头像列不会被正文挤变形）"""
    try:
        raw = [c.width.cm if c.width is not None else None for c in table.columns]
    except Exception:
        return []
    if not raw or any(w is None for w in raw):
        return []
    total = float(sum(raw))
    if total <= 0:
        return []
    return [w * 100.0 / total for w in raw]


def _docx_cell_html(cell, doc, max_w: float = 400.0) -> str:
    """单元格内容：逐段保留 run 级格式与图片，而不是压平成纯文本"""
    out = []
    for para in cell.paragraphs:
        inner = "".join(_docx_run_html(r, doc, in_cell=True, max_w=max_w) for r in para.runs)
        if not inner.strip():
            continue
        cls = ""
        try:
            if para.alignment is not None:
                a = int(para.alignment)
                if a == 1:
                    cls = ' class="center"'
                elif a == 2:
                    cls = ' class="right"'
        except Exception:
            pass
        out.append(f"<p{cls}>{inner}</p>")
    return "".join(out)


def _cell_image_pt(cell, doc):
    """单元格内首张图片的显示宽度（pt）；无图片返回 None"""
    try:
        for p in cell.paragraphs:
            for r in p.runs:
                ext = next(r._element.iter(_WP + "extent"), None)
                if ext is not None:
                    return int(ext.get("cx")) / EMU_PT
    except Exception:
        return None
    return None


def _docx_table_html(table, tbl_el, doc) -> str:
    bordered = _table_has_border(tbl_el, table)
    try:
        ncols = len(table.columns)
    except Exception:
        ncols = 0
    widths = [] if bordered else [None] * ncols
    if bordered:
        widths = _col_percents(table)
    else:
        # 版式表格：纯图片列按图片实际宽度定宽，其余列留空自动占满，
        # 避免固定百分比把文字列挤窄而出现「数据采/集」这种断字换行
        for idx in range(ncols):
            texts, imgw = [], None
            for r in table.rows:
                if idx >= len(r.cells):
                    continue
                c = r.cells[idx]
                texts.append((c.text or "").strip())
                if imgw is None:
                    imgw = _cell_image_pt(c, doc)
            if imgw and not any(texts):
                widths[idx] = min(imgw + 6.0, USABLE_PT * 0.45)

    rows = []
    for r in table.rows:
        cells = []
        for idx, c in enumerate(r.cells):
            w = widths[idx] if idx < len(widths) else None
            style = f' style="width:{w:.1f}pt"' if w else ""
            # 单元格内图片按列宽上限收敛，避免溢出到相邻栏
            max_w = (w - 12) if w else 400.0
            inner = _docx_cell_html(c, doc, max_w=max(60.0, max_w))
            cells.append(f"<td{style}>{inner}</td>")
        if any(c.replace("<td", "").strip() for c in cells):
            rows.append("<tr>" + "".join(cells) + "</tr>")
    if not rows:
        return ""
    cls = "" if bordered else ' class="plain"'
    return f"<table{cls}>" + "".join(rows) + "</table>"


def _docx_infer_level(para, base: float):
    """无 Heading 样式时按「全段加粗 + 字号明显大于正文 + 短行」推断章节标题层级。

    很多简历/公文模板只用加粗段落充当小标题，若不推断，导出后标题与正文同字号同颜色，
    整篇会失去层级。
    """
    text = (para.text or "").strip()
    if not text or len(text) > 30:
        return None
    if any(k in text for k in ("：", ":", "｜", "|")):
        return None  # 「求职意向：xxx」这类标签行不是章节标题
    runs = [r for r in para.runs if (r.text or "").strip()]
    if not runs or not all(r.bold for r in runs):
        return None
    sizes = []
    for r in runs:
        try:
            if r.font.size is not None:
                sizes.append(r.font.size.pt)
        except Exception:
            pass
    size = max(sizes) if sizes else base
    if size >= base + 4.5:
        return 2
    if size >= base + 2.5:
        return 3
    return None


def _docx_body_html(src: Path) -> str:
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    doc = Document(str(src))
    body = doc.element.body
    out = []
    # 连续同类列表段落合并为一个 <ul>/<ol>，否则每段独立成表会让有序列表逐条从 1 重新编号
    pending = None  # ["ul"|"ol", [items]]
    try:
        base_size = doc.styles["Normal"].font.size.pt
    except Exception:
        base_size = 10.5

    def flush():
        nonlocal pending
        if pending and pending[1]:
            out.append(f"<{pending[0]}>" + "".join(f"<li>{x}</li>" for x in pending[1]) + f"</{pending[0]}>")
        pending = None

    for child in body.iterchildren():
        tag = child.tag.split("}")[-1]
        if tag == "p":
            para = Paragraph(child, doc)
            style = (para.style.name or "").strip()
            low = style.lower()
            inner = "".join(_docx_run_html(r, doc) for r in para.runs)
            text = para.text.strip()
            if not inner.strip():
                continue
            level = None
            if low in ("title", "标题"):
                level = 1
            else:
                m = re.search(r"heading\s*(\d)|标题\s*(\d)", low)
                if m:
                    # Word 的 Title 为文档大标题，Heading N 顺延一级，保证层级可见
                    level = int(m.group(1) or m.group(2)) + 1
                elif "list" not in low and "列表" not in style:
                    level = _docx_infer_level(para, base_size)
            align = ' class="center"' if para.alignment is not None and int(para.alignment) == 1 else ""
            if level:
                flush()
                lv = min(4, max(1, level))
                cls = ' class="center sec"' if align else ' class="sec"'
                out.append(f"<h{lv}{cls}>{inner}</h{lv}>")
            elif "list" in low or "列表" in style:
                bullet = "number" not in low and "编号" not in style
                cls = "ul" if bullet else "ol"
                item = inner
                if cls == "ol":
                    # 正文自带的手动序号（"1. "/"1、"/"(1)"）与自动编号重复，剥离之
                    item = re.sub(r"^((?:<[a-z]+>)*)\s*(?:\d+[.)、]|[(（]\d+[)）])\s*", r"\1", item)
                if pending and pending[0] == cls:
                    pending[1].append(item)
                else:
                    flush()
                    pending = [cls, [item]]
            elif low.startswith("quote") or "引用" in style:
                flush()
                out.append(f"<blockquote>{inner}</blockquote>")
            else:
                flush()
                out.append(f"<p{align}>{inner}</p>" if text or inner else "")
        elif tag == "tbl":
            flush()
            t = Table(child, doc)
            html = _docx_table_html(t, child, doc)
            if html:
                out.append(html)
    flush()
    return "".join(out)


def _docx_to_pdf(src: Path, out: Path):
    html = _docx_body_html(src)
    if not html.strip():
        raise ValueError("Word 文档没有可提取的文字或图片内容")
    _story_pdf(html, out)


# ---------------- PPTX → PDF ----------------

def _slide_html(slide, idx: int) -> str:
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    parts = []
    title_shape = slide.shapes.title
    title = title_shape.text.strip() if title_shape is not None else ""
    parts.append(f"<h2>{_esc(f'第 {idx} 页　{title}' if title else f'第 {idx} 页')}</h2>")
    for shape in slide.shapes:
        if title_shape is not None and shape == title_shape:
            continue
        if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
            try:
                parts.append(f'<p><img src="{_img_data_uri(shape.image.blob)}" style="max-width:92%"/></p>')
            except Exception:
                continue
        elif getattr(shape, "has_table", False):
            rows = []
            for r in shape.table.rows:
                rows.append("<tr>" + "".join(f"<td>{_esc(c.text)}</td>" for c in r.cells) + "</tr>")
            if rows:
                parts.append("<table>" + "".join(rows) + "</table>")
        elif getattr(shape, "has_text_frame", False):
            for para in shape.text_frame.paragraphs:
                text = "".join(r.text for r in para.runs).strip() or (para.text or "").strip()
                if not text:
                    continue
                parts.append(f"<p>{'&nbsp;&nbsp;' * (para.level or 0)}• {_esc(text)}</p>"
                             if para.level else f"<p>{_esc(text)}</p>")
    return "".join(parts)


def _pptx_to_pdf(src: Path, out: Path):
    from pptx import Presentation

    prs = Presentation(str(src))
    pages = [_slide_html(s, i) for i, s in enumerate(prs.slides, 1)]
    if not pages:
        raise ValueError("PPT 文件中没有幻灯片")
    _pages_pdf(pages, out, footer=True)


# ---------------- PDF → DOCX ----------------

def _pdf_to_docx(src: Path, out: Path):
    import pymupdf
    from docx import Document
    from docx.shared import Pt, Cm, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()
    _set_docx_base(doc)
    ACCENT = RGBColor(0x16, 0x34, 0x4C)
    pdf = pymupdf.open(str(src))

    for page_no, page in enumerate(pdf):
        if page_no:
            doc.add_page_break()                  # 保留原 PDF 分页
        pw = page.rect.width
        tables = []
        try:
            tables = page.find_tables().tables
        except Exception:
            tables = []
        tab_rects = [t.bbox for t in tables]
        img_rects = []
        try:
            for info in page.get_image_info():
                b = info["bbox"]
                if b[2] - b[0] < 24 or b[3] - b[1] < 24:      # 过滤装饰性小图
                    continue
                if _rect_hit(b, tab_rects):                    # 表格内贴图跳过
                    continue
                img_rects.append(b)
        except Exception:
            img_rects = []

        d = page.get_text("dict")
        sizes = []
        for blk in d.get("blocks", []):
            if blk.get("type") != 0:
                continue
            for line in blk.get("lines", []):
                for span in line.get("spans", []):
                    if span["text"].strip():
                        sizes.append(round(span["size"], 1))
        body_size = max(set(sizes), key=sizes.count) if sizes else 11.0

        items = []
        for t in tables:
            items.append((t.bbox[1], "table", t))
        for b in img_rects:
            items.append((b[1], "image", b))
        for blk in d.get("blocks", []):
            if blk.get("type") != 0:
                continue
            if _rect_hit(blk["bbox"], tab_rects + list(img_rects)):
                continue
            if not any(sp["text"].strip() for ln in blk.get("lines", []) for sp in ln.get("spans", [])):
                continue
            items.append((blk["bbox"][1], "text", blk))
        items.sort(key=lambda x: x[0])

        for _, kind, payload in items:
            if kind == "image":
                x0, y0, x1, y1 = payload
                tmp = _tmp_png(out)
                try:
                    pix = page.get_pixmap(clip=pymupdf.Rect(x0, y0, x1, y1), dpi=150)
                    pix.save(str(tmp))
                    doc.add_picture(str(tmp), width=Cm(min(15.5, max(3.0, (x1 - x0) / 72 * 2.54))))
                    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
                except Exception:
                    pass
                finally:
                    tmp.unlink(missing_ok=True)
            elif kind == "table":
                rows = payload.extract()
                rows = [["" if c is None else str(c) for c in r] for r in rows if any(c for c in r)]
                if not rows:
                    continue
                cols = max(len(r) for r in rows)
                t = doc.add_table(rows=len(rows), cols=cols)
                try:
                    t.style = "Table Grid"
                except Exception:
                    pass
                for i, r in enumerate(rows):
                    for j in range(cols):
                        cell = t.cell(i, j)
                        cell.text = r[j] if j < len(r) else ""
                        for pr in cell.paragraphs:
                            for run in pr.runs:
                                run.font.size = Pt(9.5)
                                if i == 0:
                                    run.bold = True
                doc.add_paragraph()
            else:
                blk = payload
                runs, max_size = [], 0
                for line in blk.get("lines", []):
                    for span in line.get("spans", []):
                        text = span["text"]
                        if not text.strip():
                            if runs and not runs[-1][0].endswith(" ") and text:
                                runs.append((" ", False, False))
                            continue
                        max_size = max(max_size, span["size"])
                        bold = bool(span["flags"] & 16) or "Bold" in span["font"] or "bold" in span["font"]
                        italic = bool(span["flags"] & 2) or "Italic" in span["font"] or "Oblique" in span["font"]
                        runs.append((text, bold, italic))
                if not runs:
                    continue
                ratio = max_size / body_size if body_size else 1
                center = (blk["bbox"][0] + blk["bbox"][2]) / 2
                is_centered = abs(center - pw / 2) < pw * 0.06 and (blk["bbox"][2] - blk["bbox"][0]) < pw * 0.7
                if ratio >= 1.6:
                    p = doc.add_heading("", level=1)
                elif ratio >= 1.3:
                    p = doc.add_heading("", level=2)
                elif ratio >= 1.12:
                    p = doc.add_heading("", level=3)
                else:
                    p = doc.add_paragraph()
                _docx_runs(p, runs)
                if is_centered and ratio < 1.12:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in p.runs:
                    if ratio < 1.12:
                        run.font.size = Pt(min(16, max(9, round(max_size, 1))))
                    else:
                        run.font.color.rgb = ACCENT
    pdf.close()
    doc.save(str(out))


# ---------------- PPTX → DOCX ----------------

def _pptx_to_docx(src: Path, out: Path):
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    from docx import Document
    from docx.shared import Cm
    import io

    doc = Document()
    _set_docx_base(doc)
    prs = Presentation(str(src))
    for idx, slide in enumerate(prs.slides, 1):
        title = slide.shapes.title.text.strip() if slide.shapes.title is not None else ""
        doc.add_heading(f"第{idx}页  {title}" if title else f"第{idx}页", level=1)
        for shape in slide.shapes:
            if slide.shapes.title is not None and shape == slide.shapes.title:
                continue
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                try:
                    doc.add_picture(io.BytesIO(shape.image.blob), width=Cm(14))
                except Exception:
                    pass
            elif getattr(shape, "has_table", False):
                tbl = shape.table
                t = doc.add_table(rows=len(tbl.rows), cols=len(tbl.columns))
                try:
                    t.style = "Table Grid"
                except Exception:
                    pass
                for i, row in enumerate(tbl.rows):
                    for j, cell in enumerate(row.cells):
                        t.cell(i, j).text = cell.text
                doc.add_paragraph()
            elif getattr(shape, "has_text_frame", False):
                for para in shape.text_frame.paragraphs:
                    text = "".join(r.text for r in para.runs).strip() or para.text.strip()
                    if not text:
                        continue
                    doc.add_paragraph(text, style="List Bullet" if para.level else None)
        doc.add_paragraph()
    doc.save(str(out))


# ---------------- MD → DOCX ----------------

def _md_inline(text: str) -> str:
    """Markdown 行内标记 → docx run 列表"""
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", text)
    return text


def _md_to_docx(src: Path, out: Path):
    from docx import Document
    doc = Document()
    _set_docx_base(doc)
    lines = src.read_text(encoding="utf-8", errors="ignore").splitlines()
    i, in_code = 0, False
    code_buf = []
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_code and code_buf:
                from docx.shared import Pt
                p = doc.add_paragraph()
                r = p.add_run("\n".join(code_buf))
                r.font.name = "Consolas"
                r.font.size = Pt(9.5)
                code_buf = []
            in_code = not in_code
            i += 1
            continue
        if in_code:
            code_buf.append(line)
            i += 1
            continue
        if not stripped:
            i += 1
            continue
        m = len(stripped) - len(stripped.lstrip("#"))
        if 1 <= m <= 4 and stripped[m:m + 1] == " ":
            doc.add_heading(stripped[m + 1:].strip(), level=m)
        elif stripped.startswith("> "):
            p = doc.add_paragraph(_md_inline(stripped[2:]))
            if p.runs:
                p.runs[0].italic = True
        elif stripped[:2] in ("- ", "* ", "+ "):
            doc.add_paragraph(_md_inline(stripped[2:]), style="List Bullet")
        elif re.match(r"^\d+[.)、]\s+", stripped):
            doc.add_paragraph(_md_inline(re.sub(r"^\d+[.)、]\s+", "", stripped)), style="List Number")
        elif stripped.startswith("|") and i + 1 < len(lines) and re.fullmatch(
                r"\|?[\s:|-]+\|?", lines[i + 1].strip() or "-"):
            header = [c.strip() for c in stripped.strip("|").split("|")]
            rows = [header]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            cols = max(len(r) for r in rows)
            t = doc.add_table(rows=len(rows), cols=cols)
            try:
                t.style = "Table Grid"
            except Exception:
                pass
            for r_i, r in enumerate(rows):
                for c_i in range(cols):
                    cell = t.cell(r_i, c_i)
                    cell.text = r[c_i] if c_i < len(r) else ""
                    if r_i == 0:
                        for run in cell.paragraphs[0].runs:
                            run.bold = True
            continue
        else:
            doc.add_paragraph(_md_inline(stripped))
        i += 1
    doc.save(str(out))


# ---------------- MD / 纯文本 → PDF ----------------

def _md_to_html(text: str) -> str:
    """轻量 Markdown → HTML（标题/列表/引用/表格/代码块/行内强调），足够 PDF 排版使用"""
    lines = text.splitlines()
    out, i, in_code, code = [], 0, False, []
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if s.startswith("```"):
            if in_code:
                out.append("<pre>" + _esc("\n".join(code)) + "</pre>")
                code = []
            in_code = not in_code
            i += 1
            continue
        if in_code:
            code.append(line)
            i += 1
            continue
        if not s:
            i += 1
            continue
        m = len(s) - len(s.lstrip("#"))
        if 1 <= m <= 4 and s[m:m + 1] == " ":
            lv = min(4, m)
            out.append(f"<h{lv}>{_md_inline(_esc(s[m + 1:]))}</h{lv}>")
        elif s.startswith("> "):
            out.append(f"<blockquote>{_esc(s[2:])}</blockquote>")
        elif s[:2] in ("- ", "* ", "+ ") or re.match(r"^\d+[.)、]\s+", s):
            # 连续列表行合并为一个 <ul>/<ol>，否则每行单独成表会导致有序列表序号全部重置为 1
            ordered = bool(re.match(r"^\d+[.)、]\s+", s))
            items = []
            while i < len(lines):
                cur = lines[i].strip()
                if ordered:
                    m = re.match(r"^\d+[.)、]\s+(.*)$", cur)
                    if not m:
                        break
                    items.append(_esc(m.group(1)))
                else:
                    if cur[:2] not in ("- ", "* ", "+ "):
                        break
                    items.append(_esc(cur[2:]))
                i += 1
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{x}</li>" for x in items) + f"</{tag}>")
            continue
        elif s.startswith("|") and i + 1 < len(lines) and re.fullmatch(r"\|?[\s:|-]+\|?", lines[i + 1].strip() or "-"):
            header = [c.strip() for c in s.strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            buf = ["<table><tr>" + "".join(f"<th>{_esc(h)}</th>" for h in header) + "</tr>"]
            for r in rows:
                buf.append("<tr>" + "".join(f"<td>{_esc(c)}</td>" for c in r) + "</tr>")
            buf.append("</table>")
            out.append("".join(buf))
            continue
        else:
            out.append(f"<p>{_md_inline(_esc(s))}</p>")
        i += 1
    if in_code and code:
        out.append("<pre>" + _esc("\n".join(code)) + "</pre>")
    return "".join(out)


def _text_to_pdf(text: str, out: Path, markdown: bool = False):
    body = _md_to_html(text) if markdown else "".join(
        f"<p>{_esc(ln)}</p>" for ln in text.splitlines())
    if not body.strip():
        raise ValueError("文档没有可导出的文字内容")
    _story_pdf(body, out)


# ---------------- 表格 → PDF ----------------

def _table_to_pdf(rows, out: Path):
    if not rows:
        raise ValueError("未读取到表格数据")
    cols = max(len(r) for r in rows)
    head = "</th><th>".join(_esc(c) for c in rows[0][:cols])
    body = []
    for r in rows[1:]:
        body.append("<tr>" + "".join(f"<td>{_esc(r[j]) if j < len(r) else ''}</td>" for j in range(cols)) + "</tr>")
    html = (f"<table><tr><th>{head}</th></tr>{''.join(body)}</table>")
    _story_pdf(html, out, landscape=cols > 5, margin=36)


# ---------------- 表格读取（跨格式） ----------------

def _style_worksheet(ws, rows) -> None:
    """Excel 输出美化：表头深蓝底白字、冻结首行、列宽自适应、细边框、数字列右对齐"""
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    header_fill = PatternFill("solid", fgColor="16344C")
    header_font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
    body_font = Font(name="微软雅黑", size=10.5)
    thin = Side(style="thin", color="C9D3E3")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    ncol = max((len(r) for r in rows), default=0)

    for j in range(ncol):
        c = ws.cell(row=1, column=j + 1)
        c.fill = header_fill
        c.font = header_font
        c.border = border
        c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 24
    ws.freeze_panes = "A2"

    # 数字列右对齐 + 列宽自适应（采样前 200 行，避免大表逐格测量过慢）
    widths = [10.0] * ncol
    for i, r in enumerate(rows[:200]):
        for j in range(min(len(r), ncol)):
            v = r[j]
            text = "" if v is None else str(v)
            widths[j] = max(widths[j], min(60.0, len(text) * 1.9 + 2))
            cell = ws.cell(row=i + 1, column=j + 1)
            if i:  # 跳过表头行（表头样式已设）
                cell.font = body_font
                cell.border = border
                cv = cell.value  # 用写入后的实际值判断：字符串数字已在 append 时转为数值
                if isinstance(cv, (int, float)) and not isinstance(cv, bool):
                    cell.alignment = Alignment(horizontal="right")
                    cell.number_format = "#,##0.00" if isinstance(cv, float) else "#,##0"
                else:
                    cell.alignment = Alignment(vertical="center", wrap_text=len(text) > 30)
    for j in range(ncol):
        ws.column_dimensions[get_column_letter(j + 1)].width = widths[j]
    ws.auto_filter.ref = f"A1:{get_column_letter(ncol)}{min(len(rows), 2000)}"


def _table_rows_any(src, limit: int = 2000) -> list:
    """任意支持格式 → 二维表：表格类走 tabular，文档类抽取其中的表格"""
    from . import tabular
    p = Path(src)
    ext = p.suffix.lower()
    if ext in (".csv", ".xlsx", ".xls"):
        return tabular.read_rows(src, limit=limit)

    rows: list = []
    if ext == ".docx":
        from docx import Document
        doc = Document(str(p))
        for t in doc.tables:
            for r in t.rows:
                rows.append([c.text.strip() for c in r.cells])
            rows.append([])
        # 无表格的文档（如纯文字简历）降级为「每段一行」，保证转 Excel/CSV 不至于直接报错
        if not any(rows):
            rows = [[ln.strip()] for ln in (para.text.strip() for para in doc.paragraphs) if ln]
    elif ext == ".pptx":
        from pptx import Presentation
        prs = Presentation(str(p))
        for slide in prs.slides:
            for shape in slide.shapes:
                if getattr(shape, "has_table", False):
                    for r in shape.table.rows:
                        rows.append([c.text.strip() for c in r.cells])
                    rows.append([])
        if not any(rows):
            for slide in prs.slides:
                for shape in slide.shapes:
                    if getattr(shape, "has_text_frame", False) and shape.text_frame.text.strip():
                        rows.append([shape.text_frame.text.strip()])
    elif ext == ".pdf":
        import pymupdf
        pdf = pymupdf.open(str(p))
        try:
            for page in pdf:
                try:
                    for t in page.find_tables().tables:
                        for r in t.extract():
                            rows.append(["" if c is None else str(c).strip() for c in r])
                        rows.append([])
                except Exception:
                    continue
        finally:
            pdf.close()
    # 去掉尾部空行与连续空行
    while rows and not rows[-1]:
        rows.pop()
    rows = [r for i, r in enumerate(rows) if r or (i and rows[i - 1])]
    return rows[:limit]


def _read_table(src) -> list:
    return _table_rows_any(src)


# ---------------- 主入口 ----------------

async def convert(src: str, target_ext: str) -> dict:
    p = Path(src)
    ext = p.suffix.lower()
    target = ("." + (target_ext or "").strip().lstrip(".").lower()) if target_ext else ""

    if ext == ".doc":
        raise ValueError("暂不支持旧版 .doc：请在 Word/WPS 中另存为 .docx 或 PDF 后再转换")
    if ext == ".xls":
        # .xls 由 tabular 层用 xlrd 读取，若环境缺依赖会给出明确提示
        pass
    allowed = supported_targets(ext)
    if not allowed:
        raise ValueError(f"暂不支持从 {ext or '未知格式'} 转换")
    if target not in allowed:
        readable = "、".join(EXT_LABEL.get(t, t) for t in allowed)
        raise ValueError(f"{EXT_LABEL.get(ext, ext)} 文件仅支持转换为：{readable}")

    # ---- 转换结果缓存：同一文件（名称+大小+mtime）转同一目标直接复用，重复点击秒回 ----
    try:
        st = p.stat()
        key_src = f"{p.name}|{st.st_size}|{int(st.st_mtime)}|{target}"
    except OSError:
        key_src = f"{p.name}|?|{target}"
    cache_key = hashlib.md5(key_src.encode("utf-8")).hexdigest()[:12]
    out = config.EXPORT_DIR / f"{p.stem}_{cache_key}{target}"
    if out.exists() and out.stat().st_size > 0:
        return {"file_name": f"{p.stem}{target}", "path": str(out),
                "size_kb": round(out.stat().st_size / 1024, 1), "cached": True}

    if target == ".txt":
        from .parser import parse_file
        text = parse_file(src)["text"]
        if not (text or "").strip():
            raise ValueError("文档没有可提取的文字内容")
        out.write_text(text, encoding="utf-8")

    elif target == ".docx":
        if ext == ".pdf":
            _pdf_to_docx(p, out)
        elif ext == ".pptx":
            _pptx_to_docx(p, out)
        elif ext in (".md", ".markdown"):
            _md_to_docx(p, out)
        elif ext in (".csv", ".xlsx", ".xls"):
            from docx import Document
            doc = Document()
            _set_docx_base(doc)
            rows = _read_table(src)
            if not rows:
                raise ValueError("源文件中未检测到表格数据")
            cols = max(len(r) for r in rows)
            t = doc.add_table(rows=len(rows), cols=cols)
            try:
                t.style = "Table Grid"
            except Exception:
                pass
            for i, r in enumerate(rows):
                for j in range(cols):
                    t.cell(i, j).text = str(r[j]) if j < len(r) else ""
                    if i == 0:
                        for run in t.cell(i, j).paragraphs[0].runs:
                            run.bold = True
            doc.save(str(out))
        else:
            from .parser import parse_file
            from docx import Document
            doc = Document()
            _set_docx_base(doc)
            for line in parse_file(src)["text"].splitlines():
                s = line.strip()
                if not s:
                    continue
                m = len(s) - len(s.lstrip("#"))
                if 1 <= m <= 4 and s[m:m + 1] == " ":
                    doc.add_heading(s[m + 1:].strip(), level=m)
                else:
                    doc.add_paragraph(line)
            doc.save(str(out))

    elif target == ".pdf":
        if ext == ".docx":
            _docx_to_pdf(p, out)
        elif ext == ".pptx":
            _pptx_to_pdf(p, out)
        elif ext in (".csv", ".xlsx", ".xls"):
            _table_to_pdf(_read_table(src), out)
        elif ext in (".md", ".markdown"):
            _text_to_pdf(p.read_text(encoding="utf-8", errors="ignore"), out, markdown=True)
        elif ext in (".txt", ".json"):
            _text_to_pdf(p.read_text(encoding="utf-8", errors="ignore"), out)
        else:
            from .parser import parse_file
            _text_to_pdf(parse_file(src)["text"], out)

    elif target in (".xlsx", ".csv"):
        rows = _read_table(src)
        if not rows:
            raise ValueError("源文件中未检测到表格，无法转为表格格式（Excel/CSV）")
        if target == ".csv":
            with open(out, "w", encoding="utf-8-sig", newline="") as f:
                csv.writer(f).writerows(rows)
        else:
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "converted"

            def _num(v):
                # 浮点型字符串转数值（金额/比率右对齐可运算）；纯整数保留文本，防止手机号/编号被科学计数
                if isinstance(v, str) and re.fullmatch(r"-?\d+\.\d+", v) and len(v) < 16:
                    try:
                        return float(v)
                    except ValueError:
                        return v
                return v

            for r in rows:
                # openpyxl 不接受超长字符串/非法控制符以外的复杂类型，统一转字符串兜底
                ws.append(["" if c is None else _num(c) if isinstance(c, (int, float, str)) else str(c) for c in r])
            try:
                _style_worksheet(ws, rows)
            except Exception:
                pass  # 样式美化失败不影响数据输出
            wb.save(str(out))
    else:
        raise ValueError(f"不支持转换到 {target}")

    if not out.exists() or out.stat().st_size == 0:
        raise ValueError("转换结果为空，请检查源文件内容")
    return {"file_name": f"{p.stem}{target}", "path": str(out),
            "size_kb": round(out.stat().st_size / 1024, 1)}
