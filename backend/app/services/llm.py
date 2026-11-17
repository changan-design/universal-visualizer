"""LLM 接入层：默认 Agnes（OpenAI 兼容），支持用户自定义模型（base_url + api_key）

健壮性约定：
- 网络抖动 / 429 / 5xx 自动重试（指数退避），避免 AI 网关偶发 502 直接打断整条生成链路；
- 模型偶发返回空内容（推理模型把 token 全用在 reasoning 上）时，给出可读错误并重试一次；
- 所有异常统一收敛为 LLMError，路由层只需处理一种异常类型。
"""
import asyncio
import re
import shutil
import subprocess
import tempfile
import os

import httpx

from .. import config
from . import store


class LLMError(Exception):
    pass


RETRY_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


def _resolve(model_id: str | None):
    """按 model_id 解析出 (base_url, api_key, model_name)"""
    if not model_id or model_id in ("agnes-default", "agnes"):
        return config.AGNES_BASE_URL, config.AGNES_API_KEY, config.AGNES_DEFAULT_MODEL
    rows = store.query("SELECT * FROM models WHERE id=?", (model_id,))
    if not rows:
        raise LLMError(f"模型不存在: {model_id}")
    m = rows[0]
    return m["base_url"], m["api_key"], m["name"]


async def chat(messages: list, model_id: str | None = None, temperature: float = 0.7,
               max_tokens: int = 8000, timeout: float = 300, retries: int = 3) -> str:
    base_url, api_key, model = _resolve(model_id)
    payload = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    url = base_url.rstrip("/") + "/chat/completions"

    last_err = ""
    for attempt in range(max(1, retries)):
        if attempt:
            await asyncio.sleep(min(8, 1.6 * attempt))       # 退避：1.6s / 3.2s
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, json=payload, headers=headers)
        except (httpx.TransportError, httpx.TimeoutException) as e:
            last_err = f"网络异常: {type(e).__name__}: {e}"
            continue
        if resp.status_code != 200:
            snippet = resp.text[:300]
            last_err = f"模型调用失败 HTTP {resp.status_code}: {snippet}"
            if resp.status_code in RETRY_STATUS:
                continue
            raise LLMError(last_err)
        try:
            data = resp.json()
            choice = data["choices"][0]
            content = (choice["message"].get("content") or "").strip()
        except (KeyError, IndexError, ValueError):
            last_err = f"模型响应格式异常: {resp.text[:300]}"
            continue
        if not content:
            # 推理模型 max_tokens 过小时 content 可能为空（全部消耗在 reasoning 上）
            finish = (data["choices"][0].get("finish_reason") or "unknown")
            last_err = f"模型返回空内容（finish_reason={finish}），可能是输出长度不足，请重试或调大 max_tokens"
            continue
        return content
    raise LLMError(last_err or "模型调用失败")


async def list_remote_models(base_url: str, api_key: str) -> list:
    """拉取自定义服务端的可用模型列表"""
    headers = {"Authorization": f"Bearer {api_key}"}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(base_url.rstrip("/") + "/models", headers=headers)
        if resp.status_code != 200:
            raise LLMError(f"获取模型列表失败 HTTP {resp.status_code}")
        data = resp.json()
    return [m.get("id") for m in data.get("data", [])]


ECHARTS_LOCAL = "/vendor/echarts.min.js"
ECHARTS_CDN = "https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"


def ensure_echarts(html: str) -> str:
    """把生成页里的 ECharts 外链改成本地优先、CDN 兜底。

    模型默认写 jsdelivr 外链，国内网络下经常长时间转圈甚至加载失败，
    表现为「页面出来了但图表空白」。本地同源文件秒开；把 HTML 导出后
    用浏览器直接打开时（file:// 下本地路径取不到），再回退到 CDN。
    """
    import re

    if "echarts" not in (html or "").lower() or ECHARTS_LOCAL in (html or ""):
        return html
    fallback = ('<script>if(!window.echarts){document.write('
                "'<script src=\"" + ECHARTS_CDN + "\"><\\/script>')}</script>")
    tag = f'<script src="{ECHARTS_LOCAL}"></script>' + fallback
    m = re.search(r'<script[^>]*\bsrc\s*=\s*["\'][^"\']*echarts[^"\']*["\'][^>]*>\s*</script>', html, re.I)
    if m:
        return html[:m.start()] + tag + html[m.end():]
    if "</head>" in html:
        return html.replace("</head>", tag + "</head>", 1)
    return tag + html


def extract_html(text: str) -> str:
    """从 LLM 输出中提取完整 HTML 代码（不做完整性判定，交给 html_issues）"""
    t = text.strip()
    if "```" in t:
        # 优先取 ```html 代码块
        import re
        blocks = re.findall(r"```(?:html)?\s*\n?([\s\S]*?)```", t)
        for b in blocks:
            if "<html" in b.lower() or "<!doctype" in b.lower():
                return ensure_echarts(b.strip())
        if blocks and "<body" in blocks[0].lower():
            return ensure_echarts(blocks[0].strip())
    if "<html" in t.lower() or "<!doctype" in t.lower():
        return ensure_echarts(t)
    raise LLMError("模型未返回有效的 HTML 内容")


