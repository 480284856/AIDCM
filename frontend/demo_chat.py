import json
import queue
import requests
import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from client import get_client
from conversation import postprocess_text, preprocess_text, Conversation, Role

def remote_call(
        url='http://localhost:24398/generate-stream',
        gen_kwargs:dict={
            "query": "您好！",
            "params": {
                "max_length": 100,
            }
        }
):
    # 发送请求并处理流式响应
    response = requests.post(url, stream=True, json=gen_kwargs)

    # 检查响应状态码
    if response.status_code == 200:
        # 处理流式响应
        # 逐行读取响应数据，每次传递一个字符串
        for line in response.iter_lines(decode_unicode=True):
            if line:
                # 处理每一行数据
                yield line
    else:
        # 处理错误情况
        print(f"请求失败，状态码：{response.status_code}")

def remote_his_clean(
        url,
        session_id
):
    # 发送请求
    response = requests.post(url, json={"session_id": session_id})

# Append a conversation into history, while show it in a new markdown block
def append_conversation(
        conversation: Conversation,
        history: list[Conversation],
        placeholder: DeltaGenerator | None = None,
) -> None:
    history.append(conversation)
    conversation.show(placeholder)


def main(
        prompt_text: str,
        system_prompt: str,
        top_p: float = 0.8,
        temperature: float = 0.95,
        repetition_penalty: float = 1.0,
        max_new_tokens: int = 1024,
        retry: bool = False,
        Q: queue.Queue = None,
        remote_url = "http://localhost:24398/",
        llm_tag = "generate-stream",
        his_clean_tag = "his-clean"
):
    placeholder = st.empty()
    with placeholder.container():
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []

    if prompt_text == "" and retry == False:
        print("\n== Clean ==\n")
        st.session_state.chat_history = []

        remote_his_clean(remote_url + his_clean_tag, st.session_state.session_id)
        return

    history: list[Conversation] = st.session_state.chat_history
    for conversation in history:
        conversation.show()

    if retry:
        print("\n== Retry ==\n")
        last_user_conversation_idx = None
        for idx, conversation in enumerate(history):
            if conversation.role == Role.USER:
                last_user_conversation_idx = idx
        if last_user_conversation_idx is not None:
            prompt_text = history[last_user_conversation_idx].content
            del history[last_user_conversation_idx:]


    if prompt_text:
        prompt_text = prompt_text.strip()
        append_conversation(Conversation(Role.USER, prompt_text), history)
        placeholder = st.empty()
        message_placeholder = placeholder.chat_message(name="assistant", avatar="assistant")
        markdown_placeholder = message_placeholder.empty()

        output_text = ''
        part_of_output = ''
        # for response in client.generate_stream(
        #         system_prompt,
        #         tools=None,
        #         history=history,
        #         do_sample=True,
        #         max_new_tokens=max_new_tokens,
        #         temperature=temperature,
        #         top_p=top_p,
        #         stop_sequences=[str(Role.USER)],
        #         repetition_penalty=repetition_penalty,
        # ):
        
        gen_kwargs = {
            "query": prompt_text,
            "session_id": st.session_state.session_id
        }

        for response in remote_call(
            url=remote_url+llm_tag,
            gen_kwargs=gen_kwargs
        ):
            token = response.token
            if response['special']:
                print("\n==Output:==\n", output_text)
                match token.text.strip():
                    case '<|user|>':
                        break
                    case _:
                        st.error(f'Unexpected special token: {token.text.strip()}')
                        break
            output_text += response['token']
            markdown_placeholder.markdown(postprocess_text(output_text + '▌'))

            part_of_output += response['token']
            if response['token'] in ',.?!;，。？！；':
                Q.put(part_of_output)
                part_of_output = ''
        return output_text

        append_conversation(Conversation(
            Role.ASSISTANT,
            postprocess_text(output_text),
        ), history, markdown_placeholder)