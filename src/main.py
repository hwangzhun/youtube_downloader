"""
YouTube Downloader 的主入口模块
"""
import os
import sys

# 添加项目根目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

# 添加src目录到Python路径
sys.path.insert(0, current_dir)

from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap

# 导入自定义模块
from src.ui.main_window import MainWindow
from src.utils.logger import LoggerManager

def check_binary_files():
    """检查必要的二进制文件是否存在"""
    required_files = {
        'yt-dlp': 'yt-dlp.exe',  # Windows下的yt-dlp可执行文件
        'ffmpeg': 'ffmpeg.exe',  # Windows下的ffmpeg可执行文件
        'ffprobe': 'ffprobe.exe'  # Windows下的ffprobe可执行文件
    }
    
    # 获取二进制文件目录
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 检查所有必需文件
    for dir_name, file_name in required_files.items():
        file_path = os.path.join(base_dir, 'resources', 'binaries', dir_name, file_name)
        if not os.path.exists(file_path):
            return False
    return True

def main():
    """主函数"""
    # 初始化日志
    logger = LoggerManager().get_logger()
    logger.info("应用程序启动")
    
    # 创建应用程序实例
    app = QApplication(sys.argv)
    
    # 获取当前脚本所在目录
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    splash_path = os.path.join(base_dir, 'resources', 'icons', 'splash.png')
    
    # 创建启动画面
    splash = None
    if os.path.exists(splash_path):
        splash_pixmap = QPixmap(splash_path)
        if not splash_pixmap.isNull():
            splash = QSplashScreen(splash_pixmap)
            splash.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.SplashScreen)
            splash.show()
            app.processEvents()
    
    # 检查二进制文件
    has_binaries = check_binary_files()
    logger.info(f"二进制文件检查结果: {'已存在' if has_binaries else '需要更新'}")
    
    # 创建主窗口，传入二进制文件检查结果
    window = MainWindow(splash, skip_update_check=has_binaries)
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 