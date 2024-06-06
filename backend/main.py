import os
import time
import json
import asyncio
import uvicorn
import requests

from client import get_client
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from conversation import Conversation, Role, postprocess_text

app = FastAPI()

def append_conversation(
        conversation: Conversation,
        history: list[Conversation]
) -> None:
    history.append(conversation)    

@app.post("/generate-stream")
async def generate_stream(request: Request):
    body = await request.json()
    prompt_text = body.get("query", "您好！")
    system_prompt = body.get("system_prompt", "")
    tools = body.get("tools", None)
    session_id = body.get("session_id")
    kwargs = body.get("kwargs", {})
    # 可以添加如下参数到kwargs中
    # do_sample = body.get("do_sample", True)
    # max_new_tokens = body.get("max_new_tokens", 100)
    # temperature = body.get("temperature", 0.9)
    # top_p = body.get("top_p", 0.95)
    # stop_sequences = body.get("stop_sequences", [str(Role.USER)])
    # repetition_penalty = body.get("repetition_penalty", 1.0)

    prompt_text = prompt_text.strip()

    if session_id in HISTORY:
        history = HISTORY[session_id]
    else:
        HISTORY[session_id] = []
        history = []
    
    append_conversation(Conversation(Role.USER, prompt_text), history)

    def event_generator():
        output_text = ""
        for text in client.generate_stream(
                                            system_prompt,
                                            tools,
                                            history,
                                            **kwargs):
            token = text.token.text
            output_text += token
            yield json.dumps({"token":token, "special":text.token.special}, ensure_ascii=False) + '\n'
        
        append_conversation(Conversation(Role.ASSISTANT, output_text), history)

    return StreamingResponse(event_generator(), media_type="text/plain")

@app.post("his_clean")
async def his_clean(request: Request):
    global HISTORY

    body = await request.json()
    session_id = body.get("session_id")

    if session_id in HISTORY:
        del HISTORY[session_id]
    else:
        pass

if __name__ == "__main__":
    client = get_client()
    HISTORY:dict[list[Conversation]] = {}
    OUTPUT_TEXT = ""
    SYS_PROMPT = ""

    uvicorn.run(app, host="0.0.0.0", port=8000)

    # 示例用法
    """
    curl -X POST "http://localhost:8000/generate-stream" -H "Content-Type: application/json" -d '{
        "query": "您好！",
        "params": {
            "max_length": 100,
        }
        }
    }
    """