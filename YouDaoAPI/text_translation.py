import sys
import uuid
import requests
import hashlib
import time

def encrypt(signStr):
    hash_algorithm = hashlib.sha256()
    # 调整编码格式为utf-8
    hash_algorithm.update(signStr.encode('utf-8'))
    # 返回16进制形式的加密编码
    return hash_algorithm.hexdigest()

# 当请求单词的长度过长时，需要对q进行裁剪，input = q前十个字符 + q长度 + q后十个字符（当q的长度大于20时）


def truncate(q):
    if q is None:
        return None
    size = len(q)
    return q if size <= 20 else q[0:10] + str(size) + q[size-10:size]


def getTrans(query):

    YOUDAO_URL = 'http://openapi.youdao.com/api'

    APP_KEY = '4f938f684c09931e'
    
    APP_SECRET = 'dkzAd8YOi8pg77V7j7a3QTcJ0vOv6VWk'

    data = {}
    
    curtime = str(int(time.time()))

    salt = str(uuid.uuid1())

    signStr = APP_KEY + truncate(query) + salt + curtime + APP_SECRET

    sign = encrypt(signStr)

    data = {
        'from':'EN',
        'to':'zh-CHS',
        'signType':'v3',
        'curtime':curtime,
        'appKey':APP_KEY,
        'q':query,
        'salt':salt,
        'sign':sign
    }

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    responce = requests.post(YOUDAO_URL,data=data,headers=headers)

    return responce.content