"""
YouTube 視頻下載工具的安裝腳本
用於創建 Windows 安裝程序
"""
import os
import sys
import shutil
import subprocess
from cx_Freeze import setup, Executable

# 獲取當前目錄
base_dir = os.path.abspath(os.path.dirname(__file__))

# 應用程序信息
APP_NAME = "YouTube 視頻下載工具"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "一個簡單易用的 YouTube 視頻下載工具"
APP_AUTHOR = "開發者"
APP_ICON = os.path.join(base_dir, "resources", "icons", "app_icon.ico")

# 構建選項
build_options = {
    "packages": [
        "os", "sys", "re", "json", "time", "threading", "subprocess",
        "tempfile", "shutil", "zipfile", "requests", "logging"
    ],
    "excludes": [],
    "include_files": [
        ("resources", "resources"),
        ("README.md", "README.md"),
    ],
    "include_msvcr": True,
    "optimize": 2,
}

# 創建可執行文件
executables = [
    Executable(
        script="main.py",
        base="Win32GUI",
        target_name="YouTubeDownloader.exe",
        icon=APP_ICON,
        shortcut_name=APP_NAME,
        shortcut_dir="DesktopFolder",
    )
]

# 設置安裝程序
setup(
    name=APP_NAME,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    author=APP_AUTHOR,
    options={"build_exe": build_options},
    executables=executables
)

# 安裝後的操作
print("構建完成！")
print("安裝程序位於 build 目錄中")
