"""文件与生成相关接口：上传解析 / 在线输入 / HTML 生成（任务制+进度） / 摘要分类 / 图表洞察"""
import uuid, json, time, asyncio
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from .. import config
from ..services import parser, generator, store, llm, ocr

router = APIRouter(prefix="/api", tags=["files"])

# ---- 生成任务进度存储（内存态，进程重启即清空，仅用于进行中的任务）----
_jobs: dict[str, dict] = {}
MAX_JOBS_KEEP = 60


def _job_update(job_id: str, **kw):
    job = _jobs.get(job_id)
    if job:
        job.update(kw)
        job["elapsed"] = round(time.time() - job["started"], 1)


_TRUNCATE_HINT = ("\n\n【重试强制要求】上一次输出超长被截断，本次必须大幅精简：总输出严格控制在 6000 字符内——"
                  "CSS 压缩书写且不超过 100 行、图表最多 3 个、指标卡最多 4 个、明细表只写渲染逻辑不写任何数据。"
                  "宁可少装饰，也必须完整闭合 </body></html>。")

async def _gen_with_retry(job_id, fn, **kw):
    """生成任务级重试：模型输出波动导致「超长截断」/「偶发空响应」是非确定性的，
    单次成功率约 2/3，独立重试后综合成功率 >95%。其它确定性错误不重试。
    第 2 次起在请求中附加压缩指令，主动降低输出规模而不是原样重掷。"""
    extra = kw.get("extra_req") or ""
    retriable = ("不完整", "未返回有效")
    for attempt in range(4):
        try:
            return await fn(**kw)
        except llm.LLMError as e:
            if attempt >= 3 or not any(k in str(e) for k in retriable):
                raise
            if "extra_req" in kw:
                kw["extra_req"] = extra + _TRUNCATE_HINT
            _job_update(job_id, percent=12,
                        message=f"模型输出异常（{str(e)[:24]}…），已自动重试（第 {attempt + 1}/3 次）…")


