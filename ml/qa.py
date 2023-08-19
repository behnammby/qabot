from typing import Any, Optional, Union,Tuple
import logging
import threading
import queue
from uuid import UUID

from langchain.schema import LLMResult

from ml.config import Config
from ml.vectordb import VectorDB

from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.chains.question_answering import load_qa_chain
from langchain.chains.combine_documents.base import BaseCombineDocumentsChain
from langchain.prompts import PromptTemplate

from langchain.callbacks.base import BaseCallbackHandler
from langchain.callbacks.streaming_stdout_final_only import FinalStreamingStdOutCallbackHandler

from langchain import PromptTemplate
from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    AIMessagePromptTemplate,
    HumanMessagePromptTemplate,
)

class ThreadedGenerator:
    def __init__(self, question: str):
        self.queue = queue.Queue()
        self.question: str = question

    def __iter__(self):
        return self

    def __next__(self):
        item = self.queue.get()
        if item is StopIteration: raise item
        return item

    def send(self, data):
        self.queue.put(data)

    def close(self):
        self.queue.put(StopIteration)

class ChainStreamHandler(BaseCallbackHandler):
    def __init__(self, gen: ThreadedGenerator):
        super().__init__()
        self.gen: ThreadedGenerator = gen
        self.streamed: str = ""

    def on_llm_new_token(self, token: str, **kwargs):
        if token == ".":
            token += " "
        self.gen.send(token)
        self.streamed += token

    def on_llm_end(self, response: LLMResult, *, run_id: UUID, parent_run_id: Union[UUID, None] = None, **kwargs: Any) -> Any:
        logging.warning(f"\n(((((\n\n({self.gen.question})\n\n({self.streamed})\n\n)))))\n")
        return super().on_llm_end(response, run_id=run_id, parent_run_id=parent_run_id, **kwargs)

