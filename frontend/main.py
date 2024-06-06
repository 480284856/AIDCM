import os
import time
import uuid
import queue
import random
import string
import requests
import demo_chat#, demo_ci, demo_tool
import threading
import configparser
import streamlit as st

from enum import Enum
from pygame import mixer
# from add_new_tool import *
from audio.ali_stt import lingji_stt_st
from streamlit.runtime.scriptrunner import add_script_run_ctx

DEFAULT_SYSTEM_PROMPT = '''
    You are ChatGLM3, a large language model trained by Zhipu.AI. Follow the user's instructions carefully. Respond using markdown.
    '''.strip()

class Mode(str, Enum):
    CHAT, TOOL, CI = '💬 Chat', '🛠️ Tool', '🧑‍💻 Code Interpreter'

class Consumer(threading.Thread):
    def __init__(self, queue_text:queue.Queue, daemon=True):
        super().__init__(daemon=daemon)
        self.queue_text = queue_text
        self.key,self.token = load_tts_config()
    
    def generate_random_filename(self, length=10, extension=".txt"):
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length)) + extension

    def run(self):
        while True:
            text = self.queue_text.get()
            if text is None:
                break
            
            self.audio = tts(text, self.key, self.token)
            
            # Download the MP3 file
            filename = self.generate_random_filename(length=10,extension=".wav")
            response = requests.get(self.audio)
            
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            mixer.init()
            mixer.music.load(filename)
            mixer.music.play()
            while mixer.music.get_busy():
                time.sleep(0.001)
            
            os.remove(filename)
            self.queue_text.task_done()

def load_tts_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    key = config['aliyun']['key']
    token = config['aliyun']['token']
    return key,token

def web():
    st.set_page_config(
    page_title="ChatGLM3 Demo",
    page_icon=":robot:",
    layout='centered',
    initial_sidebar_state='expanded',
    )

    # Set the title of the demo
    st.title("ChatGLM3 Demo")

    # Add your custom text here, with smaller font size
    st.markdown(
        "<sub>智谱AI 公开在线技术文档: https://lslfd0slxc.feishu.cn/wiki/WvQbwIJ9tiPAxGk8ywDck6yfnof </sub> \n\n <sub> 更多 ChatGLM3-6B 的使用方法请参考文档。</sub>",
        unsafe_allow_html=True)

    with st.sidebar:
        top_p = st.slider(
            'top_p', 0.0, 1.0, 0.8, step=0.01
        )
        temperature = st.slider(
            'temperature', 0.0, 1.5, 0.95, step=0.01
        )
        repetition_penalty = st.slider(
            'repetition_penalty', 0.0, 2.0, 1.1, step=0.01
        )
        max_new_token = st.slider(
            'Output length', 5, 32000, 256, step=1
        )

        cols = st.columns(2)
        export_btn = cols[0]
        clear_history = cols[1].button("Clear History", use_container_width=True)
        retry = export_btn.button("Retry", use_container_width=True)

        system_prompt = st.text_area(
            label="System Prompt (Only for chat mode)",
            height=300,
            value=DEFAULT_SYSTEM_PROMPT,
        )

        prompt_text = st.chat_input(
            'Chat with ChatGLM3!',
            key='chat_input',
        )

    tab = st.radio(
        'Mode',
        [mode.value for mode in Mode],
        horizontal=True,
        label_visibility='hidden',
    )

    if clear_history or retry:
        prompt_text = ""

    match tab:
        case Mode.CHAT:
            demo_chat.main(
                retry=retry,
                top_p=top_p,
                temperature=temperature,
                prompt_text=prompt_text,
                system_prompt=system_prompt,
                repetition_penalty=repetition_penalty,
                max_new_tokens=max_new_token
            )
        # case Mode.TOOL:
        #     demo_tool.main(
        #         retry=retry,
        #         top_p=top_p,
        #         temperature=temperature,
        #         prompt_text=prompt_text,
        #         repetition_penalty=repetition_penalty,
        #         max_new_tokens=max_new_token,
        #         truncate_length=1024)
        # case Mode.CI:
        #     demo_ci.main(
        #         retry=retry,
        #         top_p=top_p,
        #         temperature=temperature,
        #         prompt_text=prompt_text,
        #         repetition_penalty=repetition_penalty,
        #         max_new_tokens=max_new_token,
        #         truncate_length=1024)
        case _:
            st.error(f'Unexpected tab: {tab}')




