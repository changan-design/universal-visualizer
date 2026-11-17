# 万能可视化工具（Universal Visualizer）

一站式文档处理与 AI 可视化工作台：解析 Word / PPT / PDF / TXT / Markdown / CSV / Excel / JSON / HTML / **图片（OCR）** 等文件，调用 **Agnes 大模型**完成内容总结与分类，智能选型视觉主题并生成高质感可视化 HTML 页面；另含**简历转化**（AI 专业化改写 + 可视化/ATS 双模式）、**布局感知格式转换**、滚动驱动的**海洋进入页**与玻璃拟态**质感界面**。

## ✨ 核心特性

- **文件解析与可视化**：图片 OCR（长图切片合并 / 低清图增强）、真实生成进度条、PDF 导出、公开分享链接、大文件模式（17 万+ 行全量扫描聚合，LLM 只出框架、数据运行时注入）
- **简历转化**：口语化经历长文 → AI 专业化改写（量化成果 + ATS 关键词 + 行业知识，只重组不虚构）→ 可视化简历（单强调色专业版式，支持**头像上传**：点击/拖拽、自动压缩、Word 嵌入照片）或 ATS 机器友好版；一键保存/填入个人资料；导出 HTML / Word / PDF
- **格式转换引擎 v3（布局感知 · 无字体依赖）**：PDF→Word 保留**标题层级 / 真实表格 / 图片 / 粗斜体**（PyMuPDF span 级解析）；DOCX→PDF、PPTX→PDF、MD→PDF、表格→PDF 统一走 **PyMuPDF HTML 排版管线**，内置 CJK 字体，Windows / macOS / Linux / 容器内行为一致（不再出现 `Undefined font` / `UnicodeEncodeError` 导致的转换失败），并对 PDF 做字体子集化（体积 3.5MB → ~30KB）
- **首页进入页**：滚动驱动「黄昏海面 → 穿透水面 → 深海」三段式 Canvas 动画，完全由滚动控制、可倒滚回放，尊重 prefers-reduced-motion
- **界面质感**：玻璃拟态面板 + 颗粒纹理 + 极光渐变背景 + 炫彩粒子/漂浮几何体层，焦点环与键盘可达性
- **14 个功能面板**：文件上传、批量处理、格式转换、模板主题、摘要分类、图表洞察、**简历转化**、历史、收藏、回收站、导出分享、模型接入、案例、系统设置

## 一、技术栈

| 层 | 选型 |
|---|---|
| 后端 | Python 3.9+ · FastAPI · SQLite（零部署） |
| 前端 | Vue 3 · Element Plus · Vite |
| 图表 | ECharts 5（本地 `/vendor/echarts.min.js` 优先，CDN 兜底） |
| 大模型 | Agnes AI（OpenAI 兼容协议，`config.py` 已内置 Key，可自行更换） |
| 文档引擎 | python-docx / python-pptx / pdfplumber / openpyxl / xlrd / PyMuPDF（PDF 排版与解析）/ fpdf2 |

> 模型档位说明：免费密钥仅可用 flash 系列（`agnes-2.5-flash` / `agnes-3.0-flash`）；pro 档为付费。JSON 类输出内置「解析失败自动降温重试」。

## 二、目录结构

```
universal-visualizer/
├── start.bat                    # 一键启动（Windows，自动建环境装依赖）
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口（CORS / 路由 / 静态托管）
│   │   ├── config.py            # Agnes 接入参数 / 上传限制 / 路径
│   │   ├── services/
│   │   │   ├── parser.py        # 多格式真实解析引擎
│   │   │   ├── llm.py           # LLM 统一接入层（网络抖动自动重试）
│   │   │   ├── generator.py     # HTML 智能选型生成 / 摘要 / 洞察
│   │   │   ├── convert.py       # 格式转换引擎 v3（布局感知 + PyMuPDF HTML 排版）
│   │   │   ├── tabular.py       # 表格统一读取层（csv / xlsx / xls）
│   │   │   ├── resume.py        # 简历改写 / 可视化 / ATS / Word 导出
│   │   │   └── store.py         # SQLite 数据层
│   │   └── routers/
│   │       ├── files.py         # 上传/生成/摘要/洞察/转换/预览
│   │       ├── records.py       # 历史/收藏/回收站/导出/公开分享
│   │       ├── models_router.py # 模型接入管理
│   │       ├── resume.py        # 简历接口（资料/改写/生成/导出）
│   │       └── settings.py      # 系统设置 / 内置案例
│   ├── requirements.txt
│   └── start.sh                 # 单端口部署启动脚本（读 $PORT）
└── frontend/
    ├── src/
    │   ├── App.vue              # 三栏布局 + 导航 + 全局状态
    │   ├── api.js               # 全部接口封装
    │   ├── styles.css           # 设计令牌 + 玻璃拟态 + 颗粒纹理
    │   └── components/
    │       ├── LandingPage.vue  # 首页海洋进入页（滚动驱动动画）
    │       ├── ParticleField.vue# 背景粒子/柔光球/几何体
    │       └── modules/         # 14 个功能面板（含 ResumePanel.vue 简历转化）
    └── package.json
```

