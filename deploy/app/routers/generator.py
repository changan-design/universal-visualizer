"""HTML 可视化页面生成器：LLM 根据内容主题智能选型配色/版式，输出单文件高质感 HTML"""
import json, uuid
from datetime import datetime
from .. import config
from . import llm
from . import store

THEMES = {
    "auto":       "根据内容主题自行判断并选择最贴合的视觉风格（智能选型）",
    "tech-blue":  "科技蓝：深海军蓝底 #0B1220 + 电光蓝 #3B82F6 点缀，玻璃拟态卡片，适合科技/互联网/数据类内容",
    "biz-gold":   "商务黑金：炭黑 #111 底 + 香槟金 #C9A227 点缀，衬线标题，适合金融/商业/战略报告",
    "fresh-green":"清新自然：米白 #F7F5EF 底 + 森林绿 #2F6B4F，适合环保/农业/健康类内容",
    "warm-orange":"暖橙活力：奶油白 #FFF8F0 底 + 珊瑚橙 #E8622C，适合教育/生活/营销类内容",
    "minimal":    "极简杂志：纯白底 + 近黑文字 + 一处强调色，大量留白，编辑排版风",
    "dark-neon":  "暗黑霓虹：#0A0A12 底 + 霓虹紫/青渐变，适合游戏/创意/潮流内容",
}

GEN_SYSTEM = f"""你是「万能可视化工具」的资深前端视觉设计师兼数据可视化工程师。
任务：把用户提供的文档内容转化为一个**单文件、可直接在浏览器打开的高质量 HTML 展示页**。

## 视觉要求（重要）
1. 【智能选型】{THEMES['auto']}。若用户指定了主题，则严格按指定主题执行。
2. 产出必须具备一线大厂产品页面的高级质感：
   - 设计系统：用 CSS 变量定义 --bg/--surface/--primary/--accent/--text/--text-sub/--radius/--shadow 全局令牌；
   - 字体层级：Hero 大标题 clamp(34px,5vw,56px) 加字重与字距，节标题 22-28px，正文 15-16px/1.9 行高，
     数字一律 font-variant-numeric: tabular-nums；
   - 质感细节：卡片细边框 + 多层柔和阴影、渐变强调（主色→辅助色 135deg）、微妙玻璃拟态
     （backdrop-filter: blur 用于导航/悬浮元素）、1px 高光描边（rgba(255,255,255,.08)）。
3. 页面结构：顶部 Hero 区（大标题+一句话摘要+元信息徽章）→ 核心内容区（分节卡片/时间线/对比栏等，
   依据内容形态选择最合适的版式）→ 数据可视化区 → 尾注。区块之间用 section 编号或装饰线增强节奏感。
4. 【动效与过渡（必须实现，直接影响成品评级）】
   a. 入场动画：页面加载时 Hero 元素依次淡入上移（CSS animation + animation-delay 阶梯延迟 0.08s/项）；
   b. 滚动显现（**若**采用「初始 opacity:0 + 滚动加类点亮」的写法，必须同时满足：① CSS 写成
      `.js .reveal{{opacity:0}}` 并在 <head> 最前面放 `<script>document.documentElement.className+=' js'</script>`；
      ② 真的写出 IntersectionObserver 给元素加 visible 类。否则内容永久隐形，页面看起来只剩标题——
      这是最常见的废稿原因，本项目已因此出过线上故障。更稳妥的是直接用 CSS animation 入场，不依赖 JS）：用 IntersectionObserver 给每个 section/卡片加 .reveal 类，进入视口时
      opacity 0→1 + translateY(24px)→0 过渡 0.6s cubic-bezier(.22,.61,.36,1)，加 transition-delay 制造级联；
   c. 数字滚动：关键指标数字用 rAF 实现 count-up（1.2s ease-out，支持千分位与小数）；
   d. Hover 交互：卡片 hover 上浮 translateY(-4px) + 阴影加深 + 边框亮起，过渡 .25s；
   e. 图表动画：ECharts 开启动画（animationDuration 900 + animationEasing 'cubicOut'），
      饼图用 expansion，加载时容器有淡入；
   f. 尊重 prefers-reduced-motion：有该媒体查询时关闭动画。
5. 图表：引入 ECharts CDN（https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js），
   按内容真实数据构造 option，图表配色与页面主题一致；无数据则不放图表，禁止编造精确数据
   （可基于文中描述做示意性可视化时，需标注"示意图"）。
6. 所有 CSS 内联在 <style> 中；禁止外部 CSS 文件；禁止占位假文（lorem ipsum）。
7. 中文内容用系统中文字体栈：'PingFang SC','Microsoft YaHei',sans-serif；标题可用衬线增强质感。
8. 响应式：max-width 1100px 居中，移动端不破版。
9. 【打印/PDF（必须包含）】样式末尾写 @media print {{
      .no-print, [data-no-print] {{ display:none !important; }}
      * {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
      section, .card {{ page-break-inside: avoid; break-inside: avoid; }}
      body {{ background: var(--bg) !important; }}
   }}
10. 【JS 语法自检】<script> 内必须使用标准 JS 语法：HTML 标签的 style 属性只能写 CSS（font-weight，不是 fontWeight）；
   ECharts option 遵循官方写法，字符串引号配对完整，输出前逐段自检避免语法错误导致图表不渲染。
11. 【必须写完整】结尾的 <script> 必须闭合，必须以 </body></html> 结束；图表容器必须真的被
   echarts.init + setOption 填充，不能只留一个空的 <div id="chart">。

## 输出要求
- 只输出完整 HTML 代码（从 <!DOCTYPE html> 到 </html>），不要任何解释文字，不要 markdown 代码块围栏。
- **全文控制在 9000 tokens 以内**：CSS 合并书写、零注释、零冗余选择器，动效用最简实现；
  全页至多 2 个 <script> 块（图表逻辑 + 交互逻辑各一，不要拆成十几个小块）。
  写超长被截断 = 整页报废（页面会只剩标题），宁少勿超。
- 内容必须来自用户文档的真实信息，信息密度要高：把文档里的要点、数据、结构都提炼呈现出来。"""


