"""
Open Notebook API 客戶端
負責與 Open Notebook API (8900 port) 的所有互動
"""

import httpx
from typing import Dict, Optional


class NotebookClient:
    """Open Notebook API 客戶端"""

    def __init__(self, base_url: str, default_notebook_id: str = "", model_id: str = ""):
        """
        初始化客戶端

        Args:
            base_url: Open Notebook API 的基礎 URL
            default_notebook_id: 預設的 notebook ID（可選）
            model_id: LLM model ID（可選）
        """
        self.base_url = base_url
        self.default_notebook_id = default_notebook_id
        self.model_id = model_id
        self.user_sessions: Dict[str, str] = {}  # 快取：conversation_id -> session_id

    async def get_or_create_session(self, user_id: str) -> str:
        """
        獲取或創建用戶的 chat session（每個用戶只有一個 session）

        Args:
            user_id: LINE 用戶 ID

        Returns:
            session_id: Open Notebook 的 session ID
        """
        # 如果已經有 session，直接返回
        if user_id in self.user_sessions:
            session_id = self.user_sessions[user_id]
            print(f"♻️  用戶 {user_id} 使用現有 session: {session_id}")
            return session_id

        # 首次使用，創建新 session
        try:
            async with httpx.AsyncClient(verify=False) as client:
                # 如果沒有預設 notebook_id，先創建一個
                notebook_id = self.default_notebook_id
                if not notebook_id:
                    notebook_id = await self._create_notebook(client, user_id)

                # 創建 chat session
                session_id = await self._create_session(client, notebook_id, user_id)

                # 快取 session_id
                self.user_sessions[user_id] = session_id
                print(f"✅ 為用戶 {user_id} 創建新 session: {session_id}")
                return session_id

        except Exception as e:
            print(f"❌ 創建 session 失敗: {e}")
            raise

    async def _create_notebook(self, client: httpx.AsyncClient, user_id: str) -> str:
        """創建新的 notebook"""
        response = await client.post(
            f"{self.base_url}/api/notebooks",
            json={
                "name": f"LINE Bot - {user_id}",
                "description": "LINE Bot 對話記錄"
            }
        )
        notebook_data = response.json()
        notebook_id = notebook_data["id"]
        print(f"📚 為用戶 {user_id} 創建 notebook: {notebook_id}")
        return notebook_id

    async def _create_session(
        self, client: httpx.AsyncClient, notebook_id: str, user_id: str
    ) -> str:
        """創建新的 chat session"""
        response = await client.post(
            f"{self.base_url}/api/chat/sessions",
            json={
                "notebook_id": notebook_id,
                "title": f"LINE Chat - {user_id}"
            }
        )
        session_data = response.json()
        return session_data["id"]

    async def send_message(self, user_id: str, message: str) -> Dict:
        """
        發送訊息到 Open Notebook API

        Args:
            user_id: LINE 用戶 ID (用作 conversation_id)
            message: 訊息內容

        Returns:
            API 回應資料
        """
        try:
            async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat/execute",
                    json={
                        "text": message,
                        "conversation_id": user_id
                    }
                )
                result = response.json()

                # 如果回應中有 session_id，記錄下來
                if "session_id" in result:
                    self.user_sessions[user_id] = result["session_id"]
                    print(f"📝 記錄用戶 {user_id} 的 session_id: {result['session_id']}")

                return result

        except Exception as e:
            print(f"❌ 發送訊息失敗: {e}")
            return {"error": str(e)}

    async def chat(self, conversation_id: str, notebook_id: str, message: str) -> Dict:
        """
        處理對話請求 - 檢查是否已有 session，沒有則創建新的

        Args:
            conversation_id: 對話 ID
            notebook_id: Notebook ID
            message: 訊息內容

        Returns:
            API 回應資料
        """
        try:
            async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
                # 檢查是否已經有 session
                if conversation_id in self.user_sessions:
                    session_id = self.user_sessions[conversation_id]
                    print(f"♻️  使用現有 session: {session_id} (conversation: {conversation_id})")
                else:
                    # 創建新 session
                    session_response = await client.post(
                        f"{self.base_url}/api/chat/sessions",
                        json={
                            "notebook_id": notebook_id,
                            "title": f"Chat - {conversation_id}"
                        }
                    )
                    session_data = session_response.json()

                    print(f"📋 Session 創建回應: {session_data}")

                    if "id" not in session_data:
                        raise Exception(f"創建 session 失敗: {session_data}")

                    session_id = session_data["id"]

                    # 記錄新的 session
                    self.user_sessions[conversation_id] = session_id
                    print(f"✅ 創建新 session: {session_id} (conversation: {conversation_id}, notebook: {notebook_id})")

                # 查詢 context (sources 和 notes)
                print(f"🔍 查詢 notebook context...")
                context_response = await client.post(
                    f"{self.base_url}/api/chat/context",
                    json={
                        "notebook_id": notebook_id,
                        "context_config": {}
                    }
                )
                context_data = context_response.json()
                context = context_data.get("context", {"sources": [], "notes": []})
                print(f"📚 Context 查詢完成: {len(context.get('sources', []))} sources, {len(context.get('notes', []))} notes")

                # 發送訊息到 session (帶入 context 和 model_override)
                payload = {
                    "session_id": session_id,
                    "message": message,
                    "context": context
                }

                # 如果有設定 model_id，加入 model_override
                if self.model_id:
                    payload["model_override"] = self.model_id
                    print(f"🤖 使用自訂 model: {self.model_id}")

                response = await client.post(
                    f"{self.base_url}/api/chat/execute",
                    json=payload
                )
                result = response.json()

                print(f"📤 訊息已發送到 session {session_id}")
                return result

        except Exception as e:
            print(f"❌ 對話處理失敗: {e}")
            return {"error": str(e)}
