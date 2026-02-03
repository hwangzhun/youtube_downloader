"""
打包脚本，用于生成可执行文件
"""
import os
import sys
import shutil
import subprocess
import platform

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
    
    # 根据操作系统选择路径分隔符
    if platform.system() == "Windows":
        sep = ";"
    else:
        sep = ":"
    
    # 构建命令
    cmd = [
        "pyinstaller",
        "--name=YouTube_Downloader",
        "--windowed",  # 不显示控制台窗口
        "--icon=resources/icons/app_icon.ico",
        f"--add-data=resources{sep}resources",  # 添加资源文件
        f"--add-data=src/config{sep}src/config",  # 添加配置文件
        # PyQt5 核心模块
        "--hidden-import=PyQt5",
        "--hidden-import=PyQt5.QtCore",
        "--hidden-import=PyQt5.QtGui",
        "--hidden-import=PyQt5.QtWidgets",
        "--hidden-import=PyQt5.QtWebEngineWidgets",
        "--hidden-import=PyQt5.QtWebEngineCore",
        "--hidden-import=PyQt5.sip",
        # yt-dlp 相关
        "--hidden-import=yt_dlp",
        "--hidden-import=yt_dlp.extractor",
        "--hidden-import=yt_dlp.downloader",
        "--hidden-import=yt_dlp.postprocessor",
        # 其他可能需要的模块
        "--hidden-import=json",
        "--hidden-import=urllib3",
        "--hidden-import=requests",
        "--hidden-import=certifi",
        "--hidden-import=charset_normalizer",
        "--hidden-import=idna",
        "--hidden-import=pycryptodome",
        "--hidden-import=websockets",
        "--hidden-import=websocket",
        "--hidden-import=selenium",
        "--hidden-import=undetected_chromedriver",
        # 收集所有子模块（避免遗漏）
        "--collect-all=yt_dlp",
        "--collect-all=PyQt5",
        "--noconfirm",  # 不询问确认
        "--clean",  # 清理临时文件
        "--paths=.",  # 添加当前目录到 Python 路径
        "src/main.py"
    ]
    
    # 执行构建
    try:
        subprocess.run(cmd, check=True)
        print("可执行文件构建完成！")
        print(f"输出目录: {os.path.join(current_dir, 'dist', 'YouTube_Downloader')}")
    except subprocess.CalledProcessError as e:
        print(f"构建失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build_exe() 