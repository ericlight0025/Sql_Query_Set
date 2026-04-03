# LD Query SQL GUI 開發計畫（現況版）

## 1. 目標

- 維持 YouTube/產線可用的 SQL 產生工具
- 核心邏輯集中在 Python 套件 `ld_query_sql_tool/`
- GUI 與 CLI 共用同一套 workflow，降低維護成本
- 以低風險、小步快跑方式持續優化

## 2. 已完成

### 2.1 結構整理
- 根目錄僅保留入口與設定（`gui.py`、`run_ld_query_sql_gui.bat`、`settings.json`）
- 文件集中至 `docs/`
- Java 與舊相容入口已移除

### 2.2 GUI 功能
- 深色主題與主題切換
- SQL 三分頁：
  - 原始 SQL（可編輯）
  - 目標輸出 SQL（模板渲染後）
  - 日期替換（測試預覽）
- 每個 SQL 分頁支援：
  - 複製內容
  - 另存 `.sql`
- 系統設定分頁支援：
  - 根目錄（`root_dir`）
  - Python.exe 路徑
  - 文字大小
  - 儲存設定
  - 測試 Python.exe

### 2.3 設定與路徑
- `settings.json` 支援 `root_dir`
- `output_dir/sql_file/title_file/template_file` 可使用相對路徑
- 儲存設定時會盡量寫成相對於 `root_dir` 的路徑

### 2.4 驗證與安全
- 執行前必填檢查
- 檔案存在性檢查（SQL 檔、模板檔、欄位檔）
- 日誌含時間戳，便於追查

## 3. 目前策略（重要）

- PRD 腳本允許保留 `startDate/endDate` placeholder
- 日期替換只作為「測試與預覽」功能，不強制寫死日期
- 不再以「未替換日期」阻擋執行

## 4. 下一步（建議）

1. README 補完整操作流程圖文（目前已有主畫面）
2. 將 `docs/system-spec.md` 拆為：
   - 使用規格
   - 開發規格
3. 增加最小回歸測試：
   - `root_dir` 路徑解析
   - 系統設定儲存/載入
   - 日期替換預覽