async def _run_generate_job(job_id: str, fid: str, theme: str, model_id: str | None,
                            extra_req: str, cached: dict):
    """后台执行生成全流程，阶段化更新进度（前端轮询 /api/generate/progress/{job_id}）"""
    sum_task = None
    try:
        _job_update(job_id, stage="prepare", percent=4, message="校验数据与解析缓存…")
        from ..services import bigdata, tabledata
        stats = bigdata.get_stats(fid)
        is_big = bool(stats)
        # 生成阶段占 10%~86%（LLM 生成耗时波动大，前端按时间平滑插值展示）
        _job_update(job_id, stage="design", percent=10,
                    message="AI 正在智能选型并设计页面（视觉框架 + 图表规划，约 2~4 分钟）…")
        if is_big:
            gen = await _gen_with_retry(
                job_id, generator.generate_html_bigdata,
                doc_text=cached["text"], meta=cached["meta"], stats=stats,
                theme=theme, model_id=model_id, extra_req=extra_req)
            _job_update(job_id, stage="render", percent=88, message="页面代码已生成，注入数据与导出组件…")
            rec_id = uuid.uuid4().hex[:12]
            html_code = generator.inject_bigdata(gen["html_code"], rec_id, stats)
            html_code = generator.inject_export(html_code)
            html_path = config.GENERATED_DIR / f"{rec_id}.html"
            html_path.write_text(html_code, encoding="utf-8")
            result = {"id": rec_id, "html_code": html_code, "html_path": str(html_path)}
            summary_data = {}
        else:
            # 提速关键点：HTML 生成与摘要分类并行（原先串行，节省 30~60 秒）
            auto_summary = store.get_setting("auto_summary", True)
            if auto_summary is not False:
                sum_task = asyncio.create_task(generator.summarize(cached["text"][:6000], model_id))
            result = await _gen_with_retry(
                job_id, generator.generate_html,
                doc_text=cached["text"], meta=cached["meta"], theme=theme,
                model_id=model_id, extra_req=extra_req,
                table=tabledata.get(fid))
            _job_update(job_id, stage="render", percent=88, message="页面代码已生成，注入数据与导出组件…")
            result["html_code"] = generator.inject_export(result["html_code"])
            config.GENERATED_DIR.joinpath(f"{result['id']}.html").write_text(result["html_code"], encoding="utf-8")
            try:
                summary_data = (await sum_task) if sum_task else {}
            except Exception:
                summary_data = {}       # 摘要失败不影响主结果，标题回退为文件名
        _job_update(job_id, stage="save", percent=94, message="保存页面与写入历史记录…")
        rec = {
            "id": result["id"], "title": summary_data.get("title") or cached["meta"].get("file_name", "未命名"),
            "file_name": cached["meta"].get("file_name", ""), "source_type": cached["meta"].get("ext", "txt"),
            "summary": summary_data.get("summary", ""), "category": summary_data.get("category", "未分类"),
            "tags": json.dumps(summary_data.get("tags", []), ensure_ascii=False),
            "html_path": result["html_path"], "html_code": result["html_code"],
            "theme": theme, "model": model_id or "agnes-default", "file_id": fid,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        store.execute(
            "INSERT INTO records(id,title,file_name,source_type,summary,category,tags,html_path,html_code,theme,model,file_id,status,created_at) "
            "VALUES(:id,:title,:file_name,:source_type,:summary,:category,:tags,:html_path,:html_code,:theme,:model,:file_id,'active',:created_at)", rec)
        payload = {"id": rec["id"], "title": rec["title"], "summary": rec["summary"],
                   "category": rec["category"], "tags": summary_data.get("tags", []),
                   "suggested_theme": summary_data.get("suggested_theme", ""),
                   "html_code": result["html_code"], "preview_url": f"/api/preview/{result['id']}"}
        _job_update(job_id, stage="done", percent=100, status="done",
                    message="生成完成", result=payload)
    except llm.LLMError as e:
        _job_update(job_id, stage="error", percent=100, status="failed", message=str(e), error=str(e))
    except Exception as e:
        _job_update(job_id, stage="error", percent=100, status="failed",
                    message=f"生成失败: {e}", error=f"生成失败: {e}")
    finally:
        if sum_task is not None and not sum_task.done():
            sum_task.cancel()               # 生成失败时取消并行的摘要任务，避免悬挂异常
        # 清理过早的历史任务，防止内存膨胀
        if len(_jobs) > MAX_JOBS_KEEP:
            done_ids = [k for k, v in _jobs.items() if v.get("status") in ("done", "failed")][:-20]
            for k in done_ids:
                _jobs.pop(k, None)

# 内存中缓存已解析原文（file_id -> {text, meta}），同时落盘 data/cache/{id}.json
CACHE_DIR = config.DATA_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _cache_put(fid, text, meta):
    (CACHE_DIR / f"{fid}.json").write_text(
        json.dumps({"text": text, "meta": meta}, ensure_ascii=False), encoding="utf-8")

def _cache_get(fid):
    f = CACHE_DIR / f"{fid}.json"
    if not f.exists():
        return None
    return json.loads(f.read_text(encoding="utf-8"))

@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    """上传并解析文件，返回 file_id + 原文"""
    filename = file.filename or "upload"
    ext = Path(filename).suffix.lower()
    if ext not in config.ALLOWED_EXTS:
        raise HTTPException(400, f"不支持的文件格式: {ext}（支持 {'/'.join(sorted(config.ALLOWED_EXTS))}）")
    content = await file.read()
    if not content:
        raise HTTPException(400, "文件内容为空")
    if len(content) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(400, f"文件超过 {config.MAX_UPLOAD_MB}MB 限制")
    save_path = config.UPLOAD_DIR / f"{uuid.uuid4().hex[:8]}_{Path(filename).name}"
    save_path.write_bytes(content)
    # 图片通道：走 OCR（支持长图切片有序合并、低清自动增强）
    if ext in ocr.IMAGE_EXTS:
        try:
            result = await ocr.ocr_image(str(save_path))
        except llm.LLMError as e:
            raise HTTPException(400, f"OCR 识别失败: {e}")
        except Exception as e:
            raise HTTPException(400, f"图片读取失败: {e}")
        fid = uuid.uuid4().hex[:12]
        _cache_put(fid, result["text"], result["meta"])
        return {"file_id": fid, "text": result["text"], "meta": result["meta"]}
    try:
        result = parser.parse_file(str(save_path))
    except Exception as e:
        raise HTTPException(400, f"解析失败: {e}")
    if not result["text"].strip():
        raise HTTPException(400, "未能从文件中提取到文字内容（可能是扫描件或空文档）")
    fid = uuid.uuid4().hex[:12]
    # 表格类：小表（<阈值）走「数据注入」通道，大表走全量扫描 + 明细分页通道
    if ext in (".xlsx", ".xls", ".csv"):
        from ..services import bigdata, tabular, tabledata
        total_rows = tabular.count_rows(save_path, ext)
        result["meta"]["total_rows"] = total_rows
        if total_rows >= bigdata.BIGDATA_THRESHOLD:
            try:
                stats = bigdata.scan_and_cache(fid, str(save_path))
                result["meta"].update({"bigdata": True, "total": stats["total"],
                                       "stats_preview": {"carriers": stats["carriers"],
                                                         "sources": stats["sources"]}})
            except Exception as e:
                raise HTTPException(400, f"大文件扫描失败: {e}")
        else:
            # 关键改动：逐行数据不再交给模型转写（那会导致输出超长被截断、页面只剩标题），
            # 改为后端结构化注入 window.UV_DATA，模型只写框架与图算逻辑。
            try:
                table = tabledata.prepare(str(save_path), fid)
                result["meta"].update({"table_injected": True, "table_rows": table["total"],
                                       "columns_count": len(table["headers"])})
            except Exception:
                pass        # 结构化失败仍可退回纯文本模式，不阻断上传
    _cache_put(fid, result["text"], result["meta"])
    return {"file_id": fid, "text": result["text"], "meta": result["meta"]}

@router.post("/parse-text")
async def parse_text(text: str = Form(...), title: str = Form("")):
    """在线粘贴文本输入"""
    if not text.strip():
        raise HTTPException(400, "文本内容为空")
    fid = uuid.uuid4().hex[:12]
    meta = {"file_name": title or "在线输入文本", "ext": "txt", "char_count": len(text)}
    _cache_put(fid, text, meta)
    return {"file_id": fid, "text": text, "meta": meta}

@router.get("/cache/{fid}")
async def get_cache(fid: str):
    data = _cache_get(fid)
    if not data:
        raise HTTPException(404, "解析缓存不存在或已过期")
    return data

@router.post("/generate")
async def generate(payload: dict):
    """创建生成任务（立即返回 job_id，前端轮询 /api/generate/progress/{job_id} 获取真实进度）"""
    fid = payload.get("file_id")
    theme = payload.get("theme", "auto")
    model_id = payload.get("model_id")
    extra_req = payload.get("extra_req", "")
    cached = _cache_get(fid)
    if not cached:
        raise HTTPException(404, "file_id 无效，请先上传文件或输入文本")
    job_id = uuid.uuid4().hex[:12]
    _jobs[job_id] = {"stage": "queued", "percent": 0, "message": "任务排队中…",
                     "status": "running", "error": None, "result": None,
                     "started": time.time(), "elapsed": 0}
    asyncio.create_task(_run_generate_job(job_id, fid, theme, model_id, extra_req, cached))
    return {"job_id": job_id}


@router.get("/generate/progress/{job_id}")
async def generate_progress(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "任务不存在或已过期")
    # elapsed 必须在轮询时实时计算：任务执行中途（如 LLM 生成阶段）没有阶段切换，
    # 若读存储值会一直停留在上一阶段切换时的旧值，导致前端进度卡死、计时归零
    return {"stage": job["stage"], "percent": job["percent"], "message": job["message"],
            "status": job["status"], "error": job["error"], "result": job["result"],
            "elapsed": round(time.time() - job["started"], 1)}

@router.post("/summarize")
async def summarize(payload: dict):
    cached = _cache_get(payload.get("file_id", ""))
    if not cached:
        raise HTTPException(404, "file_id 无效")
    try:
        return await generator.summarize(cached["text"], payload.get("model_id"))
    except llm.LLMError as e:
        raise HTTPException(502, str(e))

@router.post("/insight")
async def insight(payload: dict):
    cached = _cache_get(payload.get("file_id", ""))
    if not cached:
        raise HTTPException(404, "file_id 无效")
    try:
        return await generator.insight(cached["text"], payload.get("model_id"))
    except llm.LLMError as e:
        raise HTTPException(502, str(e))

@router.get("/convert/targets")
async def convert_targets(ext: str = ""):
    """前端用：给定源扩展名返回可转换的目标格式，避免出现「点了必然失败」的按钮"""
    from ..services import convert as svc
    key = (ext or "").lower()
    if key and not key.startswith("."):
        key = "." + key
    return {"ext": key, "targets": svc.supported_targets(key),
            "labels": svc.EXT_LABEL}


@router.post("/convert")
async def convert(file: UploadFile = File(...), target: str = Form(...)):
    """格式转换：按源格式支持矩阵转换，返回转换后的文件流"""
    from fastapi.responses import FileResponse
    from starlette.background import BackgroundTask
    from ..services import convert as svc

    filename = file.filename or "upload"
    ext = Path(filename).suffix.lower()
    if ext not in config.ALLOWED_EXTS:
        raise HTTPException(400, f"不支持的文件格式: {ext}")
    content = await file.read()
    if not content:
        raise HTTPException(400, "文件内容为空")
    save_path = config.UPLOAD_DIR / f"convert_{uuid.uuid4().hex[:8]}_{Path(filename).name}"
    save_path.write_bytes(content)
    try:
        result = await svc.convert(str(save_path), target)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(400, f"转换失败: {type(e).__name__}: {e}")
    finally:
        save_path.unlink(missing_ok=True)          # 转换完成后清理上传的临时文件

    def _cleanup():
        Path(result["path"]).unlink(missing_ok=True)

    # 文件发送完毕后再删除产物，避免目录无限膨胀
    return FileResponse(result["path"], filename=result["file_name"],
                        background=BackgroundTask(_cleanup))

@router.get("/preview/{rec_id}")
async def preview(rec_id: str):
    """本地预览生成的 HTML（iframe src 直接指向此接口；旧记录动态补注入导出组件）"""
    rows = store.query("SELECT html_code FROM records WHERE id=?", (rec_id,))
    if not rows:
        raise HTTPException(404, "记录不存在")
    from fastapi.responses import HTMLResponse
    return HTMLResponse(generator.inject_export(rows[0]["html_code"]))
