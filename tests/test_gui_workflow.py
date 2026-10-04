from __future__ import annotations

import queue
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from ld_query_sql_tool.gui import SqlToolApp
from ld_query_sql_tool.models import AppSettings, SqlSourceMode, WorkflowResult


class TestGuiWorkflow(unittest.TestCase):
    def make_app(self):
        app = object.__new__(SqlToolApp)
        app.settings_file = Path("custom-settings.json")
        app.base_settings = AppSettings(oa_no="OLD")
        app.is_running = False
        app.result_queue = queue.SimpleQueue()
        app.root = Mock()
        app._append_log = Mock()
        app._set_running = Mock()
        app._set_text_content = Mock()
        app.preview_notebook = Mock()
        app.main_notebook = Mock()
        return app

    def test_invalid_config_does_not_save_or_start_worker(self):
        app = self.make_app()
        app._build_settings_from_ui = Mock(return_value=AppSettings())
        app._validate_required_fields = Mock(return_value=[])
        with (
            patch("ld_query_sql_tool.gui.build_config_from_settings", side_effect=ValueError("bad input")),
            patch("ld_query_sql_tool.gui.save_settings") as save,
            patch("ld_query_sql_tool.gui.threading.Thread") as thread,
            patch("ld_query_sql_tool.gui.messagebox.showerror") as error,
        ):
            app._execute_process()
        save.assert_not_called()
        thread.assert_not_called()
        self.assertIn("bad input", error.call_args.args[1])
        app._set_running.assert_called_once_with(False)

    def test_worker_start_failure_restores_controls(self):
        app = self.make_app()
        app._build_settings_from_ui = Mock(return_value=AppSettings())
        app._validate_required_fields = Mock(return_value=[])
        app._resolve_overwrite = Mock(return_value=object())
        app._clear_log = Mock()
        with (
            patch("ld_query_sql_tool.gui.threading.Thread") as thread,
            patch("ld_query_sql_tool.gui.messagebox.showerror"),
        ):
            thread.return_value.start.side_effect = RuntimeError("thread unavailable")
            app._execute_process()
        self.assertEqual([c.args[0] for c in app._set_running.call_args_list], [True, False])

    def test_worker_queues_result_without_calling_tk(self):
        app = self.make_app()
        settings = AppSettings()
        result = WorkflowResult(success=True, messages=[], log_file=None)
        with patch("ld_query_sql_tool.gui.execute_generation", return_value=result):
            app._run_bg(object(), settings)
        app.root.after.assert_not_called()
        self.assertEqual(app.result_queue.get_nowait(), (result, settings))

    def test_unexpected_worker_error_is_delivered_to_main_thread(self):
        app = self.make_app()
        settings = AppSettings()
        with patch("ld_query_sql_tool.gui.execute_generation", side_effect=OSError("unreadable")):
            app._run_bg(object(), settings)
        app._on_result = Mock()
        app._poll_result()
        result, delivered_settings = app._on_result.call_args.args
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "unreadable")
        self.assertIs(delivered_settings, settings)

    def test_success_saves_selected_profile_and_updates_base_settings(self):
        app = self.make_app()
        settings = AppSettings(oa_no="NEW")
        result = WorkflowResult(success=True, messages=["成功"], log_file=None, output_file=Path("out.sql"))
        with (
            patch("ld_query_sql_tool.gui.save_settings") as save,
            patch("ld_query_sql_tool.gui.messagebox.showinfo") as info,
        ):
            app._on_result(result, settings)
        save.assert_called_once_with(settings, app.settings_file)
        self.assertIs(app.base_settings, settings)
        app._set_running.assert_called_once_with(False)
        self.assertIn("out.sql", info.call_args.args[1])

    def test_settings_save_failure_still_reports_successful_sql(self):
        app = self.make_app()
        result = WorkflowResult(success=True, messages=[], log_file=None, output_file=Path("out.sql"))
        with (
            patch("ld_query_sql_tool.gui.save_settings", side_effect=OSError("locked")),
            patch("ld_query_sql_tool.gui.messagebox.showinfo") as info,
            patch("ld_query_sql_tool.gui.messagebox.showerror") as error,
        ):
            app._on_result(result, AppSettings())
        info.assert_called_once()
        error.assert_not_called()
        self.assertIn("設定儲存失敗", app._append_log.call_args.args[0])
        self.assertEqual(app.base_settings.oa_no, "OLD")

    def test_failed_generation_does_not_save_settings(self):
        app = self.make_app()
        result = WorkflowResult(success=False, messages=[], log_file=None, error_message="boom")
        with (
            patch("ld_query_sql_tool.gui.save_settings") as save,
            patch("ld_query_sql_tool.gui.messagebox.showerror") as error,
        ):
            app._on_result(result, AppSettings())
        save.assert_not_called()
        error.assert_called_once_with("驗證失敗", "boom")
        self.assertEqual(app.base_settings.oa_no, "OLD")

    def test_manual_settings_save_only_writes_selected_profile(self):
        app = self.make_app()
        settings = AppSettings()
        app._apply_ui_font_size = Mock()
        app._build_settings_from_ui = Mock(return_value=settings)
        with patch("ld_query_sql_tool.gui.save_settings") as save, patch("ld_query_sql_tool.gui.messagebox.showinfo"):
            app._save_system_settings()
        save.assert_called_once_with(settings, app.settings_file)

    def test_initial_editor_resolves_source_under_root_dir(self):
        app = self.make_app()
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.sql"
            source.write_text("select 1;", encoding="utf-8")
            app._load_sql_file_into_editor = Mock()
            app._initialize_sql_editor(AppSettings(root_dir=directory, sql_file="source.sql"))
            app._load_sql_file_into_editor.assert_called_once_with(source, switch_mode=False)

    def test_inline_form_uses_current_editor_text(self):
        app = self.make_app()
        values = {
            "oa_no": "OA", "query_template": "query", "output_dir": "out",
            "sql_file": "unused.sql", "content": "內容", "author": "作者",
            "title_file": "title.txt", "template_file": "template.sql",
            "start_date": "", "end_date": "", "root_dir": ".", "python_exe": "",
            "ui_font_size": "11", "sql_source": "畫面直接輸入",
            "overwrite_mode": "自動更名", "open_output_dir": False,
        }
        for name, value in values.items():
            setattr(app, f"{name}_var", Mock(get=Mock(return_value=value)))
        app.raw_sql_text = object()
        app._get_text_content = Mock(return_value="select 'edited' from dual;")
        settings = app._build_settings_from_ui()
        self.assertEqual(settings.sql_source_mode, SqlSourceMode.INLINE)
        self.assertEqual(settings.sql_text, "select 'edited' from dual;")

    def test_invalid_date_range_does_not_replace_preview(self):
        app = self.make_app()
        app.start_date_var = Mock(get=Mock(return_value="2026-10-05"))
        app.end_date_var = Mock(get=Mock(return_value="2026-10-04"))
        with patch("ld_query_sql_tool.gui.messagebox.showwarning") as warning:
            app._apply_date_replacement()
        warning.assert_called_once()
        app._set_text_content.assert_not_called()


if __name__ == "__main__":
    unittest.main()
