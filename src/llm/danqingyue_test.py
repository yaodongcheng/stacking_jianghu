import requests
import string
import secrets
import time
import hashlib
import json
import base64
from io import BytesIO
from PIL import Image
import logging
import uuid



# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if __name__ == "__main__":


    api_key = "sk-xp97drsAZGjr7RNKvk6CmciZA0mmPyHh"  # 请替换为你的实际 API Key
    url = "https://aigc-api.fuxi.netease.com/v3/text/chat"



    inputjson = {
        "model": "doubao-seedream-5-0-260128",
        "prompt": "那恶霸猛地一拍桌子，吓得周围人纷纷后退 围观的百姓开始窃窃私语，有人悄悄退开",
        "size": "2K",
        "sequential_image_generation": "disabled",
        "stream": False,
        "response_format": "b64_json",
        "seed": -1,
        "watermark": True
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    logger.info("开始请求...")
    resp = requests.post(url, headers=headers, json=inputjson)
    logger.info(f"请求结束，状态码: {resp.status_code}")
    
    if resp.status_code == 200:
        result = json.loads(resp.text)
        if 'data' in result and len(result['data']) > 0:
            output_base64_data = result['data'][0]['b64_json']
            image_id = str(uuid.uuid1())
            image_bytes = base64.b64decode(output_base64_data)
            image = Image.open(BytesIO(image_bytes))
            output_path = f"./generated_image_{image_id}.png"
            image.save(output_path)
            logger.info(f"图片已保存到: {output_path}")
        else:
            logger.error(f"响应中没有数据: {result}")
    else:
        logger.error(f"请求失败: {resp.status_code}, {resp.text}")