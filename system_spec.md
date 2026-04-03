# LD Query SQL GUI 系統規格書

## 1. 文件目的

- 本文件定義 `ld-query-sql-gui` 的目標系統規格、模組邊界、資料模型、流程規則與驗證標準。
- 本文件優先處理目前 package 規劃不完整的問題，作為後續重構與功能擴充的唯一架構依據。
- 本文件不描述一次性實作細節，而是描述系統應該長成什麼樣。

## 2. 系統目標

- 將原始 SQL 與 `ManagerSql.sql` 模板組合，輸出可交付的管理 SQL 檔案。
- 提供 GUI 與 CLI 兩種操作入口，但核心邏輯只能有一套。
- 優先避免產出錯誤 SQL、危險 `DELETE`、錯誤引號、漏填欄位與誤覆寫輸出。
- 提供可預覽、可驗證、可追查的工作流程。

## 3. 範圍

### 3.1 本次納入

- GUI 操作流程
- CLI 操作流程
- 設定檔讀寫
- SQL 來源管理
- SQL 靜態驗證
- SQL 模板渲染
- 結果預覽
- 語法高亮
- 日誌與錯誤回報
- 輸出檔衝突處理

### 3.2 本次不納入

- 直接連資料庫做語法驗證
- 直接執行產出的 SQL
- Oracle 線上 explain plan
- 多使用者或網頁化架構
- 複雜外掛系統

## 4. 設計原則

- Python 為唯一核心實作語言。
- GUI、CLI、批次入口都必須共用相同 workflow。
- 驗證與渲染必須可測試，不能綁在 GUI event handler 裡。
- UI 只處理輸入與顯示，不承擔商業邏輯。
- 檔案 IO、設定檔、log、打開資料夾都屬於 infrastructure，不可散在各模組。
- 新功能必須可單獨回滾，不得破壞既有產線。

## 5. 目前問題

- `gui.py` 同時承擔畫面控制、設定保存、覆寫判斷、workflow 啟動，責任偏多。
- `sql_service.py` 同時處理檔名驗證、模板檢查、輸出檔衝突、SQL 渲染，邊界過大。
- 缺少專用的 SQL 驗證模組，後續新增引號檢查、`DELETE` 規則、括號檢查時會持續膨脹。
- 缺少預覽模型與高亮模組，之後 tab 預覽與語法亮度會無處安放。
- 目前資料模型尚未涵蓋：
- SQL 來源模式
- 內嵌 SQL 文字
- 開始日期與結束日期
- SQL 檢查結果
- 預覽資料

## 6. 目標 package 結構

目標 package 應調整為以下結構：

```text
ld_query_sql_tool/
  __init__.py
  models.py
  config_service.py
  workflow.py
  sql_render_service.py
  sql_validation_service.py
  preview_service.py
  log_service.py
  gui.py
  syntax_highlighter.py
```

### 6.1 模組責任

- `models.py`
  定義 dataclass、enum、常數，不放任何 UI 或 IO 邏輯。

- `config_service.py`
  專責 `settings.json` 讀寫、設定值標準化、預設值合併。

- `workflow.py`
  組裝完整執行流程：
  驗證輸入 -> 取得原始 SQL -> 執行 SQL 靜態檢查 -> 渲染模板 -> 寫檔 -> 寫 log -> 回傳結果。

- `sql_render_service.py`
  專責 token replacement、CLOB 組裝、模板渲染、輸出檔名計算。

- `sql_validation_service.py`
  專責輸入驗證與 SQL 靜態檢查。

- `preview_service.py`
  專責建立 GUI 預覽資料：
  原始 SQL、替換日期後 SQL、最終模板 SQL。

- `log_service.py`
  專責日誌落地與日誌格式。

- `gui.py`
  專責畫面元件、事件綁定、顯示結果。

- `syntax_highlighter.py`
  專責 SQL 關鍵字、字串、註解、數字的高亮標記。

## 7. 資料模型規格

### 7.1 enum

- `SqlSourceMode`
  - `file`
  - `inline`

- `OverwriteMode`
  - `prompt`
  - `error`
  - `overwrite`
  - `rename`

- `ValidationSeverity`
  - `error`
  - `warning`

### 7.2 dataclass

- `DateRange`
  - `start_date: str`
  - `end_date: str`

