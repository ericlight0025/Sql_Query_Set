# LD Query SQL GUI — Code Review

> 審查日期：2026-04-03  
> 審查範圍：專案根目錄 + `ld_query_sql_tool/` 全部模組 + `tests/`

---

## 一、垃圾檔案需清除

以下檔案是先前除錯 / 修復亂碼時產生的臨時腳本，**應全數刪除**：

| 檔案 | 說明 |
|---|---|
| `_fix_gui.py` | 修復 gui.py 亂碼的腳本 v1 |
| `_fix_gui2.py` | 修復 gui.py 亂碼的腳本 v2 |
| `_debug_gui.py` | 除錯 gui.py 行內容的腳本 |
| `remove_doc.py` | 未完成的讀檔腳本，只有 3 行 |
| `script_fix.py` | cp950→utf-8 轉碼腳本 |
| `script_fix2.py` | cp936→utf-8 轉碼腳本 |
| `script_rm.py` | 未完成的讀檔腳本，只有 3 行 |
| `guitemp.py`（在 `ld_query_sql_tool/` 內） | gui.py 的舊版亂碼備份，42KB，已無用途 |

> [!CAUTION]
> `guitemp.py` 佔 42KB 且內含亂碼中文，留在套件內會干擾閱讀和測試，**務必刪除**。

---

## 二、`gui.py` import 使用絕對路徑，與套件內其他模組不一致

### 問題

`gui.py` 使用 `from ld_query_sql_tool.xxx import ...`（絕對匯入），
但套件內所有其他模組（`cli.py`、`workflow.py`、`sql_service.py` 等）都使用 `from .xxx import ...`（相對匯入）。

### 影響

- 當 `gui.py` 直接被 `python gui.py` 執行時可能失敗（找不到 `ld_query_sql_tool` 套件）。
- 與其他模組的慣例不統一。

### 建議

統一改為相對匯入：
```python
from .config_service import build_config_from_settings, load_settings, save_settings
from .models import ...
from .sql_render_service import read_text_preserve_newlines
from .sql_service import build_output_file_path
from .syntax_highlighter import apply_sql_syntax_highlighting
from .workflow import execute_generation
```

---

## 三、`gui.py` 與 `guitemp.py` 有功能斷層

重建後的 `gui.py`（480 行）相比舊版 `guitemp.py`（1030 行），**遺失了以下功能**：

| 遺失功能 | 舊版位置 | 影響 |
|---|---|---|
| `resolved_sql_text` 分頁（替換日期後的中間 SQL） | 舊版有 3 個預覽 tab | 新版只有 2 個 tab，缺少中間結果 |
| `_build_settings_from_form()` 方法 | 舊版行 746–766 | 測試 `test_build_settings_from_form_uses_inline_sql...` 會失敗 |
| `_set_preview_content()` 方法 | 舊版行 889–913 | 測試 `test_set_preview_content_updates_preview_tabs` 會失敗 |
| `_set_text_widget_content()` 方法 | 舊版行 915–924 | 測試中有引用此方法名稱 |
| `_open_preview_window()` 方法 | 舊版行 560–604 | 測試 `test_apply_sql_theme_only_updates_sql_widgets` 會失敗 |
| `preview_windows` 列表 | 舊版行 142 | `_apply_sql_theme` 測試需要 |
| 5 套 SQL Theme（Obsidian/Monokai/Nord/Midnight/Graphite） | 舊版行 59–125 | 新版只保留 Midnight 一套 |
| Theme 切換 ComboBox | 舊版行 401–414 | 新版完全沒有 Theme 選擇器 |
| 「從原始 SQL 重新載入」按鈕和「立即產生 SQL」按鈕 | 舊版 preview toolbar | 新版輸出 tab 上沒有工具列 |
| 「開啟新視窗預覽」功能 | 舊版行 541–604 | 新版完全移除 |

> [!WARNING]
> 現有測試 `test_ld_query_sql_workflow.py` 引用了 `_set_preview_content`、`_build_settings_from_form`、`_set_text_widget_content`、`_open_preview_window`、`preview_windows` 等，**重建後的 gui.py 缺少這些 API，測試一定會失敗**。

### 建議

1. 在 `gui.py` 中補回 `_build_settings_from_form()`、`_set_preview_content()`、`_set_text_widget_content()`（或將 `_set_text_content` 改名匹配）。
2. 補回 `resolved_sql_text` 第三個預覽分頁。
3. 或者更新測試以匹配新 API。

---

## 四、`sql_service.py` 與 `sql_render_service.py` 功能重疊

### 問題

`sql_service.py` 的唯一作用是：
1. 從 `sql_render_service.py` 重新 re-export 所有函式（`build_output_file_path` 等）。
2. 提供 `generate_sql_file()` 函式。

