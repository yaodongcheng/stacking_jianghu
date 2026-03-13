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


def signed_headers(app_id, app_key, project_id):
    # 生成10位随机字母数字字符串作为nonce
    chars = string.ascii_letters + string.digits
    nonce = ''.join(secrets.choice(chars) for _ in range(10))

    # 获取秒级时间戳
    timestamp = str(int(time.time()))

    # 构建签名字符串
    str2_sign = f"appId={app_id}&nonce={nonce}&timestamp={timestamp}&appkey={app_key}"

    # 计算MD5签名并转为大写
    sign = hashlib.md5(str2_sign.encode('utf-8')).hexdigest().upper()

    # 构造请求头
    headers = {
        "Content-Type": "application/json",
        "appId": app_id,
        "projectId": project_id,
        "nonce": nonce,
        "timestamp": timestamp,
        "sign": sign,
        "version": "v2"
    }
    return headers


if __name__ == "__main__":

    app_key = "sk-xp97drsAZGjr7RNKvk6CmciZA0mmPyHh"
    app_id = "99cd5156-c089-45e1-a22d-fdd16873c1959"
    project_id = "default"  # 请替换为你的实际 project_id
    url = "https://aigc-api.apps-hangyan.danlu.netease.com/api/v3/text/chat"

    inputjson = {
        "model": "doubao-seedream-5-0-260128",
        "prompt": "星际穿越，黑洞，黑洞里冲出一辆快支离破碎的复古列车，抢视觉冲击力，电影大片，末日既视感，动感，对比色，oc渲染，光线追踪，动态模糊，景深，超现实主义，深蓝，画面通过细腻的丰富的色彩层次塑造主体与场景，质感真实，暗黑风背景的光影效果营造出氛围，整体兼具艺术幻想感，夸张的广角透视效果，耀光，反射，极致的光影，强引力，吞噬",
        "size": "2K",
        "sequential_image_generation": "disabled",
        "stream": False,
        "response_format": "b64_json",
        "seed": -1,
        "watermark": True
    }
    
    headers = signed_headers(app_id=app_id, app_key=app_key, project_id=project_id)
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