"""
打包脚本，用于生成可执行文件
"""
import os
import sys
import shutil
import subprocess

def build_exe():
    """构建可执行文件"""
    print("开始构建可执行文件...")
    
    # 清理旧的构建文件
    if os.path.exists("build"):
        shutil.rmtree("build")
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    
    # 添加项目根目录到 Python 路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)
    
    # 构建命令
    cmd = [
        "pyinstaller",
        "--name=YouTube_Downloader",
        "--windowed",  # 不显示控制台窗口
        "--icon=resources/icons/app_icon.ico",
        "--add-data=resources;resources",  # 添加资源文件
        "--hidden-import=PyQt5",
        "--hidden-import=PyQt5.QtCore",
        "--hidden-import=PyQt5.QtGui",
        "--hidden-import=PyQt5.QtWidgets",
        "--hidden-import=yt_dlp",
        "--hidden-import=ffmpeg",
        "--noconfirm",  # 不询问确认
        "--clean",  # 清理临时文件
        "--paths=.",  # 添加当前目录到 Python 路径
        "src/main.py"
    ]
    
    # 执行构建
    subprocess.run(cmd, check=True)
    
    print("可执行文件构建完成！")

if __name__ == "__main__":
    build_exe() 