- `SqlGenerationConfig`
  - `oa_no: str`
  - `query_template: str`
  - `output_dir: Path`
  - `sql_source_mode: SqlSourceMode`
  - `sql_file: Path | None`
  - `sql_text: str`
  - `content: str`
  - `author: str`
  - `title_file: Path`
  - `template_file: Path`
  - `date_range: DateRange`
  - `overwrite_mode: OverwriteMode`
  - `open_output_dir: bool`

- `SqlValidationIssue`
  - `severity: ValidationSeverity`
  - `rule_id: str`
  - `message: str`
  - `line_no: int | None`

- `PreviewPayload`
  - `raw_sql: str`
  - `resolved_sql: str`
  - `rendered_sql: str`

- `WorkflowResult`
  - `success: bool`
  - `messages: list[str]`
  - `issues: list[SqlValidationIssue]`
  - `preview: PreviewPayload | None`
  - `output_file: Path | None`
  - `log_file: Path`
  - `error_message: str`

- `AppSettings`
  - `oa_no`
  - `query_template`
  - `output_dir`
  - `sql_source_mode`
  - `sql_file`
  - `sql_text`
  - `content`
  - `author`
  - `title_file`
  - `template_file`
  - `start_date`
  - `end_date`
  - `overwrite_mode`
  - `open_output_dir`

## 8. 設定檔規格

設定檔名稱：

- `settings.json`

位置：

- 專案根目錄

格式：

```json
{
  "oa_no": "1141202337-00",
  "query_template": "001-ph-LDNCS2WKARDQUERY_Update",
  "output_dir": "C:/path/output",
  "sql_source_mode": "file",
  "sql_file": "C:/path/input.sql",
  "sql_text": "",
  "content": "查詢內容",
  "author": "陳OO",
  "title_file": "C:/path/欄位.txt",
  "template_file": "C:/path/ManagerSql.sql",
  "start_date": "2026-04-01",
  "end_date": "2026-04-30",
  "overwrite_mode": "prompt",
  "open_output_dir": false
}
```

規則：

- 缺欄位時自動套預設值。
- 不合法 enum 值要回退預設值。
- `sql_source_mode=file` 時，`sql_file` 必須有效。
- `sql_source_mode=inline` 時，`sql_text` 必須非空。

## 9. SQL 來源規格

系統必須支援兩種 SQL 來源：

- 檔案模式
- 直接輸入模式

規則：

- 檔案模式：
  讀取 `.sql` 檔案全文，保留原始換行。
- 直接輸入模式：
  使用 GUI 編輯區內容作為原始 SQL。
- 兩種模式都要進入同一套驗證與渲染流程。

## 10. 日期區間規格

GUI 必須提供：

- `開始日期`
- `結束日期`

格式：

- `YYYY-MM-DD`

Token：

- `${startDate}`
- `${endDate}`

替換規則：

- 先對原始 SQL 進行 token replacement。
- 再將替換後的 SQL 轉成 CLOB 並套入 `ManagerSql.sql`。
- `ManagerSql.sql` 內若也含上述 token，允許同樣替換。

限制：

- 系統只做字串替換，不強制包成 `DATE` 或 `TO_DATE()`。
- SQL 語法格式由模板與原始 SQL 自行決定。

## 11. 輸入驗證規格

執行前必須一次性回傳完整驗證結果，不可只丟第一個錯誤。

### 11.1 一般欄位

- `oa_no` 不可為空
- `query_template` 不可為空
- `content` 不可為空
- `author` 不可為空
- `start_date` 與 `end_date` 不可為空
- `start_date <= end_date`

### 11.2 路徑

- `output_dir` 若不存在，可自動建立
- `output_dir` 若是檔案，直接錯誤
- `title_file` 必須存在
- `template_file` 必須存在
- `sql_source_mode=file` 時 `sql_file` 必須存在

### 11.3 檔名

- `query_template` 不可包含 Windows 非法字元
- 不可使用保留名稱
- 不可尾端空白或句點

### 11.4 模板

- `ManagerSql.sql` 必須至少包含：
  - `${oaNo}`
  - `'${sqlScript}'`
  - `${content}`
  - `${author}`
  - `${title}`
  - `${sysdate}`

## 12. SQL 靜態驗證規格

### 12.1 必做規則

- 原始 SQL 不可為空
- 原始 SQL 不可只有註解或空白
- 單引號必須成對
- 括號必須平衡
- `DELETE` 語句必須包含 `WHERE`

### 12.2 錯誤等級

