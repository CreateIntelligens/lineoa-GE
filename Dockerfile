# 使用官方 Python 3.10.17 基礎映像，確保環境一致性
FROM python:3.10.17

# 設定容器內的工作目錄，所有後續命令都會在這個目錄下執行
WORKDIR /app

# 優先複製 requirements.txt 以利用 Docker 層快取機制
# 當 requirements.txt 沒有變更時，可以重用已快取的 pip install 層
COPY requirements.txt .

# 更新 pip 到最新版本，然後安裝專案依賴
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 建立非 root 使用者來執行應用程式，提高容器安全性
# 避免使用 root 權限執行應用程式，降低潛在的安全風險
RUN groupadd -r louis && useradd -r -g louis louis
RUN chown -R louis:louis /app
USER louis

# 暴露容器端口 8902，讓外部可以訪問 FastAPI 應用程式
EXPOSE 8902

# 設定預設啟動命令（在 docker-compose.yml 中會被覆蓋）
# 使用 Uvicorn ASGI 伺服器啟動 FastAPI 應用程式
CMD ["uvicorn", "main:app", "--host=0.0.0.0", "--port=8902"]
