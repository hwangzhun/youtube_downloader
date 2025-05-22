# YouTube 下載工具項目結構

## 目錄結構
```
youtube_downloader/
├── main.py                 # 主程序入口
├── installer/              # 安裝程序相關文件
├── resources/              # 資源文件
│   ├── icons/              # 圖標文件
│   ├── styles/             # 樣式文件
│   └── binaries/           # 二進制文件
│       ├── yt-dlp/         # yt-dlp 可執行文件及相關庫
│       └── ffmpeg/         # ffmpeg 可執行文件及相關庫
├── src/                    # 源代碼
│   ├── ui/                 # UI 相關模塊
│   │   ├── main_window.py  # 主窗口
│   │   ├── download_tab.py # 下載標籤頁
│   │   └── version_tab.py  # 版本標籤頁
│   ├── core/               # 核心功能模塊
│   │   ├── downloader.py   # 下載器
│   │   ├── cookie_manager.py # Cookie 管理
│   │   ├── format_converter.py # 格式轉換
│   │   └── version_manager.py # 版本管理
│   └── utils/              # 工具類
│       ├── config.py       # 配置管理
│       ├── notification.py # 通知管理
│       └── logger.py       # 日誌管理
└── tests/                  # 測試文件
```

## 模塊說明

### 主程序模塊
- `main.py`: 程序入口點，負責初始化應用程序和顯示主窗口

### UI 模塊
- `main_window.py`: 主窗口類，包含標籤頁管理和整體布局
- `download_tab.py`: 下載標籤頁，包含下載相關的所有UI元素和事件處理
- `version_tab.py`: 版本標籤頁，顯示和管理yt-dlp和ffmpeg版本

### 核心功能模塊
- `downloader.py`: 負責視頻下載的核心功能，調用yt-dlp
- `cookie_manager.py`: 管理cookie的獲取、導入和使用
- `format_converter.py`: 處理視頻格式轉換，調用ffmpeg
- `version_manager.py`: 管理yt-dlp和ffmpeg的版本檢查和更新

### 工具類模塊
- `config.py`: 管理應用程序配置
- `notification.py`: 處理下載完成通知
- `logger.py`: 日誌記錄功能

### 資源文件
- `icons/`: 存放應用程序圖標和UI圖標
- `styles/`: 存放Metro風格的樣式表
- `binaries/`: 存放yt-dlp和ffmpeg的可執行文件
