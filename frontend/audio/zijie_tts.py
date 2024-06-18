#coding=utf-8

'''
requires Python 3.6 or later
pip install requests
'''
import base64
import json
import uuid
import requests
import random
import string

def generate_random_filename(length=10, extension=".txt"):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length)) + extension

def tts(
        text
):
    # 填写平台申请的appid, access_token以及cluster
    appid = "3400210889"
    access_token= "bofQneJofrHGoiiNGGEV7rdyPUqkw7gp"
    cluster = "volcano_tts"

    voice_type = "BV002_streaming"
    host = "openspeech.bytedance.com"
    api_url = f"https://{host}/api/v1/tts"

    header = {"Authorization": f"Bearer;{access_token}"}

    request_json = {
        "app": {
            "appid": appid,
            "token": "access_token",
            "cluster": cluster
        },
        "user": {
            "uid": "388808087185088"
        },
        "audio": {
            "voice_type": voice_type,
            "encoding": "mp3",
            "speed_ratio": 1.0,
            "volume_ratio": 1.0,
            "pitch_ratio": 1.0,
        },
        "request": {
            "reqid": str(uuid.uuid4()),
            "text": text,
            "text_type": "plain",
            "operation": "query",
            "with_frontend": 1,
            "frontend_type": "unitTson"

        }
    }

    try:
        resp = requests.post(api_url, json.dumps(request_json), headers=header)
        print(f"resp body: \n{resp.json()}")
        if "data" in resp.json():
            data = resp.json()["data"]
            file_to_save = open(generate_random_filename(extension=".mp3"), "wb")
            file_to_save.write(base64.b64decode(data))
            file_to_save.close()
    except Exception as e:
        e.with_traceback()
    
    # return file_to_save



if __name__ == '__main__':
    tts("你好，这是一个测试")
