import os
import random
import string
import logging
import datetime
import speech_recognition as sr

from ali_stt import Recognition,Callback,lingji_stt_gradio
from speech_recognition import AudioData

def get_logger():
    # 日志收集器
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    
    # 设置控制台处理器，当logger被调用时，控制台处理器额外输出被调用的位置。
    # 创建一个控制台处理器并设置级别为DEBUG
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    # 创建一个格式化器，并设置格式包括文件名和行号
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s')
    ch.setFormatter(formatter)

    # 将处理器添加到logger
    logger.addHandler(ch)

    return logger

def get_random_file_name(length=20, extension='.wav'):
    '''create a random file name with current time'''
    current_time = datetime.datetime.now().strftime("%Y-%m-%d%H-%M-%S")
    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    return f"{current_time}_{random_string}{extension}"

def save_audio_file(audio:AudioData, sample_rate=16000):
    file_name = get_random_file_name()
    with open(file_name, "wb") as f:
        f.write(audio.get_wav_data(convert_rate=sample_rate))
    return file_name

def recognize_speech(audio_path, recognizer:Recognition) ->str:
    return recognizer.call(audio_path).get_sentence()[0]['text']

def lingji_stt_gradio_voice_awake(input_box):
    '''
    语音唤醒模块
    ---

    input_box: modelscope_studio的MultimodalInput
    '''
    recognizer = sr.Recognizer()
    logger = get_logger()

    recognition= Recognition(
                model="paraformer-realtime-v1",            # 语音识别模型
                format='wav',                     # 音频格式
                sample_rate=16000,                # 指定音频的采样率，16000表示每秒采样16000次。
                callback=Callback()
                )
    
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, 1)          # 调整背景噪音
        
        while True:
            try:
                # 一直监听语音
                logger.info("Listening for wake word 'hei siri'...")
                audio = recognizer.listen(source)               # 监听麦克风
                logger.info("Recognizing done.")
                audio_path = save_audio_file(audio)
                result = recognize_speech(audio_path, recognizer=recognition)
                os.remove(audio_path)
                logger.info(f"Recognized: {result}")

                # 当用户说出特定唤醒词时
                if "siri" in result:
                    logger.info("Wake word detected!")

                    # TODO: 给出固定的欢迎回复

                    # 开始录音
                    input_box = lingji_stt_gradio(input_box)
                    
                    break
            except sr.UnknownValueError:
                continue
            except TypeError as e:
                continue


def test():
    lingji_stt_gradio_voice_awake()


if __name__ == "__main__":
    test()