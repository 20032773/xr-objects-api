# XR 場景物件管理 API 規格（spec.md）

> 版本：1.0 ｜ 技術：Python 3.11 + FastAPI + Pydantic v2 + SQLAlchemy 2.x + SQLite（依 docs/compare.md 第 1 名）
> 本文件為實作（coder）與測試（tester）的唯一依據。凡標示「必須 / MUST」者皆須有對應測試。

---

## 1. 總覽

| 項目 | 規定 |
|------|------|
| Base URL | `/`（無版本前綴） |
| 資料格式 | 請求與回應皆為 `application/json; charset=utf-8`（DELETE 成功除外，無 body） |
| 編碼 | UTF-8 |
| 認證 | 無（本版不實作） |
| 時間 | 一律 UTC，ISO 8601，結尾 `Z`（例：`2026-11-18T08:30:00.123456Z`） |
| ID | UUID v4，小寫、含連字號的標準 36 字元格式 |

### 1.1 端點一覽

| 方法 | 路徑 | 說明 | 成功狀態碼 |
|------|------|------|-----------|
| GET | `/objects` | 列出物件（分頁） | 200 |
| GET | `/objects/{id}` | 取得單筆 | 200 |
| POST | `/objects` | 新增 | 201 |
| PUT | `/objects/{id}` | 整筆取代更新 | 200 |
| DELETE | `/objects/{id}` | 刪除 | 204 |

---

## 2. 專案結構（建議，coder 可微調但需保留 `get_db` 與 `app` 名稱）

```
app/
  __init__.py
  main.py        # FastAPI app 實例 `app`、lifespan 建表、註冊 router 與例外處理
  database.py    # DATABASE_URL、engine、SessionLocal、Base、get_db()
  models.py      # SQLAlchemy ORM：SceneObject
  schemas.py     # Pydantic：Vector3、ObjectCreate、ObjectUpdate、ObjectOut、ObjectList、ErrorResponse
  crud.py        # 資料存取函式（隔離資料庫細節）
  errors.py      # 統一錯誤格式的 exception handlers
tests/
  conftest.py    # 測試用 DB 與 TestClient fixture
```

---

## 3. 資料模型

### 3.1 API 資源：SceneObject

| 欄位 | 型別 | 來源 | 說明 |
|------|------|------|------|
| `id` | string (UUID v4) | 伺服器產生 | 小寫 36 字元，例 `3f2b8c1e-9a4d-4e7b-8c21-5d6f7a8b9c0d` |
| `name` | string | 使用者 | 去除前後空白後 1–100 字元 |
| `model_url` | string | 使用者 | http/https 網址，≤ 2048 字元，原樣儲存與回傳 |
| `position` | Vector3 | 使用者 | 位置（公尺），各分量 −1,000,000 ～ 1,000,000（含） |
| `rotation` | Vector3 | 使用者 | 尤拉角（度），各分量 −360 ～ 360（含） |
| `scale` | Vector3 | 使用者 | 縮放倍率，各分量 > 0 且 ≤ 10,000 |
| `created_at` | string (datetime) | 伺服器產生 | 建立時間（UTC），建立後永不改變 |
| `updated_at` | string (datetime) | 伺服器產生 | 最後更新時間（UTC）；建立時等於 `created_at` |

**Vector3**：`{"x": number, "y": number, "z": number}`，三個分量皆必填，回應中一律為 JSON 浮點數（輸入 `1` 回應為 `1.0`）。

### 3.2 資料表：`scene_objects`（SQLAlchemy 2.x，`Mapped[...]` 宣告式）

| 欄位 | SQL 型別 | 限制 |
|------|----------|------|
| `id` | `String(36)` | PRIMARY KEY |
| `name` | `String(100)` | NOT NULL |
| `model_url` | `String(2048)` | NOT NULL |
| `position_x` / `position_y` / `position_z` | `Float` | NOT NULL |
| `rotation_x` / `rotation_y` / `rotation_z` | `Float` | NOT NULL |
| `scale_x` / `scale_y` / `scale_z` | `Float` | NOT NULL |
| `created_at` | `DateTime` | NOT NULL，UTC（以 naive UTC 儲存，輸出時補 `Z`） |
| `updated_at` | `DateTime` | NOT NULL，UTC |

- `name` **不**要求唯一，可重複。
- 向量採攤平欄位儲存（不用 JSON 欄位），以利未來遷移 PostgreSQL。
- 資料表於 app 啟動時（lifespan）以 `Base.metadata.create_all(engine)` 建立。

---

## 4. 統一錯誤回應格式

