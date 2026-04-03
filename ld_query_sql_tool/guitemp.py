from __future__ import annotations

import calendar
import os
import threading
import tkinter as tk
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from .config_service import build_config_from_settings, load_settings, save_settings
from .models import (
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
from .sql_render_service import read_text_preserve_newlines
from .sql_service import build_output_file_path
from .syntax_highlighter import apply_sql_syntax_highlighting
from .workflow import execute_generation


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
DEFAULT_SQL_THEME_NAME = "Obsidian"

OVERWRITE_LABEL_TO_MODE = {
   "čŠ˘ĺ?": OverwriteMode.PROMPT.value,
   "?´ćĽčŚĺŻŤ": OverwriteMode.OVERWRITE.value,
   "?Şĺ??šĺ?": OverwriteMode.RENAME.value,
}
OVERWRITE_MODE_TO_LABEL = {value: key for key, value in OVERWRITE_LABEL_TO_MODE.items()}

SQL_SOURCE_LABEL_TO_MODE = {
   "SQL ćŞć?": SqlSourceMode.FILE.value,
   "?Ťé˘çˇ¨čźŻ": SqlSourceMode.INLINE.value,
}
SQL_SOURCE_MODE_TO_LABEL = {value: key for key, value in SQL_SOURCE_LABEL_TO_MODE.items()}

SQL_PREVIEW_THEMES = {
   "Obsidian": {
       "background": "#293134",
       "foreground": "#E0E2E4",
       "caret": "#FFCD22",
       "selection_background": "#3E4C55",
       "selection_foreground": "#F8FBFC",
       "keyword": "#93C763",
       "string": "#EC7600",
       "comment": "#66747B",
       "number": "#FFCD22",
       "placeholder": "#678CB1",
       "bind_variable": "#7DD5CF",
   },
   "Monokai": {
       "background": "#272822",
       "foreground": "#F8F8F2",
       "caret": "#F8F8F0",
       "selection_background": "#49483E",
       "selection_foreground": "#F8F8F2",
       "keyword": "#F92672",
       "string": "#E6DB74",
       "comment": "#75715E",
       "number": "#AE81FF",
       "placeholder": "#66D9EF",
       "bind_variable": "#A6E22E",
   },
   "Nord": {
       "background": "#2E3440",
       "foreground": "#D8DEE9",
       "caret": "#88C0D0",
       "selection_background": "#4C566A",
       "selection_foreground": "#ECEFF4",
       "keyword": "#81A1C1",
       "string": "#A3BE8C",
       "comment": "#616E88",
       "number": "#B48EAD",
       "placeholder": "#EBCB8B",
       "bind_variable": "#8FBCBB",
   },
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
   },
   "Graphite": {
       "background": "#1E222A",
       "foreground": "#C8CCD4",
       "caret": "#D7BA7D",
       "selection_background": "#3A404B",
       "selection_foreground": "#F5F7FA",
       "keyword": "#C678DD",
       "string": "#98C379",
       "comment": "#5C6370",
       "number": "#D19A66",
       "placeholder": "#61AFEF",
       "bind_variable": "#56B6C2",
   },
}


