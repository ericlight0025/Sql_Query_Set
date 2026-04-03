# ld-query-sql-gui 檔案放置規格書

## 1. 目的

- 定義本專案的檔案放置標準，避免程式、設定、產出、文件混放在根目錄。
- 降低維護成本，確保 GUI/CLI/批次啟動路徑一致且可預測。

## 2. 根目錄保留原則

根目錄只保留「入口、設定、專案說明、主要資料夾」：

- `gui.py`：根目錄 GUI 啟動入口（wrapper）
- `run_ld_query_sql_gui.bat`：Windows 啟動入口
- `settings.json`：預設設定檔
- `ld_query_sql_tool/`：主程式套件
- `data/`：輸入/輸出/模板資料
- `tests/`：測試
- `docs/`：規格與文件
- `logs/`：執行紀錄（可忽略版本控管）

## 3. 主程式檔案放置規則

### 3.1 Python 程式

- 全部核心程式必須在 `ld_query_sql_tool/`
- 不可在根目錄新增第二份商業邏輯程式
- 入口（`gui.py`、bat）只能呼叫套件，不可承擔業務邏輯

### 3.2 設定與輸入輸出

- 設定：`settings.json`（根目錄唯一）
- 輸入 SQL：`data/input/`
- 輸出 SQL：`data/output/`
- 模板：`data/templates/`

### 3.3 文件

- 所有規格書、計畫、review 文件放 `docs/`
- 根目錄不再放置 `*_spec.md`、`plan.md`、`code_review.md`、`todo.md`

## 4. 非主線檔案放置規則

### 4.1 Legacy 檔案

- 本專案目前不保留 Java 程式。
- 如未來需要保留歷史檔，再放入 `legacy/`，但預設應移除。

### 4.2 暫存與快取

- `__pycache__/`、`.pytest_cache/`、`.tmp_test/` 不納入版本控管
- 建議加入 `.gitignore`

## 5. 建議目錄結構（目標）

```text
ld-query-sql-gui/
  gui.py
  run_ld_query_sql_gui.bat
  settings.json
  ld_query_sql_tool/
    __init__.py
    cli.py
    gui.py
    workflow.py
    config_service.py
    models.py
    sql_render_service.py
    sql_validation_service.py
    sql_service.py
    preview_service.py
    log_service.py
    syntax_highlighter.py
  data/
    input/
    output/
    templates/
  tests/
  docs/
    file-placement-spec.md
    system-spec.md
    plan.md
    code-review.md
    todo.md
  logs/
```

## 6. 立即整理清單（MVP）

1. 建立 `docs/`，把根目錄文件移入：
   - `system_spec.md -> docs/system-spec.md`
   - `plan.md -> docs/plan.md`
   - `code_review.md -> docs/code-review.md`
   - `todo.md -> docs/todo.md`
2. Java 檔不保留，直接自版本控管移除。
3. 保留根目錄只剩入口與設定。
4. 補 `.gitignore` 排除快取與 log。

## 7. 驗收條件

- 根目錄不出現核心邏輯 Python 檔（除入口 wrapper）
- 所有文件集中於 `docs/`
- 所有 legacy 程式集中於 `legacy/`
- 啟動命令 `run_ld_query_sql_gui.bat` 與 `python gui.py` 仍可正常執行
