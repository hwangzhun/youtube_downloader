"""
创建简单的应用图标和启动画面
"""
import os
from PIL import Image, ImageDraw, ImageFont

# 创建目录
icons_dir = "/home/ubuntu/youtube_downloader/resources/icons"
os.makedirs(icons_dir, exist_ok=True)

# 创建应用图标
icon_size = 256
icon = Image.new('RGBA', (icon_size, icon_size), (0, 0, 0, 0))
draw = ImageDraw.Draw(icon)

# 绘制圆形背景
circle_color = (0, 120, 215)  # Metro蓝色
draw.ellipse((10, 10, icon_size-10, icon_size-10), fill=circle_color)

# 绘制播放按钮
triangle_color = (255, 255, 255)
triangle_points = [
    (icon_size//2 + 30, icon_size//2),
    (icon_size//2 - 15, icon_size//2 - 30),
    (icon_size//2 - 15, icon_size//2 + 30)
]
draw.polygon(triangle_points, fill=triangle_color)

# 保存图标
icon.save(os.path.join(icons_dir, 'app_icon.ico'), format='ICO')
icon.save(os.path.join(icons_dir, 'app_icon.png'), format='PNG')

# 创建启动画面
splash_width = 600
splash_height = 300
splash = Image.new('RGBA', (splash_width, splash_height), (0, 0, 0, 0))
splash_draw = ImageDraw.Draw(splash)

# 绘制背景
splash_draw.rectangle((0, 0, splash_width, splash_height), fill=(0, 120, 215))

# 绘制图标
icon_small = icon.resize((100, 100), Image.LANCZOS)
splash.paste(icon_small, (splash_width//2 - 50, 50), icon_small)

# 绘制文本
try:
    # 尝试加载字体
    font = ImageFont.truetype("arial.ttf", 24)
except:
    # 如果找不到字体，使用默认字体
    font = ImageFont.load_default()

splash_draw.text((splash_width//2, 180), "YouTube 视频下载工具", fill=(255, 255, 255), font=font, anchor="mm")
splash_draw.text((splash_width//2, 220), "作者: Hwangzhun", fill=(255, 255, 255), font=font, anchor="mm")
splash_draw.text((splash_width//2, 260), "正在加载...", fill=(255, 255, 255), font=font, anchor="mm")

# 保存启动画面
splash.save(os.path.join(icons_dir, 'splash.png'), format='PNG')

print("图标和启动画面创建完成")
