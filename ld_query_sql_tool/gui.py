# -*- coding: utf-8 -*-
"""SQL 工具主 GUI"""
from __future__ import annotations

import calendar
import os
import subprocess
import threading
import tkinter as tk
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ld_query_sql_tool.config_service import build_config_from_settings, load_settings, save_settings
from ld_query_sql_tool.models import (
    AppSettings,
    DEFAULT_INPUT_DIR,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SETTINGS_FILE,
    DEFAULT_TEMPLATE_DIR,
    OverwriteMode,
    PreviewPayload,
    SqlSourceMode,
    WorkflowResult,
)
from ld_query_sql_tool.sql_render_service import read_text_preserve_newlines
from ld_query_sql_tool.sql_service import build_output_file_path
from ld_query_sql_tool.syntax_highlighter import apply_sql_syntax_highlighting
from ld_query_sql_tool.workflow import execute_generation

DEFAULT_SQL_THEME_NAME = "Midnight"

# UI 主題設定（可快速切換，低風險）
UI_THEMES = {
    "Scandinavian Dark": {
        "app_bg": "#0E1117",
        "surface_bg": "#151A23",
        "surface_alt_bg": "#1D2330",
        "input_bg": "#0F141C",
        "text": "#E6EDF3",
        "muted": "#9AA7B7",
        "accent": "#4A90E2",
        "accent_active": "#66A6F0",
        "accent_soft": "#1C2A3D",
        "border": "#273043",
        "log_bg": "#0F1622",
        "tab_selected": "#1F3556",
        "tab_active": "#243A5C",
        "tab_text_selected": "#FFFFFF",
        "tab_text": "#C7D2DF",
    },
    "Neo-Brutal Dark": {
        "app_bg": "#0D0D0D",
        "surface_bg": "#141414",
        "surface_alt_bg": "#1F1F1F",
        "input_bg": "#0F0F0F",
        "text": "#F5F5F5",
        "muted": "#B1B1B1",
        "accent": "#FF6B00",
        "accent_active": "#FF8A33",
        "accent_soft": "#2A1A0A",
        "border": "#2B2B2B",
        "log_bg": "#101010",
        "tab_selected": "#3A240F",
        "tab_active": "#432A12",
        "tab_text_selected": "#FFFFFF",
        "tab_text": "#E6E6E6",
    },
    "Modern Studio Dark": {
        "app_bg": "#0B1220",
        "surface_bg": "#121C2B",
        "surface_alt_bg": "#182334",
        "input_bg": "#0F1724",
        "text": "#E6EDF3",
        "muted": "#93A4B7",
        "accent": "#3A86C8",
        "accent_active": "#55A4E8",
        "accent_soft": "#182C40",
        "border": "#2C3A4D",
        "log_bg": "#0E1723",
        "tab_selected": "#1B2A3C",
        "tab_active": "#22364E",
        "tab_text_selected": "#FFFFFF",
        "tab_text": "#D2DCE7",
    },
}

DEFAULT_UI_THEME_NAME = "Modern Studio Dark"

OVERWRITE_LABEL_TO_MODE = {
    "詢問": OverwriteMode.PROMPT.value,
    "直接覆寫": OverwriteMode.OVERWRITE.value,
    "自動更名": OverwriteMode.RENAME.value,
}
OVERWRITE_MODE_TO_LABEL = {value: key for key, value in OVERWRITE_LABEL_TO_MODE.items()}

SQL_SOURCE_LABEL_TO_MODE = {
    "從檔案讀取": SqlSourceMode.FILE.value,
    "畫面直接輸入": SqlSourceMode.INLINE.value,
}
SQL_SOURCE_MODE_TO_LABEL = {value: key for key, value in SQL_SOURCE_LABEL_TO_MODE.items()}

SQL_PREVIEW_THEMES = {
    "Midnight": {
        "background": "#0F1B24",
        "foreground": "#E7F2F8",
        "caret": "#7BD5FF",
        "selection_background": "#24546F",
        "selection_foreground": "#F7FCFF",
        "keyword": "#7BD5FF",
        "string": "#A5E075",
        "comment": "#5F8294",
        "number": "#F6D06F",
        "placeholder": "#F2A7FF",
        "bind_variable": "#8AE6C9",
    }
}