# ---- 结构化表格专属提示词：逐行数据由后端注入，模型只写框架与图算逻辑 ----
TABLE_GEN_SYSTEM = """你是「万能可视化工具」的资深前端工程师。任务：把一份**结构化表格数据**做成单文件可视化分析页。

## 数据供给协议（必须严格遵守，违者即废稿）
表格的真实数据**不在你的输出里**。后端已把下面这个 <script> 注入到页面 </head> 之前：
window.UV_DATA = {
  headers: ["城市","项目名称","最高投标限价(元)","报价浮动率", ...],   // 列名数组，顺序固定
  rows: [["唐山市","xx工程",2881325.21,null,0.9625, ...], ...],       // 二维数组，数字是 number，空值是 null
  total: 55,                                                          // 真实总行数
  truncated: false,                                                   // rows 是否为部分行
  profiles: [                                                         // 每列统计画像，可直接用来设计图表
    {"name":"城市","type":"category","distinct":4,"top":[{"v":"唐山市","n":14}, ...]},
    {"name":"最高投标限价(元)","type":"number","min":...,"max":...,"avg":...,"sum":...},
    ...
  ]
}

## 铁律（违反任何一条即为废稿）
1. **严禁把 rows 的逐行数据抄进 HTML**。页面中不得出现硬编码的明细行，所有明细必须由 JS 读 UV_DATA.rows 渲染。
2. 图表 option 必须在 JS 里**现场计算**：对 rows 分组计数 / 求和 / 排序，结果再赋给 series.data。
   例：城市分布 = 遍历 rows，按 headers 里「城市」列的下标累加计数。
3. 必须实现**明细数据表**：用 UV_DATA.headers 做表头、UV_DATA.rows 做数据渲染，
   带前端分页（每页 20 行）、关键字搜索框、点表头排序，以及「第 x-y 条 / 共 total 条」计数。
4. 页面所有数字都必须来自 UV_DATA，禁止硬编码、禁止编造。
5. **输出体积控制在 7000 tokens 以内**：CSS 合并书写、不写注释、不重复选择器。宁可少几个装饰，
   也绝不能写超长导致 HTML 被截断（截断会让整页白屏）。
6. 结尾必须闭合所有 <script>，并以 </body></html> 结束。

## 视觉要求
1. 【智能选型】根据数据主题自行选择最贴合的视觉风格。
2. 设计系统：CSS 变量 --bg/--surface/--primary/--accent/--text/--text-sub/--radius/--shadow；字体层级分明
   （Hero 标题 clamp(30px,4.5vw,48px)，节标题 20-24px，正文 14-15px/1.8）；数字用 tabular-nums。
3. 图表统一用 ECharts，配色与主题一致，animationDuration 900 + cubicOut。
4. 卡片 hover 上浮 + 阴影过渡；表格行 hover 高亮。
5. 所有 CSS 内联；中文系统字体栈；max-width 1200px 居中；移动端不破版。
6. 必须包含 @media print 样式（隐藏 .no-print，print-color-adjust: exact，thead 重复表头）。
7. 若用 .reveal 做滚动显现，必须遵守 .js .reveal 写法并写出 IntersectionObserver，否则内容会永久隐形。

## 页面结构
Hero（标题 + 数据范围说明 + 3~5 个关键指标卡，数值全部由 UV_DATA 现算）→ 图表区（2~4 个图表：
分类分布 / 数值排行 / 状态占比 / 数值区间分布，按 profiles 的列类型选）→ 明细表区 → 尾注（数据来源、生成时间）。

## 输出要求
- 只输出完整 HTML（<!DOCTYPE html> 到 </html>），不要解释，不要 markdown 围栏。"""