但 `gui.py` 同時直接 import 了 `sql_service.build_output_file_path` 和 `sql_render_service.read_text_preserve_newlines`，造成混淆——到底該從哪個模組引用？

### 影響

- `sql_service.py` 行 6–19 的巨大 re-export block 完全是冗餘的。
- 開發者不確定該引用 `sql_service` 還是 `sql_render_service`。

### 建議

- `sql_service.py` 只保留 `generate_sql_file()`，不要 re-export。
- 所有直接使用者改為從原始模組 import。

---

## 五、`sql_render_service.py` 職責過多

目前 `sql_render_service.py` 同時負責：

1. 讀檔（`read_text_preserve_newlines`、`read_title_file_and_join_by_double_pipe`）
2. SQL 文字處理（`escape_sql_literal`、`build_sql_clob_expression`）
3. 日期 token 替換（`resolve_date_tokens`）
4. 模板填充（`fill_manager_sql_template`）
5. 輸出檔路徑計算（`build_output_file_path`、`build_renamed_output_file`）
6. 檔案衝突處理（`resolve_output_file_conflict`）
7. Stage 相關邏輯（`normalize_query_template_base`、`build_stage_query_template`）

> [!IMPORTANT]
> 這違反了 `system_spec.md` 第 6.1 節對 `sql_render_service.py` 的定義：「專責 token replacement、CLOB 組裝、模板渲染、輸出檔名計算」。檔案衝突處理和讀檔功能不應在此。

### 建議

- 將 `resolve_output_file_conflict`、`build_renamed_output_file` 移到 `sql_service.py`。
- 將 `read_text_preserve_newlines` 考慮移到一個共用的 `file_utils.py`（因為 `sql_validation_service.py` 也有引用它）。

---

## 六、`sql_validation_service.py` 缺少 SQL 靜態檢查

根據 `plan.md` 第 2、3 項和 `system_spec.md` 第 12 章，驗證服務**應該檢查但目前沒有實作**：

| 規格要求 | 目前狀態 |
|---|---|
| 單引號是否成對 (`SQL_QUOTE_UNBALANCED`) | ❌ 未實作 |
| 括號是否平衡 (`SQL_PAREN_UNBALANCED`) | ❌ 未實作 |
| `DELETE` 語句必須包含 `WHERE` (`SQL_DELETE_WITHOUT_WHERE`) | ❌ 未實作 |
| SQL 不可為空 / 只有註解 (`SQL_EMPTY`) | ❌ 未實作 |

> [!IMPORTANT]
> 這是 `plan.md` 定義的「第一批：安全性優先」功能，缺少這些檢查代表危險 SQL 可能被直接產出。

---

## 七、`workflow.py` 有兩個幾乎重複的函式

### 問題

`execute_generation()` 和 `execute_generation_bundle()` 有大量重複的程式碼：
- 驗證 → 生成 → 開啟資料夾 → 寫 log → 組裝 result 的流程幾乎一模一樣。
- 錯誤處理 pattern 完全相同（try/except → log → return WorkflowResult）。

### 建議

提煉出共用的 `_execute_single_stage()` 輔助函式，讓兩個 public API 調用它。

---

## 八、`gui.py` 的 `_append_log` tag 判斷過於簡陋

```python
tag = "error" if "失敗" in text or "異常" in text else "warning" if "成功" in text else "info"
```

### 問題

- workflow 回傳的訊息用 `✓ 執行成功`、`✗ 驗證失敗` 等格式，但 `_append_log` 只檢查 `"失敗"` 和 `"成功"`。
- `"已輸出"` 等訊息不會被標為 warning/success。
- `"FAILED"` 的英文關鍵字完全不匹配。

### 建議

參考舊版 `_resolve_log_tag` 的邏輯，擴充判斷關鍵字：
```python
if any(kw in text for kw in ("失敗", "錯誤", "不存在", "FAILED", "✗")):
    return "error"
if any(kw in text for kw in ("完成", "成功", "SUCCESS", "已輸出", "✓")):
    return "success"
return "info"
```

---

## 九、`gui.py` 的 `_execute_process` 跳過了 `start_date` / `end_date` 驗證

### 問題

`_execute_process()` 直接在 GUI 端組裝 `AppSettings`，但沒有做任何前置驗證。
所有驗證都被推遲到 `execute_generation()` 內部的 `collect_validation_issues()` 才執行。

這代表使用者按下「執行」後，畫面**先切到輸出 Tab、清空 log、啟動 spinner**，然後才在背景 thread 內發現錯誤再跳回來顯示 messagebox。

### 建議

在啟動 thread 之前先呼叫 `collect_validation_issues(config)` 做一次前置驗證，有錯就直接顯示、不啟動背景工作。

---

## 十、舊版 Java 檔案仍在專案根目錄

| 檔案 | 大小 |
|---|---|
| `LD_query_SqlService.java` | 5.5 KB |
| `LD_query_SqlServiceAppGUI.java` | 22 KB |
| `ManagerSql.sql` | 429 B |

