
import os
import sys
import json
import logging

from fastapi import FastAPI, Request
from fastapi.responses import Response

from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from sse_starlette.sse import EventSourceResponse

sys.path.append(os.path.join(os.path.dirname(__file__), "ml"))

from ml.config import load_config
from ml.qa import QA, ThreadedGenerator

root = logging.getLogger()

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.WARNING)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)

config = load_config(script_dir=os.path.dirname(__file__))

qa = QA(config)


origins = ["*"]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Question(BaseModel):
    content: str 

class Message(BaseModel):
    role: str

class Prompt(BaseModel):
    message: Question
    temperature: float

@app.post("/answer")
async def answer(question: Question):
    resp = qa.answer(question.content)

    return resp

@app.post("/v1/chat/completions")
async def v1ChatCompletions(question: Prompt):
    resp = qa.answer(question.message.content)
    return resp

@app.post("/v2/chat/completions")
async def v2ChatCompletions(req: Request, question: Prompt):
    # print(f"///////////// Temp {question.temperature} /////////////////")
    return EventSourceResponse(gen(req, await qa.answer_stream(question.message.content, question.temperature)))


async def gen(req: Request, gen: ThreadedGenerator):
    for i in gen:
        if await req.is_disconnected():
            break
        yield json.dumps({
            "choices": [
                {
                    "delta": {
                        "content": i
                    }
                }
            ]
        })

    yield json.dumps({
            "choices": [
                {
                    "finish_reason": "finished"
                }
            ]
        })