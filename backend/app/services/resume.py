"""简历转化服务：个人资料存取 / 口语化经历 AI 专业化改写 / 简历 HTML 生成（可视化 + ATS 双模式）/ Word 导出

设计依据（2026 招聘趋势调研）：
- 97% 企业使用 ATS 机器初筛 → 正文必须单栏、标准节标题、禁表格/文本框/照片/技能条
- 量化成果优先：强动词开头 + 数字（规模/百分比/时长），无精确数据用"约/超过"估算、禁止编造
- 行业关键词自然融入；清除 AI 味套话（"吃苦耐劳/结果导向"等）
- 可视化模式面向人类审阅：单一强调色、专业极简、留白 ≥50%，正文结构仍保持 ATS 可解析
"""
import json, uuid
from datetime import datetime
from pathlib import Path
from .. import config
from . import llm, store
from .generator import _chat_json, inject_export

PROFILE_KEY = "resume_profile"          # 个人资料存 settings 表（一键填入）
RESUME_DIR = config.DATA_DIR / "resume"  # 结构化简历数据落盘（Word 导出依赖）
RESUME_DIR.mkdir(parents=True, exist_ok=True)

ACCENT = "#16344C"  # 深藏青：专业、克制、打印友好（2026 简历趋势推荐主色之一）

# ==================== 1. AI 专业化改写 ====================

OPTIMIZE_SYSTEM = f"""你是资深 HR 顾问兼行业猎头，精通简历优化与 ATS（申请人追踪系统）机器筛选逻辑。
任务：把用户口语化、流水账式的经历长文，结合其所属行业与目标岗位知识，改写为**专业化、结构化、强量化**的简历内容。

## 改写铁律
1. 【量化为王】每条经历用强动词开头（主导/搭建/推动/优化/交付…），必须带数字：规模、百分比、金额、人数、时长。
   原文没有的数据可基于合理推断给出量级估算（用"约/超过/30%+"表述），**禁止凭空捏造精确数字**；
   确实无法量化时，改写为"具体动作 + 影响范围"，禁止空话。
2. 【关键词强化】结合行业/岗位提取 12~18 个硬技能关键词，自然融入经历描述与技能分组（ATS 按语境匹配，禁止堆砌）。
3. 【清除套话】删除"吃苦耐劳、有责任心、结果导向、团队精神"等 AI 味/水词；软技能必须用事实证明。
4. 【结构重组】按"概述 → 核心技能关键词 → 工作经历（倒序）→ 项目 → 教育 → 证书"重组，突出与目标岗位的匹配点。
5. 【诚实边界】只基于用户提供的真实经历重组改写，不虚构工作经历、学历、公司。

## 输出格式
输出严格 JSON（不要 markdown 围栏、不要解释）：
{{
  "basics": {{"name":"姓名","phone":"电话","email":"邮箱","position":"求职意向岗位","city":"城市"}},
  "summary": "个人优势概述，2~3 行，突出年限+领域+核心战绩",
  "keywords": ["关键词1","关键词2","…12~18个"],
  "work": [{{"company":"公司","title":"职位","period":"2020.03 - 2024.05","highlights":["量化成果1","量化成果2"]}}],
  "education": [{{"school":"学校","degree":"学历/专业","period":"2012-2016","note":"荣誉/相关课程(可空)"}}],
  "skills": [{{"category":"技能分类","items":["技能1","技能2"]}}],
  "projects": [{{"name":"项目名","role":"角色","period":"时间","desc":"一句话说明+量化结果"}}],
  "certifications": ["证书1"],
  "advice": ["给用户的改进建议1（如补充哪段量化数据）","建议2"]
}}
缺失字段用空数组/空字符串，不要编造。用户表单里已有的正确信息（姓名/电话/教育等）原样保留。"""

# ==================== 2. 可视化简历页生成 ====================