class QA:
    def __init__(self, config: Config) -> None:
        self.config: Config = config
        self.db: VectorDB = VectorDB(self.config)

    def answer(self, question: str) -> str:
        docs = self.db.get_relevant_docs(question)
        chain = self.get_chain()

        result = chain({"input_documents": docs, "question": question},return_only_outputs=True)
        return result["output_text"]

    async def answer_stream(self, question: str, temprature: float) -> ThreadedGenerator:
        gen = ThreadedGenerator(question)
        threading.Thread(target=self.answer_thread, args=(gen, question, temprature)).start()

        return gen
    
    def answer_thread(self, gen: ThreadedGenerator, question: str, temp: float):
        try:
            docs = self.db.get_relevant_docs(question)
            if len(docs) == 0:
                logging.info(f"couldn't get any relevant docs for query {question}")
                print(f"couldn't get any relevant docs for query {question}")
                return
            # else:
            #     print("--------------------------")
            #     print(question)
            #     print("////////////////////")
            #     print(docs)
            #     print("--------------------------")

            # chat_llm = self.get_chat_model(streaming=True, generator=gen)
            # processing_prompt = self.get_chat_prompt(sys_tpl_name="processing_sys", human_tpl_name="processing_human")
            # chat_llm(processing_prompt.format_prompt(question=question).to_messages())

           
            chain = self.get_chain(method="stuff", streaming=True, generator=gen, temperature=temp)
            chain({"input_documents": docs, "question": question},return_only_outputs=True)
        except Exception as exp:
            print(exp)
        finally:
            gen.close()

    def get_chat_prompt(self, sys_tpl_name: str, human_tpl_name: str) -> ChatPromptTemplate:
        sys_tpl = self.config.tpl(sys_tpl_name)
        human_tpl = self.config.tpl(human_tpl_name)

        sys_msg_prompt = SystemMessagePromptTemplate.from_template(sys_tpl)
        human_msg_prompt = SystemMessagePromptTemplate.from_template(human_tpl)

        return ChatPromptTemplate.from_messages([sys_msg_prompt, human_msg_prompt])
    
    def get_chain(self, method: Union[str, None] = None, streaming: bool = False, generator: Union[ThreadedGenerator, None] = None, temperature: float = 0.7) -> BaseCombineDocumentsChain:
        if method is None:
            method = self.config.method
            
        if method == "stuff":
            return self.get_stuff_chain(streaming, generator, temperature=temperature)
        elif method == "refine":
            return self.get_refine_chain(streaming, generator, temperature=temperature)
        elif method == "reduce":
            return self.get_reduce_chain(streaming, generator, temperature=temperature)
        else:
            raise RuntimeError(f"invalid method {self.config.method}")        

    def get_refine_chain(self, streaming: bool, gen: Union[ThreadedGenerator, None], temperature: float = 0.7) -> BaseCombineDocumentsChain:
        model = self.get_refine_model(streaming, gen,temperature=temperature)
        question_prompt, combine_prompt = self.get_reduce_prompt()

        return load_qa_chain(llm=model, chain_type="map_reduce", return_map_steps=False,
                          question_prompt=question_prompt, combine_prompt=combine_prompt, verbose=False)

    def get_reduce_chain(self, streaming: bool, gen: Union[ThreadedGenerator, None], temperature: float = 0.7) -> BaseCombineDocumentsChain:
        model = self.get_refine_model(streaming, gen, temperature=temperature)
        initial_prompt, refine_prompt = self.get_refine_prompt()

        return load_qa_chain(llm=model, chain_type="refine", return_refine_steps=False,
                          question_prompt=initial_prompt, refine_prompt=refine_prompt, verbose=False)

    def get_stuff_chain(self, streaming: bool, gen: Union[ThreadedGenerator, None], stuff_tpl: str = "", temperature: float = 0.7) -> BaseCombineDocumentsChain:
        model = self.get_stuff_model(streaming, gen, temperature=temperature)
        prompt = self.get_stuff_prompt(stuff_tpl)

        return load_qa_chain(llm=model, chain_type="stuff", prompt=prompt)

    def get_refine_prompt(self, refine_tpl: str = "", initial_tpl: str = "") -> Tuple[PromptTemplate, PromptTemplate]:
        if refine_tpl == "":
            refine_tpl = "refine_prompt"
        
        if initial_tpl == "":
            initial_tpl = "initial_prompt"
        
        refine_prompt_template = self.config.tpl(refine_tpl)
        refine_prompt = PromptTemplate(
            input_variables=["question", "existing_answer", "context_str"],
            template=refine_prompt_template,
        )

        initial_qa_template = self.config.tpl(initial_tpl)
        initial_qa_prompt = PromptTemplate(
            input_variables=["context_str", "question"], template=initial_qa_template
        )

        return initial_qa_prompt, refine_prompt
    
    def get_reduce_prompt(self, summarize_tpl: str = "", combine_tpl: str = "") -> Tuple[PromptTemplate, PromptTemplate]:
        if summarize_tpl == "":
            summarize_tpl = "summarize_prompt"

        if combine_tpl == "":
            combine_tpl = "combine_prompt"

        summarize_prompt_template = self.config.tpl(summarize_tpl)
        question_prompt = PromptTemplate(
            template=summarize_prompt_template, input_variables=[
                "context", "question"]
        )

        combine_prompt_template = self.config.tpl(combine_tpl)
        combine_prompt = PromptTemplate(
            template=combine_prompt_template, input_variables=[
                "summaries", "question"]
        )

        return question_prompt, combine_prompt

    def get_stuff_prompt(self, stuff_tpl: str = "") -> PromptTemplate:
        if stuff_tpl == "":
            stuff_tpl = "stuff_prompt"

        stuff_prompt_template = self.config.tpl(stuff_tpl)
        stuff_prompt = PromptTemplate(
            template=stuff_prompt_template, input_variables=[
                "context", "question"
            ]
        )

        return stuff_prompt

    def get_refine_model(self, streaming: bool, generator: Union[ThreadedGenerator, None], temperature: float = 0.7) -> Union[OpenAI, ChatOpenAI]:
        if self.config.model.startswith("text-davinci"):
            if streaming:
                return OpenAI(openai_api_key= self.config.open_ai_key, streaming=True, callbacks=[ChainStreamHandler(generator)], model= self.config.model, temperature=temperature, max_tokens=1280) # type: ignore
            else:
                return OpenAI(openai_api_key= self.config.open_ai_key, model= self.config.model, temperature=temperature, max_tokens=1280) # type: ignore
        elif self.config.model.startswith("gpt-3.5-turbo"):
            if streaming:
                return ChatOpenAI(openai_api_key= self.config.open_ai_key, streaming=True, callbacks=[ChainStreamHandler(generator)], model= self.config.model, temperature=temperature, max_tokens=1280) # type: ignore
            else:
                return ChatOpenAI(openai_api_key= self.config.open_ai_key, model= self.config.model, temperature=temperature, max_tokens=1280) # type: ignore

        raise RuntimeError("invalid model for refine method")

    def get_reduce_model(self, streaming: bool, generator: Union[ThreadedGenerator, None], temperature: float = 0.7) -> Union[OpenAI, ChatOpenAI]:
        if self.config.model.startswith("text-davinci"):
            if streaming:
                return OpenAI(openai_api_key= self.config.open_ai_key, streaming=True, callbacks=[ChainStreamHandler(generator)], model= self.config.model, temperature=temperature, max_tokens=-1) # type: ignore
            else:     
                return OpenAI(openai_api_key= self.config.open_ai_key, model= self.config.model, temperature=temperature, max_tokens=-1) # type: ignore
        elif self.config.model.startswith("gpt-3.5-turbo"):
            if streaming:
                return ChatOpenAI(openai_api_key= self.config.open_ai_key, streaming=True, callbacks=[ChainStreamHandler(generator)], model= self.config.model, temperature=temperature, max_tokens=None) # type: ignore
            else:
                return ChatOpenAI(openai_api_key= self.config.open_ai_key, model= self.config.model, temperature=temperature, max_tokens=None) # type: ignore
        
        raise RuntimeError("invalid model for reduce method")

    def get_stuff_model(self, streaming: bool, generator: Union[ThreadedGenerator, None], temperature: float = 0.7) -> Union[OpenAI, ChatOpenAI]:
        if self.config.model.startswith("text-davinci"):
            if streaming:
                return OpenAI(openai_api_key= self.config.open_ai_key, streaming=True, callbacks=[ChainStreamHandler(generator)], model= self.config.model, temperature=temperature, max_tokens=-1) # type: ignore
            else:
                return OpenAI(openai_api_key= self.config.open_ai_key, model= self.config.model, temperature=temperature, max_tokens=-1) # type: ignore
                
        elif self.config.model.startswith("gpt-3.5-turbo"):
            if streaming:
                return ChatOpenAI(openai_api_key= self.config.open_ai_key, streaming=True, callbacks=[ChainStreamHandler(generator)], model= self.config.model, temperature=temperature, max_tokens=None) # type: ignore
            else:
                return ChatOpenAI(openai_api_key= self.config.open_ai_key, model= self.config.model, temperature=temperature, max_tokens=None) # type: ignore

        
        raise RuntimeError("invalid model for stuff method")

    def get_chat_model(self, streaming: bool, generator: Union[ThreadedGenerator, None], temperature: float = 0.7) -> ChatOpenAI:
        if self.config.model.startswith("gpt-3.5-turbo"):
            if streaming:
                return ChatOpenAI(openai_api_key= self.config.open_ai_key, streaming=True, callbacks=[ChainStreamHandler(generator)], model= self.config.model, temperature=temperature, max_tokens=None) # type: ignore
            else:
                return ChatOpenAI(openai_api_key= self.config.open_ai_key, model= self.config.model, temperature=temperature, max_tokens=None) # type: ignore

        
        raise RuntimeError("invalid model for reduce method")
