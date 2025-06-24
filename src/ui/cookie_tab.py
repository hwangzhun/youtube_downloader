"""
YouTube Downloader Cookie标签页模块
负责创建和管理Cookie标签页界面
"""
import os
import sys
from typing import Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QTextEdit, QMessageBox, QGroupBox, QStatusBar,
    QFileDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon

# 使用绝对导入
from src.core.cookie_manager import CookieManager
from src.utils.logger import LoggerManager


# 添加一个工作线程类
class ChromeCookieWorker(QThread):
    """Chrome Cookie获取工作线程"""
    finished = pyqtSignal(bool, str)  # 完成信号，参数：是否成功，消息
    
    def __init__(self):
        super().__init__()
        self.logger = LoggerManager().get_logger()
    
    def run(self):
        try:
            from src.core.cookie.get_chrome_cookie import get_youtube_cookies
            success = get_youtube_cookies()
            
            if success:
                cookie_file = 'youtube_cookies.txt'
                if os.path.exists(cookie_file):
                    self.finished.emit(True, "Chrome Cookie获取成功")
                else:
                    self.finished.emit(False, "Chrome Cookie获取失败：文件未生成")
            else:
                self.finished.emit(False, "Chrome Cookie获取失败")
                
        except Exception as e:
            self.logger.error(f"获取Chrome Cookie失败: {str(e)}")
            self.finished.emit(False, f"获取Chrome Cookie失败: {str(e)}")