所有非 2xx 回應（含 FastAPI 內建的 404 路由不存在、405、422）**必須**使用以下格式：

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      { "loc": ["body", "scale", "x"], "msg": "Input should be greater than 0", "type": "greater_than" }
    ]
  }
}
```

| 欄位 | 型別 | 說明 |
|------|------|------|
| `error.code` | string | 機器可讀代碼，見下表 |
| `error.message` | string | 人類可讀訊息（內容不做精確比對） |
| `error.details` | array | 驗證錯誤時為非空陣列；其他錯誤為空陣列 `[]` |
| `details[].loc` | array of string/int | 錯誤位置，第一個元素為 `"body"`、`"path"` 或 `"query"` |
| `details[].msg` | string | 錯誤說明 |
| `details[].type` | string | 錯誤類型（沿用 Pydantic type 或自訂） |

| HTTP 狀態 | `code` | 觸發情境 |
|-----------|--------|----------|
| 404 | `NOT_FOUND` | id 格式正確但物件不存在；或路由不存在 |
| 405 | `METHOD_NOT_ALLOWED` | 方法不支援（例：`PATCH /objects/{id}`、`DELETE /objects`） |
| 422 | `VALIDATION_ERROR` | 請求 body / path / query 任何驗證失敗（含 JSON 語法錯誤、body 非物件、缺 body） |
| 500 | `INTERNAL_ERROR` | 未預期錯誤；`message` 固定為 `"Internal server error"`，不可洩漏堆疊或 SQL |

**測試要點**：tester 對錯誤回應應斷言 `status_code`、`error.code`，驗證錯誤另斷言 `details` 非空且某筆 `loc` 包含出錯欄位名稱；不比對 `message`/`msg` 內文。

**實作提示**：在 `errors.py` 註冊 `RequestValidationError`、`StarletteHTTPException`、`Exception` 三個 handler。`details` 由 `exc.errors()` 轉換，只保留 `loc`、`msg`、`type`（不可直接輸出 `ctx`/`input`，避免序列化失敗如 NaN）。

---

## 5. 輸入驗證規則

### 5.1 通用

| 規則 | 行為 |
|------|------|
| 額外欄位（頂層） | **禁止** → 422（`extra="forbid"`）。包含使用者傳入 `id`、`created_at`、`updated_at` 也是 422 |
| 額外欄位（Vector3 內） | **禁止** → 422（例：`{"x":1,"y":2,"z":3,"w":4}`） |
| 欄位值為 `null` | 一律 422（沒有任何欄位可為 null） |
| body 非 JSON 物件 | 422（例：`[]`、`"abc"`、`123`） |
| JSON 語法錯誤 | 422 |
| POST/PUT 缺 body | 422 |

### 5.2 `name`

| 規則 | 細節 |
|------|------|
| 必填 | 缺少 → 422 |
| 型別 | 必須是 JSON string；數字、布林、陣列、物件 → 422（不做型別轉換） |
| 前處理 | 以 Python `str.strip()` 去除前後空白，**儲存與回傳去除後的值** |
| 長度 | 去除後 1 ～ 100 個字元（Unicode code point 計算，中文 1 字 = 1） |
| 不可空白 | `""`、`"   "`、`"\t\n"` → 422 |
| 控制字元 | 去除後仍含 U+0000–U+001F 或 U+007F → 422（例：`"a\u0000b"`、`"a\nb"`） |

邊界值：100 字元 → 201；101 字元 → 422；`"  ab  "` → 201 且回傳 `"ab"`；`" " + "a"*100 + " "` → 201（去除後 100）。

### 5.3 `model_url`

| 規則 | 細節 |
|------|------|
| 必填 / 型別 | 必須是 JSON string，否則 422 |
| 長度 | 1 ～ 2048 字元（**不**做 strip；含前後空白即違反下一條） |
| 空白字元 | 字串中任何位置含空白字元（空格、tab、換行）→ 422 |
| scheme | 必須為 `http` 或 `https`（不分大小寫）；`ftp://`、`file://`、`javascript:`、`data:` → 422 |
| host | 必須有非空主機名（`http://`、`http:///a.glb`、`https://:80` → 422） |
| port | 若有，須為 1–65535 的整數（`http://a.com:99999/x` → 422） |
| 儲存 | 驗證通過後**原樣**儲存與回傳（不加尾斜線、不正規化大小寫） |
| 副檔名 | 不檢查（`.glb`、`.gltf`、無副檔名皆可） |

實作提示：用 `urllib.parse.urlsplit` 檢查 `scheme`、`hostname`、並存取 `.port`（越界時拋 `ValueError` → 轉為驗證錯誤）。勿用 `HttpUrl` 型別直接輸出，因其會正規化字串。

