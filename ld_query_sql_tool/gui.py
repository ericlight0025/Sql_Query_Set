# -*- coding: utf-8 -*-
"""SQL 工具主 GUI"""
from __future__ import annotations

import calendar
import os
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

APP_BG = "#0B1220"
SURFACE_BG = "#121C2B"
SURFACE_ALT_BG = "#182334"
INPUT_BG = "#0F1724"
TEXT_COLOR = "#E6EDF3"
MUTED_TEXT_COLOR = "#93A4B7"
ACCENT_COLOR = "#3A86C8"
ACCENT_ACTIVE_COLOR = "#55A4E8"
ACCENT_SOFT_COLOR = "#182C40"
BORDER_COLOR = "#2C3A4D"
LOG_COLOR = "#0E1723"
TAB_SELECTED_BG = "#1B2A3C"
TAB_ACTIVE_BG = "#22364E"
DEFAULT_SQL_THEME_NAME = "Midnight"

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
        self.root.configure(bg=APP_BG)
        self.is_running = False

        self.loaded_settings_error = ""
        settings = self._load_initial_settings()
        self.base_settings = settings

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

        self._build_style()
        self._build_layout()
        self._initialize_sql_editor(settings)
        self._apply_sql_theme(self.sql_theme_var.get())

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
        style.configure("Root.TFrame", background=APP_BG)
        style.configure("Surface.TFrame", background=SURFACE_BG)
        style.configure("Panel.TLabelframe", background=SURFACE_BG, foreground=TEXT_COLOR)
        style.configure("Panel.TLabelframe.Label", background=APP_BG, foreground=TEXT_COLOR)
        style.configure("Field.TLabel", background=SURFACE_BG, foreground=TEXT_COLOR)
        style.configure("Dark.TEntry", fieldbackground=INPUT_BG, foreground=TEXT_COLOR, padding=(8, 6))
        style.configure("Dark.TCombobox", fieldbackground=INPUT_BG, foreground=TEXT_COLOR, padding=(8, 6))
        style.map("Dark.TCombobox", fieldbackground=[("readonly", INPUT_BG)], foreground=[("readonly", TEXT_COLOR)])
        style.configure("Field.TCheckbutton", background=SURFACE_BG, foreground=TEXT_COLOR)
        style.configure("Primary.TButton", padding=(16, 8), font=("Microsoft JhengHei UI", 11, "bold"), background=ACCENT_COLOR, foreground="white")
        style.map("Primary.TButton", background=[("active", ACCENT_ACTIVE_COLOR)], foreground=[("active", "white")])
        style.configure("Secondary.TButton", padding=(10, 6), background=ACCENT_SOFT_COLOR, foreground=TEXT_COLOR)
        style.map("Secondary.TButton", background=[("active", "#D7E8F0")], foreground=[("active", "black")])
        style.configure("Hint.TLabel", background=SURFACE_BG, foreground=MUTED_TEXT_COLOR)
        style.configure("SectionTitle.TLabel", background=SURFACE_BG, foreground=TEXT_COLOR)
        style.configure("Preview.TNotebook", background=APP_BG, borderwidth=0)
        style.configure("Preview.TNotebook.Tab", background=SURFACE_ALT_BG, foreground=TEXT_COLOR, padding=(12, 6))
        style.map("Preview.TNotebook.Tab", background=[("selected", TAB_SELECTED_BG)], foreground=[("selected", TEXT_COLOR)])

    def _build_layout(self) -> None:
        container = ttk.Frame(self.root, style="Root.TFrame", padding=10)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)

        header = tk.Frame(container, bg=APP_BG)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        tk.Label(header, text="SQL 組合產生工具", bg=APP_BG, fg=TEXT_COLOR, font=("Microsoft JhengHei UI", 18, "bold")).pack(side="left")

        self.main_notebook = ttk.Notebook(container, style="Preview.TNotebook")
        self.main_notebook.grid(row=1, column=0, sticky="nsew")

        input_tab = ttk.Frame(self.main_notebook, style="Root.TFrame", padding=8)
        output_tab = ttk.Frame(self.main_notebook, style="Root.TFrame", padding=8)
        self.main_notebook.add(input_tab, text="設定與執行")
        self.main_notebook.add(output_tab, text="檢視與輸出")
        input_tab.columnconfigure(0, weight=1)
        output_tab.columnconfigure(0, weight=1)
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

        self._add_entry_row(form, 0, "OA 號碼", self.oa_no_var)
        self._add_entry_row(form, 1, "Query 前綴名稱", self.query_template_var)
        self._add_entry_row(form, 2, "輸出資料夾", self.output_dir_var, [("瀏覽", self._browse_output_dir)])
        self.sql_source_combobox = self._add_combobox_row(form, 3, "SQL 原始來源", self.sql_source_var, list(SQL_SOURCE_LABEL_TO_MODE))
        self._add_entry_row(form, 4, "SQL 檔案", self.sql_file_var, [("瀏覽", self._browse_sql_file), ("載入文字至編輯區", self._load_sql_file_into_editor_from_button)])
        self._add_entry_row(form, 5, "開始日期", self.start_date_var, [("選日曆", lambda: self._open_date_picker(self.start_date_var, "開始")), ("清除", self._clear_start_date)])
        self._add_entry_row(form, 6, "結束日期", self.end_date_var, [("選日曆", lambda: self._open_date_picker(self.end_date_var, "結束")), ("清除", self._clear_end_date)])
        self._add_entry_row(form, 7, "開發內容說明", self.content_var)
        self._add_entry_row(form, 8, "作者", self.author_var)
        self._add_entry_row(form, 9, "欄位文字檔", self.title_file_var, [("瀏覽", self._browse_title_file)])
        self._add_entry_row(form, 10, "模板 SQL 檔", self.template_file_var, [("瀏覽", self._browse_template_file)])
        self.overwrite_mode_combobox = self._add_combobox_row(form, 11, "檔案已存在處理模式", self.overwrite_mode_var, list(OVERWRITE_LABEL_TO_MODE))
        self._add_checkbox_row(form, 12, "完成後自動開啟輸出資料夾", self.open_output_dir_var)

        # 輸出 Tab - 預覽區塊
        preview_frame = ttk.LabelFrame(output_tab, text="SQL 文字檢視", style="Panel.TLabelframe", padding=10)
        preview_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(1, weight=1)

        self.preview_notebook = ttk.Notebook(preview_frame, style="Preview.TNotebook")
        self.preview_notebook.grid(row=1, column=0, sticky="nsew")

        self.raw_sql_text = self._build_preview_tab(self.preview_notebook, "原始 SQL (可編輯)", editable=True)
        self.rendered_sql_text = self._build_preview_tab(self.preview_notebook, "目標輸出 SQL (模板渲染後)")

        # 輸出 Tab - Log 區塊
        log_frame = ttk.LabelFrame(output_tab, text="執行紀錄", style="Panel.TLabelframe", padding=10)
        log_frame.grid(row=1, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = tk.Text(log_frame, height=8, bg=LOG_COLOR, fg=TEXT_COLOR, font=("Consolas", 10), borderwidth=0)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        self.log_text.tag_configure("info", foreground=TEXT_COLOR)
        self.log_text.tag_configure("error", foreground="#FF6B6B")
        self.log_text.tag_configure("warning", foreground="#FFD93D")
        self.log_text.configure(state="disabled")

        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def _build_preview_tab(self, notebook: ttk.Notebook, title: str, editable: bool = False) -> tk.Text:
        frame = ttk.Frame(notebook, style="Surface.TFrame", padding=6)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        notebook.add(frame, text=title)

        text_widget = tk.Text(frame, undo=editable, height=15, bg=LOG_COLOR, fg=TEXT_COLOR, font=("Consolas", 11), borderwidth=0, wrap="none")
        text_widget.grid(row=0, column=0, sticky="nsew")
        text_widget._is_editable = editable
        text_widget._is_sql_widget = True

        y_scroll = ttk.Scrollbar(frame, orient="vertical", command=text_widget.yview)
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll = ttk.Scrollbar(frame, orient="horizontal", command=text_widget.xview)
        x_scroll.grid(row=1, column=0, sticky="ew")
        text_widget.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        if editable:
            text_widget.bind("<<Modified>>", self._on_sql_text_modified)
        else:
            text_widget.configure(state="disabled")
        return text_widget

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
            mode_enum = SqlSourceMode(SQL_SOURCE_LABEL_TO_MODE.get(self.sql_source_var.get(), "file"))
            overwrite_enum = OverwriteMode(OVERWRITE_LABEL_TO_MODE.get(self.overwrite_mode_var.get(), "prompt"))
            
            raw_t = self._get_text_content(self.raw_sql_text)
            st = AppSettings(
                oa_no=self.oa_no_var.get().strip(),
                query_template=self.query_template_var.get().strip(),
                output_dir=self.output_dir_var.get().strip(),
                sql_source_mode=mode_enum,
                sql_file=self.sql_file_var.get().strip(),
                sql_text=raw_t if mode_enum.value == 'inline' else "",
                content=self.content_var.get().strip(),
                author=self.author_var.get().strip(),
                title_file=self.title_file_var.get().strip(),
                template_file=self.template_file_var.get().strip(),
                start_date=self.start_date_var.get().strip(),
                end_date=self.end_date_var.get().strip(),
                overwrite_mode=overwrite_enum,
                open_output_dir=self.open_output_dir_var.get()
            )
            config = build_config_from_settings(st)
            resolved = self._resolve_overwrite(config)
            if not resolved: return
            
            self._clear_log()
            self.main_notebook.select(1)
            self._set_running(True)
            threading.Thread(target=self._run_bg, args=(resolved, st), daemon=True).start()
        except Exception as e:
            messagebox.showerror("錯誤", f"輸入參數異常:\n{e}")

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
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{text}\n", tag)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _apply_sql_theme(self, tname: str):
        theme = SQL_PREVIEW_THEMES.get(tname, SQL_PREVIEW_THEMES["Midnight"])
        for w in (self.raw_sql_text, self.rendered_sql_text):
            w.configure(bg=theme["background"], fg=theme["foreground"], insertbackground=theme["caret"],
                        selectbackground=theme["selection_background"], selectforeground=theme["selection_foreground"])
            self._refresh_sql_highlighting(w, theme)

    def _refresh_sql_highlighting(self, widget: tk.Text, theme: dict = None):
        if getattr(widget, "_is_sql_widget", False):
            s = str(widget.cget("state"))
            widget.configure(state="normal")
            apply_sql_syntax_highlighting(widget, theme or SQL_PREVIEW_THEMES["Midnight"])
            widget.configure(state=s)

    def _on_sql_text_modified(self, ev):
        if getattr(ev.widget, "edit_modified", lambda: False)():
            self._refresh_sql_highlighting(ev.widget)
            ev.widget.edit_modified(False)

    def _clear_start_date(self): self.start_date_var.set("")
    def _clear_end_date(self): self.end_date_var.set("")

    def _open_date_picker(self, v: tk.StringVar, t: str):
        p = tk.Toplevel(self.root)
        p.title(t)
        p.geometry("250x250")
        p.resizable(False, False)
        p.configure(bg=APP_BG)
        p.grab_set()

        try: idt = datetime.strptime(v.get().strip(), "%Y-%m-%d").date()
        except: idt = date.today()

        state = {"y": idt.year, "m": idt.month}
        hf = tk.Frame(p, bg=SURFACE_BG)
        hf.pack(fill="x", pady=5)
        
        tk.Button(hf, text="◀", bg=SURFACE_BG, fg=TEXT_COLOR, command=lambda: nav(-1)).pack(side="left")
        ml = tk.Label(hf, text="", bg=SURFACE_BG, fg=TEXT_COLOR, font=("Consolas", 12))
        ml.pack(side="left", expand=True)
        tk.Button(hf, text="▶", bg=SURFACE_BG, fg=TEXT_COLOR, command=lambda: nav(1)).pack(side="right")

        cf = tk.Frame(p, bg=APP_BG)
        cf.pack(pady=5)
        for i, wd in enumerate(["一", "二", "三", "四", "五", "六", "日"]):
            tk.Label(cf, text=wd, bg=APP_BG, fg=MUTED_TEXT_COLOR, width=3).grid(row=0, column=i)
        
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
                b = tk.Button(cf, text=str(d), width=3, bg=SURFACE_BG, fg=TEXT_COLOR, command=lambda dd=d: pick(dd))
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