SUMMARY_SYSTEM = """你是文档分析专家。分析用户提供的文档内容，输出严格的 JSON（不要 markdown 围栏、不要解释）：
{"title": "提炼的文档标题", "summary": "150-250字内容总结", "category": "分类（从这些里选或自拟：商业报告/技术文档/教育材料/会议纪要/营销策划/学术研究/法律文书/新闻资讯/其他）",
"tags": ["标签1","标签2","标签3","标签4","标签5"], "keywords": ["关键词1","关键词2"],
"content_type": "内容形态：报告类/叙述类/数据类/教程类/演讲类", "suggested_theme": "建议主题：tech-blue/biz-gold/fresh-green/warm-orange/minimal/dark-neon 之一"}"""

INSIGHT_SYSTEM = """你是数据分析专家。从用户提供的文档内容中提取可量化信息，构造图表洞察。输出严格 JSON（不要围栏）：{"charts": [{"title": "图表标题", "type": "bar|line|pie|radar", "note": "数据来源说明（来自文档哪部分/是否示意）",
"option": {ECharts option 对象，含 xAxis/series 等，配色用一组和谐色}}], "insights": ["洞察结论1", "洞察结论2"]}
要求：
1. 1-4 个图表；若文档无可量化数据，构造 1 个基于内容权重的示意雷达/条形图并在 note 标注"示意"；insights 给 2-4 条一针见血的结论。
2. 【严格纯 JSON】option 内禁止任何 JavaScript 函数/箭头函数/表达式（如 formatter 不能写 value=>...，改用字符串模板 "{value}%" 或 "{c}"）；禁止注释；禁止尾逗号；所有 key 用双引号。"""

def _num_setting(key: str, default):
    """读取用户在「系统设置」中保存的数值项，异常值回退默认"""
    try:
        v = store.get_setting(key, default)
        return v if isinstance(v, (int, float)) and not isinstance(v, bool) else default
    except Exception:
        return default


async def generate_html(doc_text: str, meta: dict, theme: str = "auto",
                        model_id: str | None = None, extra_req: str = "",
                        table: dict | None = None) -> dict:
    """调用 LLM 生成 HTML，落盘并返回 {record} 数据

    table 不为 None 时走「表格数据注入」通道：逐行数据不进 prompt、也不允许模型转写，
    模型只负责框架与图算逻辑，从根上消除「数据内联导致输出超长被截断」的故障。
    """
    theme_desc = THEMES.get(theme, THEMES["auto"])
    max_chars = int(_num_setting("max_context_chars", config.MAX_CONTEXT_CHARS))
    temperature = float(_num_setting("temperature", 0.65))

    if table:
        from . import tabledata
        system = TABLE_GEN_SYSTEM + f"\n当前主题说明：{theme_desc}"
        user_prompt = f"""【数据文件】{meta.get('file_name', '表格')} | 格式：{meta.get('ext', '.xlsx')} | 真实总行数：{table['total']} | 列数：{len(table['headers'])}
【指定主题】{theme if theme != 'auto' else 'auto（你来自智能选型）'}
【附加要求】{extra_req or '无'}

【表格结构与列画像（真实统计结果；明细数据请从 window.UV_DATA.rows 读取，不要写进页面）】
{tabledata.brief(table)}
"""
    else:
        system = GEN_SYSTEM + f"\n当前指定主题说明：{theme_desc}"
        user_prompt = f"""【文档元信息】文件：{meta.get('file_name','在线输入')} | 格式：{meta.get('ext','txt')} | 字数：{meta.get('char_count', len(doc_text))}
【指定主题】{theme if theme != 'auto' else 'auto（你来自智能选型，并在页面注释里说明你为什么选这个风格）'}
【附加要求】{extra_req or '无'}

【文档内容】
{doc_text[:max_chars]}"""

    messages = [{"role": "system", "content": system},
                {"role": "user", "content": user_prompt}]
    raw = await llm.chat(messages, model_id=model_id, temperature=temperature, max_tokens=16000)
    html_code = llm.extract_html(raw)
    html_code = await _finalize_html(messages, html_code, model_id, temperature)

    rec_id = uuid.uuid4().hex[:12]
    html_path = config.GENERATED_DIR / f"{rec_id}.html"
    if table:
        html_code = inject_table(html_code, table)
    html_path.write_text(html_code, encoding="utf-8")
    return {"id": rec_id, "html_code": html_code, "html_path": str(html_path)}