- `error`
  阻擋執行
- `warning`
  顯示提醒，但不阻擋執行

### 12.3 規則代碼

- `INPUT_REQUIRED`
- `PATH_INVALID`
- `TEMPLATE_TOKEN_MISSING`
- `SQL_EMPTY`
- `SQL_QUOTE_UNBALANCED`
- `SQL_PAREN_UNBALANCED`
- `SQL_DELETE_WITHOUT_WHERE`

## 13. 模板渲染規格

執行順序：

1. 取得原始 SQL
2. 替換日期 token
3. 執行 SQL 靜態檢查
4. 將原始 SQL 按 10 行切塊，轉成 `to_clob(...)`
5. 將 CLOB 與其他欄位套入 `ManagerSql.sql`
6. 產出最終 SQL 文字
7. 依覆寫規則寫入檔案

字串逃脫規則：

- 單引號 `'` 必須轉成 `''`
- 保留原始換行

## 14. 輸出檔規格

輸出檔命名：

- `${query_template}.sql`

衝突策略：

- `prompt`
  GUI 詢問使用者
- `error`
  直接失敗
- `overwrite`
  直接覆寫
- `rename`
  自動改成 `${query_template}_1.sql`

## 15. GUI 規格

### 15.1 主畫面區塊

- 基本欄位區
- SQL 來源選擇區
- 日期區間區
- 執行按鈕區
- 驗證訊息區
- 預覽區
- log 區

### 15.2 預覽區

必須使用 tab：

- `原始 SQL`
- `輸出結果`

規則：

- 原始 SQL tab 顯示實際送去驗證與渲染前的 SQL。
- 輸出結果 tab 顯示模板渲染後的完整 SQL。
- 執行失敗時也應保留原始 SQL 預覽。

### 15.3 語法高亮

高亮最少包含：

- SQL 關鍵字
- 字串
- 註解
- 數字

限制：

- 若 tkinter 原生高亮維護成本過高，先以 tag-based 實作，不導入重型 UI 框架。

### 15.4 執行控制

- 執行中禁用執行按鈕
- 執行完成恢復按鈕
- 執行前先顯示完整驗證結果

## 16. CLI 規格

CLI 必須支援：

- 讀取 `settings.json`
- 覆蓋設定檔欄位
- 控制覆寫模式
- 控制是否開啟輸出資料夾
- 輸出驗證訊息、執行訊息與錯誤訊息

CLI 不處理：

- `prompt` 互動式覆寫詢問

CLI 規則：

- `prompt` 進入 CLI 時必須降為 `error`

## 17. 日誌規格

每次執行都必須寫入 log。

至少包含：

- 執行時間
- success / failed
- 輸入摘要
- SQL 來源模式
- 輸出檔案
- 驗證錯誤
- 例外訊息

## 18. 測試規格

### 18.1 單元測試

- 設定檔讀寫
- SQL token replacement
- 單引號檢查
- 括號檢查
- `DELETE` 無 `WHERE` 攔截
- 檔名合法性
- 覆寫 / 自動改名
- 日期 token 替換
- 預覽內容生成

### 18.2 手動測試

- GUI 可正常啟動
- 檔案模式可產生 SQL
- 直接輸入模式可產生 SQL
- 日期區間可正確替換
- tab 可切換檢視
- 高亮不影響複製與輸出

## 19. 實作順序

### 第一階段：補齊資料模型與 package 邊界

- 調整 `models.py`
- 拆出 `sql_validation_service.py`
- 拆出 `sql_render_service.py`
- 拆出 `log_service.py`
- 定義 `preview_service.py`

### 第二階段：補齊安全規則

- 一次性完整輸入驗證
- 單引號與括號檢查
- `DELETE` 無 `WHERE` 攔截

### 第三階段：補齊使用流程

- SQL 來源模式切換
- 日期區間欄位
- 預覽 tabs

### 第四階段：補齊顯示體驗

- SQL 語法高亮

## 20. 驗收標準

- package 模組責任清楚，不再由單一檔案承擔過多角色
- GUI 與 CLI 共用相同 workflow
- 所有必要輸入可在執行前被完整檢查
- 危險 SQL 可在執行前被攔截
- 使用者可直接在畫面預覽原始 SQL 與輸出結果
- 日期與 SQL 來源模式可被設定、保存與重用
- 系統具備基本測試覆蓋與 log 追查能力
