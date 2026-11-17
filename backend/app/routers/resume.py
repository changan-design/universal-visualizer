"""简历转化接口：个人资料存取 / AI 专业化改写 / 简历生成（可视化+ATS）/ Word·HTML 导出"""
from pathlib import Path
import re
from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import FileResponse
from .. import config
from ..services import resume, llm

router = APIRouter(prefix="/api/resume", tags=["resume"])


@router.get("/profile")
async def read_profile():
    return await resume.get_profile()


@router.post("/profile")
async def write_profile(profile: dict = Body(...)):
    return await resume.save_profile(profile)


@router.post("/optimize")
async def optimize(payload: dict = Body(...)):
    """口语化经历长文 + 表单 → AI 专业化改写（结合行业/岗位知识，量化+关键词）"""
    try:
        result = await resume.optimize(payload, payload.get("model_id"))
    except llm.LLMError as e:
        raise HTTPException(500, str(e))
    return result


@router.post("/generate")
async def generate(payload: dict = Body(...)):
    """结构化简历数据 → 生成简历页并写入历史（visual=True 可视化版 / False ATS 极简版）"""
    data = payload.get("data")
    if not data or not (data.get("basics") or {}).get("name"):
        raise HTTPException(400, "请先完善姓名等基本信息")
    try:
        return await resume.generate(data, visual=bool(payload.get("visual", True)),
                                     model_id=payload.get("model_id"))
    except llm.LLMError as e:
        raise HTTPException(500, str(e))


@router.get("/records/{rec_id}/export/docx")
async def export_docx(rec_id: str):
    """导出 Word 版简历（python-docx 确定性构建，ATS 解析可靠）"""
    from ..services import store
    rows = store.query("SELECT title FROM records WHERE id=?", (rec_id,))
    if not rows:
        raise HTTPException(404, "记录不存在")
    try:
        data = resume.load_resume_data(rec_id)
    except FileNotFoundError:
        raise HTTPException(404, "该简历记录缺少结构化数据，无法导出 Word")
    name = (data.get("basics") or {}).get("name") or "简历"
    safe = re.sub(r'[\\/:*?"<>|]', "_", f"{name}_简历")[:60]
    out = config.EXPORT_DIR / f"{safe}_{rec_id}.docx"
    resume.build_docx(data, out)
    from starlette.background import BackgroundTask
    return FileResponse(str(out), filename=f"{safe}.docx",
                        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        background=BackgroundTask(lambda: out.unlink(missing_ok=True)))