async def _finalize_html(messages: list, html: str, model_id: str | None,
                         temperature: float, rounds: int = 8) -> str:
    """确保 HTML 完整且图表真的能渲染。

    历史故障一：55 行表格被要求逐行转写，输出触顶 max_tokens，HTML 从 <script> 中间截断，
    图表初始化整段丢失 → 页面只剩标题。对策：截断续写。
    历史故障二：模型写出 return{x:value:x.maxBid} 这类无效 JS，运行时抛 SyntaxError，
    异常点之后的表格渲染整段不执行 → 页面只有标题。对策：node --check 定点修复。
    """
    # 第一道闸：结构完整性（截断续写）
    issues = llm.html_issues(html)
    attempt = 0
    while issues and attempt < rounds:
        attempt += 1
        prev_len = len(html)
        html = await llm.continue_html(messages, html, model_id=model_id,
                                       temperature=max(0.2, temperature - 0.2))
        issues = llm.html_issues(html)
        if issues and len(html) <= prev_len + 50:
            break  # 续写没有实质进展，继续耗轮次无意义
    if issues:
        raise llm.LLMError("页面生成不完整（" + "；".join(issues) +
                           f"，已输出约 {len(html) // 1000}k 字符）。"
                           "模型输出疑似达到长度上限，请重试，或在设置中换用输出更长的模型。")
    # 第二道闸：内联脚本语法（宿主机无 node 时自动跳过，交由页面自愈脚本兜底）
    err = llm.js_syntax_error(html)
    attempt = 0
    while err and attempt < rounds:
        attempt += 1
        fixed = await llm.fix_script(messages, html, err, model_id=model_id,
                                     temperature=max(0.2, temperature - 0.4))
        if fixed == html:
            break
        html = fixed
        err = llm.js_syntax_error(html)
    if err:
        raise llm.LLMError("页面脚本存在无法自动修复的语法错误：" + err +
                           "。请重试，或在设置中换用其它模型。")
    # 第三道闸：渲染有效性（容器存在但从未初始化 / .reveal 永久隐形）
    rissues = render_issues(html)
    if rissues:
        fixed = await llm.fix_script(
            messages, html,
            "渲染有效性检查未通过：" + "；".join(rissues) +
            "。请输出修正后的完整脚本（若缺少图表初始化或滚动显现代码，请补齐到该脚本中）。",
            model_id=model_id, temperature=temperature)
        if fixed != html:
            html = fixed
        rissues = render_issues(html)
        if rissues:
            # 注入的自愈脚本已能兜底 reveal 隐形问题；图表容器缺失仍视为不可交付
            fatal = [x for x in rissues if "echarts" in x or "setOption" in x]
            if fatal:
                raise llm.LLMError("页面图表未初始化（" + "；".join(fatal) + "）。请重试。")
    return html


