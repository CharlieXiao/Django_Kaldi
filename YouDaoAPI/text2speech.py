import requests
import hashlib
import random
import time

def getSpeech(query):

    YOUDAO_URL = 'http://openapi.youdao.com/api'

    APP_KEY = '4f938f684c09931e'
    
    APP_SECRET = 'dkzAd8YOi8pg77V7j7a3QTcJ0vOv6VWk'

    lang = 'en'
    data = {}
    salt = random.randint(1, 65536)
    sign = APP_KEY + query + str(salt) + APP_SECRET

    m1 = hashlib.md5()
    m1.update(sign.encode('utf-8'))
    sign = m1.hexdigest()

    data['appKey'] = APP_KEY
    data['q'] = query
    data['salt'] = salt
    data['sign'] = sign
    data['langType'] = lang

    response = requests.post(YOUDAO_URL, data=data)

    return response.content

