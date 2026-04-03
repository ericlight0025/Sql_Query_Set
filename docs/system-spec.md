# LD Query SQL GUI 系統規格書（現況版）

## 1. 文件目的

- 定義目前可運作版本的實際規格。
- 統一 GUI / CLI / 設定檔 / 路徑規則，避免文件與實作脫節。

## 2. 系統目標

- 將原始 SQL 套入 `data/templates/ManagerSql.sql` 模板。
- 產出可交付 SQL 到 `data/output/`（或設定指定目錄）。
- 提供 GUI 與 CLI 兩種入口，核心流程共用同一套服務。

## 3. 專案結構（現況）

```text
.
├─ gui.py
├─ run_ld_query_sql_gui.bat
├─ settings.json
├─ ld_query_sql_tool/
├─ data/
│  ├─ input/
│  ├─ output/
│  └─ templates/
├─ tests/
└─ docs/
```

## 4. 核心模組責任

- `ld_query_sql_tool/gui.py`
  - GUI 畫面、分頁、按鈕事件、訊息顯示。
- `ld_query_sql_tool/config_service.py`
  - `settings.json` 讀寫、欄位正規化、路徑相對化。
- `ld_query_sql_tool/workflow.py`
  - 執行流程組裝：驗證 -> 生成 -> 回傳結果。
- `ld_query_sql_tool/sql_render_service.py`
  - SQL 內容處理、CLOB 組裝、模板渲染。
- `ld_query_sql_tool/sql_validation_service.py`
  - 路徑與設定驗證（由 workflow 呼叫）。
- `ld_query_sql_tool/sql_service.py`
  - SQL 檔案輸出流程。

## 5. 設定檔規格（settings.json）

### 5.1 位置

- 專案根目錄：`settings.json`

### 5.2 主要欄位

- `oa_no`：系統號碼
- `query_template`：輸出檔名稱主體
- `root_dir`：路徑基準（建議 `.`）
- `output_dir`、`sql_file`、`title_file`、`template_file`
- `sql_source_mode`：`file` 或 `inline`
- `sql_text`：inline 模式使用
- `start_date`、`end_date`
- `overwrite_mode`：`prompt` / `overwrite` / `rename` / `error`
- `python_exe`：GUI 啟動與測試路徑
- `ui_font_size`

### 5.3 路徑規則

- 專案內路徑預設存相對路徑（相對於 `root_dir`）。
- 執行時統一解析為絕對路徑。

## 6. GUI 規格

### 6.1 主分頁

- `設定與執行`
- `檢視與輸出`
- `系統設定`

### 6.2 SQL 分頁（檢視與輸出）

- `原始 SQL (可編輯)`
- `目標輸出 SQL (模板渲染後)`
- `日期替換`

### 6.3 操作功能

- SQL 分頁都支援：
  - 複製內容
  - 另存 `.sql`
- 系統設定支援：
  - 根目錄設定與瀏覽
  - Python.exe 設定與測試
  - 字體大小儲存

## 7. 日期替換規格（現況）

- 第一頁日期輸入（開始/結束）主要供測試預覽使用。
- `日期替換` 分頁將 `startDate/endDate` 類 placeholder 替換後顯示。
- PRD 可保留 placeholder，不強制寫死日期。
- 執行流程不因 placeholder 存在而阻擋。

## 8. 執行前驗證（GUI）

- 必填欄位檢查：
  - 系統號碼、Query 前綴名稱、來源模式、模板檔、欄位檔
- 檔案存在性檢查：
  - SQL 檔（file 模式）
  - 模板 SQL 檔
  - 欄位文字檔
- 驗證失敗會中止執行並顯示訊息。

## 9. 日誌規格

- 顯示於 GUI `執行紀錄` 區塊。
- 每筆附時間戳：`[HH:MM:SS] 訊息`。

## 10. 啟動方式

### 10.1 GUI

- `run_ld_query_sql_gui.bat`
- 或 `python gui.py`

### 10.2 CLI

- `python -m ld_query_sql_tool.cli --help`

