from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.api.v1.api import api_router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

LANDING_PAGE = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{settings.APP_NAME}</title>
<style>
  :root {{ color-scheme: light dark; }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    background: #0b0b0f;
    color: #e8e8ec;
    padding: 24px;
  }}
  .card {{
    max-width: 560px;
    width: 100%;
    background: #16161d;
    border: 1px solid #2a2a35;
    border-radius: 16px;
    padding: 40px;
  }}
  h1 {{ margin: 0 0 8px; font-size: 1.5rem; }}
  .version {{ color: #8a8a99; font-size: 0.85rem; margin: 0 0 24px; }}
  .flow {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
    margin: 0 0 28px;
    font-size: 0.85rem;
    color: #b8b8c5;
  }}
  .flow span.step {{
    background: #21212b;
    border: 1px solid #2f2f3a;
    border-radius: 999px;
    padding: 6px 14px;
  }}
  .flow span.arrow {{ color: #55556b; }}
  .links {{ display: flex; gap: 12px; flex-wrap: wrap; }}
  a.btn {{
    display: inline-block;
    padding: 10px 18px;
    border-radius: 10px;
    text-decoration: none;
    font-size: 0.9rem;
    font-weight: 600;
    transition: opacity 0.15s;
  }}
  a.btn:hover {{ opacity: 0.85; }}
  a.primary {{ background: #f55036; color: #fff; }}
  a.secondary {{ background: #21212b; color: #e8e8ec; border: 1px solid #2f2f3a; }}
  footer {{ margin-top: 28px; font-size: 0.75rem; color: #55556b; }}
</style>
</head>
<body>
  <div class="card">
    <h1>{settings.APP_NAME}</h1>
    <p class="version">v{settings.APP_VERSION} - personal tool, no auth</p>
    <div class="flow">
      <span class="step">Product Data</span>
      <span class="arrow">&rarr;</span>
      <span class="step">Scraper/API</span>
      <span class="arrow">&rarr;</span>
      <span class="step">Product Scoring</span>
      <span class="arrow">&rarr;</span>
      <span class="step">LLM Analysis</span>
    </div>
    <div class="links">
      <a class="btn primary" href="/docs">Swagger Docs</a>
      <a class="btn secondary" href="/redoc">ReDoc</a>
      <a class="btn secondary" href="/api/v1/health/">Health Check</a>
    </div>
    <footer>TikTok Shop product research - FastAPI backend</footer>
  </div>
</body>
</html>"""


@app.get("/", tags=["Root"], response_class=HTMLResponse)
async def read_root():
    """Landing page with links to the interactive API docs."""
    return LANDING_PAGE


app.include_router(api_router, prefix="/api/v1")
