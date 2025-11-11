# LINE Bot - Notebook Session Management

整合 LINE OA 與 Open Notebook API 的聊天機器人，支援自動 session 管理、context 查詢和自訂 LLM 模型。

## 🎯 功能

- ✅ LINE OA Webhook 整合
- ✅ 自動為每個用戶管理 Notebook session
- ✅ 自動查詢 notebook context (sources + notes)
- ✅ 支援自訂 LLM 模型 (model_override)
- ✅ 支援多場景 System Prompt 切換（LINE Bot / 外部 API / 自訂）
- ✅ 對話記錄永久保存至 Notebook
- ✅ AI 回覆即時返回給 LINE 用戶
- ✅ RESTful API 端點供外部調用
- ✅ FastAPI 自動生成 API 文件 (/docs)

## 🚀 快速開始

### 1. 環境變數設定

```bash
cp .env.example .env
```

編輯 `.env`：

```env
# LINE Bot Configuration
ChannelSecret=your_line_channel_secret
ChannelAccessToken=your_line_channel_access_token

# Server Configuration
PORT=8902

# Open Notebook API Configuration
NOTEBOOK_API_URL=https://your-notebook-api-host:8900
NOTEBOOK_ID=notebook:your_notebook_id  # Optional: leave empty to auto-create per user

# LLM Model (可用模型見: GET /api/models)
MODEL_ID=model:your_model_id  # 自訂模型 ID
# MODEL_ID=  # 留空使用預設模型

# System Prompts (Optional)
PROMPT_ID=system_prompt:xxx  # 虛擬人客服 (外部 API 使用)
PROMPT_ID_LINE=system_prompt:xxx     # LINE 客服 (LINE Bot 使用)

# Container User Mapping (optional)
HOST_UID=1000
HOST_GID=1000
```

### 2. 使用 Docker Compose 啟動

```bash
docker-compose up -d
```

### 3. 設定 LINE Webhook

在 LINE Developers Console 設定 Webhook URL：
```
https://your-domain.com/callback
```

例如使用 **Cloudflare Workers** 作為 SSL 終端：
```
https://your-cloudflare-worker.workers.dev/callback
```

## 📋 架構說明

### 系統流程

```
LINE 用戶發送訊息："化妝品出口日本需要什麼文件？"
          ↓
    LINE Platform
          ↓ Webhook (POST /callback)
    Cloudflare Workers (SSL termination)
          ↓
    LINE Bot FastAPI (Port 8902)
          ├─ 驗證 LINE 簽章
          ├─ 提取 user_id, message
          └─ NotebookClient.chat(user_id, notebook_id, message)
              ├─ 檢查 session 快取：user_sessions[user_id]
              ├─ 若不存在：
              │   └─ POST /api/chat/sessions (創建新 session)
              ├─ 查詢 context：
              │   └─ POST /api/chat/context (獲取 sources + notes)
              └─ 發送訊息：
                  └─ POST /api/chat/execute
                      ├─ session_id
                      ├─ message
                      ├─ context (sources + notes)
                      ├─ model_override (若有設定 MODEL_ID)
                      └─ prompt_id (若有設定 PROMPT_ID)
          ↓
    Notebook API (Port 8900)
          ├─ 使用指定的 LLM 模型處理訊息
          ├─ 存儲對話記錄
          └─ 返回 AI 回應
          ↓
    LINE Bot 回覆用戶：AI 生成的回答
```

### Session 管理機制

- **每個用戶只有一個 session**：使用 `user_id` 作為 `conversation_id`
- **記憶體快取**：`user_sessions: Dict[str, str]` 映射 `conversation_id → session_id`
- **自動創建**：首次對話自動創建 session，後續對話重用同一個 session
- **持久化**：對話記錄保存在 Notebook API 的資料庫中

## 🔧 API 端點

### LINE Bot

- `POST /callback` - LINE Webhook（處理 LINE 訊息事件）
- `GET /health` - 健康檢查
- `GET /` - 服務資訊
- `GET /docs` - FastAPI 自動生成的 API 文件（Swagger UI）

### Chat API

- `POST /api/chat` - 統一對話端點（支援外部調用）

**請求格式：**
```json
{
  "text": "化妝品出口日本需要什麼文件？",
  "conversation_id": "external_test_001",
  "notebook_id": "notebook:your_notebook_id",
  "prompt_id": "system_prompt:xxx"
}
```