def render_issues(html: str) -> list:
    """渲染有效性：容器存在但从未被填充 = 用户看到的「只有标题没有内容」"""
    import re
    out = []
    # 容器识别兼容两种命名：id 含 chart（chCity/chart1）与 class 形如 chart-box/chart-card
    n_cont = len(re.findall(r'id=["\'][^"\']*chart[^"\']*["\']', html, re.I)) or \
             len(re.findall(r'class=["\'][^"\']*chart[-_ ]?(?:box|card|wrap|container)[^"\']*["\']', html, re.I))
    n_init = len(re.findall(r"echarts\s*\.\s*init", html))
    n_opt = len(re.findall(r"\.\s*setOption", html))
    if n_cont and not n_init:
        out.append(f"{n_cont} 个图表容器但未调用 echarts.init")
    if n_cont and not n_opt:
        out.append(f"{n_cont} 个图表容器但未调用 setOption（图表会是空白）")
    if re.search(r"\.reveal\s*\{[^}]*opacity\s*:\s*0", html) and "IntersectionObserver" not in html:
        out.append(".reveal 初始不可见但缺少 IntersectionObserver（内容会永久隐形）")
    # 脚本引用了不存在的元素 id → 运行时 null 崩溃，异常点之后的渲染全部中断
    ids_html = set(re.findall(r'id=["\']([^"\']+)["\']', html))
    created = set(re.findall(r"\.id\s*=\s*['\"]([^'\"]+)['\"]", html))
    refd = set()
    for s in re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S | re.I):
        refd |= set(re.findall(r"getElementById\(['\"]([^'\"]+)['\"]\)", s))
    ghost = sorted(refd - ids_html - created)
    if ghost:
        out.append("脚本引用了页面中不存在的元素 id: " + ", ".join(f'#{x}' for x in ghost[:6]))
    return out

async def summarize(doc_text: str, model_id: str | None = None) -> dict:
    max_chars = int(_num_setting("max_context_chars", config.MAX_CONTEXT_CHARS))
    return await _chat_json(SUMMARY_SYSTEM, doc_text[:max_chars], model_id,
                            max_tokens=2000, temperature=0.3)

async def insight(doc_text: str, model_id: str | None = None) -> dict:
    max_chars = int(_num_setting("max_context_chars", config.MAX_CONTEXT_CHARS))
    return await _chat_json(INSIGHT_SYSTEM, doc_text[:max_chars], model_id,
                            max_tokens=5000, temperature=0.4)

async def _chat_json(system: str, user: str, model_id: str | None,
                     max_tokens: int, temperature: float) -> dict:
    """带自动重试的 JSON 生成：reasoning 模型偶尔输出非法 JSON，失败后降温重试一次"""
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    last_err = None
    for attempt, temp in enumerate((temperature, max(0.1, temperature - 0.3))):
        try:
            raw = await llm.chat(messages, model_id=model_id, temperature=temp, max_tokens=max_tokens)
            return _safe_json(raw)
        except (llm.LLMError, ValueError) as e:
            last_err = e
    raise llm.LLMError(f"JSON 解析重试后仍失败: {last_err}")

def _safe_json(raw: str) -> dict:
    t = raw.strip()
    if t.startswith("```"):
        t = t.split("```")[1]
        if t.startswith("json"):
            t = t[4:]
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end == -1:
        raise llm.LLMError("模型未返回有效 JSON")
    t = t[start:end + 1]
    import json as _json, re
    try:
        return _json.loads(t)
    except _json.JSONDecodeError:
        pass
    # 容错清洗：去掉块注释/行注释、尾逗号、把单引号 key/值替换为双引号后再试
    cleaned = re.sub(r"/\*[\s\S]*?\*/|//[^\n\"]*", "", t)
    cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)
    try:
        return _json.loads(cleaned)
    except _json.JSONDecodeError as e:
        raise llm.LLMError(f"模型返回的 JSON 无法解析（{e}），请重试") from e


# ==================== 大文件模式（海量明细数据可视化）====================