class CookieTab(QWidget):
    """Cookie标签页类"""
    
    def __init__(self, status_bar: QStatusBar = None):
        """
        初始化Cookie标签页
        
        Args:
            status_bar: 状态栏
        """
        super().__init__()
        
        # 初始化日志
        self.logger = LoggerManager().get_logger()
        self.status_bar = status_bar
        
        # 初始化Cookie管理器
        self.cookie_manager = CookieManager()
        
        # 添加Cookie状态显示
        self.cookie_status = "未使用"  # 添加状态属性
        
        # 添加工作线程属性
        self.cookie_worker = None
        
        # 初始化UI
        self.init_ui()
        
        # 记录日志
        self.logger.info("Cookie标签页初始化完成")
    
    def init_ui(self):
        """初始化UI"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 创建Cookie状态区域
        status_group = QGroupBox("Cookie状态")
        status_layout = QVBoxLayout(status_group)
        
        # 状态显示
        self.status_label = QLabel("当前状态：未使用")
        self.status_label.setWordWrap(True)  # 允许文本换行
        self.status_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)  # 文本左对齐
        self.status_label.setTextFormat(Qt.RichText)  # 启用富文本格式
        status_layout.addWidget(self.status_label)
        
        # 按钮水平布局
        status_button_layout = QHBoxLayout()

        # 验证按钮
        self.verify_button = QPushButton("验证Cookie")
        self.verify_button.clicked.connect(self.verify_cookies)
        status_button_layout.addWidget(self.verify_button)

        # 清除按钮
        self.clear_button = QPushButton("清除Cookie")
        self.clear_button.clicked.connect(self.clear_loaded_cookie)
        status_button_layout.addWidget(self.clear_button)

        status_layout.addLayout(status_button_layout)
        
        # 添加状态区域到主布局
        main_layout.addWidget(status_group)
        
        # 创建Cookie文件区域
        cookie_file_group = QGroupBox("Cookie文件")
        cookie_file_layout = QVBoxLayout(cookie_file_group)
        
        # Cookie文件路径输入框
        file_path_layout = QHBoxLayout()
        self.cookie_file_input = QLineEdit()
        self.cookie_file_input.setPlaceholderText("")  # 清空占位符
        file_path_layout.addWidget(self.cookie_file_input)
        
        # 浏览按钮
        self.browse_button = QPushButton("浏览...")
        self.browse_button.clicked.connect(self.browse_cookie_file)
        file_path_layout.addWidget(self.browse_button)
        
        cookie_file_layout.addLayout(file_path_layout)
        
        # 创建按钮布局
        button_layout = QHBoxLayout()
        
        # Chromium浏览器获取按钮
        self.chrome_button = QPushButton("获取浏览器的 Cookie")
        self.chrome_button.clicked.connect(self.get_youtube_cookies)
        button_layout.addWidget(self.chrome_button)
        
        # 添加说明文字
        note_label = QLabel("此功能仅支持 Chrome、Firefox、Edge浏览器，其他浏览器的请自行获取cookie")
        note_label.setStyleSheet("color: #666; font-size: 10px;")
        note_label.setWordWrap(True)
        cookie_file_layout.addWidget(note_label)
        
        # 自动提取按钮
        self.auto_extract_button = QPushButton("自动提取Cookie")
        self.auto_extract_button.setEnabled(False)
        self.auto_extract_button.clicked.connect(self.auto_extract_cookies)
        button_layout.addWidget(self.auto_extract_button)
        
        cookie_file_layout.addLayout(button_layout)
        
        # 添加Cookie文件区域到主布局
        main_layout.addWidget(cookie_file_group)
        
        # 添加Cookie说明文字
        note_label = QLabel("⚠️ Cookie 使用说明：")
        note_label.setStyleSheet("color: #e67e22; font-size: 12px; font-weight: bold; margin: 10px 0;")
        main_layout.addWidget(note_label)
        
        note_content = QLabel("Cookie 不是必需的，仅在以下情况需要：\n1. 下载会员专属视频\n2. 下载年龄限制视频\n3. 下载私人视频")
        note_content.setStyleSheet("color: #e67e22; font-size: 11px; margin: 5px 0 15px 0;")
        note_content.setWordWrap(True)
        main_layout.addWidget(note_content)
        
        # 创建Cookie内容区域
        cookie_content_group = QGroupBox("Cookie内容")
        cookie_content_layout = QVBoxLayout(cookie_content_group)
        
        # Cookie内容显示
        self.cookie_content = QTextEdit()
        self.cookie_content.setReadOnly(True)
        self.cookie_content.setPlaceholderText("Cookie内容将显示在这里")
        cookie_content_layout.addWidget(self.cookie_content)
        
        # 添加Cookie内容区域到主布局
        main_layout.addWidget(cookie_content_group)
        
        # 添加弹性空间
        main_layout.addStretch()
    
    def clear_loaded_cookie(self):
        """清除已加载的Cookie信息，但不删除文件。"""
        # 1. 清空UI组件
        self.cookie_file_input.clear()
        self.cookie_content.clear()
        
        # 2. 重置状态标签
        self.status_label.setText("当前状态：未使用")
        
        # 3. 更新内部和外部状态
        self.update_cookie_status(False)
        self.update_status_message("已清除加载的 Cookie")
        
        # 4. 通知用户
        QMessageBox.information(self, "操作成功", "已清除加载的 Cookie 信息。")
        self.logger.info("用户清除了已加载的 Cookie 信息。")

    def verify_cookies(self):
        """验证Cookie"""
        cookie_file = self.cookie_file_input.text()
        
        if not cookie_file:
            QMessageBox.warning(self, "警告", "请先选择或获取Cookie文件")
            return
        
        if not os.path.exists(cookie_file):
            QMessageBox.warning(self, "警告", "Cookie文件不存在")
            return
        
        try:
            # 导入验证函数
            from src.core.cookie.check_cookies import verify_cookie
            is_valid, message, user_id, username = verify_cookie(cookie_file)
            
            if is_valid:
                self.update_cookie_status(True)
                # 使用HTML格式化状态文本
                status_text = f"""
                <div style='margin: 10px 0;'>
                    <p style='color: #2ecc71; font-weight: bold; margin-bottom: 10px;'>Cookie验证成功</p>
                    <p style='margin: 5px 0;'><b>用户ID:</b> <span style='color: #3498db;'>{user_id}</span></p>
                    <p style='margin: 5px 0;'><b>用户名:</b> <span style='color: #3498db;'>@{username}</span></p>
                </div>
                """
                self.status_label.setText(status_text)
                self.update_status_message("Cookie验证成功")
                QMessageBox.information(self, "成功", f"Cookie验证成功！\n\n用户ID: {user_id}\n用户名: @{username}")
            else:
                self.update_cookie_status(False)
                self.update_status_message(f"Cookie验证失败: {message}")
                QMessageBox.warning(self, "警告", f"Cookie验证失败:\n{message}")
        except Exception as e:
            self.logger.error(f"验证Cookie失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"验证Cookie失败:\n{str(e)}")
            self.update_status_message("Cookie验证失败")
    
    def get_youtube_cookies(self):
        """获取Chrome浏览器的Cookie"""
        try:
            self.logger.info("开始获取Chrome Cookie...")
            # 禁用按钮，防止重复点击
            self.chrome_button.setEnabled(False)
            self.update_status_message("正在获取Chrome Cookie...")
            
            # 创建并启动工作线程
            self.logger.debug("创建ChromeCookieWorker线程")
            self.cookie_worker = ChromeCookieWorker()
            self.cookie_worker.finished.connect(self.handle_cookie_result)
            self.logger.debug("启动ChromeCookieWorker线程")
            self.cookie_worker.start()
            
        except Exception as e:
            self.logger.error(f"启动Chrome Cookie获取失败: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "错误", f"启动Chrome Cookie获取失败:\n{str(e)}")
            self.update_status_message("Chrome Cookie获取失败")
            self.chrome_button.setEnabled(True)
    
    def handle_cookie_result(self, success: bool, message: str):
        """处理Cookie获取结果"""
        try:
            self.logger.info(f"收到Cookie获取结果: success={success}, message={message}")
            if success:
                # 加载生成的cookie文件
                cookie_file = 'youtube_cookies.txt'
                self.logger.debug(f"设置Cookie文件路径: {cookie_file}")
                self.cookie_file_input.setText(cookie_file)
                self.load_cookie_content(cookie_file)
                self.update_status_message(message)
                self.logger.info("Cookie获取成功并已加载")
            else:
                self.logger.warning(f"Cookie获取失败: {message}")
                QMessageBox.warning(self, "警告", message)
                self.update_status_message(message)
        except Exception as e:
            self.logger.error(f"处理Cookie结果失败: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "错误", f"处理Cookie结果失败:\n{str(e)}")
            self.update_status_message("处理Cookie结果失败")
        finally:
            # 重新启用按钮
            self.logger.debug("重新启用Chrome Cookie获取按钮")
            self.chrome_button.setEnabled(True)
    
    def browse_cookie_file(self):
        """浏览Cookie文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择Cookie文件",
            "",
            "Netscape Cookie文件 (*.txt);;所有文件 (*.*)"
        )
        
        if file_path:
            self.cookie_file_input.setText(file_path)
            self.load_cookie_content(file_path)
    
    def load_cookie_content(self, file_path: str):
        """加载Cookie内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.cookie_content.setText(content)
                self.update_status_message("Cookie文件加载成功")
        except Exception as e:
            self.logger.error(f"加载Cookie文件失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"加载Cookie文件失败:\n{str(e)}")
            self.update_status_message("Cookie文件加载失败")
    
    def auto_extract_cookies(self):
        """自动提取Cookie"""
        try:
            success, temp_cookie_file, error_message = self.cookie_manager.auto_extract_cookies()
            
            if success:
                self.cookie_file_input.setText(temp_cookie_file)
                self.load_cookie_content(temp_cookie_file)
                self.update_status_message("Cookie自动提取成功")
            else:
                QMessageBox.warning(self, "警告", f"Cookie自动提取失败:\n{error_message}")
                self.update_status_message("Cookie自动提取失败")
        except Exception as e:
            self.logger.error(f"自动提取Cookie失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"自动提取Cookie失败:\n{str(e)}")
            self.update_status_message("Cookie自动提取失败")
    
    def update_status_message(self, message: str):
        """更新状态栏消息"""
        if self.status_bar:
            self.status_bar.showMessage(message)
    
    def update_cookie_status(self, is_using: bool):
        """更新Cookie使用状态"""
        self.cookie_status = "使用中" if is_using else "未使用"
        
        # 设置状态文本样式
        if is_using:
            status_style = "color: #2ecc71; font-weight: bold;"  # 绿色
        else:
            status_style = "color: #e74c3c; font-weight: bold;"  # 红色
        
        self.status_label.setText(f'<span style="{status_style}">当前状态：{self.cookie_status}</span>')
        
        # 更新状态栏
        self.update_status_message(f"Cookie状态已更新：{self.cookie_status}")
    
    def get_cookie_file(self) -> str:
        """获取当前Cookie文件路径"""
        return self.cookie_file_input.text()
    
    def is_cookie_available(self) -> bool:
        """检查Cookie是否可用"""
        return bool(self.cookie_file_input.text() and os.path.exists(self.cookie_file_input.text())) 