這些是 Java 版本的舊實現，與 Python 版本完全無關。如果不再使用，建議移到 `archive/` 或直接刪除。

---

## 十一、測試與新版 GUI 已經脫節

### 當前測試引用的 API 在新 `gui.py` 中不存在

```
test_ld_query_sql_workflow.py:
  - app._set_preview_content(preview)          → gui.py 無此方法
  - app._build_settings_from_form()            → gui.py 無此方法
  - app._set_text_widget_content(...)          → gui.py 改名為 _set_text_content
  - app._open_preview_window(...)              → gui.py 已移除
  - app.preview_windows                        → gui.py 已移除
  - app._handle_result(result, settings)       → gui.py 改名為 _on_result
  - SQL_PREVIEW_THEMES["夜幕"]                  → gui.py 改名為 "Midnight"
  - 測試期望 showerror("執行失敗", ...)         → gui.py 用 showerror("錯誤", ...)
  - 測試期望 showinfo("完成", "已輸出檔案:...") → gui.py 用 showinfo("成功", "模組產生完成!...")
```

> [!CAUTION]
> 執行 `python -m pytest tests/` **一定會出錯**。必須在修復 gui.py API 或更新測試之間擇一處理。

---

## 十二、`models.py` 的 `AppSettings` 有 `before_sql_*` / `after_sql_*` 欄位，但 GUI 完全沒用到

```python
before_sql_file: str = str(DEFAULT_SQL_FILE)
before_sql_text: str = ""
after_sql_file: str = str(DEFAULT_SQL_FILE)
after_sql_text: str = ""
```

`workflow.py` 也有完整的 `execute_generation_bundle()` 支援三階段（Before/Update/After），但 GUI 完全沒有三階段的 UI。`settings.json` 也已經存了這些欄位。

### 建議

- 如果三階段是未來需求，在 `plan.md` 中記錄。
- 如果不需要，清掉 `models.py` 中的冗餘欄位和 `workflow.py` 中的 `execute_generation_bundle()`，避免維護負擔。

---

## 十三、`config_service.py` 缺少 `before_sql_*` / `after_sql_*` 到 `SqlGenerationConfig` 的轉換

`build_config_from_settings()` 只處理 `sql_file` 和 `sql_text`，完全忽略 `before_sql_file`、`before_sql_text`、`after_sql_file`、`after_sql_text`。如果真的要支援三階段，這個函式需要擴充。

---

## 十四、日期格式不一致

| 位置 | 格式 |
|---|---|
| `system_spec.md` 日期規格 | `YYYY-MM-DD` |
| `settings.json` 範例 | `2026-04-01`（YYYY-MM-DD） |
| `sql_validation_service.py` validate_date_range | `%Y-%m-%d` |
| `gui.py` 日期選擇器 | `%Y-%m-%d`（一致 ✓） |

目前統一為 `YYYY-MM-DD`，這一點是一致的。✅

---

## 十五、`syntax_highlighter.py` 的 offset 算法在多行文字時可能錯位

```python
def _offset_to_index(offset: int) -> str:
    return f"1.0+{offset}c"
```

這個做法把整個文字當作從 `1.0` 開始的字元流，而 Tk Text widget 的 `+Nc` 計數方式包含換行符，所以在大部分情況下是正確的。但如果文字中包含 `\r\n`（Windows 換行），Tk 在內部只算一個字元，而 Python 的 offset 算兩個字元，**可能造成高亮位置偏移**。

### 建議

在 `apply_sql_syntax_highlighting` 前先把文字統一成 `\n` 換行再計算 offset，或改用 `line.col` 格式定位。

---

## 總結：建議處理優先級

### 🔴 立即處理（影響功能正確性）

1. 刪除所有垃圾檔案（`_fix_gui*.py`、`script_*.py`、`remove_doc.py`、`guitemp.py`）
2. 修復 `gui.py` 的 import 為相對匯入
3. 補回 `gui.py` 遺失的 API（`_build_settings_from_form`、`_set_preview_content` 等），或更新測試
4. 確保 `python -m pytest tests/` 通過

### 🟡 短期處理（影響安全性）

5. 在 `sql_validation_service.py` 實作 SQL 靜態檢查（引號、括號、DELETE 無 WHERE）
6. 在 `gui.py` 的 `_execute_process` 中加入前置驗證

### 🟢 中期處理（改善架構品質）

7. 整理 `sql_service.py` / `sql_render_service.py` 的職責邊界
8. 決定三階段（Before/Update/After）功能的去留
9. 補回 `resolved_sql_text` 第三預覽 tab 和 Theme 切換器
10. 提煉 `workflow.py` 的重複程式碼
11. 修正 `syntax_highlighter.py` 的 `\r\n` 偏移問題
