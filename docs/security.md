# 加分題：OWASP Top 10 (2021) 資安審查

- 審查者：security-auditor 子代理（tools 只有 Read、Grep、Glob，只讀不改）
- 範圍：app/ 7 個檔案、requirements.txt（參考 docs/spec.md）
- 處理流程：高、中嚴重度交給 coder 修正 → tester 重跑測試
- **結果：0 項高、0 項中嚴重度**，因此沒有需要 coder 修正的項目；低嚴重度項目列為未來對外部署前的建議。
- 最終測試：`python -m pytest -v` 191 passed（見 docs/test-result.txt）

## 摘要

| 項目 | 嚴重度 | 重點 |
|---|---|---|
| A01 存取控制失效 | 低 | 無認證（規格明定本版不做），無使用者/擁有者概念；對外部署前加 API Key |
| A02 加密機制失效 | 無（不適用） | 無密碼、token、個資；HTTPS 屬部署層 |
| A03 注入攻擊 | 低 | 全用 SQLAlchemy ORM 參數化查詢，無 SQL 注入；model_url 只允許 http/https；前端顯示 name 需做輸出編碼 |
| A04 不安全的設計 | 低 | 無速率限制、body 大小與資料筆數上限 |
| A05 安全設定錯誤 | 低 | /docs 預設開啟；500 不洩漏堆疊、422 不回傳 input |
| A06 易受攻擊與過時的元件 | 低 | 無鎖定檔、版本下限偏低、測試套件與正式套件混放 |
| A07 識別與身分驗證失效 | 無（不適用） | 無帳號系統，屬作業範圍 |
| A08 軟體與資料完整性失效 | 低 | 無不安全反序列化；依賴未做雜湊鎖定 |
| A09 安全日誌與監控失效 | 低 | 寫入操作無稽核紀錄 |
| A10 SSRF | 無（不適用） | 伺服器從不主動抓取 model_url |

## security-auditor 完整回報

# OWASP Top 10 (2021) 資安審查：XR 場景物件管理 API

**結論：沒有高或中嚴重度的問題，所以這一輪 coder 不需要修改。** 以下 10 項發現都是低嚴重度或不適用。

**審查範圍：** `app/` 底下 7 個檔案（`__init__.py`、`main.py`、`crud.py`、`errors.py`、`schemas.py`、`database.py`、`models.py`）和 `requirements.txt`，另外參考 `docs/spec.md`（v1.0，第 1.0 節寫明「認證：無（本版不實作）」）。我只有讀檔權限，沒有執行任何程式或掃描工具，結論都是從原始碼推得的。

## 一、A01～A10 審查結果

