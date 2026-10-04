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
- `ld_query_sql_tool/file_service.py`
  - 同目錄暫存、原子發布、並行更名及輸入檔保護，供 SQL / 設定檔 / GUI 另存共用。

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
- 相對 `root_dir` 以專案根目錄為基準；自訂設定檔位置不影響這個規則。
- 設定原子回存；自訂設定檔不會連帶寫入預設設定。自動回存限 SQL 產生成功後。

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
- `日期替換` 分頁支援 `${startDate}`、`:startDate`、`?startDate?`、獨立 `startDate`（endDate 同理），以單次掃描替換，避免殘留外層符號或誤改較長識別字。
- 日期同時留空則保留原始占位符；提供時須有效且開始不晚於結束。
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
- 範本無法讀取或非 UTF-8 時回傳驗證錯誤，背景執行異常也會回到 GUI 恢復按鈕。
- 背景執行緒僅將結果送入佇列，所有 Tk 操作由主執行緒完成。

## 9. 日誌規格

- 顯示於 GUI `執行紀錄` 區塊。
- 每筆附時間戳：`[HH:MM:SS] 訊息`。
- 寫入 `logs/ld_query_sql_gui.log` 失敗時只追加警告，`WorkflowResult.log_file` 為 `None`，不改變 SQL 成敗。

## 10. 啟動方式

### 10.1 GUI

- `run_ld_query_sql_gui.bat`
- 優先使用 JSON 設定的 `python_exe`；無設定時改用 `py -3` 或 PATH 上的 `python`，需 Python 3.11 以上。
- 或 `python gui.py`

### 10.2 CLI

- `python -m ld_query_sql_tool.cli --help`

## 11. 輸出完整性

- CLOB 每 10 行分段並限制跳脫後 UTF-8 內容每段最多 4,000 位元組；原始 SQL 日期占位符保留。
- 模板只掃描一次，插入內容不再觸發模板替換。
- 覆寫使用 `os.replace`；拒絕覆寫與自動更名使用 `os.link` 原子發布，避免檢查檔案存在與寫入之間的競爭。
- 不支援硬連結的檔案系統會回報失敗，不降級為可能覆寫的操作。
- SQL 產生流程檢查來源、欄位、範本的實際路徑與硬連結，禁止覆蓋輸入。
- 舊的三階段 bundle API 先檢查設定齊全與輸出檔名互異。它依序產出而非跨檔案交易；中途失敗時透過 `output_files` 回報已完成檔案，供呼叫端處理。