BIGDATA_GEN_SYSTEM = """你是「万能可视化工具」的资深前端工程师。任务：为一份**海量明细数据表**（数万至数十万行）生成单文件可视化 HTML。

## 架构约定（必须严格遵守，违者即废稿）
明细数据**不在** HTML 里，也不可能塞进 HTML。数据供给协议如下：
1. 后端会在 </head> 前注入：`<script>window.PAGE_DATA = {真实聚合统计JSON}; window.__REC_ID__ = "记录ID";</script>`
   - PAGE_DATA 含：total（真实总条数）、headers（列名）、carriers（分布字典）、sources（分布字典）、segments（号段分布字典）、columns（列名数组）
2. 页面所有数字（Hero 大数字、图表、标签页计数）**只能从 window.PAGE_DATA 读取/计算**，禁止硬编码任何数量。
3. 明细表必须实现分页查询，调用后端接口：
   `GET /api/records/${window.__REC_ID__}/data?page=1&size=100&carrier=全部&source=全部&keyword=`
   返回 JSON：{ total, page, size, rows: [[...单元格...]], headers }
   - 实现 loadPage(page) 函数：fetch 上述接口（carrier/source 取当前激活的筛选值），渲染表格（用 headers 对齐列）+ 显示「第 x-y 条 / 共 total 条」+ 上一页/下一页/跳转按钮。
   - 筛选标签页（运营商/数据来源）切换时重置到第 1 页并带参重新请求。
4. 图表用 ECharts CDN 渲染 PAGE_DATA 的真实分布（如 carriers 饼图、sources 条形图、segments 条形图），图例/标签用真实类别名。

## 视觉要求（精简执行，篇幅优先保证完整）
- CSS 设计令牌（--bg/--surface/--primary/--accent/--radius/--shadow）、字体层级分明、
  Hero 大数字 clamp(40px,6vw,64px) + tabular-nums；max-width 1100px 居中；所有 CSS 内联。
- Hero 区展示 PAGE_DATA.total（toLocaleString 千分位）；卡片 hover 过渡；
  滚动显现用 IntersectionObserver + .reveal；ECharts animationDuration 900。
- 打印样式：@media print 隐藏 .no-print、print-color-adjust:exact、thead 重复表头。
- 明细表加载中显示「加载中…」文字即可（不要写骨架屏/shimmer 动画，节省篇幅）。
- ECharts CDN：https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js

## 输出要求（最重要）
- 只输出完整 HTML（<!DOCTYPE html> 到 </html>），不要解释，不要 markdown 围栏。
- **全文控制在 8000 tokens 以内**：CSS 合并书写、零注释、零冗余选择器。
  写超长被截断 = 整页报废，宁少勿超。
- 除 PAGE_DATA 提供的数据外，页面中不得出现任何编造的数量数字。"""


async def generate_html_bigdata(doc_text: str, meta: dict, stats: dict,
                                theme: str = "auto", model_id: str | None = None,
                                extra_req: str = "") -> dict:
    """大文件模式：LLM 生成框架，数字全部来自 PAGE_DATA 协议"""
    stats_brief = {
        "total": stats["total"], "headers": stats["headers"], "col_map": stats["col_map"],
        "carriers": stats["carriers"], "sources": stats["sources"], "segments": stats["segments"],
    }
    user_prompt = f"""【数据文件】{meta.get('file_name')} | 总条数：{stats['total']}（真实值，必须作为页面展示的总数）
【指定主题】{theme}
【附加要求】{extra_req or '无'}
【聚合统计（window.PAGE_DATA 将注入这些真实数据）】
{json.dumps(stats_brief, ensure_ascii=False)}
【列画像（通用统计，任何表格都可据此设计图表）】
{_profiles_brief(stats)}
【表头样本（前 500 行预览，供你理解列含义）】
{doc_text[:6000]}"""
    messages = [{"role": "system", "content": BIGDATA_GEN_SYSTEM + f"\n主题说明：{THEMES.get(theme, THEMES['auto'])}"},
                {"role": "user", "content": user_prompt}]
    raw = await llm.chat(messages, model_id=model_id, temperature=0.5, max_tokens=16000)
    html_code = llm.extract_html(raw)
    html_code = await _finalize_html(messages, html_code, model_id, 0.5)
    return {"html_code": html_code}  # 注入在路由层完成后统一落盘


def _profiles_brief(stats: dict, max_chars: int = 2000) -> str:
    """大文件模式也给出通用列画像，避免非「运营商/来源」类大表格拿不到可画的数据"""
    profs = stats.get("profiles") or []
    if not profs:
        return "（无列画像，按表头与样本自行推断）"
    lines = []
    for p in profs[:24]:
        t = p.get("type")
        desc = f"- {p.get('name')} | {t} | 去重{p.get('distinct')}"
        if t == "number":
            desc += f" | min {p.get('min')} max {p.get('max')} avg {p.get('avg')}"
        elif t == "category":
            desc += " | " + "、".join(f"{x['v']}({x['n']})" for x in p.get("top", [])[:8])
        lines.append(desc)
    return "\n".join(lines)[:max_chars]


