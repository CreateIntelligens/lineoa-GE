"""
LINE Bot - 主應用程式
負責路由和應用程式初始化
"""

import os
import sys
import aiohttp
from fastapi import Request, FastAPI, HTTPException
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent
from linebot.aiohttp_async_http_client import AiohttpAsyncHttpClient
from linebot import AsyncLineBotApi, WebhookParser

from src.notebook_client import NotebookClient
from src.line_handler import handle_text_message

# =============================================================================
# 環境變數配置
# =============================================================================

# Server 配置
PORT = int(os.getenv("PORT", "8902"))

# LINE Bot 配置
CHANNEL_SECRET = os.getenv("ChannelSecret")
CHANNEL_ACCESS_TOKEN = os.getenv("ChannelAccessToken")

# Open Notebook API 配置
NOTEBOOK_API_URL = os.getenv("NOTEBOOK_API_URL", "https://localhost:8900")
NOTEBOOK_ID = os.getenv("NOTEBOOK_ID", "")
MODEL_ID = os.getenv("MODEL_ID", "")  # LLM model override

# 驗證必要環境變數
if not CHANNEL_SECRET:
    print("錯誤：請設定 ChannelSecret 環境變數")
    sys.exit(1)
if not CHANNEL_ACCESS_TOKEN:
    print("錯誤：請設定 ChannelAccessToken 環境變數")
    sys.exit(1)

# =============================================================================
# 初始化服務
# =============================================================================

# FastAPI 應用程式
app = FastAPI(
    title="LINE Bot - Notebook Session",
    description="LINE Bot with Open Notebook API integration",
    version="1.0.0"
)

# LINE Bot API
session = aiohttp.ClientSession()
async_http_client = AiohttpAsyncHttpClient(session)
line_bot_api = AsyncLineBotApi(CHANNEL_ACCESS_TOKEN, async_http_client)
parser = WebhookParser(CHANNEL_SECRET)

# Notebook API 客戶端
notebook_client = NotebookClient(NOTEBOOK_API_URL, NOTEBOOK_ID, MODEL_ID)

# =============================================================================
# 路由端點
# =============================================================================

@app.post("/callback")
async def callback(request: Request) -> str:
    """
    LINE Bot Webhook 端點

    處理 LINE Platform 發送的 webhook 事件
    """
    # 驗證簽章
    signature = request.headers.get("X-Line-Signature")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature")

    body = (await request.body()).decode()

    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # 處理事件
    for event in events:
        if isinstance(event, MessageEvent) and event.message.type == "text":
            await handle_text_message(event, line_bot_api, notebook_client, NOTEBOOK_ID)

    return "OK"


@app.get("/health")
async def health_check():
    """健康檢查端點"""
    return {
        "status": "ok",
        "service": "linebot-notebook-session",
        "notebook_api": NOTEBOOK_API_URL
    }


@app.get("/")
async def root():
    """根路徑"""
    return {
        "service": "LINE Bot - Notebook Session",
        "status": "running",
        "endpoints": {
            "webhook": "/callback",
            "health": "/health",
            "chat": "/api/chat"
        }
    }

# =============================================================================
# Chat API 端點
# =============================================================================

@app.post("/api/chat")
async def chat(data: dict):
    """
    對話端點 - 自動管理 session

    接收參數:
    - text: 訊息內容
    - conversation_id: 對話 ID
    - notebook_id: Notebook ID
    """
    text = data.get("text")
    conversation_id = data.get("conversation_id")
    notebook_id = data.get("notebook_id")

    if not text or not conversation_id or not notebook_id:
        return {
            "error": "Missing required fields: text, conversation_id, notebook_id"
        }

    result = await notebook_client.chat(conversation_id, notebook_id, text)
    return result

# =============================================================================
# 應用程式啟動
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    print("=" * 80)
    print("LINE Bot - Notebook Session Management")
    print("=" * 80)
    print(f"🚀 Server Port: {PORT}")
    print(f"📓 Notebook API: {NOTEBOOK_API_URL}")
    print(f"📚 Notebook ID: {NOTEBOOK_ID or '(auto-create per user)'}")
    print("=" * 80)

    uvicorn.run(app, host="0.0.0.0", port=PORT)