RESUME_VISUAL_SYSTEM = f"""你是顶级简历设计工作室的视觉总监。任务：把结构化简历数据生成为**单文件高质感简历 HTML 页**（可视化版，面向人类审阅）。

## 视觉规范（2026 专业极简风，违者即废稿）
1. 【单一强调色】全页只允许一个强调色 {ACCENT}（深藏青），用于姓名/节标题/分隔线/量化数字高亮；其余一律近黑白灰。禁渐变背景、禁多彩配色。
2. 【版式】A4 纸面感知：max-width 820px 居中，白色纸面卡片 + 极细边框 + 柔和阴影，页面底色 #f2f4f8；
   留白 ≥50%；正文单栏主轴（保持 ATS 可解析），顶部为姓名 Hero 区（姓名大字号衬线 + 求职意向 + 联系方式一行）。
   若 basics.avatar 存在（值为占位符 "__AVATAR__"）：在 Hero 区右侧渲染正圆形头像（直径 96~112px，object-fit:cover，
   外圈 3px 浅强调色圆环 + 细腻柔影），与姓名块左右排布、垂直居中，图片 src 必须原样写 "__AVATAR__"；
   avatar 缺失时不留任何占位。
3. 【字体】标题衬线栈 'Noto Serif SC','SimSun',serif 增强编辑排版感，正文 'PingFang SC','Microsoft YaHei',sans-serif；
   正文 ≥14px，节标题 17~19px，姓名 clamp(30px,5vw,42px)；数字 font-variant-numeric: tabular-nums。
4. 【内容呈现】节标题用「小型大写间距 + 细底线」样式；每段经历：左对齐公司/职位 + 右对齐时间（同一行两端对齐）；
   量化数字用 <strong> 强调色加粗；技能用分类分组的行内标签（细边框 chip，非进度条）；
   核心关键词区放在概述之后（招聘官 6~7 秒首屏扫描）。
5. 【禁止】技能进度条/星级、图表装饰、emoji、表格布局、页眉页脚包裹联系方式。
   【照片规则】仅允许使用 basics.avatar 提供的真实头像（圆形，置于 Hero 区），禁止生成占位头像/剪影/图标占位。
6. 【动效（克制）】入场时 Hero 与各节依次淡入上移（animation-delay 阶梯 0.06s）；滚动显现用 IntersectionObserver；
   打印时全部禁用；@media (prefers-reduced-motion: reduce) 时关闭动画。
7. 【打印】@media print {{ 底色变白、阴影去除、纸面卡片无边距、节禁止跨页截断（break-inside: avoid）、
   * {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }} }}
8. 所有 CSS 内联 <style>；禁止外部 CSS；禁止占位假文；响应式（≤600px 单列堆叠不破版）。

## 输出要求
只输出完整 HTML（<!DOCTYPE html> 到 </html>），不要解释，不要 markdown 围栏。
所有内容必须来自提供的结构化数据，禁止编造任何经历或数字。"""


# ==================== 3. ATS 确定性模板（非可视化模式，不依赖 LLM） ====================

def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_ats_html(data: dict) -> str:
    """确定性渲染 ATS 友好简历：单栏、语义化标签、标准节标题、无装饰（机器解析零损耗）"""
    b = data.get("basics", {})
    contact = " · ".join(x for x in (b.get("phone", ""), b.get("email", ""), b.get("city", "")) if x)

    def _d(x, key):
        """兼容两种输入形态：结构化 dict 或纯字符串（解析结果/用户手填都可能是字符串）"""
        if isinstance(x, dict):
            return x
        return {key: x} if isinstance(x, str) else {}

    def items(lst, renderer):
        return "\n".join(renderer(i) for i in (lst or []))

    work = items(data.get("work"), lambda w: (lambda w: f"""
  <article>
    <h3>{_esc(w.get('title',''))} · {_esc(w.get('company',''))}<span class="period">{_esc(w.get('period',''))}</span></h3>
    <ul>{''.join(f'<li>{_esc(h)}</li>' for h in w.get('highlights', []))}</ul>
  </article>""")(_d(w, "title")))

    edu = items(data.get("education"), lambda e: (lambda e: f"""
  <article>
    <h3>{_esc(e.get('school',''))} · {_esc(e.get('degree',''))}<span class="period">{_esc(e.get('period',''))}</span></h3>
    {'<p>' + _esc(e.get('note','')) + '</p>' if e.get('note') else ''}
  </article>""")(_d(e, "school")))

    def _skill(s):
        if isinstance(s, str):
            return f'<p>{_esc(s)}</p>'
        return f'<p><strong>{_esc(s.get("category",""))}：</strong>{_esc(" · ".join(s.get("items", [])))}</p>'

    skills = items(data.get("skills"), _skill)
    projects = items(data.get("projects"), lambda p: (lambda p: f'<p><strong>{_esc(p.get("name",""))}</strong>（{_esc(p.get("role",""))}，{_esc(p.get("period",""))}）—— {_esc(p.get("desc",""))}</p>')(_d(p, "name")))
    certs = "".join(f'<li>{_esc(c)}</li>' for c in data.get("certifications", []) if isinstance(c, str))
    kws = "".join(f'<span class="kw">{_esc(k)}</span>' for k in data.get("keywords", []) if isinstance(k, str))

    def section(title, body):
        return f'\n <section><h2>{title}</h2>{body}</section>' if body.strip() else ""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(b.get('name','简历'))}的简历</title>