**參數說明：**
- `text` *（必填）*：訊息內容
- `conversation_id` *（必填）*：對話 ID，用於識別用戶
- `notebook_id` *（必填）*：Notebook ID
- `prompt_id` *（可選）*：自訂 System Prompt ID
  - 若不提供，使用預設的虛擬人客服 prompt（`PROMPT_ID`）
  - 若提供，使用指定的 prompt

**回應格式：**
```json
{
  "session_id": "chat_session:xxxxxxxxxxxxx",
  "messages": [
    {
      "id": "uuid",
      "type": "human",
      "content": "化妝品出口日本需要什麼文件？",
      "timestamp": null
    },
    {
      "id": "lc_run--uuid",
      "type": "ai",
      "content": "化妝品出口到日本需要準備的文件...",
      "timestamp": null
    }
  ]
}
```

**測試範例：**

1. 使用預設 prompt（虛擬人客服）：
```bash
curl -X POST https://your-domain.com/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "text": "你好，請簡單回答：1+1等於多少？",
    "conversation_id": "test_user_001",
    "notebook_id": "notebook:your_notebook_id"
  }'
```

2. 使用自訂 prompt：
```bash
curl -X POST https://your-domain.com/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "text": "你好，請簡單回答：1+1等於多少？",
    "conversation_id": "test_user_001",
    "notebook_id": "notebook:your_notebook_id",
    "prompt_id": "system_prompt:your_custom_prompt_id"
  }'
```

## 🗂️ 專案結構

```
/
├── src/                      # 源碼模組
│   ├── __init__.py          # 模組初始化
│   ├── notebook_client.py   # Notebook API 客戶端（核心邏輯）
│   └── line_handler.py      # LINE 訊息處理
├── main.py                  # 主程式（FastAPI 路由）
├── requirements.txt         # Python 依賴
├── Dockerfile              # Docker 映像檔
├── docker-compose.yml      # Docker Compose 配置
├── .env.example            # 環境變數範例
└── README.md               # 說明文件
```

## 🔑 核心功能說明

### 1. 自動 Session 管理

`NotebookClient.chat()` 方法會：
1. 檢查 `conversation_id` 是否已有對應的 `session_id`
2. 若無，自動創建新的 chat session
3. 快取 `session_id` 供後續對話重用

### 2. Context 自動查詢

每次發送訊息前，自動查詢 notebook 的：
- **sources**：知識庫來源文件
- **notes**：筆記和參考資料

### 3. 模型自訂

透過 `MODEL_ID` 環境變數，可指定使用的 LLM 模型：
- 支援 Groq、OpenAI、Google 等多種 provider
- 若未設定，使用 Notebook API 的預設模型

查詢可用模型：
```bash
curl -k https://your-notebook-api-host:8900/api/models
```

### 4. System Prompt 管理

本專案支援針對不同使用場景設定不同的 System Prompt：

**預設配置：**
- `PROMPT_ID`：外部 API 使用的預設 prompt（虛擬人客服）
- `PROMPT_ID_LINE`：LINE Bot 專用 prompt（LINE 客服）

**使用方式：**
1. **LINE Bot**：自動使用 `PROMPT_ID_LINE`
2. **外部 API 不帶 prompt_id**：使用 `PROMPT_ID`（預設虛擬人客服）
3. **外部 API 帶 prompt_id**：使用指定的 prompt

**範例：**
```bash
# 使用預設 prompt
curl -X POST https://your-domain.com/api/chat -d '{"text":"...","conversation_id":"...","notebook_id":"..."}'

# 使用自訂 prompt
curl -X POST https://your-domain.com/api/chat -d '{"text":"...","conversation_id":"...","notebook_id":"...","prompt_id":"system_prompt:xxx"}'
```

## 📌 注意事項

- **Port 配置**：確保 `NOTEBOOK_API_URL` 指向正確的 port（通常是 8900）
- **SSL/TLS**：本專案使用 Cloudflare Workers 處理 SSL，內部為 HTTP
- **模型限制**：確保 `MODEL_ID` 存在於 Notebook API 的模型清單中
- **錯誤處理**：若 Notebook API 連線失敗，會回覆錯誤訊息給用戶

## 🐛 除錯

查看即時日誌：
```bash
docker-compose logs -f linebot-adk
```

常見問題：
1. **All connection attempts failed** → 檢查 `NOTEBOOK_API_URL` 的 port 是否正確
2. **Model not found** → 確認 `MODEL_ID` 存在於可用模型清單中
3. **Invalid signature** → 檢查 LINE `ChannelSecret` 是否正確

## 📜 授權

MIT License