def inject_bigdata(html_code: str, rec_id: str, stats: dict) -> str:
    """把真实聚合数据与记录 ID 注入 HTML（head 前注入，兜底覆盖协议）

    注意：不能在注入后再做 __REC_ID__ 全局替换 —— 那会把注入脚本里的
    `window.__REC_ID__` 一起改坏。这里先安全替换「带引号的占位符」，
    再注入同时声明 window.__REC_ID__ 与同名全局变量，两种写法都能取到值。
    """
    page_data = {
        "total": stats["total"], "headers": stats["headers"], "col_map": stats["col_map"],
        "carriers": stats["carriers"], "sources": stats["sources"], "segments": stats["segments"],
        "columns": stats.get("columns", []),
    }
    out = html_code
    if "window.__UV_DATA_INJECTED__" in out:      # 幂等：本服务的注入脚本已存在（页面自身读 PAGE_DATA 不算）
        return out
    out = out.replace('"__REC_ID__"', f'"{rec_id}"').replace("'__REC_ID__'", f"'{rec_id}'")
    script = (f'<script>window.__UV_DATA_INJECTED__ = 1;'
              f' window.PAGE_DATA = {json.dumps(page_data, ensure_ascii=False)};'
              f' window.__REC_ID__ = "{rec_id}"; var __REC_ID__ = window.__REC_ID__;</script>')
    lower = out.lower()
    if "</head>" in lower:
        idx = lower.index("</head>")
        out = out[:idx] + script + "\n" + out[idx:]
    elif "<body" in lower:
        idx = lower.index("<body")
        out = out[:idx] + script + "\n" + out[idx:]
    else:
        out = script + "\n" + out
    return out


# ==================== 表格数据注入（数据不经模型转写）====================

def inject_table(html_code: str, table: dict) -> str:
    """把真实表格数据以 window.UV_DATA 注入页面（幂等），模型输出里不再有逐行数据"""
    if 'id="uv-data-injected"' in html_code:
        return html_code
    payload = json.dumps(table, ensure_ascii=False).replace("</", "<\\/")
    script = f'<script id="uv-data-injected">window.UV_DATA = {payload};</script>'
    lower = html_code.lower()
    if "</head>" in lower:
        idx = lower.index("</head>")
        return html_code[:idx] + script + "\n" + html_code[idx:]
    if "<body" in lower:
        idx = lower.index("<body")
        return html_code[:idx] + script + "\n" + html_code[idx:]
    return script + "\n" + html_code


# ==================== 可见性自愈（防「内容永久隐形」）====================
# 真实故障：模型用了 .reveal{opacity:0} 却没写出 IntersectionObserver（输出被截断），
# 于是 Hero 之外的所有卡片永远停在 opacity:0，用户看到的就是「只有标题，下面一片空白」。
# 这段脚本自己补一个观察器：内容进入视口 700ms 仍不可见就强制点亮，并额外做首屏与打印兜底。
_REVEAL_GUARD = """
<style id="uv-guard-style">
@media print{.reveal{opacity:1!important;transform:none!important;visibility:visible!important}}
</style>
<script id="uv-reveal-guard">
(function(){
  if(window.__uvRevealGuard) return; window.__uvRevealGuard=1;
  var show=function(el){ if(el&&el.classList){ el.classList.add('visible'); el.style.opacity='1'; el.style.transform='none'; } };
  function scan(){
    var els=document.querySelectorAll('.reveal');
    if(!els.length) return;
    var vh=window.innerHeight||document.documentElement.clientHeight;
    for(var i=0;i<els.length;i++){
      var el=els[i];
      if(el.classList.contains('visible')) continue;
      var r=el.getBoundingClientRect();
      var entered = r.top < vh*1.05 && r.bottom > -40;   // 已进入（或部分进入）视口
      if(entered){
        if(!el.__uvT){ el.__uvT=setTimeout(function(){ if(!el.classList.contains('visible')) show(el); },700); }
      }else if(el.__uvT){ clearTimeout(el.__uvT); el.__uvT=null; }
    }
  }
  var ticking=false;
  function onScroll(){ if(ticking) return; ticking=true; requestAnimationFrame(function(){ ticking=false; scan(); }); }
  // 运行时报错兜底：任何脚本异常都不允许页面静默空白——立即点亮全部内容并给出可见提示
  window.addEventListener('error',function(e){
    try{
      var els=document.querySelectorAll('.reveal');
      for(var i=0;i<els.length;i++) show(els[i]);
      if(!document.getElementById('uv-err-tip')){
        var t=document.createElement('div'); t.id='uv-err-tip';
        t.style.cssText='position:fixed;left:50%;bottom:24px;transform:translateX(-50%);z-index:99998;'+
          'max-width:86vw;padding:10px 18px;border-radius:10px;background:rgba(153,27,27,.94);color:#fff;'+
          'font:13px/1.6 PingFang SC,Microsoft YaHei,sans-serif;box-shadow:0 8px 24px rgba(0,0,0,.25)';
        t.textContent='页面部分脚本运行出错，图表可能未完全展示（'+(e&&e.message?String(e.message).slice(0,120):'未知错误')+'）';
        document.body&&document.body.appendChild(t);
        setTimeout(function(){ t.parentNode&&t.parentNode.removeChild(t); },8000);
      }
    }catch(_){}
  });
  function boot(){
    scan();
    window.addEventListener('scroll',onScroll,{passive:true});
    window.addEventListener('resize',onScroll,{passive:true});
    // 全量兜底：2.6s 后一个都没点亮，说明页面自身的观察器没生效，直接全部显示
    setTimeout(function(){
      var els=document.querySelectorAll('.reveal');
      if(els.length && !document.querySelectorAll('.reveal.visible').length){
        for(var i=0;i<els.length;i++) show(els[i]);
      }
    },2600);
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot);
  else boot();
})();
</script>
"""


