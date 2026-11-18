# Part B：XR 場景物件管理 API 資料庫方案比較

由 3 個 db-evaluator 子代理並行評估（各自只評估一個資料庫），主 Agent 驗證 JSON 格式後依總分排序。
評分 1～5 分：安裝＝安裝設定難易度、Python＝Python/FastAPI 整合、測試＝pytest 測試方便度、資料適配＝與場景物件資料結構的適配、擴充＝未來擴充性。
同分時依「測試」、再依「Python」分數排序。

| 排名 | 資料庫 | 安裝 | Python | 測試 | 資料適配 | 擴充 | 總分 | 優點 | 缺點 | 建議套件 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | SQLite | 5 | 5 | 5 | 4 | 3 | **22** | • Python 3.11 標準函式庫內建 sqlite3，不用另外安裝伺服器或做任何設定，資料就存在單一檔案裡。<br>• SQLAlchemy 2.x 和 SQLModel 對 SQLite 的支援很完整，搭配 FastAPI 的 Depends 依賴注入就能管理資料庫連線（Session）。<br>• pytest 可以用 sqlite:///:memory: 或 tmp_path 為每個測試建立隔離的資料庫，再用 dependency_overrides 換掉正式的 Session，速度快又不會互相干擾。<br>• position、rotation、scale 可以拆成 9 個 REAL 欄位，或另外存成 JSON 欄位，固定結構的場景物件很適合用關聯式資料表來存。 | • 同一時間只能有一個寫入者，多人同時大量寫入時效能會受限，不適合高併發的正式環境。<br>• 沒有原生的向量型別，x、y、z 只能拆成多個欄位或存成 JSON，查詢和驗證要靠 Pydantic 處理。<br>• 記憶體資料庫搭配 TestClient 時要設定 StaticPool 和 check_same_thread=False，否則不同執行緒看不到同一個資料庫。<br>• 未來要擴充到多台伺服器或雲端部署時，需要遷移到 PostgreSQL 這類資料庫，最好一開始就透過 ORM 和 Alembic 存取，之後比較好換。 | SQLAlchemy 2.x（或 SQLModel）+ 內建 sqlite3 驅動 |
| 2 | PostgreSQL | 2 | 5 | 3 | 4 | 5 | **19** | • 生態系成熟，可搭配 SQLAlchemy 2.x（同步用 psycopg 3，非同步用 asyncpg），FastAPI 官方文件與社群範例很多。<br>• 支援交易、約束與 CHECK，可確保 position/rotation/scale 的浮點欄位資料完整。<br>• 有 JSONB、陣列與 PostGIS 等擴充，以後想加空間查詢或彈性屬性都能直接支援。<br>• 可水平擴充、可做讀寫分離，正式環境部署很成熟，往後擴充不需要換資料庫。 | • 要另外安裝並啟動資料庫服務（本機安裝或 Docker），設定帳號、密碼與連線字串，對課堂作業來說比較麻煩。<br>• 在 Windows 上安裝與管理服務比較麻煩，換到別的機器還要重新設定環境。<br>• pytest 要建立獨立的測試資料庫，或用 testcontainers / pytest-postgresql 搭配每個測試結束後 rollback，不像 SQLite in-memory 那樣開箱即用。<br>• 這份作業只有單一資料表加簡單 CRUD，PostgreSQL 多數進階功能用不到，顯得大材小用。 | SQLAlchemy 2.x + psycopg 3（pytest 可搭配 pytest-postgresql 或 testcontainers-python） |
| 3 | MongoDB | 2 | 4 | 3 | 5 | 5 | **19** | • 文件型資料模型可直接把 position、rotation、scale 存成巢狀的 {x,y,z} 子文件，與 Pydantic 模型幾乎一對一對應。<br>• 官方 PyMongo 已內建非同步 API（取代已停止開發的 Motor），搭配 Beanie ODM 可直接用 Pydantic 定義文件，與 FastAPI 整合流暢。<br>• 不需要 schema migration，未來新增欄位（例如材質、標籤、階層關係）很容易。<br>• 內建 replica set 與 sharding，也有 Atlas 雲端服務，未來擴充性很好。 | • 需要另外安裝並執行 MongoDB 伺服器（本機安裝、Docker 或 Atlas），以課堂作業規模來說設定比 SQLite 麻煩很多。<br>• pytest 測試需要伺服器在執行中，或改用 mongomock / mongomock-motor 模擬，而模擬工具和真實行為可能有差異，非同步支援也有限制。<br>• ObjectId 需要額外轉換成字串才能放進 FastAPI 的回應模型，增加樣板程式碼。<br>• 沒有強制 schema，資料驗證完全靠應用層的 Pydantic，資料一致性要自己把關。 | PyMongo（內建 AsyncMongoClient）+ Beanie ODM；測試用 mongomock 或每個測試獨立的 test database |

## 選擇與理由

選擇 **SQLite**（總分 22，第 1 名），PostgreSQL 與 MongoDB 皆為 19 分。SQLite 在安裝、Python 整合與測試三項都拿到滿分：Python 內建驅動、不需另外架設資料庫伺服器，pytest 可為每個測試建立隔離的暫存資料庫，最符合課堂作業單機開發與自動化測試的需求。它的缺點是寫入併發與水平擴充較弱，因此實作時透過資料存取層隔離資料庫細節，未來若要正式上線可再遷移到擴充性滿分的 PostgreSQL。

原始 JSON：docs/agent-runs/1～3-db-evaluator.json