## 三、启动说明

### 方式 A：一键启动（Windows 推荐）

1. 安装 [Python 3.9+](https://python.org)（勾选 Add to PATH）与 [Node.js 18+](https://nodejs.org)
2. 双击根目录 **`start.bat`** —— 首次运行自动创建虚拟环境、安装前后端依赖，然后启动服务并打开浏览器

### 方式 B：手动启动

```bash
# 后端（端口 8000）
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows（macOS/Linux: source .venv/bin/activate）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
uvicorn app.main:app --host 127.0.0.1 --port 8000

# 前端（端口 5173，新开一个终端）
cd frontend
npm install                     # 项目已内置 .npmrc（国内镜像源），无需额外配置
npm run dev
```

打开 **http://localhost:5173** 即可使用；接口文档 http://localhost:8000/docs 。
前端端口/后端地址可用环境变量覆盖：`UV_PORT`（前端端口）、`UV_BACKEND`（后端地址，如 `http://localhost:9000`）。

### GitHub Pages 静态部署

仓库内置 `.github/workflows/deploy-pages.yml`：推送 `main` 后自动构建 `frontend/` 并发布到 GitHub Pages。静态站点仅包含前端；如需调用 AI/文件解析接口，请在仓库 Variables 中配置 `VITE_API_BASE` 指向已部署的后端地址（例如 `https://your-backend.example.com`），否则页面可打开但接口不可用。

### 方式 C：单端口部署（服务器/托管场景）

```bash
cd frontend && npm install && npm run build
# 将 frontend/dist 内容拷贝到 backend/static/，之后后端单进程同时供页与供接口
cd ../backend && pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
# 托管平台：PORT 由环境注入，直接执行 ./start.sh（内部读 $PORT）
```

后端检测到 `backend/static/index.html` 存在时自动切换为单端口模式（首页、静态资源、`/api` 同端口）。

### 快速体验

1. 进入页滚动到底，点「进入工作台」
2. 左侧「案例查看」→ 载入「季度经营分析报告」→ 生成可视化
3. 「简历转化」→ 粘贴口语化经历 → AI 改写 → 生成可视化简历 → 导出 HTML/Word/PDF
4. 「格式转换」→ 上传 PDF 转 Word，验证标题/表格/图片还原

## 四、主要接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/upload` · `/api/parse-text` | 上传解析 / 在线文本输入 |
| POST | `/api/generate` | 核心：生成可视化 HTML + 自动摘要分类 |
| POST | `/api/summarize` · `/api/insight` | 摘要分类 / 图表洞察 |
| POST | `/api/convert` · `GET /api/convert/targets` | 格式转换（multipart，布局感知 v3）/ 查询某格式支持的目标 |
| GET | `/api/preview/{id}` | 生成页预览 |
| GET/POST | `/api/history` · `/api/trash` · `/api/records/*` | 历史 / 回收站 / 收藏恢复分享导出 |
| POST | `/api/resume/optimize` | 简历经历 AI 专业化改写 |
| POST | `/api/resume/generate` | 简历生成（`visual` 开关：可视化 / ATS） |
| GET/POST | `/api/resume/profile` | 个人资料存取（含头像） |
| GET | `/api/resume/records/{id}/export/docx` | 简历 Word 导出（嵌入头像） |
| GET/POST/DELETE | `/api/models*` · `/api/settings` · `/api/cases` | 模型管理 / 设置 / 内置案例 |

## 五、实现要点

- **简历 AI 改写**：结合行业/岗位知识重组经历，强动词 + 量化成果（无精确数据用"约/超过"估算，禁止编造）+ 12~18 个 ATS 关键词；AI 味套话自动清除。
- **头像链路**：前端 Canvas 压缩至 512px/JPEG 85% 后随 `basics.avatar`（data URL）持久化；可视化生成用 `__AVATAR__` 占位符（base64 不占 LLM 上下文，生成后回填）；Word 导出由 python-docx 直接嵌图；ATS 版按招聘行业调研保持无照片。
- **PDF→Word 布局还原**：span 级字号中位数定正文基准 → 偏大自动映射 Heading 层级；`find_tables` 重建真实表格（表头加粗）；图像区域 `get_pixmap` 裁剪回嵌；保留原分页。
- **任意格式→PDF**：统一把文档转成语义 HTML（标题/列表/引用/表格/图片/粗斜体），交给 PyMuPDF `Story` 流式排版分页，**不依赖系统安装中文字体**；输出前做字体子集化与压缩。
- **格式转换支持矩阵**：Word→PDF/TXT/Excel/CSV；PDF→Word/TXT/Excel/CSV；PPT→PDF/Word/TXT/Excel；Markdown/TXT/JSON/HTML→PDF/Word/TXT；Excel/CSV→PDF/Word/互转/TXT。前端按源格式动态给出按钮，后端二次校验，不支持的组合返回明确中文原因。
- **大文件模式**：xlsx/csv ≥1000 行全量流式扫描聚合落盘，LLM 只生成页面框架，明细走分页 API，杜绝大模型手写海量数据导致的编造（注入脚本含幂等标记，避免 `__REC_ID__` 占位符被二次替换破坏）。
- **表格数据注入协议（UV_DATA）**：中小表格（<1000 行）同样不让模型转写数据——后端 `tabledata.py` 读全量行 + 逐列画像（类型/去重 Top/数值 min-max-avg），落盘后以 `window.UV_DATA` 注入页面；模型只写「读 UV_DATA 现算」的图表与明细表逻辑。历史故障：55 行数据被要求逐行写进 HTML，输出触顶 max_tokens 从 `<script>` 中间截断，图表初始化整段丢失，页面只剩标题。
- **生成页三道质量闸（`generator._finalize_html`）**：① 结构完整性——缺 `</html>`/`<script>` 未闭合自动续写（最多 4 轮，无进展提前终止）；② 内联脚本语法——`node --check` 逐段校验（无 node 环境自动跳过），报错定点让模型只重写出错的那段脚本；③ 渲染有效性——图表容器无 `echarts.init`/`setOption`、`.reveal` 隐形缺 IntersectionObserver、脚本引用不存在的元素 id（运行时 null 崩溃）都会被拦截修复。另有页面内自愈脚本：任何 JS 异常都强制点亮 `.reveal` 内容并给出可见提示，杜绝「只有标题没有内容」的静默白屏。
- **简历模块输入兼容**：ATS 渲染与 Word 导出对 `work/education/projects/skills` 同时接受结构化 dict 与纯字符串两种形态（解析结果与手填数据形态不一，原先字符串会直接 500）。
- **无表格文档转表格格式降级**：docx/pptx 无表格时转 Excel/CSV 不再报错，降级为「每段/每个文本框一行」。
- **图表库兜底**：生成页原引用 jsdelivr CDN，国内网络下易长时间转圈导致「页面出来了但图表空白」；`llm.ensure_echarts()` 统一改写为**本地 `/vendor/echarts.min.js` 优先 + 同源失败时 document.write 回退 CDN**，兼顾线上访问与导出后本地打开两种场景（幂等，重复调用不重复注入）。
- **Word 版式保真**：转换不是「抽文字重排」，而是还原源文档的视觉结构——① 表格单元格逐段保留 run 级字号/颜色/加粗与内嵌图片（原来压平成纯文本，导致姓名缩成正文大小、头像直接丢失）；② 按 `w:tblBorders` 与表格样式判断是否真带边框，只给数据表画线，简历头部这类**分栏排版表不再出现方框**；③ 图片按 `wp:extent`（EMU→pt）还原显示尺寸并按栏宽收敛，避免 `max-width:100%` 对图片不生效导致放大溢出；④ 无 Heading 样式的加粗短行（如「个人简介」）按字号与加粗推断层级，生成带淡分隔线的章节标题；⑤ 版式表格中纯图片列按图片实际宽度定宽、文字列自适应，避免「数据采/集」这类断字换行。
- **Word 列表还原**：连续同类列表段落合并为单个 `<ol>/<ul>`（否则每段独立成表会让有序列表逐条从 1 重新编号），并剥离正文自带的手动序号避免与自动编号重复；`Title` 与 `Heading N` 分层映射，保证文档大标题与章节标题字号有别。
- **防 token 溢出**：原文按 `MAX_CONTEXT_CHARS`（14000 字）截断送模型。
- **软删除**：删除先进回收站，可恢复或彻底删除（联动清理生成文件）。
- **公开分享**：`/share/{share_id}` 无鉴权路由，拿到链接即可访问。
