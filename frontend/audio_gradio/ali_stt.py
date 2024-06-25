# For prerequisites running the following sample, visit https://help.aliyun.com/document_detail/611472.html
import logging
import time
import threading
import pyaudio
import dashscope
import gradio as gr
from dashscope.audio.asr import (Recognition, RecognitionCallback,
                                 RecognitionResult)
from dashscope.common.constants import REQUEST_TIMEOUT_KEYWORD

import speech_recognition as sr


recognizer = sr.Recognizer()

dashscope.api_key='sk-8deaaacf2fb34929a076dfc993273195'
stream = None                              # 音频流对象，用于读取音频数据。
mic = None                                 # 麦克风对象
transform_res = None                       # 转写结果记录,记录每一次转写结果.
recognition_active = False           # 是否开始实时语音识别的标志,第一次点击麦克风按钮会设置为True,第二次点击会设置为False
stt_thread = None                          # 语音识别运行线程, 得当作全局变量,否则第二次运行的时候,会识别不到这个变量,因为其只在lingji_stt_gradio函数的if语句中被初始化了,第二次运行的时候(即第二次点击的时候),会进入else分支,然后发生找不到这个变量的错误,设置为全局变量可以解决这个问题.

# 回调函数，在某个条件下会调用其成员函数
class Callback(RecognitionCallback):
    def on_open(self) -> None:
        global stream, mic

        # 创建一个Pyaudio实例，用于与音频接口交互，比如打开、关闭音频流和获取设备信息。
        mic = pyaudio.PyAudio()
        # 创建一个音频流，用于从麦克风或其他音频源获取音频数据。
        stream = mic.open(
            format=pyaudio.paInt16,  # 音频数据格式,pyaudio.paInt16表示16位深度
            channels=1,              # 指定音频的声道数，1表示单声道Mono
            rate=16000,              # 指定音频的采样率，16000表示每秒采样1600次
            input=True)              # 指定该流用于输入，用于从麦克风或其他音频源获取音频数据
    
    def on_close(self) -> None:
        global stream, mic

        if stream:
            # 关闭音频流，防止继续读取数据
            stream.stop_stream()
            stream.close()
            stream = None
        if mic:
            # 关闭PyAudio实例，释放资源
            mic.terminate()
            mic = None
    
    def on_event(self, result: RecognitionResult) -> None:
        # 处理每一次转写结果
        global transform_res

        transform_res = result
        print("RecognitionCallback sentence: ", result.get_sentence())

    def on_complete(self) -> None:
        # 当识别全部完成时调用
        global transform_res

        print("RecognitionCallback on_complete：", transform_res.get_sentence())

class CallbackVoiceAwake(Callback):
    def on_complete(self) -> None:
        global recognition_active,transform_res

        recognition_active = False  # 识别结束，将标志设置为False，这样主线程就可以关闭录音实例了。

class AudioRecognitionThread(threading.Thread):
    def __init__(self):
        # 设置为守护进程，当主程序崩溃时，其也会自动结束。
        super().__init__(daemon=True)

        self.logger = logging.getLogger(__name__)

        if not self.logger.handlers:
            logging.basicConfig(level=logging.INFO)

    def run(self):
        """覆盖Thread类的run方法，用于定义线程执行的任务。"""
        global stream, recognition, recognition_active

        # 先进行监听，如果没有声音，则不进发送音频数据

        while recognition_active:
            try:
                
                data = stream.read(3200, exception_on_overflow=False)
                recognition.send_audio_frame(data)
                print("stream 长度", len(recognition._stream_data))
            except Exception as e:
                # print(e)
                pass
            time.sleep(0.01)  # 控制循环频率，减少CPU占用
        logging.log(level=logging.INFO, msg="Thread of stt is finished...")

def lingji_stt_gradio(inputs) -> str:
    # 定义语音识别的函数
    global recognition, recognition_active, stream, stt_thread

    # 添加触发按钮
    if not recognition_active:                   # 如果没有激活语音识别
            stt_thread = AudioRecognitionThread() # 线程在调用其.start方法后,不能够再次调用,所以每次都需要重新创建.

            recognition_active = True               # 设置识别激活语音识别
            Recognition.SILENCE_TIMEOUT_S = 200
            
            kwargs = {REQUEST_TIMEOUT_KEYWORD: 120}
            recognition= Recognition(
                model="paraformer-realtime-v1",   # 语音识别模型
                format='pcm',                     # 音频格式
                sample_rate=16000,                # 指定音频的采样率，16000表示每秒采样16000次。
                callback=Callback(),
                **kwargs
                )

            recognition.start()                   # 开始语音识别
            while not stream:                     # 等待stream,麦克风等设备初始化好,再进行语音识别.
                continue
            stt_thread.start()                    # 开始识音
            logging.log(logging.INFO, "开始识音")
    else:                                         # 如果已经激活识别
        recognition_active = False                # 取消识别激活标志
        recognition.stop()                        # 停止语音识别
        recognition = None                        # 因为stop时已经删除掉了一些组件，所以把语音识别实例删除掉，下次再重新创建。
        stt_thread.join()                         # 此时stt线程应该是要结束运行的.
    
        return transform_res.get_sentence()['text']

def lingji_stt_gradio_va() -> str:
    '''
    拥有语音唤醒功能的实时文本转语音函数
    '''
    global recognition, recognition_active, stream, stt_thread,transform_res

    # 麦克风准备
    Recognition.SILENCE_TIMEOUT_S = 200      
    kwargs = {REQUEST_TIMEOUT_KEYWORD: 120}
    recognition= Recognition(
        model="paraformer-realtime-v1",   # 语音识别模型
        format='pcm',                     # 音频格式
        sample_rate=16000,                # 指定音频的采样率，16000表示每秒采样16000次。
        callback=CallbackVoiceAwake(),
        **kwargs
        )
    recognition.start()

    # 使用麦克风进行录音
    while not stream:                     # 等待stream,麦克风等设备初始化好,再进行语音识别.
        continue
    stt_thread = AudioRecognitionThread() # 发送语音帧的线程
    recognition_active = True             # 可以进行录音了
    stt_thread.start()                    # 开始识音

    # 关闭录音实例
    while recognition_active:             # 等待Callback的on_complete回调函数把recognition_active设置为False
        time.sleep(0.01)
    recognition.stop()                    # 停止语音识别
    stt_thread.join()                     # 此时stt线程应该是要结束运行的.

    return transform_res.get_sentence()['text']

if __name__ == "__main__":
    lingji_stt_gradio(None)