<style>
  :root {{ --accent: {ACCENT}; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: 'PingFang SC','Microsoft YaHei',sans-serif; color: #1f2733; margin: 0;
         background: #f2f4f8; font-size: 14px; line-height: 1.75; }}
  .sheet {{ max-width: 820px; margin: 24px auto; background: #fff; padding: 48px 56px; }}
  h1 {{ font-size: 30px; margin: 0 0 4px; color: var(--accent); }}
  .intent {{ font-size: 15px; font-weight: 600; margin: 0 0 6px; }}
  .contact {{ color: #5b6472; font-size: 13px; margin: 0 0 18px; }}
  h2 {{ font-size: 17px; color: var(--accent); border-bottom: 1.5px solid var(--accent);
        padding-bottom: 5px; margin: 26px 0 12px; letter-spacing: 1px; }}
  h3 {{ font-size: 14.5px; margin: 14px 0 4px; display: flex; justify-content: space-between; gap: 12px; }}
  .period {{ color: #6b7686; font-weight: 400; font-size: 13px; white-space: nowrap; }}
  ul {{ margin: 4px 0 10px; padding-left: 20px; }}
  li {{ margin-bottom: 3px; }}
  p {{ margin: 5px 0; }}
  .summary {{ margin: 0 0 8px; }}
  .kws {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  .kw {{ border: 1px solid #ccd3e0; border-radius: 4px; padding: 1px 9px; font-size: 12.5px; color: #39414e; }}
  @media print {{ body {{ background: #fff; }} .sheet {{ margin: 0; padding: 24px 8px; }}
    * {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }} section {{ break-inside: avoid; }} }}
  @media (max-width: 600px) {{ .sheet {{ padding: 24px 18px; margin: 0; }} h3 {{ flex-direction: column; }} }}
</style>
</head>
<body>
<main class="sheet">
  <h1>{_esc(b.get('name', ''))}</h1>
  {'<p class="intent">求职意向：' + _esc(b.get('position', '')) + '</p>' if b.get('position') else ''}
  {'<p class="contact">' + _esc(contact) + '</p>' if contact else ''}
  {section('个人概述', f'<p class="summary">{_esc(data.get("summary",""))}</p>')}
  {section('核心技能关键词', f'<div class="kws">{kws}</div>')}
  {section('工作经历', work)}
  {section('项目经历', projects)}
  {section('教育背景', edu)}
  {section('专业技能', skills)}
  {section('证书', f'<ul>{certs}</ul>')}
</main>
</body>
</html>"""


# ==================== 4. Word 导出（python-docx） ====================

def _decode_avatar(data_url: str) -> bytes | None:
    """basics.avatar（data URL）→ 图片二进制；非法/缺失返回 None"""
    if not data_url or not data_url.startswith("data:image"):
        return None
    import base64
    try:
        raw = base64.b64decode(data_url.split(",", 1)[1])
        return raw if raw else None
    except Exception:
        return None


def build_docx(data: dict, out_path: Path):
    from docx import Document
    from docx.shared import Pt, RGBColor, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn

    ACC = RGBColor(0x16, 0x34, 0x4C)
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)
    normal._element.get_or_add_rPr()
    rpr = normal.element.rPr
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), "微软雅黑")
    for s in doc.sections:
        s.top_margin = s.bottom_margin = Cm(1.6)
        s.left_margin = s.right_margin = Cm(1.9)

    def para(text="", size=10.5, bold=False, color=None, before=0, after=4, align=None, container=None):
        host = container if container is not None else doc
        p = host.add_paragraph()
        p.paragraph_format.space_before = Pt(before)
        p.paragraph_format.space_after = Pt(after)
        if align is not None:
            p.alignment = align
        if text:
            r = p.add_run(text)
            r.bold = bold
            r.font.size = Pt(size)
            if color:
                r.font.color.rgb = color
        return p

    def section(title):
        para(title, size=13, bold=True, color=ACC, before=12, after=6)

    b = data.get("basics", {})

    # ---- Hero 头部：有头像 → 两栏表格（左信息/右照片）；无头像 → 常规段落 ----
    avatar_raw = _decode_avatar(b.get("avatar", ""))
    header_host = doc
    if avatar_raw:
        import io
        tbl = doc.add_table(rows=1, cols=2)
        tbl.autofit = False
        tbl.columns[0].width = Cm(13.4)
        tbl.columns[1].width = Cm(3.6)
        left, right = tbl.rows[0].cells
        left.width, right.width = Cm(13.4), Cm(3.6)
        header_host = left
        pr = right.paragraphs[0]
        pr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        run = pr.add_run()
        try:
            run.add_picture(io.BytesIO(avatar_raw), height=Cm(3.2))
        except Exception:
            pass  # 图片异常时静默降级为无头像版式

    para(b.get("name", ""), size=22, bold=True, color=ACC, after=2, container=header_host)
    if b.get("position"):
        para(f"求职意向：{b['position']}", size=12, bold=True, after=2, container=header_host)
    contact = " | ".join(x for x in (b.get("phone", ""), b.get("email", ""), b.get("city", "")) if x)
    if contact:
        para(contact, size=10, color=RGBColor(0x6B, 0x76, 0x86), after=8, container=header_host)

    if data.get("summary"):
        section("个人概述")
        para(data["summary"])
    if data.get("keywords"):
        section("核心技能关键词")
        para("  ·  ".join(str(k) for k in data["keywords"]))
    # 兼容纯字符串条目（解析结果/手填都可能是 str），避免 AttributeError 500
    def _d(x, key):
        return x if isinstance(x, dict) else {key: x} if isinstance(x, str) else {}

    def _skill_line(s):
        if isinstance(s, str):
            return s
        return f"{s.get('category', '')}：{' · '.join(s.get('items', []))}".strip("：")

    if data.get("work"):
        section("工作经历")
        for w0 in data["work"]:
            w = _d(w0, "title")
            para(f"{w.get('title', '')} · {w.get('company', '')}（{w.get('period', '')}）", bold=True, before=6, after=2)
            for h in w.get("highlights", []):
                p = para("• " + str(h), after=1)
                p.paragraph_format.left_indent = Cm(0.5)
    if data.get("projects"):
        section("项目经历")
        for pr0 in data["projects"]:
            pr = _d(pr0, "name")
            para(f"{pr.get('name', '')}（{pr.get('role', '')}，{pr.get('period', '')}）", bold=True, before=4, after=1)
            para(pr.get("desc", ""))
    if data.get("education"):
        section("教育背景")
        for e0 in data["education"]:
            e = _d(e0, "school")
            para(f"{e.get('school', '')} · {e.get('degree', '')}（{e.get('period', '')}）", bold=True, after=1)
            if e.get("note"):
                para(e["note"])
    if data.get("skills"):
        section("专业技能")
        for s in data["skills"]:
            para(_skill_line(s), after=2)
    if data.get("certifications"):
        section("证书")
        for c in data["certifications"]:
            para("• " + str(c))

    doc.save(str(out_path))


# ==================== 5. 高层流程 ====================

async def get_profile() -> dict:
    return store.get_setting(PROFILE_KEY, {})


async def save_profile(profile: dict) -> dict:
    store.set_setting(PROFILE_KEY, profile)
    return {"ok": True}


async def optimize(payload: dict, model_id: str | None = None) -> dict:
    """口语化经历 + 结构化表单 → AI 专业化改写（量化/关键词/结构重组）"""
    story = (payload.get("story") or "").strip()
    form = payload.get("form") or {}
    industry = payload.get("industry", "")
    position = payload.get("position", "")
    target = payload.get("target", "")
    if not story and not form:
        raise llm.LLMError("请先填写经历长文或结构化信息")
    user_prompt = f"""【所属行业】{industry or '未提供（请根据经历内容判断）'}
【目标岗位】{position or '未提供（请根据经历内容判断）'}
【目标 JD / 补充要求】{target or '无'}
【结构化表单（已确认的正确信息，原样保留其中的姓名/电话/邮箱/教育等）】
{json.dumps(form, ensure_ascii=False)[:4000]}
【口语化经历长文】
{story[:config.MAX_CONTEXT_CHARS]}"""
    result = await _chat_json(OPTIMIZE_SYSTEM, user_prompt, model_id, max_tokens=6000, temperature=0.5)
    return result


async def generate(data: dict, visual: bool = True, model_id: str | None = None) -> dict:
    """结构化简历数据 → HTML（visual=LLM 可视化页 / False=ATS 确定性模板）→ 落盘 + 写入 records"""
    b = data.get("basics", {})
    name = b.get("name") or "未命名"
    if visual:
        # 头像 data URL 体积大，不进 LLM prompt：以占位符传递，生成后原样回填
        avatar_url = b.get("avatar") or ""
        prompt_data = data
        if avatar_url.startswith("data:image"):
            import copy
            prompt_data = copy.deepcopy(data)
            prompt_data["basics"]["avatar"] = "__AVATAR__"
        user_prompt = f"""【结构化简历数据】
{json.dumps(prompt_data, ensure_ascii=False)[:config.MAX_CONTEXT_CHARS]}"""
        raw = await llm.chat(
            [{"role": "system", "content": RESUME_VISUAL_SYSTEM},
             {"role": "user", "content": user_prompt}],
            model_id=model_id, temperature=0.55, max_tokens=12000)
        html_code = llm.extract_html(raw)
        if avatar_url.startswith("data:image"):
            html_code = html_code.replace("__AVATAR__", avatar_url)
    else:
        html_code = render_ats_html(data)
    html_code = inject_export(html_code)

    rec_id = uuid.uuid4().hex[:12]
    html_path = config.GENERATED_DIR / f"{rec_id}.html"
    html_path.write_text(html_code, encoding="utf-8")
    (RESUME_DIR / f"{rec_id}.json").write_text(
        json.dumps(data, ensure_ascii=False), encoding="utf-8")

    keywords = data.get("keywords", [])[:5]
    rec = {
        "id": rec_id, "title": f"{name}的简历",
        "file_name": f"{name}_简历.html", "source_type": "resume",
        "summary": data.get("summary", ""), "category": "简历",
        "tags": json.dumps(keywords, ensure_ascii=False),
        "html_path": str(html_path), "html_code": html_code,
        "theme": "resume-visual" if visual else "resume-ats",
        "model": model_id or "agnes-default", "file_id": "",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    store.execute(
        "INSERT INTO records(id,title,file_name,source_type,summary,category,tags,html_path,html_code,theme,model,file_id,status,created_at) "
        "VALUES(:id,:title,:file_name,:source_type,:summary,:category,:tags,:html_path,:html_code,:theme,:model,:file_id,'active',:created_at)", rec)
    return {"id": rec_id, "title": rec["title"], "preview_url": f"/api/preview/{rec_id}"}


def load_resume_data(rec_id: str) -> dict:
    f = RESUME_DIR / f"{rec_id}.json"
    if not f.exists():
        raise FileNotFoundError("该简历记录缺少结构化数据")
    return json.loads(f.read_text(encoding="utf-8"))
