"""
YouTube Downloader 代理设置标签页模块
负责创建和管理代理设置界面
"""
import os
import threading
from typing import Optional, Tuple

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QMessageBox, QGroupBox, QStatusBar, QCheckBox,
    QRadioButton, QButtonGroup, QSpinBox, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QIntValidator

from src.utils.logger import LoggerManager
from src.utils.config import ConfigManager


class ProxyTestThread(QThread):
    """代理测试线程"""
    
    # 测试完成信号: (成功, 消息)
    test_finished = pyqtSignal(bool, str)
    
    def __init__(self, proxy_url: str):
        super().__init__()
        self.proxy_url = proxy_url
    
    def run(self):
        """执行代理测试"""
        try:
            import requests
            
            proxies = {
                'http': self.proxy_url,
                'https': self.proxy_url
            }
            
            # 测试访问 YouTube
            response = requests.get(
                'https://www.youtube.com',
                proxies=proxies,
                timeout=10,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
            
            if response.status_code == 200:
                self.test_finished.emit(True, "代理连接成功！可以正常访问 YouTube")
            else:
                self.test_finished.emit(False, f"代理连接失败，状态码: {response.status_code}")
                
        except requests.exceptions.ProxyError as e:
            self.test_finished.emit(False, f"代理服务器错误: 无法连接到代理服务器")
        except requests.exceptions.ConnectTimeout:
            self.test_finished.emit(False, "连接超时: 代理服务器响应超时")
        except requests.exceptions.ConnectionError:
            self.test_finished.emit(False, "连接错误: 无法建立连接，请检查代理地址和端口")
        except Exception as e:
            self.test_finished.emit(False, f"测试失败: {str(e)}")


class ProxyTab(QWidget):
    """代理设置标签页类"""
    
    # 代理设置变更信号
    proxy_changed = pyqtSignal(bool, str)  # (启用状态, 代理URL)
    
    def __init__(self, config_manager: ConfigManager, status_bar: QStatusBar = None):
        """
        初始化代理设置标签页
        
        Args:
            config_manager: 配置管理器
            status_bar: 状态栏
        """
        super().__init__()
        
        # 初始化日志
        self.logger = LoggerManager().get_logger()
        self.config_manager = config_manager
        self.status_bar = status_bar
        
        # 测试线程
        self.test_thread: Optional[ProxyTestThread] = None
        
        # 初始化UI
        self.init_ui()
        
        # 加载配置
        self.load_config()
        
        # 记录日志
        self.logger.info("代理设置标签页初始化完成")
    
    def init_ui(self):
        """初始化UI"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # ========== 启用代理复选框 ==========
        self.enable_proxy_checkbox = QCheckBox("启用代理")
        self.enable_proxy_checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 14px;
                font-weight: bold;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        self.enable_proxy_checkbox.stateChanged.connect(self.on_proxy_enabled_changed)
        main_layout.addWidget(self.enable_proxy_checkbox)
        
        # ========== 代理设置区域 ==========
        self.proxy_settings_group = QGroupBox("代理设置")
        proxy_settings_layout = QVBoxLayout(self.proxy_settings_group)
        proxy_settings_layout.setSpacing(12)
        
        # 代理类型选择
        type_layout = QHBoxLayout()
        type_label = QLabel("代理类型:")
        type_label.setFixedWidth(80)
        type_layout.addWidget(type_label)
        
        self.proxy_type_group = QButtonGroup(self)
        self.http_radio = QRadioButton("HTTP")
        self.https_radio = QRadioButton("HTTPS")
        self.socks5_radio = QRadioButton("SOCKS5")
        
        self.proxy_type_group.addButton(self.http_radio, 1)
        self.proxy_type_group.addButton(self.https_radio, 2)
        self.proxy_type_group.addButton(self.socks5_radio, 3)
        
        self.http_radio.setChecked(True)
        
        type_layout.addWidget(self.http_radio)
        type_layout.addWidget(self.https_radio)
        type_layout.addWidget(self.socks5_radio)
        type_layout.addStretch()
        
        proxy_settings_layout.addLayout(type_layout)
        
        # 代理地址
        host_layout = QHBoxLayout()
        host_label = QLabel("代理地址:")
        host_label.setFixedWidth(80)
        host_layout.addWidget(host_label)
        
        self.proxy_host_input = QLineEdit()
        self.proxy_host_input.setPlaceholderText("例如: 127.0.0.1")
        self.proxy_host_input.setText("127.0.0.1")
        host_layout.addWidget(self.proxy_host_input)
        
        proxy_settings_layout.addLayout(host_layout)
        
        # 代理端口
        port_layout = QHBoxLayout()
        port_label = QLabel("代理端口:")
        port_label.setFixedWidth(80)
        port_layout.addWidget(port_label)
        
        self.proxy_port_input = QSpinBox()
        self.proxy_port_input.setRange(1, 65535)
        self.proxy_port_input.setValue(7890)
        self.proxy_port_input.setFixedWidth(100)
        port_layout.addWidget(self.proxy_port_input)
        port_layout.addStretch()
        
        proxy_settings_layout.addLayout(port_layout)
        
        main_layout.addWidget(self.proxy_settings_group)
        
        # ========== 代理认证区域（可选） ==========
        self.auth_group = QGroupBox("代理认证（可选）")
        auth_layout = QVBoxLayout(self.auth_group)
        auth_layout.setSpacing(12)
        
        # 用户名
        username_layout = QHBoxLayout()
        username_label = QLabel("用户名:")
        username_label.setFixedWidth(80)
        username_layout.addWidget(username_label)
        
        self.proxy_username_input = QLineEdit()
        self.proxy_username_input.setPlaceholderText("留空表示不需要认证")
        username_layout.addWidget(self.proxy_username_input)
        
        auth_layout.addLayout(username_layout)
        
        # 密码
        password_layout = QHBoxLayout()
        password_label = QLabel("密码:")
        password_label.setFixedWidth(80)
        password_layout.addWidget(password_label)
        
        self.proxy_password_input = QLineEdit()
        self.proxy_password_input.setPlaceholderText("留空表示不需要认证")
        self.proxy_password_input.setEchoMode(QLineEdit.Password)
        password_layout.addWidget(self.proxy_password_input)
        
        # 显示/隐藏密码按钮
        self.show_password_btn = QPushButton("显示")
        self.show_password_btn.setFixedWidth(50)
        self.show_password_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        self.show_password_btn.clicked.connect(self.toggle_password_visibility)
        password_layout.addWidget(self.show_password_btn)
        
        auth_layout.addLayout(password_layout)
        
        main_layout.addWidget(self.auth_group)
        
        # ========== 状态和操作区域 ==========
        status_group = QGroupBox("状态")
        status_layout = QVBoxLayout(status_group)
        
        # 状态显示
        self.status_label = QLabel("当前状态: 代理未启用")
        self.status_label.setStyleSheet("font-size: 13px; padding: 5px;")
        status_layout.addWidget(self.status_label)
        
        # 代理预览
        self.proxy_preview_label = QLabel("代理地址预览: -")
        self.proxy_preview_label.setStyleSheet("color: #666; font-size: 12px; padding: 5px;")
        self.proxy_preview_label.setWordWrap(True)
        status_layout.addWidget(self.proxy_preview_label)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        # 测试代理按钮
        self.test_button = QPushButton("测试代理")
        self.test_button.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                padding: 10px 25px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.test_button.clicked.connect(self.test_proxy)
        button_layout.addWidget(self.test_button)
        
        # 保存设置按钮
        self.save_button = QPushButton("保存设置")
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                padding: 10px 25px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.save_button.clicked.connect(self.save_config)
        button_layout.addWidget(self.save_button)
        
        button_layout.addStretch()
        
        status_layout.addLayout(button_layout)
        
        main_layout.addWidget(status_group)
        
        # ========== 说明文字 ==========
        note_label = QLabel("💡 提示：代理设置将应用于视频信息获取和下载过程。常见代理端口：Clash(7890)、V2Ray(10808)、SSR(1080)")
        note_label.setStyleSheet("color: #666; font-size: 11px; padding: 10px 0;")
        note_label.setWordWrap(True)
        main_layout.addWidget(note_label)
        
        # 添加弹性空间
        main_layout.addStretch()
        
        # 连接信号以更新预览
        self.proxy_host_input.textChanged.connect(self.update_proxy_preview)
        self.proxy_port_input.valueChanged.connect(self.update_proxy_preview)
        self.proxy_username_input.textChanged.connect(self.update_proxy_preview)
        self.proxy_password_input.textChanged.connect(self.update_proxy_preview)
        self.proxy_type_group.buttonClicked.connect(self.update_proxy_preview)
        
        # 初始状态
        self.update_ui_state()
    
    def on_proxy_enabled_changed(self, state: int):
        """代理启用状态变更"""
        self.update_ui_state()
        self.update_proxy_preview()
    
    def update_ui_state(self):
        """更新UI状态"""
        enabled = self.enable_proxy_checkbox.isChecked()
        
        # 启用/禁用设置区域
        self.proxy_settings_group.setEnabled(enabled)
        self.auth_group.setEnabled(enabled)
        self.test_button.setEnabled(enabled)
        
        # 更新状态标签
        if enabled:
            self.status_label.setText("当前状态: <span style='color: #28a745; font-weight: bold;'>代理已启用</span>")
        else:
            self.status_label.setText("当前状态: <span style='color: #6c757d;'>代理未启用</span>")
    
    def toggle_password_visibility(self):
        """切换密码可见性"""
        if self.proxy_password_input.echoMode() == QLineEdit.Password:
            self.proxy_password_input.setEchoMode(QLineEdit.Normal)
            self.show_password_btn.setText("隐藏")
        else:
            self.proxy_password_input.setEchoMode(QLineEdit.Password)
            self.show_password_btn.setText("显示")
    
    def get_proxy_type(self) -> str:
        """获取当前选择的代理类型"""
        if self.http_radio.isChecked():
            return "http"
        elif self.https_radio.isChecked():
            return "https"
        elif self.socks5_radio.isChecked():
            return "socks5"
        return "http"
    
    def set_proxy_type(self, proxy_type: str):
        """设置代理类型"""
        if proxy_type == "http":
            self.http_radio.setChecked(True)
        elif proxy_type == "https":
            self.https_radio.setChecked(True)
        elif proxy_type == "socks5":
            self.socks5_radio.setChecked(True)
    
    def build_proxy_url(self) -> str:
        """构建代理URL"""
        proxy_type = self.get_proxy_type()
        host = self.proxy_host_input.text().strip()
        port = self.proxy_port_input.value()
        username = self.proxy_username_input.text().strip()
        password = self.proxy_password_input.text()
        
        if not host:
            return ""
        
        # 构建URL
        if username and password:
            # 带认证的代理
            proxy_url = f"{proxy_type}://{username}:{password}@{host}:{port}"
        else:
            # 不带认证的代理
            proxy_url = f"{proxy_type}://{host}:{port}"
        
        return proxy_url
    
    def update_proxy_preview(self):
        """更新代理预览"""
        if not self.enable_proxy_checkbox.isChecked():
            self.proxy_preview_label.setText("代理地址预览: -")
            return
        
        proxy_url = self.build_proxy_url()
        if proxy_url:
            # 隐藏密码
            display_url = proxy_url
            password = self.proxy_password_input.text()
            if password:
                display_url = proxy_url.replace(password, "****")
            self.proxy_preview_label.setText(f"代理地址预览: {display_url}")
        else:
            self.proxy_preview_label.setText("代理地址预览: 请填写代理地址")
    
    def test_proxy(self):
        """测试代理连接"""
        if not self.enable_proxy_checkbox.isChecked():
            QMessageBox.warning(self, "提示", "请先启用代理")
            return
        
        proxy_url = self.build_proxy_url()
        if not proxy_url:
            QMessageBox.warning(self, "提示", "请填写代理地址")
            return
        
        # 禁用测试按钮
        self.test_button.setEnabled(False)
        self.test_button.setText("测试中...")
        self.update_status_message("正在测试代理连接...")
        
        # 创建测试线程
        self.test_thread = ProxyTestThread(proxy_url)
        self.test_thread.test_finished.connect(self.on_test_finished)
        self.test_thread.start()
    
    def on_test_finished(self, success: bool, message: str):
        """测试完成回调"""
        # 恢复测试按钮
        self.test_button.setEnabled(True)
        self.test_button.setText("测试代理")
        
        if success:
            self.status_label.setText(f"当前状态: <span style='color: #28a745; font-weight: bold;'>代理已启用 - 连接正常</span>")
            self.update_status_message("代理测试成功")
            QMessageBox.information(self, "测试成功", message)
        else:
            self.status_label.setText(f"当前状态: <span style='color: #dc3545; font-weight: bold;'>代理已启用 - 连接失败</span>")
            self.update_status_message("代理测试失败")
            QMessageBox.warning(self, "测试失败", message)
        
        self.logger.info(f"代理测试结果: success={success}, message={message}")
    
    def load_config(self):
        """从配置加载代理设置"""
        try:
            # 加载代理设置
            self.enable_proxy_checkbox.setChecked(
                self.config_manager.get('proxy_enabled', False)
            )
            self.set_proxy_type(
                self.config_manager.get('proxy_type', 'http')
            )
            self.proxy_host_input.setText(
                self.config_manager.get('proxy_host', '127.0.0.1')
            )
            self.proxy_port_input.setValue(
                self.config_manager.get('proxy_port', 7890)
            )
            self.proxy_username_input.setText(
                self.config_manager.get('proxy_username', '')
            )
            self.proxy_password_input.setText(
                self.config_manager.get('proxy_password', '')
            )
            
            # 更新UI状态
            self.update_ui_state()
            self.update_proxy_preview()
            
            self.logger.info("代理配置加载完成")
            
        except Exception as e:
            self.logger.error(f"加载代理配置失败: {str(e)}")
    
    def save_config(self):
        """保存代理设置到配置"""
        try:
            # 保存代理设置
            self.config_manager.set('proxy_enabled', self.enable_proxy_checkbox.isChecked())
            self.config_manager.set('proxy_type', self.get_proxy_type())
            self.config_manager.set('proxy_host', self.proxy_host_input.text().strip())
            self.config_manager.set('proxy_port', self.proxy_port_input.value())
            self.config_manager.set('proxy_username', self.proxy_username_input.text().strip())
            self.config_manager.set('proxy_password', self.proxy_password_input.text())
            
            # 保存到文件
            self.config_manager.save_config()
            
            # 发射变更信号
            proxy_url = self.build_proxy_url() if self.enable_proxy_checkbox.isChecked() else ""
            self.proxy_changed.emit(self.enable_proxy_checkbox.isChecked(), proxy_url)
            
            self.update_status_message("代理设置已保存")
            QMessageBox.information(self, "成功", "代理设置已保存")
            
            self.logger.info("代理配置保存完成")
            
        except Exception as e:
            self.logger.error(f"保存代理配置失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"保存设置失败:\n{str(e)}")
    
    def update_status_message(self, message: str):
        """更新状态栏消息"""
        if self.status_bar:
            self.status_bar.showMessage(message)
    
    def is_proxy_enabled(self) -> bool:
        """检查代理是否启用"""
        return self.enable_proxy_checkbox.isChecked()
    
    def get_proxy_url(self) -> Optional[str]:
        """获取代理URL（如果已启用）"""
        if self.enable_proxy_checkbox.isChecked():
            return self.build_proxy_url()
        return None
