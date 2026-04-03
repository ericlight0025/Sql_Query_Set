# LD Query SQL GUI

`ld-query-sql-gui` 是一個用 Python 製作的 SQL 產生工具。  
用途是把「原始 SQL」套進 `ManagerSql.sql` 模板，輸出可交付的管理 SQL 檔，並提供 GUI / CLI 兩種操作方式。

## 這個工具在做什麼

- 管理 OA Query SQL 產生流程（模板渲染、輸出檔產生、衝突處理）
- 提供 SQL 編輯與預覽（原始 / 模板渲染後 / 日期替換測試）
- 支援語法亮度、複製內容、另存 SQL
- 支援 `settings.json` 設定保存（含根目錄、Python 路徑、字體大小）
- 支援輸出前基本驗證（必填欄位、檔案存在性）

## 快速開始

### 1) GUI（Windows）

```bat
run_ld_query_sql_gui.bat
```

或

```bash
python gui.py
```

### 2) CLI

```bash
python -m ld_query_sql_tool.cli --help
```

範例：

```bash
python -m ld_query_sql_tool.cli ^
  --oa-no 1151234567-00 ^
  --query-template 001-ph-LDOOOO_Update ^
  --sql-source-mode file ^
  --sql-file data/input/source.sql ^
  --save-settings
```

## 設定檔（settings.json）

重點欄位：

- `root_dir`: 路徑基準目錄（建議 `.`，即專案根目錄）
- `output_dir`, `sql_file`, `title_file`, `template_file`: 可用相對於 `root_dir` 的路徑
- `python_exe`: 啟動用 Python 路徑（可在系統設定頁測試）
- `sql_source_mode`: `file` 或 `inline`
- `overwrite_mode`: `prompt` / `overwrite` / `rename` / `error`

## 日期替換說明

- 第一頁輸入的日期是「測試替換」用途
- `日期替換` 分頁會將 SQL 內的 `startDate` / `endDate`（含 `?startDate?` 類型）替換後顯示
- PRD 腳本可保留 placeholder，不會強制寫死日期

## 專案結構

```text
.
├─ gui.py                         # 根目錄 GUI 啟動入口
├─ run_ld_query_sql_gui.bat       # Windows 啟動入口
├─ settings.json                  # 設定檔
├─ ld_query_sql_tool/             # 核心程式
├─ data/
│  ├─ input/
│  ├─ output/
│  └─ templates/
├─ tests/
└─ docs/
```

## 開發與測試

語法檢查：

```bash
python -m py_compile ld_query_sql_tool/gui.py
```

單元測試（若已配置）：

```bash
python -m unittest
```