class SqlToolApp:
   """GUI ?Şč?č˛Źćś?čź¸?Ľč?éĄŻç¤şçľć?ďźĺˇčĄé?čźŻäş¤çľ?workflow??""

   EMPTY_PREVIEW_MESSAGE = "ĺ°ćŞ?˘ç? SQL?č??ĺ°čź¸ĺĽ?č¨­ĺŽĺ??¸ď??ć??é?ĺ§ç˘??SQL?ă?
   RUNNING_PREVIEW_MESSAGE = "SQL ?˘ç?ä¸­ď?ĺŽć?ĺžć?éĄŻç¤ş?Ľć??żć?ĺž?SQL ?ĺ?čŁĺ? SQL??

   def __init__(self, root: tk.Tk, settings_file: Path = DEFAULT_SETTINGS_FILE) -> None:
       self.root = root
       self.settings_file = Path(settings_file)
       self.root.title("SQL çŽĄç?ĺˇĽĺˇ")
       self.root.geometry("1380x980")
       self.root.minsize(1180, 860)
       self.root.configure(bg=APP_BG)
       self.is_running = False
       self.preview_windows: list[tuple[tk.Toplevel, tk.Text]] = []

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
       self.sql_source_var = tk.StringVar(
           value=SQL_SOURCE_MODE_TO_LABEL.get(str(settings.sql_source_mode), "SQL ćŞć?")
       )
       self.sql_theme_var = tk.StringVar(value=DEFAULT_SQL_THEME_NAME)
       self.overwrite_mode_var = tk.StringVar(
           value=OVERWRITE_MODE_TO_LABEL.get(str(settings.overwrite_mode), "čŠ˘ĺ?")
       )
       self.open_output_dir_var = tk.BooleanVar(value=settings.open_output_dir)

       self._build_style()
       self._build_layout()
       self._initialize_sql_editor(settings)
       self._apply_sql_theme(self.sql_theme_var.get())

       if self.loaded_settings_error:
           self._append_log(f"č¨­ĺ?ćŞč??Ľĺ¤ą?ď?ĺˇ˛ćš?¨é?č¨­ĺ? {self.loaded_settings_error}")

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
       style.configure("Panel.TLabelframe", background=SURFACE_BG, foreground=TEXT_COLOR, bordercolor=BORDER_
          COLOR)
       style.configure("Panel.TLabelframe.Label", background=APP_BG, foreground=TEXT_COLOR)
       style.configure("Field.TLabel", background=SURFACE_BG, foreground=TEXT_COLOR)
       style.configure(
           "Dark.TEntry",
           fieldbackground=INPUT_BG,
           foreground=TEXT_COLOR,
           bordercolor=BORDER_COLOR,
           lightcolor=BORDER_COLOR,
           darkcolor=BORDER_COLOR,
           padding=(10, 8),
       )
       style.configure(
           "Dark.TCombobox",
           fieldbackground=INPUT_BG,
           foreground=TEXT_COLOR,
           bordercolor=BORDER_COLOR,
           lightcolor=BORDER_COLOR,
           darkcolor=BORDER_COLOR,
           padding=(10, 8),
       )
       style.map(
           "Dark.TCombobox",
           fieldbackground=[("readonly", INPUT_BG)],
           foreground=[("readonly", TEXT_COLOR)],
       )
       style.configure("Field.TCheckbutton", background=SURFACE_BG, foreground=TEXT_COLOR)
       style.configure(
           "Primary.TButton",
           padding=(22, 12),
           font=("Microsoft JhengHei UI", 11, "bold"),
           borderwidth=0,
       )
       style.map(
           "Primary.TButton",
           background=[("active", ACCENT_ACTIVE_COLOR), ("!disabled", ACCENT_COLOR)],
           foreground=[("!disabled", "white")],
       )
       style.configure(
           "Secondary.TButton",
           padding=(12, 8),
           background=ACCENT_SOFT_COLOR,
           foreground=TEXT_COLOR,
           bordercolor=BORDER_COLOR,
           lightcolor=BORDER_COLOR,
           darkcolor=BORDER_COLOR,
       )
       style.map(
           "Secondary.TButton",
           background=[("active", "#D7E8F0"), ("!disabled", ACCENT_SOFT_COLOR)],
           foreground=[("!disabled", TEXT_COLOR)],
       )
       style.configure("Hint.TLabel", background=SURFACE_BG, foreground=MUTED_TEXT_COLOR)
       style.configure("SectionTitle.TLabel", background=SURFACE_BG, foreground=TEXT_COLOR)
       style.configure("Preview.TNotebook", background=APP_BG, borderwidth=0, tabmargins=(0, 0, 0, 0))
       style.configure(
           "Preview.TNotebook.Tab",
           background=SURFACE_ALT_BG,
           foreground=TEXT_COLOR,
           padding=(18, 10),
           font=("Microsoft JhengHei UI", 10, "bold"),
           borderwidth=0,
       )
       style.map(
           "Preview.TNotebook.Tab",
           background=[("selected", TAB_SELECTED_BG), ("active", TAB_ACTIVE_BG)],
           foreground=[("selected", TEXT_COLOR), ("active", TEXT_COLOR)],
       )

   def _build_layout(self) -> None:
       container = ttk.Frame(self.root, style="Root.TFrame", padding=18)
       container.pack(fill="both", expand=True)
       container.columnconfigure(0, weight=1)
       container.rowconfigure(1, weight=1)

       header = tk.Frame(container, bg=APP_BG)
       header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
       header.columnconfigure(0, weight=1)

       title = tk.Label(
           header,
           text="SQL çŽĄç?ĺˇĽĺˇ",
           bg=APP_BG,
           fg=TEXT_COLOR,
           font=("Microsoft JhengHei UI", 24, "bold"),
       )
       title.grid(row=0, column=0, sticky="w")

       subtitle = tk.Label(
           header,
           text="čź¸ĺĽ?č?č˛Źĺ??¸č¨­ĺŽď?čź¸ĺş?č?č˛ŹćŞ˘?Ľĺ?ĺ§?SQL?ćĽ?ćż?ç??č?ĺ°č?ĺž?SQL??,
           bg=APP_BG,
           fg=MUTED_TEXT_COLOR,
           font=("Microsoft JhengHei UI", 10),
       )
       subtitle.grid(row=1, column=0, sticky="w", pady=(4, 0))

       self.main_notebook = ttk.Notebook(container, style="Preview.TNotebook")
       self.main_notebook.grid(row=1, column=0, sticky="nsew")

       self.input_tab = ttk.Frame(self.main_notebook, style="Root.TFrame", padding=8)
       self.output_tab = ttk.Frame(self.main_notebook, style="Root.TFrame", padding=8)
       self.main_notebook.add(self.input_tab, text="čź¸ĺĽ??)
       self.main_notebook.add(self.output_tab, text="čź¸ĺş??)

       self.input_tab.columnconfigure(0, weight=1)
       self.output_tab.columnconfigure(0, weight=1)
       self.output_tab.rowconfigure(0, weight=4)
       self.output_tab.rowconfigure(1, weight=1)

       action_frame = ttk.LabelFrame(self.input_tab, text="ĺżŤéĺˇčĄ?, style="Panel.TLabelframe", padding=18)
       action_frame.grid(row=0, column=0, sticky="ew", pady=(0, 14))
       action_frame.columnconfigure(0, weight=1)

       action_title = ttk.Label(
           action_frame,
           text="?ĺĄŤ?ć¸ďźĺ??é?ĺ§ç˘??SQL??,
           style="SectionTitle.TLabel",
           font=("Microsoft JhengHei UI", 13, "bold"),
       )
       action_title.grid(row=0, column=0, sticky="w")

       action_hint = ttk.Label(
           action_frame,
           text="ĺŚć?čŚç´?ĽĺžŽčŞżĺ?ĺ§?SQLďźĺ??°čź¸?şé?çŹŹä??é?çą¤çˇ¨čźŻď??ć??ç¨?Ťé˘ SQL ?ć°?˘ç??ă?,
           style="Hint.TLabel",
       )
       action_hint.grid(row=1, column=0, sticky="w", pady=(6, 14))

       self.execute_button = ttk.Button(
           action_frame,
           text="?ĺ??˘ç? SQL",
           style="Primary.TButton",
           command=self._execute_process,
       )
       self.execute_button.grid(row=2, column=0, sticky="w")

       form = ttk.LabelFrame(self.input_tab, text="čź¸ĺĽ?ć¸", style="Panel.TLabelframe", padding=16)
       form.grid(row=1, column=0, sticky="nsew")
       form.columnconfigure(1, weight=1)

       self._add_entry_row(form, 0, "OA ?ç˘ź", self.oa_no_var)
       self._add_entry_row(form, 1, "Query çŻćŹ", self.query_template_var)
       self._add_entry_row(form, 2, "čź¸ĺşčˇŻĺ?", self.output_dir_var, [("?čŚ˝", self._browse_output_dir)])
       self._add_entry_row(
           form,
           3,
           "SQL ćŞć?",
           self.sql_file_var,
           [("?čŚ˝", self._browse_sql_file), ("čźĺĽçˇ¨čźŻ??, self._load_sql_file_into_editor_from_button)],
       )
       self.sql_source_combobox = self._add_combobox_row(
           form,
           4,
           "SQL äžć?",
           self.sql_source_var,
           list(SQL_SOURCE_LABEL_TO_MODE),
       )
       self._add_entry_row(
           form,
           5,
           "?ĺ???,
           self.start_date_var,
           [("?¸ć??Ľć?", lambda: self._open_date_picker(self.start_date_var, "?ĺ???)), ("ć¸çŠş", self._clear
          _start_date)],
       )
       self._add_entry_row(
           form,
           6,
           "çľć???,
           self.end_date_var,
           [("?¸ć??Ľć?", lambda: self._open_date_picker(self.end_date_var, "çľć???)), ("ć¸çŠş", self._clear_e
          nd_date)],
       )
       self._add_entry_row(form, 7, "?§ĺŽš", self.content_var)
       self._add_entry_row(form, 8, "ä˝č?, self.author_var)
       self._add_entry_row(form, 9, "ćŹä?ćŞć?", self.title_file_var, [("?čŚ˝", self._browse_title_file)])
       self._add_entry_row(form, 10, "ć¨ĄćżćŞć?", self.template_file_var, [("?čŚ˝", self._browse_template_file
          )])
       self.overwrite_mode_combobox = self._add_combobox_row(
           form,
           11,
           "?ĺ?ćŞč???,
           self.overwrite_mode_var,
           list(OVERWRITE_LABEL_TO_MODE),
       )
       self._add_checkbox_row(form, 12, "ĺŽć?ĺžčŞ?é??čź¸?şč??ĺ¤ž", self.open_output_dir_var)

       preview_frame = ttk.LabelFrame(self.output_tab, text="SQL ĺˇĽä???, style="Panel.TLabelframe", padding=
          16)
       preview_frame.grid(row=0, column=0, sticky="nsew")
       preview_frame.columnconfigure(0, weight=1)
       preview_frame.rowconfigure(3, weight=1)

       preview_header = ttk.Frame(preview_frame, style="Surface.TFrame")
       preview_header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
       preview_header.columnconfigure(0, weight=1)

       preview_title = ttk.Label(
           preview_header,
           text="çŹŹä??é?çą¤ĺŻ?´ćĽçˇ¨čźŻ?ĺ? SQL??,
           style="SectionTitle.TLabel",
           font=("Microsoft JhengHei UI", 13, "bold"),
       )
       preview_title.grid(row=0, column=0, sticky="w")

       preview_hint = ttk.Label(
           preview_header,
           text="äżŽćšĺŽĺ??Żç´?Ľç¨?Ťé˘?§ĺŽš?ć°?˘ç?ďźĺł?´ĺŞ?ć? SQL çˇ¨čźŻ? themeďźä??šć´éŤ?dark mode??,
           style="Hint.TLabel",
       )
       preview_hint.grid(row=1, column=0, sticky="w", pady=(4, 0))

       theme_frame = ttk.Frame(preview_header, style="Surface.TFrame")
       theme_frame.grid(row=0, column=1, rowspan=2, sticky="e")
       theme_label = ttk.Label(theme_frame, text="SQL Theme", style="Field.TLabel")
       theme_label.grid(row=0, column=0, padx=(0, 8))
       self.theme_combobox = ttk.Combobox(
           theme_frame,
           textvariable=self.sql_theme_var,
           values=list(SQL_PREVIEW_THEMES),
           state="readonly",
           style="Dark.TCombobox",
           width=10,
       )
       self.theme_combobox.grid(row=0, column=1)
       self.theme_combobox.bind("<<ComboboxSelected>>", self._on_sql_theme_changed)

       preview_toolbar = ttk.Frame(preview_frame, style="Surface.TFrame")
       preview_toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 12))
       preview_toolbar.columnconfigure(0, weight=1)

       left_toolbar = ttk.Frame(preview_toolbar, style="Surface.TFrame")
       left_toolbar.grid(row=0, column=0, sticky="w")

       self.reload_sql_button = ttk.Button(
           left_toolbar,
           text="ĺž?SQL ćŞé?čźĺ?ĺ§?SQL",
           style="Secondary.TButton",
           command=self._load_sql_file_into_editor_from_button,
       )
       self.reload_sql_button.grid(row=0, column=0, padx=(0, 8))

       self.regenerate_from_editor_button = ttk.Button(
           left_toolbar,
           text="?¨çŤ??SQL ?ć°?˘ç?",
           style="Primary.TButton",
           command=self._regenerate_from_editor,
       )
       self.regenerate_from_editor_button.grid(row=0, column=1)

       right_toolbar = ttk.Frame(preview_toolbar, style="Surface.TFrame")
       right_toolbar.grid(row=0, column=1, sticky="e")

       self.open_current_preview_button = ttk.Button(
           right_toolbar,
           text="?Žĺ??çą¤?ć°čŚç?",
           style="Secondary.TButton",
           command=self._open_selected_preview_window,
       )
       self.open_current_preview_button.grid(row=0, column=0, padx=(0, 8))

       self.open_rendered_preview_button = ttk.Button(
           right_toolbar,
           text="ĺ°č?ĺž?SQL ?ć°čŚç?",
           style="Secondary.TButton",
           command=self._open_rendered_preview_window,
       )
       self.open_rendered_preview_button.grid(row=0, column=1)

       self.preview_notebook = ttk.Notebook(preview_frame, style="Preview.TNotebook")
       self.preview_notebook.grid(row=3, column=0, sticky="nsew")

       self.raw_sql_text = self._build_preview_tab(self.preview_notebook, "?ĺ? SQL", editable=True)
       self.resolved_sql_text = self._build_preview_tab(self.preview_notebook, "?Ľć??żć?ĺž?SQL")
       self.rendered_sql_text = self._build_preview_tab(self.preview_notebook, "ĺ°č?ĺž?SQL")
       self._set_preview_content(None)

       log_frame = ttk.LabelFrame(self.output_tab, text="?ˇč??Ľč?", style="Panel.TLabelframe", padding=16)
       log_frame.grid(row=1, column=0, sticky="nsew", pady=(14, 0))
       log_frame.columnconfigure(0, weight=1)
       log_frame.rowconfigure(0, weight=1)

       self.log_text = tk.Text(
           log_frame,
           height=10,
           bg=LOG_COLOR,
           fg=TEXT_COLOR,
           insertbackground=TEXT_COLOR,
           relief="flat",
           borderwidth=0,
           font=("Consolas", 11),
           wrap="word",
       )
       self.log_text.grid(row=0, column=0, sticky="nsew")
       self.log_text.tag_configure("info", foreground=TEXT_COLOR)
       self.log_text.tag_configure("success", foreground="#7EE787")
       self.log_text.tag_configure("warning", foreground="#F2CC60")
       self.log_text.tag_configure("error", foreground="#FF9B8E")
       self.log_text.configure(state="disabled")

       scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
       scrollbar.grid(row=0, column=1, sticky="ns")
       self.log_text.configure(yscrollcommand=scrollbar.set)

   def _build_preview_tab(self, notebook: ttk.Notebook, tab_title: str, editable: bool = False) -> tk.Text:
       tab = ttk.Frame(notebook, style="Surface.TFrame", padding=8)
       tab.columnconfigure(0, weight=1)
       tab.rowconfigure(0, weight=1)
       notebook.add(tab, text=tab_title)

       text_widget = tk.Text(
           tab,
           undo=editable,
           maxundo=-1,
           height=12,
           bg=LOG_COLOR,
           fg=TEXT_COLOR,
           insertbackground=TEXT_COLOR,
           relief="flat",
           borderwidth=0,
           font=("Consolas", 11),
           wrap="none",
       )
       text_widget.grid(row=0, column=0, sticky="nsew")
       text_widget._is_editable = editable  # type: ignore[attr-defined]
       text_widget._is_sql_widget = True  # type: ignore[attr-defined]
       if editable:
           text_widget.bind("<<Modified>>", self._on_sql_text_modified)
           text_widget.edit_modified(False)
       if not editable:
           text_widget.configure(state="disabled")

       y_scrollbar = ttk.Scrollbar(tab, orient="vertical", command=text_widget.yview)
       y_scrollbar.grid(row=0, column=1, sticky="ns")
       x_scrollbar = ttk.Scrollbar(tab, orient="horizontal", command=text_widget.xview)
       x_scrollbar.grid(row=1, column=0, sticky="ew")
       text_widget.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
       return text_widget

   def _initialize_sql_editor(self, settings: AppSettings) -> None:
       initial_text = settings.sql_text if str(settings.sql_source_mode) == SqlSourceMode.INLINE.value else "
          "
       if initial_text:
           self._set_text_widget_content(self.raw_sql_text, initial_text, editable=True)
       else:
           sql_file = Path(settings.sql_file)
           if sql_file.is_file():
               self._load_sql_file_into_editor(sql_file, switch_source_mode=False, announce=False)

       self._set_text_widget_content(self.resolved_sql_text, self.EMPTY_PREVIEW_MESSAGE, editable=False)
       self._set_text_widget_content(self.rendered_sql_text, self.EMPTY_PREVIEW_MESSAGE, editable=False)

   def _open_selected_preview_window(self) -> None:
       preview_title, preview_widget = self._get_selected_preview_tab()
       self._open_preview_window(preview_title, self._get_text_widget_content(preview_widget))

   def _open_rendered_preview_window(self) -> None:
       self._open_preview_window("ĺ°č?ĺž?SQL", self._get_text_widget_content(self.rendered_sql_text))

   def _get_selected_preview_tab(self) -> tuple[str, tk.Text]:
       preview_tabs = [
           ("?ĺ? SQL", self.raw_sql_text),
           ("?Ľć??żć?ĺž?SQL", self.resolved_sql_text),
           ("ĺ°č?ĺž?SQL", self.rendered_sql_text),
       ]
       if not hasattr(self, "preview_notebook"):
           return preview_tabs[0]

       current_index = self.preview_notebook.index(self.preview_notebook.select())
       return preview_tabs[current_index]

   def _open_preview_window(self, preview_title: str, content: str) -> None:
       theme = SQL_PREVIEW_THEMES.get(self.sql_theme_var.get(), SQL_PREVIEW_THEMES[DEFAULT_SQL_THEME_NAME])

       preview_window = tk.Toplevel(self.root)
       preview_window.title(f"SQL ?čŚ˝ - {preview_title}")
       preview_window.geometry("1220x860")
       preview_window.minsize(920, 680)
       preview_window.configure(bg=APP_BG)

       container = ttk.Frame(preview_window, style="Root.TFrame", padding=14)
       container.pack(fill="both", expand=True)
       container.columnconfigure(0, weight=1)
       container.rowconfigure(1, weight=1)

       header = tk.Label(
           container,
           text=preview_title,
           bg=APP_BG,
           fg=TEXT_COLOR,
           font=("Microsoft JhengHei UI", 18, "bold"),
       )
       header.grid(row=0, column=0, sticky="w", pady=(0, 12))

       text_widget = tk.Text(
           container,
           bg=theme["background"],
           fg=theme["foreground"],
           insertbackground=theme["caret"],
           relief="flat",
           borderwidth=0,
           font=("Consolas", 11),
           wrap="none",
       )
       text_widget.grid(row=1, column=0, sticky="nsew")

       y_scrollbar = ttk.Scrollbar(container, orient="vertical", command=text_widget.yview)
       y_scrollbar.grid(row=1, column=1, sticky="ns")
       x_scrollbar = ttk.Scrollbar(container, orient="horizontal", command=text_widget.xview)
       x_scrollbar.grid(row=2, column=0, sticky="ew")
       text_widget.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)

       text_widget.insert("1.0", content)
       self._refresh_sql_highlighting(text_widget, theme)
       text_widget.configure(state="disabled")
       self.preview_windows.append((preview_window, text_widget))

   def _add_entry_row(
       self,
       parent: ttk.LabelFrame,
       row_index: int,
       label_text: str,
       variable: tk.StringVar,
       actions: list[tuple[str, Callable[[], None]]] | None = None,
   ) -> None:
       label = ttk.Label(parent, text=f"{label_text}:", style="Field.TLabel")
       label.grid(row=row_index, column=0, sticky="w", padx=(0, 10), pady=6)

       entry = ttk.Entry(parent, textvariable=variable, style="Dark.TEntry")
       entry.grid(row=row_index, column=1, sticky="ew", pady=6)

       if actions:
           button_frame = ttk.Frame(parent, style="Surface.TFrame")
           button_frame.grid(row=row_index, column=2, padx=(10, 0), pady=6, sticky="e")
           for button_index, (button_text, button_command) in enumerate(actions):
               ttk.Button(
                   button_frame,
                   text=button_text,
                   style="Secondary.TButton",
                   command=button_command,
               ).grid(row=0, column=button_index, padx=(0 if button_index == 0 else 8, 0))

   def _add_combobox_row(
       self,
       parent: ttk.LabelFrame,
       row_index: int,
       label_text: str,
       variable: tk.StringVar,
       options: list[str],
   ) -> ttk.Combobox:
       label = ttk.Label(parent, text=f"{label_text}:", style="Field.TLabel")
       label.grid(row=row_index, column=0, sticky="w", padx=(0, 10), pady=6)

       combobox = ttk.Combobox(
           parent,
           textvariable=variable,
           values=options,
           state="readonly",
           style="Dark.TCombobox",
       )
       combobox.grid(row=row_index, column=1, sticky="ew", pady=6)
       return combobox

   def _add_checkbox_row(
       self,
       parent: ttk.LabelFrame,
       row_index: int,
       label_text: str,
       variable: tk.BooleanVar,
   ) -> None:
       checkbox = ttk.Checkbutton(parent, text=label_text, variable=variable, style="Field.TCheckbutton")
       checkbox.grid(row=row_index, column=1, sticky="w", pady=6)

   def _browse_output_dir(self) -> None:
       selected = filedialog.askdirectory(
           initialdir=self._get_initial_dir(self.output_dir_var.get(), DEFAULT_OUTPUT_DIR)
       )
       if selected:
           self.output_dir_var.set(selected)
           self._append_log(f"?¸ć?äşč??ĺ¤ž: {selected}")

   def _browse_sql_file(self) -> None:
       selected = filedialog.askopenfilename(
           initialdir=self._get_initial_dir(self.sql_file_var.get(), DEFAULT_INPUT_DIR),
           filetypes=[("SQL ćŞć?", "*.sql"), ("??ć?ćĄ?, "*.*")],
       )
       if selected:
           self.sql_file_var.set(selected)
           self.sql_source_var.set(SQL_SOURCE_MODE_TO_LABEL[SqlSourceMode.FILE.value])
           self._append_log(f"?¸ć?äş?SQL ćŞć?: {selected}")
           self._load_sql_file_into_editor(Path(selected), switch_source_mode=False, announce=False)

   def _browse_title_file(self) -> None:
       selected = filedialog.askopenfilename(
           initialdir=self._get_initial_dir(self.title_file_var.get(), DEFAULT_INPUT_DIR),
           filetypes=[("?ĺ?ćŞ?, "*.txt"), ("??ć?ćĄ?, "*.*")],
       )
       if selected:
           self.title_file_var.set(selected)
           self._append_log(f"?¸ć?äşć?ä˝ć?ćĄ? {selected}")

   def _browse_template_file(self) -> None:
       selected = filedialog.askopenfilename(
           initialdir=self._get_initial_dir(self.template_file_var.get(), DEFAULT_TEMPLATE_DIR),
           filetypes=[("SQL çŻćŹ", "*.sql"), ("??ć?ćĄ?, "*.*")],
       )
       if selected:
           self.template_file_var.set(selected)
           self._append_log(f"?¸ć?äşć¨Ą?żć?ćĄ? {selected}")

   def _load_sql_file_into_editor_from_button(self) -> None:
       sql_file_text = self.sql_file_var.get().strip()
       if not sql_file_text:
           messagebox.showerror("čźĺĽĺ¤ąć?", "čŤĺ??ĺ? SQL ćŞć?čˇŻĺ???)
           return

       self._load_sql_file_into_editor(Path(sql_file_text), switch_source_mode=True, announce=True)

   def _load_sql_file_into_editor(
       self,
       sql_file: Path,
       *,
       switch_source_mode: bool,
       announce: bool,
   ) -> bool:
       if not sql_file.is_file():
           messagebox.showerror("čźĺĽĺ¤ąć?", f"SQL ćŞć?ä¸ĺ???\n{sql_file}")
           return False

       try:
           content = read_text_preserve_newlines(sql_file)
       except Exception as exc:
           messagebox.showerror("čźĺĽĺ¤ąć?", str(exc))
           return False

       self._set_text_widget_content(self.raw_sql_text, content, editable=True)
       if switch_source_mode:
           self.sql_source_var.set(SQL_SOURCE_MODE_TO_LABEL[SqlSourceMode.FILE.value])
       if hasattr(self, "main_notebook"):
           self.main_notebook.select(self.output_tab)
       if hasattr(self, "preview_notebook"):
           self.preview_notebook.select(0)
       if announce:
           self._append_log(f"ĺˇ˛ĺ? SQL ćŞč??Ľĺ°?ĺ? SQL çˇ¨čźŻ?: {sql_file}")
       return True

   def _regenerate_from_editor(self) -> None:
       self.sql_source_var.set(SQL_SOURCE_MODE_TO_LABEL[SqlSourceMode.INLINE.value])
       self._execute_process()

   def _get_initial_dir(self, file_path: str, fallback_dir: Path) -> str:
       if file_path:
           candidate = Path(file_path)
           if candidate.exists():
               return str(candidate.parent if candidate.is_file() else candidate)
       return str(fallback_dir)

   def _build_settings_from_form(self) -> AppSettings:
       overwrite_label = self.overwrite_mode_var.get()
       sql_source_mode = SQL_SOURCE_LABEL_TO_MODE.get(self.sql_source_var.get(), SqlSourceMode.FILE.value)
       sql_text = self._get_text_widget_content(self.raw_sql_text) if sql_source_mode == SqlSourceMode.INLINE
          .value else ""
       return AppSettings(
           oa_no=self.oa_no_var.get().strip(),
           query_template=self.query_template_var.get().strip(),
           output_dir=self.output_dir_var.get().strip(),
           sql_source_mode=sql_source_mode,
           sql_file=self.sql_file_var.get().strip(),
           sql_text=sql_text,
           content=self.content_var.get().strip(),
           author=self.author_var.get().strip(),
           title_file=self.title_file_var.get().strip(),
           template_file=self.template_file_var.get().strip(),
           start_date="",
           end_date="",
           overwrite_mode=OVERWRITE_LABEL_TO_MODE.get(overwrite_label, OverwriteMode.PROMPT.value),
           open_output_dir=self.open_output_dir_var.get(),
       )

   def _execute_process(self) -> None:
       if self.is_running:
           return

       form_settings = self._build_settings_from_form()
       self._clear_log()
       self._prepare_preview_for_execution(form_settings)
       if hasattr(self, "main_notebook"):
           self.main_notebook.select(self.output_tab)

       try:
           config = build_config_from_settings(form_settings)
           resolved_config = self._resolve_overwrite_mode(config)
       except Exception as exc:
           self._append_log(f"?ˇč??ćŞ˘?Ľĺ¤ą?? {exc}")
           messagebox.showerror("?ˇč?ĺ¤ąć?", str(exc))
           return

       if resolved_config is None:
           self._append_log("ĺˇ˛ĺ?ćśĺˇčĄ?)
           return

       self._set_running(True)
       worker = threading.Thread(
           target=self._run_generation,
           args=(resolved_config, form_settings),
           daemon=True,
       )
       worker.start()

   def _prepare_preview_for_execution(self, form_settings: AppSettings) -> None:
       if not all(hasattr(self, name) for name in ("raw_sql_text", "resolved_sql_text", "rendered_sql_text"))
          :
           return

       current_raw_sql = self._get_text_widget_content(self.raw_sql_text)
       if not current_raw_sql.strip() and form_settings.sql_file:
           sql_file = Path(form_settings.sql_file)
           if sql_file.is_file():
               try:
                   current_raw_sql = read_text_preserve_newlines(sql_file)
                   self._set_text_widget_content(self.raw_sql_text, current_raw_sql, editable=True)
               except Exception:
                   pass

       self._set_text_widget_content(self.resolved_sql_text, self.RUNNING_PREVIEW_MESSAGE, editable=False)
       self._set_text_widget_content(self.rendered_sql_text, self.RUNNING_PREVIEW_MESSAGE, editable=False)
       if hasattr(self, "preview_notebook"):
           self.preview_notebook.select(2)

   def _resolve_overwrite_mode(self, config):
       if str(config.overwrite_mode) != OverwriteMode.PROMPT.value:
           return config

       candidate_output = build_output_file_path(replace(config, overwrite_mode=OverwriteMode.ERROR))
       if not candidate_output.exists():
           return replace(config, overwrite_mode=OverwriteMode.ERROR)

       answer = messagebox.askyesnocancel(
           "čź¸ĺşćŞĺˇ˛ĺ­ĺ¨",
           "čź¸ĺşćŞĺˇ˛ĺ­ĺ¨?\n?Żď??´ćĽčŚĺŻŤ\n?Śď??Şĺ??šĺ?\n?ć?ďźĺ?ć­˘ĺˇčĄ?,
       )
       if answer is None:
           return None
       if answer is True:
           return replace(config, overwrite_mode=OverwriteMode.OVERWRITE)
       return replace(config, overwrite_mode=OverwriteMode.RENAME)

   def _run_generation(self, config, successful_settings: AppSettings) -> None:
       result = execute_generation(config)
       self.root.after(0, lambda: self._handle_result(result, successful_settings))

   def _handle_result(
       self,
       result: WorkflowResult,
       successful_settings: AppSettings | None = None,
   ) -> None:
       for message in result.messages:
           self._append_log(message)

       self._set_preview_content(result.preview)

       if result.success and successful_settings is not None:
           self._persist_successful_settings(successful_settings)

       self._set_running(False)
       if hasattr(self, "main_notebook"):
           self.main_notebook.select(self.output_tab)

       if result.success:
           self._open_generated_results(result.output_file, output_dir_opened=result.output_dir_opened)
           messagebox.showinfo("ĺŽć?", f"ĺˇ˛čź¸?şć?ćĄ?\n{result.output_file}")
       else:
           messagebox.showerror("?ˇč?ĺ¤ąć?", result.error_message)

   def _persist_successful_settings(self, settings: AppSettings) -> None:
       try:
           save_settings(settings, self.settings_file)
           self.base_settings = settings
       except Exception as exc:
           self._append_log(f"č¨­ĺ?ćŞĺŻŤ?Ľĺ¤ą?? {exc}")

   def _set_running(self, running: bool) -> None:
       self.is_running = running
       self.execute_button.configure(
           state="disabled" if running else "normal",
           text="?ˇč?ä¸?.." if running else "?ĺ??˘ç? SQL",
       )
       for widget_name in (
           "regenerate_from_editor_button",
           "reload_sql_button",
           "open_current_preview_button",
           "open_rendered_preview_button",
           "theme_combobox",
           "sql_source_combobox",
           "overwrite_mode_combobox",
       ):
           if hasattr(self, widget_name):
               getattr(self, widget_name).configure(state="disabled" if running else "normal")
       self.root.configure(cursor="watch" if running else "")

   def _set_preview_content(
       self,
       preview: PreviewPayload | None,
       *,
       status_message: str | None = None,
   ) -> None:
       if not all(
           hasattr(self, attribute_name)
           for attribute_name in ("raw_sql_text", "resolved_sql_text", "rendered_sql_text")
       ):
           return

       if preview is None:
           message = status_message or self.EMPTY_PREVIEW_MESSAGE
           if not self._get_text_widget_content(self.raw_sql_text).strip():
               self._set_text_widget_content(self.raw_sql_text, "", editable=True)
           self._set_text_widget_content(self.resolved_sql_text, message, editable=False)
           self._set_text_widget_content(self.rendered_sql_text, message, editable=False)
           return

       self._set_text_widget_content(self.raw_sql_text, preview.raw_sql, editable=True)
       self._set_text_widget_content(self.resolved_sql_text, preview.resolved_sql, editable=False)
       self._set_text_widget_content(self.rendered_sql_text, preview.rendered_sql, editable=False)
       if hasattr(self, "preview_notebook"):
           self.preview_notebook.select(2)

   def _set_text_widget_content(self, widget: tk.Text, content: str, *, editable: bool | None = None) -> None
          :
       editable_state = editable if editable is not None else bool(getattr(widget, "_is_editable", False))
       widget.configure(state="normal")
       widget.delete("1.0", "end")
       widget.insert("1.0", content)
       self._refresh_sql_highlighting(widget)
       widget.configure(state="normal" if editable_state else "disabled")
       if editable_state:
           widget.edit_modified(False)

   def _get_text_widget_content(self, widget: tk.Text) -> str:
       current_state = str(widget.cget("state"))
       if current_state == "disabled":
           widget.configure(state="normal")
           content = widget.get("1.0", "end-1c")
           widget.configure(state="disabled")
           return content
       return widget.get("1.0", "end-1c")

   def _on_sql_theme_changed(self, _event=None) -> None:
       self._apply_sql_theme(self.sql_theme_var.get())

   def _apply_sql_theme(self, theme_name: str) -> None:
       theme = SQL_PREVIEW_THEMES.get(theme_name, SQL_PREVIEW_THEMES[DEFAULT_SQL_THEME_NAME])
       for widget_name in ("raw_sql_text", "resolved_sql_text", "rendered_sql_text"):
           if hasattr(self, widget_name):
               self._apply_theme_to_text_widget(getattr(self, widget_name), theme)

       active_windows: list[tuple[tk.Toplevel, tk.Text]] = []
       for window, text_widget in self.preview_windows:
           if not window.winfo_exists():
               continue
           self._apply_theme_to_text_widget(text_widget, theme)
           active_windows.append((window, text_widget))
       self.preview_windows = active_windows

   def _apply_theme_to_text_widget(self, widget: tk.Text, theme: dict[str, str]) -> None:
       widget.configure(
           bg=theme["background"],
           fg=theme["foreground"],
           insertbackground=theme["caret"],
           selectbackground=theme["selection_background"],
           selectforeground=theme["selection_foreground"],
       )
       self._refresh_sql_highlighting(widget, theme)

   def _refresh_sql_highlighting(self, widget: tk.Text, theme: dict[str, str] | None = None) -> None:
       if not bool(getattr(widget, "_is_sql_widget", False)):
           return

       active_theme = theme or SQL_PREVIEW_THEMES.get(
           self.sql_theme_var.get(),
           SQL_PREVIEW_THEMES[DEFAULT_SQL_THEME_NAME],
       )
       current_state = str(widget.cget("state"))
       if current_state == "disabled":
           widget.configure(state="normal")
       apply_sql_syntax_highlighting(widget, active_theme)
       if current_state == "disabled":
           widget.configure(state="disabled")

   def _on_sql_text_modified(self, event) -> None:
       widget = event.widget
       if not isinstance(widget, tk.Text):
           return
       if not widget.edit_modified():
           return
       self._refresh_sql_highlighting(widget)
       widget.edit_modified(False)

   def _open_generated_results(self, output_file: Path | None, *, output_dir_opened: bool) -> None:
       if output_file is None or not output_file.exists():
           return

       if not hasattr(os, "startfile"):
           self._append_log("?Žĺ?çłťçľąä¸ćŻ?´čŞ?é??čź¸?şć?ćĄ?)
           return

       try:
           os.startfile(str(output_file))
           self._append_log(f"ĺˇ˛é??čź¸?şć?ćĄ? {output_file}")
       except Exception as exc:
           self._append_log(f"?Ąć??Şĺ??ĺ?čź¸ĺşćŞć?: {exc}")

       output_dir = output_file.parent
       if output_dir_opened or not output_dir.exists():
           return

       try:
           os.startfile(str(output_dir))
           self._append_log(f"ĺˇ˛é??čź¸?şč??ĺ¤ž: {output_dir}")
       except Exception as exc:
           self._append_log(f"?Ąć??Şĺ??ĺ?čź¸ĺşčłć?ĺ¤? {exc}")

   def _append_log(self, message: str) -> None:
       tag = self._resolve_log_tag(message)
       self.log_text.configure(state="normal")

   def _clear_log(self) -> None:
       self.log_text.configure(state="normal")
       self.log_text.configure(state="disabled")

   def _resolve_log_tag(self, message: str) -> str:
       if any(keyword in message for keyword in ("ĺ¤ąć?", "?ŻčŞ¤", "ä¸ĺ???, "FAILED")):
           return "error"
       if any(keyword in message for keyword in ("ĺŽć?", "?ĺ?", "SUCCESS", "ĺˇ˛čź¸??)):
           return "warning"
       return "info"


def main() -> None:
   root = tk.Tk()
   SqlToolApp(root)
   root.mainloop()