合法例：`https://cdn.example.com/models/chair.glb`、`http://localhost:8000/a.gltf`、`HTTPS://EXAMPLE.COM/A.GLB`、`https://example.com`。
不合法例：`example.com/a.glb`（無 scheme）、`ftp://example.com/a.glb`、`https://exa mple.com/a.glb`、`""`。
邊界：總長 2048 → 201；2049 → 422。

### 5.4 Vector3（`position`、`rotation`、`scale` 共通）

| 規則 | 細節 |
|------|------|
| 必填 | 三個向量欄位在 POST/PUT 皆必填，缺少 → 422 |
| 型別 | 必須是 JSON 物件；陣列 `[1,2,3]` → 422 |
| 分量 | `x`、`y`、`z` 三個都必須存在，缺任一 → 422 |
| 分量型別 | JSON number（整數或浮點數）；字串 `"1.5"`、布林 `true`、`null` → 422 |
| 有限數值 | `NaN`、`Infinity`、`-Infinity`、溢位為 inf 的值（如 `1e400`）→ 422 |

實作提示：分量型別用 `Annotated[float, Field(strict=True, allow_inf_nan=False)]`（Pydantic v2 strict float 接受 int、拒絕 str/bool）；Vector3 設 `model_config = ConfigDict(extra="forbid")`。
測試提示：`NaN`/`Infinity` 需以原始字串送出，如 `client.post("/objects", content='{"...":..., "position":{"x":NaN,"y":0,"z":0}}', headers={"Content-Type":"application/json"})`。

### 5.5 各向量範圍（皆為閉區間，除 scale 下界為開區間）

| 欄位 | 每個分量範圍 | 通過邊界 | 失敗邊界 |
|------|-------------|---------|---------|
| `position` | −1,000,000 ≤ v ≤ 1,000,000 | `1000000`、`-1000000`、`0` | `1000000.001`、`-1000000.001` |
| `rotation`（度，尤拉角 XYZ） | −360 ≤ v ≤ 360 | `360`、`-360`、`0`、`359.9` | `360.0001`、`-360.0001`、`720` |
| `scale` | 0 < v ≤ 10,000 | `0.0001`、`1`、`10000` | `0`、`-0.0`、`-1`、`10000.0001` |

- rotation 不做正規化（傳 `360` 回傳 `360.0`，不轉成 `0`）。

### 5.6 Path 參數 `id`

| 規則 | 行為 |
|------|------|
| 格式 | 須符合 `^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$` |
| 格式錯誤 | 422 `VALIDATION_ERROR`，`loc` 為 `["path","id"]`（例：`abc`、`123`、無連字號 32 碼、多一碼） |
| 大小寫 | 大寫 UUID 視為合法，查詢前轉小寫（大寫查詢可找到同一筆） |
| 格式正確但不存在 | 404 `NOT_FOUND` |

### 5.7 Query 參數（僅 `GET /objects`）

| 參數 | 型別 | 預設 | 範圍 | 違規 |
|------|------|------|------|------|
| `limit` | int | 50 | 1 ～ 100（含） | `0`、`101`、`abc`、`1.5` → 422 |
| `offset` | int | 0 | ≥ 0 | `-1`、`abc` → 422 |

- 未定義的 query 參數忽略（不報錯）。

### 5.8 驗證優先順序

FastAPI 在進入 handler 前驗證 path、query、body；因此 **422 優先於 404**：對不存在的合法 id 送無效 body 的 PUT → 422。

---

## 6. 端點細節

### 6.1 `GET /objects` — 列表

- 排序：`created_at` 升冪，相同時以 `id` 升冪。
- 回應 200：

