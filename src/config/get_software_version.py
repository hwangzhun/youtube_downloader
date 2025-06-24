import os
import json

def get_software_version():
    """获取软件版本号"""
    try:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config['software_version']
    except Exception as e:
        print(f"读取配置文件失败: {str(e)}")
        return 'null'
    
# print(get_software_version())