class SqlToolApp:
    def __init__(self, root: tk.Tk, settings_file: Path = DEFAULT_SETTINGS_FILE) -> None:
        self.root = root
        self.settings_file = Path(settings_file)
        self.root.title("SQL 管理工具")
        self.root.geometry("1200x900")
        self.root.minsize(1000, 800)
        self.is_running = False

        self.loaded_settings_error = ""
        settings = self._load_initial_settings()
        self.base_settings = settings

        self.ui_theme_var = tk.StringVar(value=DEFAULT_UI_THEME_NAME)
        self._theme = UI_THEMES[self.ui_theme_var.get()]
        self.root.configure(bg=self._theme["app_bg"])

        self.oa_no_var = tk.StringVar(value=settings.oa_no)
        self.query_template_var = tk.StringVar(value=settings.query_template)
        self.output_dir_var = tk.StringVar(value=settings.output_dir)
        self.sql_file_var = tk.StringVar(value=settings.sql_file)
        self.content_var = tk.StringVar(value=settings.content)
        self.author_var = tk.StringVar(value=settings.author)
        self.title_file_var = tk.StringVar(value=settings.title_file)
        self.template_file_var = tk.StringVar(value=settings.template_file)
        self.start_date_var = tk.StringVar(value=settings.start_date)
        self.end_date_var = tk.StringVar(value=settings.end_date)
        self.sql_source_var = tk.StringVar(value=SQL_SOURCE_MODE_TO_LABEL.get(str(settings.sql_source_mode), "從檔案讀取"))
        self.sql_theme_var = tk.StringVar(value=DEFAULT_SQL_THEME_NAME)
        self.overwrite_mode_var = tk.StringVar(value=OVERWRITE_MODE_TO_LABEL.get(str(settings.overwrite_mode), "詢問"))
        self.open_output_dir_var = tk.BooleanVar(value=settings.open_output_dir)
        self.root_dir_var = tk.StringVar(value=settings.root_dir or ".")
        self.python_exe_var = tk.StringVar(value=settings.python_exe)
        self.ui_font_size_var = tk.StringVar(value=settings.ui_font_size or "11")

        self._build_style()
        self._build_layout()
        self._initialize_sql_editor(settings)
        self._apply_sql_theme(self.sql_theme_var.get())
        self._apply_ui_theme(self.ui_theme_var.get())
        self._apply_ui_font_size()
        self.start_date_var.trace_add("write", lambda *_: self._refresh_date_tab_sql())
        self.end_date_var.trace_add("write", lambda *_: self._refresh_date_tab_sql())
        self._refresh_date_tab_sql()
        self._start_demo_autoplay_if_enabled()

        if self.loaded_settings_error:
            self._append_log(f"設定檔載入失敗: {self.loaded_settings_error}")

    def _load_initial_settings(self) -> AppSettings:
        try:
            return load_settings(self.settings_file)
        except Exception as exc:
            self.loaded_settings_error = str(exc)
            return AppSettings()

    def _build_style(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        # 初始樣式先用預設主題，後續由 _apply_ui_theme 重設
        self._apply_ui_theme(self.ui_theme_var.get())

    def _build_layout(self) -> None:
        container = ttk.Frame(self.root, style="Root.TFrame", padding=10)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)

        header = tk.Frame(container, bg=self._theme["app_bg"])
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        tk.Label(
            header,
            text="SQL 組合產生工具",
            bg=self._theme["app_bg"],
            fg=self._theme["text"],
            font=("Microsoft JhengHei UI", 18, "bold"),
        ).pack(side="left")

        self.main_notebook = ttk.Notebook(container, style="Preview.TNotebook")
        self.main_notebook.grid(row=1, column=0, sticky="nsew")

        input_tab = ttk.Frame(self.main_notebook, style="Root.TFrame", padding=8)
        output_tab = ttk.Frame(self.main_notebook, style="Root.TFrame", padding=8)
        settings_tab = ttk.Frame(self.main_notebook, style="Root.TFrame", padding=8)
        self.main_notebook.add(input_tab, text="設定與執行")
        self.main_notebook.add(output_tab, text="檢視與輸出")
        self.main_notebook.add(settings_tab, text="系統設定")
        input_tab.columnconfigure(0, weight=1)
        output_tab.columnconfigure(0, weight=1)
        settings_tab.columnconfigure(0, weight=1)
        output_tab.rowconfigure(0, weight=3)
        output_tab.rowconfigure(1, weight=1)

        # 執行區塊
        action_frame = ttk.LabelFrame(input_tab, text="執行動作", style="Panel.TLabelframe", padding=10)
        action_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.execute_button = ttk.Button(action_frame, text="執行 SQL 組合", style="Primary.TButton", command=self._execute_process)
        self.execute_button.pack(anchor="w")

        # 欄位區塊
        form = ttk.LabelFrame(input_tab, text="輸入參數", style="Panel.TLabelframe", padding=10)
        form.grid(row=1, column=0, sticky="nsew")
        form.columnconfigure(1, weight=1)

        self._add_entry_row(form, 0, "系統號碼", self.oa_no_var)
        self._add_entry_row(form, 1, "Query 前綴名稱", self.query_template_var)
        self._add_entry_row(form, 2, "輸出資料夾", self.output_dir_var, [("瀏覽", self._browse_output_dir)])
        self.ui_theme_combobox = self._add_combobox_row(form, 3, "UI 主題", self.ui_theme_var, list(UI_THEMES))
        self.ui_theme_combobox.bind("<<ComboboxSelected>>", self._on_ui_theme_selected)
        self.sql_source_combobox = self._add_combobox_row(form, 4, "SQL 原始來源", self.sql_source_var, list(SQL_SOURCE_LABEL_TO_MODE))
        self._add_entry_row(form, 5, "SQL 檔案", self.sql_file_var, [("瀏覽", self._browse_sql_file), ("載入文字至編輯區", self._load_sql_file_into_editor_from_button)])
        self._add_entry_row(form, 6, "開始日期", self.start_date_var, [("選日曆", lambda: self._open_date_picker(self.start_date_var, "開始")), ("清除", self._clear_start_date)])
        self._add_entry_row(form, 7, "結束日期", self.end_date_var, [("選日曆", lambda: self._open_date_picker(self.end_date_var, "結束")), ("清除", self._clear_end_date)])
        self._add_entry_row(form, 8, "開發內容說明", self.content_var)
        self._add_entry_row(form, 9, "作者", self.author_var)
        self._add_entry_row(form, 10, "欄位文字檔", self.title_file_var, [("瀏覽", self._browse_title_file)])
        self._add_entry_row(form, 11, "模板 SQL 檔", self.template_file_var, [("瀏覽", self._browse_template_file)])
        self.overwrite_mode_combobox = self._add_combobox_row(form, 12, "檔案已存在處理模式", self.overwrite_mode_var, list(OVERWRITE_LABEL_TO_MODE))
        self._add_checkbox_row(form, 13, "完成後自動開啟輸出資料夾", self.open_output_dir_var)

        # 輸出 Tab - 預覽區塊
        preview_frame = ttk.LabelFrame(output_tab, text="SQL 文字檢視", style="Panel.TLabelframe", padding=10)
        preview_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(1, weight=1)

        self.preview_notebook = ttk.Notebook(preview_frame, style="Preview.TNotebook")
        self.preview_notebook.grid(row=1, column=0, sticky="nsew")
        self.preview_notebook.bind("<<NotebookTabChanged>>", self._on_preview_tab_changed)

        self.raw_sql_text = self._build_preview_tab(self.preview_notebook, "原始 SQL (可編輯)", editable=True)
        self.rendered_sql_text = self._build_preview_tab(self.preview_notebook, "目標輸出 SQL (模板渲染後)")
        self._build_date_tab(self.preview_notebook)

        # 輸出 Tab - Log 區塊
        log_frame = ttk.LabelFrame(output_tab, text="執行紀錄", style="Panel.TLabelframe", padding=10)
        log_frame.grid(row=1, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = tk.Text(
            log_frame,
            height=8,
            bg=self._theme["log_bg"],
            fg=self._theme["text"],
            font=("Consolas", 10),
            borderwidth=0,
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")
        self.log_text.tag_configure("info", foreground=self._theme["text"])
        self.log_text.tag_configure("error", foreground="#FF6B6B")
        self.log_text.tag_configure("warning", foreground="#FFD93D")
        self.log_text.configure(state="disabled")

        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)

        # 系統設定 Tab
        system_frame = ttk.LabelFrame(settings_tab, text="系統設定", style="Panel.TLabelframe", padding=10)
        system_frame.grid(row=0, column=0, sticky="nsew")
        system_frame.columnconfigure(1, weight=1)
        self._add_entry_row(
            system_frame,
            0,
            "根目錄",
            self.root_dir_var,
            [("瀏覽", self._browse_root_dir)],
        )
        self._add_entry_row(
            system_frame,
            1,
            "Python.exe 位置",
            self.python_exe_var,
            [("瀏覽", self._browse_python_exe)],
        )
        self._add_entry_row(
            system_frame,
            2,
            "文字大小",
            self.ui_font_size_var,
        )
        ttk.Button(system_frame, text="儲存設定", style="Primary.TButton", command=self._save_system_settings).grid(
            row=3, column=1, sticky="w", pady=(8, 0)
        )
        ttk.Button(system_frame, text="測試 Python.exe", style="Secondary.TButton", command=self._test_python_exe).grid(
            row=3, column=2, sticky="w", padx=8, pady=(8, 0)
        )

    def _build_preview_tab(self, notebook: ttk.Notebook, title: str, editable: bool = False) -> tk.Text:
        frame = ttk.Frame(notebook, style="Surface.TFrame", padding=6)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        notebook.add(frame, text=title)

        text_widget = tk.Text(
            frame,
            undo=editable,
            height=15,
            bg=self._theme["log_bg"],
            fg=self._theme["text"],
            font=("Consolas", 11),
            borderwidth=0,
            wrap="none",
        )
        text_widget.grid(row=0, column=0, sticky="nsew")
        text_widget._is_editable = editable
        text_widget._is_sql_widget = True

        y_scroll = ttk.Scrollbar(frame, orient="vertical", command=text_widget.yview)
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll = ttk.Scrollbar(frame, orient="horizontal", command=text_widget.xview)
        x_scroll.grid(row=1, column=0, sticky="ew")
        text_widget.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        ttk.Button(
            frame,
            text="複製內容",
            style="Secondary.TButton",
            command=lambda w=text_widget, t=title: self._copy_sql_text(w, t),
        ).grid(row=2, column=0, sticky="e", pady=(6, 0))
        ttk.Button(
            frame,
            text="另存 .sql",
            style="Secondary.TButton",
            command=lambda w=text_widget, t=title: self._save_sql_text(w, t),
        ).grid(row=2, column=0, sticky="w", pady=(6, 0))

        if editable:
            text_widget.bind("<<Modified>>", self._on_sql_text_modified)
        else:
            text_widget.configure(state="disabled")
        return text_widget

    def _build_date_tab(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook, style="Surface.TFrame", padding=10)
        frame.columnconfigure(1, weight=1)
        notebook.add(frame, text="日期替換")
        self.date_tab_frame = frame

        ttk.Label(
            frame,
            text="直接使用第一頁輸入的開始/結束日期，取代 SQL 內的 startDate / endDate。",
            style="Hint.TLabel",
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(0, 8))
        ttk.Button(frame, text="套用日期替換", style="Primary.TButton", command=self._apply_date_replacement).grid(
            row=1, column=0, sticky="w", padx=10, pady=(6, 0)
        )
        ttk.Button(
            frame,
            text="另存 .sql",
            style="Secondary.TButton",
            command=lambda: self._save_sql_text(self.date_sql_text, "日期替換"),
        ).grid(row=1, column=1, sticky="w", padx=10, pady=(6, 0))
        ttk.Button(
            frame,
            text="複製內容",
            style="Secondary.TButton",
            command=lambda: self._copy_sql_text(self.date_sql_text, "日期替換"),
        ).grid(row=1, column=2, sticky="e", padx=10, pady=(6, 0))
        self.date_sql_text = tk.Text(
            frame,
            height=18,
            bg=self._theme["log_bg"],
            fg=self._theme["text"],
            font=("Consolas", 11),
            borderwidth=0,
            wrap="none",
        )
        self.date_sql_text.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=10, pady=(10, 0))
        self.date_sql_text._is_sql_widget = True
        self.date_sql_text._is_editable = False
        self.date_sql_text.configure(state="disabled")
        frame.rowconfigure(2, weight=1)

    def _add_entry_row(self, parent: ttk.LabelFrame, row: int, label: str, variable: tk.StringVar, actions: list = None) -> None:
        ttk.Label(parent, text=f"{label}:", style="Field.TLabel").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        ttk.Entry(parent, textvariable=variable, style="Dark.TEntry").grid(row=row, column=1, sticky="ew", pady=5)
        if actions:
            btn_frame = ttk.Frame(parent, style="Surface.TFrame")
            btn_frame.grid(row=row, column=2, padx=10, sticky="e")
            for i, (btn_text, cmd) in enumerate(actions):
                ttk.Button(btn_frame, text=btn_text, style="Secondary.TButton", command=cmd).grid(row=0, column=i, padx=4)

    def _add_combobox_row(self, parent: ttk.LabelFrame, row: int, label: str, variable: tk.StringVar, options: list) -> ttk.Combobox:
        ttk.Label(parent, text=f"{label}:", style="Field.TLabel").grid(row=row, column=0, sticky="w", padx=10, pady=5)
        combo = ttk.Combobox(parent, textvariable=variable, values=options, state="readonly", style="Dark.TCombobox")
        combo.grid(row=row, column=1, sticky="ew", pady=5)
        return combo

    def _add_checkbox_row(self, parent: ttk.LabelFrame, row: int, label: str, variable: tk.BooleanVar) -> None:
        ttk.Checkbutton(parent, text=label, variable=variable, style="Field.TCheckbutton").grid(row=row, column=1, sticky="w", pady=5)

    def _browse_output_dir(self):
        sel = filedialog.askdirectory()
        if sel: self.output_dir_var.set(sel)

    def _browse_sql_file(self):
        sel = filedialog.askopenfilename(filetypes=[("SQL files", "*.sql"), ("All", "*.*")])
        if sel:
            self.sql_file_var.set(sel)
            self._load_sql_file_into_editor_from_button()

    def _browse_title_file(self):
        sel = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All", "*.*")])
        if sel: self.title_file_var.set(sel)

    def _browse_template_file(self):
        sel = filedialog.askopenfilename(filetypes=[("SQL files", "*.sql"), ("All", "*.*")])
        if sel: self.template_file_var.set(sel)

    def _browse_python_exe(self):
        initial = self._resolve_dialog_initial_dir(self.python_exe_var.get().strip(), expect_file=True)
        sel = filedialog.askopenfilename(
            initialdir=initial,
            filetypes=[("Python", "python.exe"), ("All", "*.*")],
        )
        if sel: self.python_exe_var.set(sel)

    def _browse_root_dir(self):
        initial = self._resolve_dialog_initial_dir(self.root_dir_var.get().strip(), expect_file=False)
        sel = filedialog.askdirectory(initialdir=initial, mustexist=True)
        if sel:
            settings_root = Path(self.settings_file).parent.resolve()
            selected = Path(sel).resolve()
            try:
                rel = selected.relative_to(settings_root).as_posix()
                self.root_dir_var.set(rel if rel else ".")
            except Exception:
                self.root_dir_var.set(str(selected))

    def _initialize_sql_editor(self, settings: AppSettings) -> None:
        initial_text = settings.sql_text if str(settings.sql_source_mode) == SqlSourceMode.INLINE.value else ""
        if initial_text:
            self._set_text_content(self.raw_sql_text, initial_text, editable=True)
        else:
            p = Path(settings.sql_file)
            if p.is_file():
                self._load_sql_file_into_editor(p, switch_mode=False)

    def _load_sql_file_into_editor_from_button(self):
        p = self.sql_file_var.get().strip()
        if p and Path(p).is_file():
            self._load_sql_file_into_editor(Path(p), switch_mode=True)
            self.main_notebook.select(1)
        else:
            messagebox.showerror("錯誤", "SQL 檔案路徑無效。")

    def _load_sql_file_into_editor(self, p: Path, switch_mode: bool):
        try:
            content = read_text_preserve_newlines(p)
            self._set_text_content(self.raw_sql_text, content, editable=True)
            if switch_mode:
                self.sql_source_var.set("畫面直接輸入")
            self._append_log(f"已從檔案載入內容至編輯區。")
        except Exception as e:
            messagebox.showerror("錯誤", f"無法讀取檔案: {e}")

    def _execute_process(self) -> None:
        if self.is_running: return
        try:
            st = self._build_settings_from_ui()
            missing = self._validate_required_fields(st)
            if missing:
                self._append_log(f"已取消執行：缺少必填欄位 -> {', '.join(missing)}")
                messagebox.showwarning("提醒", f"以下欄位為必填:\n{chr(10).join(missing)}")
                return
            config = build_config_from_settings(st)
            resolved = self._resolve_overwrite(config)
            if not resolved: return
            
            self._clear_log()
            self.main_notebook.select(1)
            self._set_running(True)
            threading.Thread(target=self._run_bg, args=(resolved, st), daemon=True).start()
        except Exception as e:
            messagebox.showerror("錯誤", f"輸入參數異常:\n{e}")

    def _validate_required_fields(self, st: AppSettings) -> list[str]:
        missing: list[str] = []
        if not st.oa_no.strip():
            missing.append("系統號碼")
        if not st.query_template.strip():
            missing.append("Query 前綴名稱")
        if not str(st.sql_source_mode):
            missing.append("SQL 原始來源")
        if str(st.sql_source_mode) == SqlSourceMode.FILE.value and not st.sql_file.strip():
            missing.append("SQL 檔案")
        if str(st.sql_source_mode) == SqlSourceMode.INLINE.value and not st.sql_text.strip():
            missing.append("原始 SQL 內容")
        if not st.template_file.strip():
            missing.append("模板 SQL 檔")
        if not st.title_file.strip():
            missing.append("欄位文字檔")

        if str(st.sql_source_mode) == SqlSourceMode.FILE.value and st.sql_file.strip():
            sql_path = self._resolve_with_root(st.sql_file.strip(), st.root_dir)
            if not sql_path.is_file():
                missing.append(f"SQL 檔案不存在: {sql_path}")
        if st.template_file.strip():
            template_path = self._resolve_with_root(st.template_file.strip(), st.root_dir)
            if not template_path.is_file():
                missing.append(f"模板 SQL 檔不存在: {template_path}")
        if st.title_file.strip():
            title_path = self._resolve_with_root(st.title_file.strip(), st.root_dir)
            if not title_path.is_file():
                missing.append(f"欄位文字檔不存在: {title_path}")
        return missing

    def _save_system_settings(self) -> None:
        try:
            self._apply_ui_font_size()
            st = self._build_settings_from_ui()
            save_settings(st, self.settings_file)
            # 系統設定另外同步到專案根目錄 settings.json
            if Path(self.settings_file).resolve() != DEFAULT_SETTINGS_FILE.resolve():
                save_settings(st, DEFAULT_SETTINGS_FILE)
            messagebox.showinfo("成功", "系統設定已儲存。")
        except Exception as e:
            messagebox.showerror("錯誤", f"儲存設定失敗:\n{e}")

    def _test_python_exe(self) -> None:
        python_exe = self._normalize_python_exe(self.python_exe_var.get().strip())
        self.python_exe_var.set(python_exe)
        if not python_exe:
            messagebox.showwarning("提醒", "請先輸入 Python.exe 路徑。")
            return
        if not Path(python_exe).is_file():
            messagebox.showerror("錯誤", f"找不到檔案:\n{python_exe}")
            return
        try:
            result = subprocess.run(
                [python_exe, "--version"],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
            version_text = (result.stdout or result.stderr or "").strip()
            if result.returncode == 0:
                self._append_log(f"Python 測試成功: {version_text}")
                messagebox.showinfo("成功", f"Python 可執行。\n{version_text}")
            else:
                messagebox.showerror("錯誤", f"執行失敗 (code={result.returncode})\n{version_text}")
        except Exception as exc:
            messagebox.showerror("錯誤", f"測試失敗:\n{exc}")

    def _build_settings_from_ui(self) -> AppSettings:
        # 統一整理 UI 欄位，避免多處維護
        mode_enum = SqlSourceMode(SQL_SOURCE_LABEL_TO_MODE.get(self.sql_source_var.get(), "file"))
        overwrite_enum = OverwriteMode(OVERWRITE_LABEL_TO_MODE.get(self.overwrite_mode_var.get(), "prompt"))
        raw_t = self._get_text_content(self.raw_sql_text)
        return AppSettings(
            oa_no=self.oa_no_var.get().strip(),
            query_template=self.query_template_var.get().strip(),
            output_dir=self.output_dir_var.get().strip(),
            sql_source_mode=mode_enum,
            sql_file=self.sql_file_var.get().strip(),
            sql_text=raw_t if mode_enum.value == "inline" else "",
            content=self.content_var.get().strip(),
            author=self.author_var.get().strip(),
            title_file=self.title_file_var.get().strip(),
            template_file=self.template_file_var.get().strip(),
            start_date=self.start_date_var.get().strip(),
            end_date=self.end_date_var.get().strip(),
            overwrite_mode=overwrite_enum,
            open_output_dir=self.open_output_dir_var.get(),
            root_dir=self.root_dir_var.get().strip() or ".",
            python_exe=self._normalize_python_exe(self.python_exe_var.get().strip()),
            ui_font_size=self.ui_font_size_var.get().strip(),
        )

    def _normalize_python_exe(self, path_text: str) -> str:
        value = path_text.strip()
        if not value:
            return value
        p = Path(value)
        if p.is_dir():
            return str(p / "python.exe")
        return value

    def _resolve_with_root(self, path_text: str, root_dir: str) -> Path:
        p = Path(path_text)
        if p.is_absolute():
            return p
        base = Path(root_dir or ".")
        if not base.is_absolute():
            base = Path(DEFAULT_SETTINGS_FILE).parent / base
        return base / p

    def _resolve_dialog_initial_dir(self, value: str, *, expect_file: bool) -> str:
        if not value:
            return str(Path(self.settings_file).parent.resolve())
        target = self._resolve_with_root(value, self.root_dir_var.get().strip() or ".")
        if expect_file:
            target = target.parent if target.suffix else target
        return str(target if target.exists() else Path(self.settings_file).parent.resolve())

    def _start_demo_autoplay_if_enabled(self) -> None:
        if os.environ.get("LDQ_DEMO_AUTO", "").strip() != "1":
            return
        self.root.after(800, self._run_demo_autoplay)

    def _run_demo_autoplay(self) -> None:
        # 自動展示每一頁，方便錄製工具說明影片
        self.start_date_var.set("2026-04-01")
        self.end_date_var.set("2026-04-30")

        steps: list[tuple[int, callable]] = [
            (0, lambda: self.main_notebook.select(0)),      # 設定與執行
            (1800, lambda: self.main_notebook.select(1)),   # 檢視與輸出
            (3200, lambda: self.preview_notebook.select(0)),  # 原始 SQL
            (4800, lambda: self.preview_notebook.select(1)),  # 目標輸出 SQL
            (6400, lambda: self.preview_notebook.select(2)),  # 日期替換
            (7600, self._apply_date_replacement),
            (9800, lambda: self.main_notebook.select(2)),   # 系統設定
            (11600, lambda: self.main_notebook.select(0)),  # 回到設定與執行
        ]

        for delay_ms, action in steps:
            self.root.after(delay_ms, action)

    def _apply_ui_font_size(self) -> None:
        raw = self.ui_font_size_var.get().strip()
        try:
            size = max(9, min(16, int(raw)))
        except ValueError:
            size = 11
        self.ui_font_size_var.set(str(size))
        # 重新套用主題字體大小
        style = ttk.Style(self.root)
        style.configure("Field.TLabel", font=("Microsoft JhengHei UI", size))
        style.configure("Dark.TEntry", font=("Microsoft JhengHei UI", size))
        style.configure("Dark.TCombobox", font=("Microsoft JhengHei UI", size))
        style.configure("Field.TCheckbutton", font=("Microsoft JhengHei UI", size))
        style.configure("Primary.TButton", font=("Microsoft JhengHei UI", size, "bold"))
        style.configure("Secondary.TButton", font=("Microsoft JhengHei UI", size))

    def _apply_date_replacement(self) -> None:
        start = self.start_date_var.get().strip()
        end = self.end_date_var.get().strip()
        if not start or not end:
            messagebox.showwarning("提醒", "請先設定開始日期與結束日期。")
            return
        raw = self._get_text_content(self.raw_sql_text)
        replaced, start_hits, end_hits = self._replace_date_tokens(raw)
        if replaced == raw:
            messagebox.showinfo("提示", "未找到 startDate / endDate 可替換。")
            return
        self._set_text_content(self.date_sql_text, replaced, editable=False)
        self.main_notebook.select(1)
        self.preview_notebook.select(self.date_tab_frame)
        self._append_log(f"已套用日期替換。startDate: {start_hits} 次, endDate: {end_hits} 次")

    def _build_date_replaced_sql(self, raw: str) -> str:
        replaced, _, _ = self._replace_date_tokens(raw)
        return replaced

    def _replace_date_tokens(self, raw: str) -> tuple[str, int, int]:
        start = self.start_date_var.get().strip()
        end = self.end_date_var.get().strip()
        replaced = raw
        start_hits = 0
        end_hits = 0
        if start:
            for token in ("?startDate?", "startDate", ":startDate", "${startDate}"):
                start_hits += replaced.count(token)
                replaced = replaced.replace(token, start)
        if end:
            for token in ("?endDate?", "endDate", ":endDate", "${endDate}"):
                end_hits += replaced.count(token)
                replaced = replaced.replace(token, end)
        return replaced, start_hits, end_hits

    def _refresh_date_tab_sql(self) -> None:
        if not hasattr(self, "date_sql_text") or not hasattr(self, "raw_sql_text"):
            return
        raw = self._get_text_content(self.raw_sql_text)
        self._set_text_content(self.date_sql_text, self._build_date_replaced_sql(raw), editable=False)

    def _on_preview_tab_changed(self, _ev) -> None:
        selected = self.preview_notebook.select()
        if not selected:
            return
        if self.preview_notebook.tab(selected, "text") == "日期替換":
            self._refresh_date_tab_sql()

    def _resolve_overwrite(self, config):
        if config.overwrite_mode.value != "prompt": return config
        c = replace(config, overwrite_mode=OverwriteMode.ERROR)
        if not build_output_file_path(c).exists(): return c
        ans = messagebox.askyesnocancel("覆寫確認", "輸出檔案已存在！\n按 Yes 覆寫，按 No 更名，按 Cancel 取消。")
        if ans is None: return None
        return replace(config, overwrite_mode=OverwriteMode.OVERWRITE if ans else OverwriteMode.RENAME)

    def _run_bg(self, config, st: AppSettings):
        res = execute_generation(config)
        self.root.after(0, lambda: self._on_result(res, st))

    def _on_result(self, res: WorkflowResult, st: AppSettings):
        for m in res.messages: self._append_log(m)
        if res.preview:
            self._set_text_content(self.raw_sql_text, res.preview.raw_sql, editable=True)
            self._set_text_content(self.rendered_sql_text, res.preview.rendered_sql, editable=False)
        self._set_running(False)
        if res.success:
            save_settings(st, self.settings_file)
            messagebox.showinfo("成功", f"模組產生完成！\n{res.output_file}")
            self.preview_notebook.select(1)
        else:
            messagebox.showerror("驗證失敗", res.error_message)
            self.preview_notebook.select(0)

    def _set_running(self, state: bool):
        self.is_running = state
        self.execute_button.configure(state="disabled" if state else "normal", text="處理中..." if state else "執行 SQL 組合")
        self.root.configure(cursor="watch" if state else "")

    def _set_text_content(self, widget: tk.Text, txt: str, editable: bool):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", txt)
        self._refresh_sql_highlighting(widget)
        widget.configure(state="normal" if editable else "disabled")
        widget._is_editable = editable
        if editable: widget.edit_modified(False)

    def _get_text_content(self, widget: tk.Text) -> str:
        s = str(widget.cget("state"))
        widget.configure(state="normal")
        t = widget.get("1.0", "end-1c")
        widget.configure(state=s)
        return t

    def _append_log(self, text: str):
        tag = "error" if "失敗" in text or "異常" in text else "warning" if "成功" in text else "info"
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{ts}] {text}\n", tag)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _copy_sql_text(self, widget: tk.Text, tab_name: str) -> None:
        text = self._get_text_content(widget)
        if not text.strip():
            messagebox.showwarning("提醒", "目前沒有可複製的內容。")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self._append_log(f"{tab_name} 內容已複製到剪貼簿。")

    def _save_sql_text(self, widget: tk.Text, tab_name: str) -> None:
        text = self._get_text_content(widget)
        if not text.strip():
            messagebox.showwarning("提醒", "目前沒有可儲存的內容。")
            return
        default_name = {
            "原始 SQL (可編輯)": "raw_sql.sql",
            "目標輸出 SQL (模板渲染後)": "rendered_sql.sql",
            "日期替換": "date_replaced_sql.sql",
        }.get(tab_name, "sql_output.sql")
        target = filedialog.asksaveasfilename(
            defaultextension=".sql",
            filetypes=[("SQL files", "*.sql"), ("All files", "*.*")],
            initialfile=default_name,
        )
        if not target:
            return
        Path(target).write_text(text, encoding="utf-8", newline="\n")
        self._append_log(f"{tab_name} 已另存: {target}")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _apply_sql_theme(self, tname: str):
        theme = SQL_PREVIEW_THEMES.get(tname, SQL_PREVIEW_THEMES["Midnight"])
        widgets = [self.raw_sql_text, self.rendered_sql_text]
        if hasattr(self, "date_sql_text"):
            widgets.append(self.date_sql_text)
        for w in widgets:
            w.configure(
                bg=theme["background"],
                fg=theme["foreground"],
                insertbackground=theme["caret"],
                selectbackground=theme["selection_background"],
                selectforeground=theme["selection_foreground"],
            )
            self._refresh_sql_highlighting(w, theme)

    def _apply_ui_theme(self, tname: str):
        # 統一套用 UI 主題（只改視覺，不動功能）
        self._theme = UI_THEMES.get(tname, UI_THEMES[DEFAULT_UI_THEME_NAME])
        self.root.configure(bg=self._theme["app_bg"])
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Root.TFrame", background=self._theme["app_bg"])
        style.configure("Surface.TFrame", background=self._theme["surface_bg"])
        style.configure("Panel.TLabelframe", background=self._theme["surface_bg"], foreground=self._theme["text"])
        style.configure("Panel.TLabelframe.Label", background=self._theme["app_bg"], foreground=self._theme["text"])
        style.configure("Field.TLabel", background=self._theme["surface_bg"], foreground=self._theme["text"])
        style.configure("Dark.TEntry", fieldbackground=self._theme["input_bg"], foreground=self._theme["text"], padding=(8, 6))
        style.configure("Dark.TCombobox", fieldbackground=self._theme["input_bg"], foreground=self._theme["text"], padding=(8, 6))
        style.map("Dark.TCombobox", fieldbackground=[("readonly", self._theme["input_bg"])], foreground=[("readonly", self._theme["text"])])
        style.configure("Field.TCheckbutton", background=self._theme["surface_bg"], foreground=self._theme["text"])
        style.configure("Primary.TButton", padding=(16, 8), font=("Microsoft JhengHei UI", 11, "bold"), background=self._theme["accent"], foreground="white")
        style.map("Primary.TButton", background=[("active", self._theme["accent_active"])], foreground=[("active", "white")])
        style.configure("Secondary.TButton", padding=(10, 6), background=self._theme["accent_soft"], foreground=self._theme["text"])
        style.map("Secondary.TButton", background=[("active", "#D7E8F0")], foreground=[("active", "black")])
        style.configure("Hint.TLabel", background=self._theme["surface_bg"], foreground=self._theme["muted"])
        style.configure("SectionTitle.TLabel", background=self._theme["surface_bg"], foreground=self._theme["text"])
        style.configure("Preview.TNotebook", background=self._theme["app_bg"], borderwidth=0)
        style.configure("Preview.TNotebook.Tab", background=self._theme["surface_alt_bg"], foreground=self._theme["tab_text"], padding=(12, 6))
        style.map(
            "Preview.TNotebook.Tab",
            background=[("selected", self._theme["tab_selected"]), ("active", self._theme["tab_active"])],
            foreground=[("selected", self._theme["tab_text_selected"]), ("active", self._theme["text"])],
        )

        # 直接更新非 ttk 元件顏色
        if hasattr(self, "log_text"):
            self.log_text.configure(bg=self._theme["log_bg"], fg=self._theme["text"])
        if hasattr(self, "raw_sql_text"):
            self.raw_sql_text.configure(fg=self._theme["text"])
        if hasattr(self, "rendered_sql_text"):
            self.rendered_sql_text.configure(fg=self._theme["text"])
        if hasattr(self, "date_sql_text"):
            self.date_sql_text.configure(bg=self._theme["log_bg"], fg=self._theme["text"])

    def _on_ui_theme_selected(self, _ev):
        self._apply_ui_theme(self.ui_theme_var.get())

    def _refresh_sql_highlighting(self, widget: tk.Text, theme: dict = None):
        if getattr(widget, "_is_sql_widget", False):
            s = str(widget.cget("state"))
            widget.configure(state="normal")
            apply_sql_syntax_highlighting(widget, theme or SQL_PREVIEW_THEMES["Midnight"])
            widget.configure(state=s)

    def _on_sql_text_modified(self, ev):
        if getattr(ev.widget, "edit_modified", lambda: False)():
            self._refresh_sql_highlighting(ev.widget)
            if ev.widget is self.raw_sql_text:
                self._refresh_date_tab_sql()
            ev.widget.edit_modified(False)

    def _clear_start_date(self): self.start_date_var.set("")
    def _clear_end_date(self): self.end_date_var.set("")

    def _open_date_picker(self, v: tk.StringVar, t: str):
        p = tk.Toplevel(self.root)
        p.title(t)
        p.geometry("250x250")
        p.resizable(False, False)
        p.configure(bg=self._theme["app_bg"])
        p.grab_set()

        try: idt = datetime.strptime(v.get().strip(), "%Y-%m-%d").date()
        except: idt = date.today()

        state = {"y": idt.year, "m": idt.month}
        hf = tk.Frame(p, bg=self._theme["surface_bg"])
        hf.pack(fill="x", pady=5)
        
        tk.Button(hf, text="◀", bg=self._theme["surface_bg"], fg=self._theme["text"], command=lambda: nav(-1)).pack(side="left")
        ml = tk.Label(hf, text="", bg=self._theme["surface_bg"], fg=self._theme["text"], font=("Consolas", 12))
        ml.pack(side="left", expand=True)
        tk.Button(hf, text="▶", bg=self._theme["surface_bg"], fg=self._theme["text"], command=lambda: nav(1)).pack(side="right")

        cf = tk.Frame(p, bg=self._theme["app_bg"])
        cf.pack(pady=5)
        for i, wd in enumerate(["一", "二", "三", "四", "五", "六", "日"]):
            tk.Label(cf, text=wd, bg=self._theme["app_bg"], fg=self._theme["muted"], width=3).grid(row=0, column=i)
        
        btns = []
        def nav(d):
            state["m"] += d
            if state["m"] < 1: state["m"]=12; state["y"]-=1
            elif state["m"] > 12: state["m"]=1; state["y"]+=1
            draw()
        
        def pick(d):
            v.set(f"{state['y']}-{state['m']:02d}-{d:02d}")
            p.destroy()

        def draw():
            ml.configure(text=f"{state['y']} 年 {state['m']} 月")
            for b in btns: b.destroy()
            btns.clear()
            fw, dim = calendar.monthrange(state["y"], state["m"])
            r, c = 1, fw
            for d in range(1, dim + 1):
                b = tk.Button(
                    cf,
                    text=str(d),
                    width=3,
                    bg=self._theme["surface_bg"],
                    fg=self._theme["text"],
                    command=lambda dd=d: pick(dd),
                )
                b.grid(row=r, column=c, padx=1, pady=1)
                btns.append(b)
                c += 1
                if c > 6: c, r = 0, r+1
        draw()
        p.update_idletasks()
        rx, ry = self.root.winfo_rootx(), self.root.winfo_rooty()
        rw, rh = self.root.winfo_width(), self.root.winfo_height()
        p.geometry(f"+{rx + (rw - 250) // 2}+{ry + (rh - 250) // 2}")

def main():
    root = tk.Tk()
    app = SqlToolApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()