```json
{
  "items": [
    {
      "id": "3f2b8c1e-9a4d-4e7b-8c21-5d6f7a8b9c0d",
      "name": "Chair",
      "model_url": "https://cdn.example.com/models/chair.glb",
      "position": { "x": 1.0, "y": 0.0, "z": -2.5 },
      "rotation": { "x": 0.0, "y": 90.0, "z": 0.0 },
      "scale": { "x": 1.0, "y": 1.0, "z": 1.0 },
      "created_at": "2026-11-18T08:30:00.123456Z",
      "updated_at": "2026-11-18T08:30:00.123456Z"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

- `total` 為資料表總筆數（不受 limit/offset 影響）。
- 無資料時：`{"items": [], "total": 0, "limit": 50, "offset": 0}`。
- `offset` 超過總數 → 200，`items` 為 `[]`。
- 錯誤：422（query 驗證失敗）。

### 6.2 `GET /objects/{id}` — 單筆

- 200：回傳單一 SceneObject（同 6.1 items 內元素格式）。
- 404：`{"error":{"code":"NOT_FOUND","message":"Object not found","details":[]}}`
- 422：id 格式錯誤。

### 6.3 `POST /objects` — 新增

請求：

```json
{
  "name": "Chair",
  "model_url": "https://cdn.example.com/models/chair.glb",
  "position": { "x": 1, "y": 0, "z": -2.5 },
  "rotation": { "x": 0, "y": 90, "z": 0 },
  "scale": { "x": 1, "y": 1, "z": 1 }
}
```

- 201：回傳完整 SceneObject（含伺服器產生的 `id`、`created_at`、`updated_at`，且兩時間相等）。
- 回應 header `Location: /objects/{id}`。
- 422：任何驗證失敗（第 5 節）。驗證失敗時**不得**寫入資料庫（之後 `total` 不變）。

### 6.4 `PUT /objects/{id}` — 整筆取代

- 請求 body 規則與 POST **完全相同**（五個欄位皆必填、禁止額外欄位）；不支援部分更新。
- 200：回傳更新後 SceneObject。`id`、`created_at` 不變；`updated_at` 更新為目前時間，且 `updated_at >= created_at`（測試斷言 `>=`，避免時鐘解析度問題）。
- 404：id 格式正確但不存在（body 合法時）。
- 422：id 格式錯誤或 body 驗證失敗；失敗時原資料不得被修改。
- PUT **不會**建立新資源（不存在即 404）。

### 6.5 `DELETE /objects/{id}` — 刪除

- 204：刪除成功，無 response body。
- 再次 DELETE 同 id → 404；之後 GET 同 id → 404。
- 422：id 格式錯誤。

---

## 7. 資料庫設定與測試替換

### 7.1 `app/database.py` 介面（必須提供）

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./xr_objects.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- 所有路由**必須**透過 `Depends(get_db)` 取得 Session，不可直接使用模組層級 Session。
- `DATABASE_URL` 於模組匯入時讀取；只支援 SQLite URL（`connect_args` 為 SQLite 專用）。

### 7.2 替換方式（兩者皆須可用）

**方式 A：環境變數**（整合測試／手動執行）

```
DATABASE_URL=sqlite:///./test.db  python -m pytest -v
```
需在 `import app` 之前設定（例如在 `conftest.py` 最上方 `os.environ.setdefault(...)`）。

**方式 B：dependency override（建議，tester 預設採用）**

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db

@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,           # 讓 in-memory DB 在多連線間共用
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
```

- 每個測試函式取得全新空資料庫，測試間互不影響。
- lifespan 中的 `create_all` 作用於預設 engine，不影響 override 的測試 DB（可接受）。
- 測試不得寫入專案目錄下的 `xr_objects.db`。

---

## 8. 必測案例清單（tester 最低覆蓋）

| # | 案例 | 預期 |
|---|------|------|
| 1 | POST 合法 body | 201、回傳欄位完整、id 為小寫 UUID、`created_at == updated_at`、有 `Location` |
| 2 | GET 列表空 / 有資料 / limit+offset / total | 200，格式如 6.1 |
| 3 | GET 單筆存在 / 不存在 / id 格式錯誤 | 200 / 404 / 422 |
| 4 | PUT 合法 / 不存在 / 無效 body / 無效 id | 200 / 404 / 422 / 422；created_at 不變 |
| 5 | DELETE 存在 / 再刪 / 不存在 / 無效 id | 204 / 404 / 404 / 422 |
| 6 | name：缺少、`""`、`"   "`、101 字、100 字、前後空白被去除、非字串、含控制字元 | 422/422/422/422/201/201/422/422 |
| 7 | model_url：無 scheme、ftp、javascript:、含空白、無 host、port 越界、2048/2049 字、原樣回傳 | 依 5.3 |
| 8 | 向量：缺分量、多分量、字串分量、布林分量、null、陣列格式、NaN、Infinity、1e400 | 422 |
| 9 | 範圍邊界：position ±1e6、rotation ±360/±360.0001、scale 0/0.0001/10000/10000.0001/負值 | 依 5.5 |
| 10 | 額外欄位：頂層 `foo`、`id`、`created_at`；向量內 `w` | 422 |
| 11 | 錯誤格式：所有 4xx 皆有 `error.code`/`message`/`details` | 依第 4 節 |
| 12 | 驗證失敗不寫入 / 不修改資料 | total 與原資料不變 |
| 13 | 405：`PATCH /objects/{id}` | 405 `METHOD_NOT_ALLOWED` |
| 14 | 大寫 UUID 查詢 | 找得到同一筆（200） |