def html_issues(html: str) -> list[str]:
    """检查 HTML 是否输出完整。

    真实故障：55 行表格让模型把数据逐行转写成 JS 数组，输出触达 max_tokens 上限，
    HTML 从 <script> 的 const rawData 中间被切断 —— 结尾没有 </body></html>，
    图表初始化和滚动显现脚本整段丢失，页面只剩 Hero 标题。必须在落盘前拦住。
    """
    if not html or not html.strip():
        return ["内容为空"]
    low = html.lower()
    issues = []
    if "</html>" not in low:
        issues.append("缺少 </html>（输出被截断）")
    if "<body" in low and "</body>" not in low:
        issues.append("缺少 </body>（输出被截断）")
    if low.count("<script") != low.count("</script>"):
        issues.append(f"<script> 未闭合（{low.count('<script')} 开 / {low.count('</script>')} 闭）")
    if low.count("<style") != low.count("</style>"):
        issues.append(f"<style> 未闭合（{low.count('<style')} 开 / {low.count('</style>')} 闭）")
    return issues


CONTINUE_PROMPT = (
    "你上一条输出因长度限制被截断了，HTML 没有写完。"
    "请**紧接着断点继续输出剩余内容**：不要重复已经输出过的任何部分，"
    "不要重新开始，不要解释，不要 markdown 代码围栏，一直写到 </html> 为止。"
)


async def continue_html(messages: list, partial: str, model_id: str | None = None,
                        temperature: float = 0.5, max_tokens: int = 16000) -> str:
    """请求模型从断点续写，并拼接成完整 HTML（自动去重、去围栏）"""
    frag = partial.strip()[-200:]
    msgs = list(messages) + [
        {"role": "assistant", "content": partial},
        {"role": "user", "content": CONTINUE_PROMPT + f"\n已输出内容的结尾是：`...{frag}`\n请严格从该结尾的下一个字符继续。"},
    ]
    tail = await chat(msgs, model_id=model_id, temperature=temperature, max_tokens=max_tokens)
    # 续写常带 ``` 围栏，剥掉
    tail = re.sub(r"^\s*```(?:html)?\s*", "", tail.strip())
    tail = re.sub(r"```\s*$", "", tail).strip()
    # 去掉模型偶尔重复输出的开头（<!DOCTYPE / <html）。
    # 若模型无视指令从头重写且写得更短（重写又被截断），采用它只会丢失已有进度，保持原样视为无进展
    if re.match(r"^\s*<(!doctype|html)", tail, re.I):
        return tail.strip() if len(tail) > len(partial) else partial
    return partial + "\n" + tail


FIX_SCRIPT_PROMPT = (
    "上面的 <script> 存在 JavaScript 语法错误，页面因此完全无法渲染（图表和表格全部空白）。"
    "请输出**修正后的完整脚本**：只输出 JS 代码本身，不要 <script> 标签，不要解释，不要 markdown 围栏。"
    "除修复语法错误外，不要改动任何其它逻辑、变量名或输出结构。"
)


def inline_scripts(html: str) -> list[str]:
    """提取全部内联 <script> 内容（不含外链）"""
    return re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S | re.I)


def js_syntax_error(html: str) -> str | None:
    """用 node --check 对内联脚本做语法校验，返回首个错误描述；无 node 环境则跳过返回 None。

    真实故障：模型把 series data 写成 return{x:value:x.maxBid}（应为 {value:...}），
    运行时抛 SyntaxError，异常点之后的表格渲染整段不执行 —— 页面「只有标题没有内容」。
    这类错误在服务端拦不住（无法正则判断），但只要宿主机有 node 就能精准检出。
    """
    node = shutil.which("node")
    if not node:
        return None
    for i, s in enumerate(inline_scripts(html)):
        if not s.strip():
            continue
        fd, path = tempfile.mkstemp(suffix=".js")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(s)
            r = subprocess.run([node, "--check", path], capture_output=True, text=True, timeout=30)
            if r.returncode != 0:
                keep = []
                for x in (r.stderr or "").strip().splitlines():
                    x = " ".join(x.split())
                    if not x or set(x) <= {"^"} or x.startswith("at "):
                        continue
                    keep.append(x.split("\\")[-1].split("/")[-1])  # 去掉临时目录路径
                return f"第 {i + 1} 个内联脚本语法错误: {' | '.join(keep)[-400:]}"
        except Exception:
            continue  # 校验器自身异常不阻断主流程
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
    return None


async def fix_script(messages: list, html: str, error: str, model_id: str | None = None,
                     temperature: float = 0.3) -> str:
    """针对语法错误的定点修复：只重写出错的那个脚本块，其余 HTML 原样保留"""
    scripts = inline_scripts(html)
    m = re.search(r"第 (\d+) 个内联脚本", error)
    idx = int(m.group(1)) - 1 if m else len(scripts) - 1  # 缺省取最后一个（通常是主脚本）
    if not 0 <= idx < len(scripts):
        return html
    pattern = re.compile(
        r"(<script(?![^>]*\bsrc=)[^>]*>)(.*?)(</script>)", re.S | re.I)
    blocks = list(pattern.finditer(html))
    if idx >= len(blocks):
        return html
    blk = blocks[idx]
    msgs = list(messages) + [
        {"role": "assistant", "content": "以下是页面脚本：\n```js\n" + blk.group(2) + "\n```"},
        {"role": "user", "content": f"node --check 报错：\n{error}\n\n" + FIX_SCRIPT_PROMPT},
    ]
    fixed = await chat(msgs, model_id=model_id, temperature=temperature, max_tokens=16000)
    fixed = re.sub(r"^\s*```(?:js|javascript)?\s*", "", fixed.strip())
    fixed = re.sub(r"```\s*$", "", fixed).strip()
    fixed = re.sub(r"^\s*</?script[^>]*>", "", fixed).strip()
    if not fixed or "function" not in fixed and "=" not in fixed:
        return html  # 模型没给出有效脚本，保持原样（交由外层重试/报错）
    return html[:blk.start(2)] + fixed + html[blk.end(2):]