| 項目 | 適用性 | 發現的問題（檔案:行號） | 嚴重度 | 建議修法 |
|---|---|---|---|---|
| **A01 存取控制失效** | 適用 | 1. 所有端點都沒有存取控制，任何人都能 PUT/DELETE 任何物件（`app/main.py:65-80`）。<br>2. 判斷為低的理由：規格明定本版不做認證（`docs/spec.md:15`），而且沒有使用者帳號、也沒有「誰擁有哪個物件」的概念，所以不存在越權存取（IDOR）。照 `uvicorn app.main:app` 預設啟動只綁 `127.0.0.1`，外部連不進來。<br>3. 沒有設定 CORS，瀏覽器維持預設的同源限制，這樣是對的。 | 低 | 作業範圍內不用修。如果要對外部署（綁 `0.0.0.0` 或上雲），至少要加一組 API Key 的 header 檢查（用 FastAPI `Depends` 驗證 `X-API-Key`），保護 POST/PUT/DELETE。 |
| **A02 加密機制失效** | 不適用 | 沒有密碼、token、個資或金鑰。ID 用 `uuid.uuid4()`（`app/crud.py:62`），它的亂數來自 `os.urandom`，夠安全。傳輸加密（HTTPS）屬於部署層的事。 | 無 | 對外部署時放在 TLS 反向代理後面。 |
| **A03 注入攻擊** | 適用 | 1. **SQL 注入：沒發現。** 全部走 SQLAlchemy ORM 和參數化查詢（`app/crud.py:45-57`），沒有拼接字串的 SQL。`limit`/`offset` 已限定為整數並設了範圍（`app/main.py:43-44`）。id 有正規表示式白名單（`app/main.py:14-16`）。<br>2. **儲存型 XSS：風險很低。** `model_url` 只接受 http/https（`app/schemas.py:91`），已擋掉 `javascript:` 和 `data:`。`name` 擋了控制字元，但允許 `<script>` 這類 HTML 字元（`app/schemas.py:65-73`）。API 只回傳 `application/json`，本身不會執行。真正的風險在前端或 XR 客戶端，如果它用 innerHTML 直接插入 `name` 就會出事。 | 低 | 目前不用改後端。前端顯示 `name` 時要做輸出編碼（用 textContent，不要用 innerHTML）。 |
| **A04 不安全的設計** | 適用 | 1. 沒有速率限制，也沒有資料總筆數上限，可以無限 POST 把 SQLite 檔案和磁碟塞滿（`app/main.py:58-62`、`app/crud.py:60-71`）。<br>2. 沒有限制請求 body 大小：FastAPI/uvicorn 會先把整個 body 讀進記憶體，之後 Pydantic 才檢查長度（`app/schemas.py:76-80`），超大 JSON 會吃掉記憶體。<br>3. 以課堂規模、只綁本機的條件來看，實際風險很低。 | 低 | 可以考慮：(a) 部署時由反向代理限制 body 大小（例如 nginx `client_max_body_size 16k`）；(b) 加 `slowapi` 做速率限制；(c) 在 `create_object` 加筆數上限。都不是作業的必要項目。 |
| **A05 安全設定錯誤** | 適用 | 1. `/docs`、`/redoc`、`/openapi.json` 預設是開著的（`app/main.py:32`），會公開 API 結構。這是開發和評分需要的，可以接受。<br>2. 錯誤處理做得好：500 一律回 `"Internal server error"`，不洩漏堆疊或 SQL（`app/errors.py:94-95,103-105`）；驗證錯誤只輸出 `loc`/`msg`/`type`，不回傳 `input`/`ctx`（`app/errors.py:42-58`）。<br>3. `DATABASE_URL` 預設是相對路徑 `./xr_objects.db`（`app/database.py:9`），資料庫檔案位置會隨啟動時的工作目錄改變。這比較像可靠性問題。<br>4. 沒有加 `X-Content-Type-Options: nosniff` 等安全標頭。對純 JSON API 影響很小。 | 低 | 正式環境可以用 `FastAPI(docs_url=None, redoc_url=None, openapi_url=None)`，或透過環境變數控制是否開啟。資料庫路徑可改成以專案目錄為基準的絕對路徑。 |
| **A06 易受攻擊與過時的元件** | 適用 | 1. `requirements.txt:1-6` 只寫版本範圍，沒有鎖定版本的檔案（lock file），每次安裝結果可能不同。<br>2. 下限偏低：`fastapi>=0.110` 允許安裝較舊的 Starlette。依我的了解，Starlette 過去有幾個已知 CVE 和 multipart 表單或檔案上傳有關（例如 CVE-2024-47874）。不過本 API 只收 JSON，沒有 Form 或 UploadFile 端點，實際打不到。具體受影響的版本我沒有在這裡查證。<br>3. `pytest`、`httpx` 這類測試工具和正式執行的套件混在同一個檔案（`requirements.txt:5-6`）。 | 低 | 拉高下限（例如 `fastapi>=0.115`），產生鎖定檔（`pip freeze > requirements.lock` 或用 `pip-tools`），並用 `pip-audit` 定期掃描。測試套件拆到 `requirements-dev.txt`。 |
| **A07 識別與身分驗證失效** | 不適用（依作業範圍） | 沒有帳號、登入、session 或 token，也就沒有弱密碼、暴力破解、session 固定攻擊這類問題。規格明定本版不做認證（`docs/spec.md:15`），所以「沒有登入機制」屬於設計範圍，不算缺陷。 | 無 | 未來要對外開放時，同 A01 的建議（API Key 或 OAuth2）。 |
| **A08 軟體與資料完整性失效** | 部分適用 | 沒有 pickle 或 yaml.load 這類不安全的反序列化，JSON 一律經 Pydantic 嚴格驗證並禁止額外欄位（`app/schemas.py:104-111`）。沒有 CI/CD 流程。唯一的缺口是依賴套件沒有做雜湊值鎖定。 | 低 | 可選：`pip install --require-hashes -r requirements.lock`。 |
| **A09 安全日誌與監控失效** | 適用 | 1. 只有未處理的例外會寫 log（`app/errors.py:104`）。PUT/DELETE 這類寫入操作沒有稽核紀錄，只能靠 uvicorn 的存取日誌。<br>2. log 裡記錄了 `request.url.path`（`app/errors.py:104`），而 path 是解碼後的值，理論上可以用 `%0a` 偽造 log 行。不過要先讓 handler 拋出未預期的例外才會寫入，條件很難達成。 | 低 | 可選：在 create/update/delete 成功後用 `logger.info` 記錄方法、id 和時間。記錄 path 時用 `%r` 格式，讓換行字元被跳脫。 |
| **A10 伺服器端請求偽造（SSRF）** | 不適用 | 伺服器只儲存 `model_url`，從不主動去抓（全部程式碼中沒有 httpx/requests/urllib 的請求呼叫，`httpx` 只用在測試），所以不構成 SSRF。另外有兩點：`model_url` 允許 `localhost`、`169.254.169.254` 這類內網位址（`app/schemas.py:76-98`），而且 `urlsplit` 對 `https://a.com\@b.com` 這種網址的解析可能和瀏覽器不同。這些只會影響前端或 XR 客戶端。 | 無 | 未來如果加了「伺服器端下載或預覽模型」的功能，必須加上主機白名單並阻擋私有和保留 IP 區段。 |

## 二、需要 coder 修正的項目（高、中嚴重度）

**沒有。** 以作業規模（沒有帳號系統、規格明定不做認證、預設只綁本機）來看，各項都是低嚴重度或不適用。

整體來看，這份實作的安全基礎不錯：
- 全面使用 ORM 參數化查詢。
- 用 Pydantic 嚴格驗證所有輸入，並禁止額外欄位。
- `model_url` 只接受 http/https。
- 錯誤回應不洩漏內部資訊。

如果之後要提升到可以對外部署，建議依序處理這三項（目前都是可選）：
1. **A01/A07：** 加 API Key，保護會寫入資料的端點。
2. **A06：** 拉高套件版本下限、產生鎖定檔、加入 `pip-audit`，並把測試套件分離出去。
3. **A04：** 由反向代理限制 body 大小並加上速率限制。
