"""根目錄 GUI 啟動入口，避免直接打開套件內模組造成相對匯入失敗。"""

from ld_query_sql_tool.gui import SqlToolApp, main

__all__ = ["SqlToolApp", "main"]


if __name__ == "__main__":
    main()
