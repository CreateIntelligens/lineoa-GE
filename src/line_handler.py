"""
LINE Bot 訊息處理邏輯
負責處理 LINE 訊息事件並與 Notebook API 互動
"""

from linebot.models import MessageEvent, TextSendMessage
from linebot import AsyncLineBotApi
from src.notebook_client import NotebookClient


async def handle_text_message(
    event: MessageEvent,
    line_bot_api: AsyncLineBotApi,
    notebook_client: NotebookClient,
    notebook_id: str
) -> None:
    """
    處理 LINE 文字訊息

    Args:
        event: LINE 訊息事件
        line_bot_api: LINE Bot API 實例
        notebook_client: Notebook API 客戶端
        notebook_id: Notebook ID
    """
    user_id = event.source.user_id
    message = event.message.text

    print(f"📩 收到訊息: {message} (用戶: {user_id})")

    try:
        # 使用新的 chat 方法,自動管理 session
        result = await notebook_client.chat(user_id, notebook_id, message)

        # 檢查是否有錯誤
        if 'error' in result:
            raise Exception(result['error'])

        print(f"✅ 訊息已轉發到 Notebook API")
        print(f"📊 Session ID: {result.get('session_id')}")

        # 取得 AI 回應
        messages = result.get('messages', [])
        ai_message = None
        for msg in reversed(messages):
            if msg.get('type') == 'ai':
                ai_message = msg.get('content')
                break

        # 如果沒有 AI 回應，拋出錯誤
        if not ai_message:
            raise Exception("未收到 AI 回應")

        # 回覆 AI 的回應
        await line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=ai_message)
        )

    except Exception as e:
        print(f"❌ 處理訊息失敗: {e}")
        await line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"抱歉，處理訊息時發生錯誤：{str(e)}")
        )
