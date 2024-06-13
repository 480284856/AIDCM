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
from audio.zijie_tts import tts
from audio.ali_stt import lingji_stt_st
from streamlit.runtime.scriptrunner import add_script_run_ctx

DEFAULT_SYSTEM_PROMPT = '''
    You are ChatGLM3, a large language model trained by Zhipu.AI. Follow the user's instructions carefully. Respond using markdown.
    '''.strip()

class Mode(str, Enum):
    CHAT, TOOL, CI = '💬 Chat', '🛠️ Tool', '🧑‍💻 Code Interpreter'

class TextConsumer(threading.Thread):
    def __init__(self, queue_text:queue.Queue, daemon=True):
        '''
        消耗文字队列中的元素的类实现。
        '''
        super().__init__(daemon=daemon)
        self.queue_text = queue_text

    def run(self):
        while True:
            text = self.queue_text.get()
            if text is None:
                break
            
            self.audio = tts(text)
            
            mixer.init()
            mixer.music.load(self.audio)
            mixer.music.play()
            while mixer.music.get_busy():
                time.sleep(0.001)
            
            os.remove(self.audio)
            self.queue_text.task_done()

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

    tab = st.radio(
        'Mode',
        [mode.value for mode in Mode],
        horizontal=True,
        label_visibility='hidden',
    )

    if clear_history or retry:
        prompt_text = ""

    prompt_text = st.chat_input('Chat with me!', key='chat_input')

    match tab:
        case Mode.CHAT:
            prompt_text_from_audio = lingji_stt_st()

            if not prompt_text:                       # 如果没有从文本输入框输入
                prompt_text = prompt_text_from_audio
            
            if "tts_thread" not in st.session_state:  # 如果没有开启语音合成功能
                if 'queue_text' not in st.session_state:
                    st.session_state.queue_text = queue.Queue()
                c = TextConsumer(queue_text=st.session_state.queue_text)
                c = add_script_run_ctx(c)
                st.session_state.tts_thread = c
                st.session_state.tts_thread.start()

            demo_chat.main(
                retry=retry,
                top_p=top_p,
                temperature=temperature,
                prompt_text=prompt_text,
                system_prompt=system_prompt,
                repetition_penalty=repetition_penalty,
                max_new_tokens=max_new_token,
                Q = st.session_state.queue_text,
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

if __name__ == "__main__":
    web()


