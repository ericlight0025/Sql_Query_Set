# GUI 美化與使用者體驗優化計劃 (todo.md)

本計劃旨在提升 `ld-query-sql-gui` 的視覺質感與操作順暢度，將原本傳統的 Tkinter 介面現代化。

---

## 🎨 階段一：視覺風格與佈景主題 (Visual Modernization)

- [ ] **引入現代化主題庫**
  - 建議使用 `sv-ttk` (Sun Valley) 或 `azure-ttk`，讓元件具備 Windows 11 的圓角、陰影與動畫效果。
  - 實作切換開關，支援「深色模式 (Dark)」與「淺色模式 (Light)」。
- [ ] **統一字體與配色**
  - 全域使用微軟正黑體 (Microsoft JhengHei UI) 或更現代的字體 (如 Segoe UI)。
  - 重新定義核心配色表 (Accent Color)，確保按鈕、標籤與高亮色調一致。
- [ ] **按鈕圖示化 (Icons)**
  - 為「瀏覽」、「選日曆」、「執行」等按鈕加入對應的小圖示 (PNG 或 Base64 嵌入)。

---

## 📐 階段二：版面配置與邏輯分組 (Layout Optimization)

- [ ] **資訊分塊 (Grouping Fields)**
  - 目前輸入欄位過於密集，改用 `LabelFrame` 或 `Collapsible Pane` 將欄位分組：
    - **基本資訊**: OA 號碼、開發內容、作者。
    - **檔案路徑**: SQL 來源、輸出路徑、模板路徑。
    - **時間設定**: 開始日期、結束日期。
- [ ] **動態版面調整**
  - 當「SQL 原始來源」切換時，自動隱藏/顯示不相關的欄位（例如：選「直接輸入」時隱藏「SQL 檔案」路徑欄位）。
- [ ] **優化間距 (Padding & Margins)**
  - 增加元件間的外部間距 (padx, pady)，避免視覺擁擠。

---

## ⚡ 階段三：互動功能與 UX 強化 (UX Enhancements)

- [ ] **懸停提示 (Tooltips)**
  - 為每個輸入標籤增加 Tooltip，說明該欄位的用途與格式規範 (如：`${startDate}` 的用法)。
- [ ] **改進日期選取器 (Calendar UI)**
  - 美化自製的日期小視窗，使其與主視窗主題一致。
  - 加入「快速選擇」按鈕（如：今天、本月初、本月底）。
- [ ] **執行狀態反饋**
  - 執行時在按鈕旁顯示轉圈圈 (Spinner) 或進度條 (Progressbar)。
  - 成功或失敗時，使用更美觀的浮動通知 (Toast) 取代傳統的強制彈窗。

---

## 📝 階段四：SQL 編輯器升級 (Editor Improvements)

- [ ] **加入行號 (Line Numbers)**
  - 在 SQL 原始碼與預覽區左側加入自動對齊的行號欄。
- [ ] **優化語法高亮 (Syntax Highlighting)**
  - 擴充關鍵字庫 (包含常用內建函數)。
  - 加入「自動完成 (Autocomplete)」基礎提示 (選配)。
- [ ] **快速功能按鈕**
  - 在 SQL 預覽區上方加入「複製全文」、「清除內容」、「自動格式化 (SQL Format)」等快捷按鈕。

---

## 🛠️ 技術實作清單 (Next Steps for Dev)

1. [ ] 研究 `sv-ttk` 的整合方式，並在 `gui.py` 中測試主題套用。
2. [ ] 重新設計 `_build_layout` 函式，實作欄位分組邏輯。
3. [ ] 準備一組 16x16 或 24x24 的圖示資源 (Browse, Save, Play, Calendar)。
4. [ ] 實作 `Tooltip` 類別並綁定至重要欄位。
5. [ ] 更新 `syntax_highlighter.py` 以支援更細緻的標記規則。
