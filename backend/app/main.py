"""万能可视化工具 - FastAPI 后端入口
启动: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .services import store
from .routers import files, records, models_router, settings, resume

app = FastAPI(title="万能可视化工具 API", version="1.0.0",
              description="解析 Word/PPT/PDF/TXT 等文件，AI 总结分类并生成高质感可视化 HTML")

# CORS：允许 Vite 开发服务器跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_methods=["*"], allow_headers=["*"],
)

store.init_db()
app.include_router(files.router)
app.include_router(records.router)
app.include_router(records.share_router)
app.include_router(models_router.router)
app.include_router(resume.router)
app.include_router(settings.router)

@app.get("/api/health")
async def health():
    """健康检查：进程存活 + 关键依赖可用性（部署后排查环境问题用，不暴露任何密钥）"""
    import sys
    modules = {}
    for name in ("fastapi", "pymupdf", "docx", "pptx", "openpyxl", "xlrd",
                 "pdfplumber", "PIL", "fpdf", "httpx"):
        try:
            __import__(name)
            modules[name] = "ok"
        except Exception as e:
            modules[name] = f"{type(e).__name__}: {e}"
    try:
        from .services import convert as _cv
        modules["services.convert"] = f"ok({len(_cv.TARGETS)})"
    except Exception as e:
        modules["services.convert"] = f"{type(e).__name__}: {e}"
    return {"status": "ok", "python": sys.version.split()[0], "modules": modules}


# 生成的 HTML 静态目录（备用直链）
from . import config
app.mount("/generated", StaticFiles(directory=str(config.GENERATED_DIR)), name="generated")
app.mount("/exports", StaticFiles(directory=str(config.EXPORT_DIR)), name="exports")

# 前端构建产物托管（backend/static，部署为单端口服务时由本服务直接供页）
STATIC_DIR = config.BASE_DIR / "static"
if (STATIC_DIR / "index.html").exists():
    if (STATIC_DIR / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")

    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(str(STATIC_DIR / "index.html"))

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        """单端口模式下的静态资源兜底（favicon / 图片等）；API 路径不拦截，保持 JSON 404"""
        from fastapi import HTTPException
        if full_path.startswith(("api/", "share/", "generated/", "exports/", "docs", "openapi.json")):
            raise HTTPException(404, "Not Found")
        candidate = (STATIC_DIR / full_path).resolve()
        if full_path and candidate.is_file() and str(candidate).startswith(str(STATIC_DIR.resolve())):
            return FileResponse(str(candidate))
        return FileResponse(str(STATIC_DIR / "index.html"))
else:
    @app.get("/")
    async def root():
        return {"app": "万能可视化工具", "docs": "/docs", "share_example": "/share/{share_id}"}

@app.get("/favicon.ico")
async def favicon():
    return FileResponse(str(config.BASE_DIR / "favicon.ico")) if (config.BASE_DIR / "favicon.ico").exists() else {"ok": 1}