def inject_guard(html_code: str) -> str:
    """注入可见性自愈脚本（幂等）"""
    if "uv-reveal-guard" in html_code or ".reveal" not in html_code:
        return html_code
    if "</body>" in html_code:
        return html_code.replace("</body>", _REVEAL_GUARD + "</body>", 1)
    return html_code + _REVEAL_GUARD


# ==================== PDF 导出组件（确定性注入，不依赖 LLM）====================

_EXPORT_SNIPPET = """
<style>
#uv-pdf-fab{position:fixed;right:22px;bottom:26px;z-index:99999;display:flex;align-items:center;gap:8px;
  padding:11px 20px;border:0;border-radius:999px;cursor:pointer;font-size:14px;font-weight:600;
  font-family:'PingFang SC','Microsoft YaHei',sans-serif;color:#fff;
  background:linear-gradient(135deg,#4f6ef7,#8b5cf6);box-shadow:0 6px 22px rgba(79,110,247,.45);
  transition:transform .22s,box-shadow .22s}
#uv-pdf-fab:hover{transform:translateY(-3px);box-shadow:0 10px 30px rgba(79,110,247,.55)}
#uv-pdf-fab:active{transform:translateY(0)}
#uv-pdf-tip{position:fixed;left:50%;top:26px;transform:translateX(-50%) translateY(-80px);z-index:99999;
  padding:10px 22px;border-radius:10px;background:rgba(17,24,39,.92);color:#fff;font-size:13px;
  font-family:'PingFang SC','Microsoft YaHei',sans-serif;transition:transform .35s cubic-bezier(.22,.61,.36,1)}
#uv-pdf-tip.show{transform:translateX(-50%) translateY(0)}
@media print{
  #uv-pdf-fab,#uv-pdf-tip{display:none!important}
  *{-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important}
  section,.card,[class*=card]{page-break-inside:avoid;break-inside:avoid}
  thead{display:table-header-group}
  tr{page-break-inside:avoid}
  body{width:100%!important;max-width:100%!important;margin:0!important}
}
</style>
<button id="uv-pdf-fab" data-no-print class="no-print" onclick="window.__uvExportPdf&&window.__uvExportPdf()">
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"
    stroke-linecap="round" stroke-linejoin="round"><path d="M6 9V2h12v7"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/></svg>
  导出 PDF
</button>
<div id="uv-pdf-tip">正在调起打印…在弹窗中选择「另存为 PDF」即可导出</div>
<script>
window.__uvExportPdf=function(){
  var t=document.getElementById('uv-pdf-tip');t&&t.classList.add('show');
  setTimeout(function(){window.print();setTimeout(function(){t&&t.classList.remove('show')},800)},160);
};
</script>
"""


def inject_export(html_code: str) -> str:
    """把可见性自愈 + PDF 导出悬浮按钮注入生成页（幂等）

    兜底放在这里而非只在生成时注入，是为了让「历史上已生成的坏记录」在预览时也能恢复显示。
    """
    out = inject_guard(html_code)
    if "uv-pdf-fab" in out:
        return out
    if "</body>" in out:
        return out.replace("</body>", _EXPORT_SNIPPET + "</body>", 1)
    return out + _EXPORT_SNIPPET
