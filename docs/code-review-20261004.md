# Sql_Query_Set code review 與修正紀錄

審查基準：`main` 的 `893ca728cf0d1acf2037df743d63923cbdd08918`。修正分支：`fix/sql-generation-safety-20261004`。

## 已修正問題

| 優先級 | 問題與影響 | 修正與驗證 |
| --- | --- | --- |
| P1 | CLI 缺少模組啟動入口，README 的 `python -m ld_query_sql_tool.cli` 不會執行任何工作 | 增加 `SystemExit(main())`，以實際子程序驗證成功、衝突結束碼及自動更名 |
| P1 | CLOB 僅每 10 行分段，長行、中文或大量單引號可能超出 Oracle 字串位元組上限 | 10 行區塊內再按跳脫後 UTF-8 4,000 位元組切段；測試完整重組、Unicode、CRLF 與引號 |
| P1 | 連續 `.replace()` 會把插入 SQL 及描述內的同名占位符再次替換 | 原始模板單次掃描；測試 `${author}`、`${title}`、`${sysdate}` 原文保留 |
| P1 | 直接開啟輸出及設定檔為 `w`，失敗時會先截斷既有內容 | 同目錄暫存、flush/fsync 後原子發布；注入磁碟寫入及發布失敗，確認原檔與 JSON 完整 |
| P1 | 輸出先檢查存在再寫入，並行執行可能覆蓋另一程序的檔案 | `error` / `rename` 以原子硬連結發布；8 個並行寫入驗證單一勝出或全部獨立完整輸出 |
| P1 | 輸出可與來源 SQL 或範本重名，覆寫模式會破壞輸入 | 檢查實際路徑及硬連結，測試來源、欄位、範本與硬連結全部受保護 |
| P2 | GUI 日期替換先處理裸字，會留下 `:` / `${}` 或誤改較長識別字 | 與核心服務共用單次匹配；支援四種占位符且保留 `startDateColumn` 等名稱；手動套用前驗證日期區間 |
| P2 | 未設定日期的預覽會把占位符替換為空字串 | 空日期保留原始占位符；最終 SQL 仍使用原始 SQL 而非測試日期 |
| P2 | 範本讀取或日誌寫入錯誤可能直接逸出，或把已成功產生的 SQL 誤報失敗 | 範本 I/O / UTF-8 錯誤回傳驗證問題；日誌失敗附警告，`log_file=None` |
| P2 | 背景執行緒呼叫 Tk `after`，異常時按鈕可能停在處理中 | worker 僅送結果到佇列，主執行緒輪詢；背景異常及啟動失敗會恢復操作 |
| P2 | 自訂設定檔儲存時連帶覆蓋預設設定；回存失敗打斷成功提示 | 只儲存指定 profile，設定失敗警告不掩蓋 SQL 成功 |
| P2 | 設定存取的相對路徑基準不一致，GUI 載入來源也忽略 `root_dir` | 統一以專案根目錄解析相對 `root_dir`，GUI 編輯器遵循同一規則 |
| P2 | CLI 在驗證前回存設定，失敗的輸入仍污染 profile | 僅產生成功後回存；回存失敗另報 SQL 已產生並返回 `1` |
| P2 | Windows 啟動檔依賴個人虛擬環境，手工刪 JSON 引號／逗號會破壞路徑 | PowerShell 正式解析 JSON，未指定 Python 時使用 `py -3` / PATH `python` |
| P2 | Windows 檔名驗證未排除控制字元 | 拒絕名稱中換行、Tab、NUL 等字元 |
| P2 | 舊三階段 API 缺設定時直接 KeyError，相同輸出名稱會互相覆寫 | 執行前檢查階段齊全及輸出路徑互異，回傳結構化失敗 |
| P2 | 舊 GUI 測試匯入已移除常數與方法，整組測試無法載入 | 改為現行 GUI 流程的無顯示器回歸測試，保留核心既有測試並校正日期預覽契約 |
| P2 | 未被使用的 `guitemp.py` 含損壞文字與未閉合字串，整個套件編譯失敗 | 確认沒有引用後移除過期備份；套件全體語法檢查通過 |

## 驗證結果

環境：Linux、Python 3.12.14。47 項自動測試全部通過，未跳過測試。

```bash
python -m unittest discover -s tests -v
python -m compileall -q ld_query_sql_tool gui.py tests
python -m ld_query_sql_tool.cli --help
git diff --check
```

CLI 整合測試會從專案外工作目錄啟動真實 Python 子程序，使用自訂設定檔，檢查實際 SQL、原始占位符、拒絕覆寫及自動更名結果。GUI 測試使用替身物件驗證背景佇列、錯誤回報、控制項復原與設定保存，未啟動真實 Tk 視窗。

## 使用條件與驗收限制

- `error` / `rename` 需支援硬連結的檔案系統（例如 NTFS）。不支援的網路或外接檔案系統會明確失敗，不採用會競爭覆寫的降級做法。
- Oracle 字串限制參考 [Oracle Database 19c — Literals](https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/Literals.html)。本工具以 UTF-8 / AL32UTF8 分段；其他資料庫字元集須另行確認。
- 未連接 Oracle 執行產出的 SQL，尚未驗證目標資料表欄位長度、資料庫字元集及客戶端行為。
- 尚未在 Windows 執行 `.bat` 或驗證真實 Tk 視窗；需人工確認 Python 路徑含空白、逗號、中文時的啟動，以及視窗操作與日期預覽。
- 三階段 bundle API 仍是依序輸出，沒有跨檔案交易。中途失敗時 `output_files` 列出已完成檔案；目前 GUI 使用單檔流程。
