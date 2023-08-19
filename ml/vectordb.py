from langchain.document_loaders import UnstructuredWordDocumentLoader, UnstructuredHTMLLoader, DirectoryLoader, CSVLoader ,UnstructuredFileLoader
from langchain.text_splitter import CharacterTextSplitter,RecursiveCharacterTextSplitter
from langchain.vectorstores.chroma import Chroma
from langchain.schema import Document
from langchain.embeddings import OpenAIEmbeddings
from config import Config
from typing import List, Tuple
import logging
import time

class VectorDB:
    def __init__(self, config: Config) -> None:
        self.config = config

        embedding = OpenAIEmbeddings(openai_api_key=self.config.open_ai_key) #type: ignore
        persistent_dir = self.config.persistent_dir

        self.db: Chroma = Chroma(persist_directory=persistent_dir, embedding_function=embedding)

    def add_documents(self, dir: str) -> None:
        logging.info("defining a new unstructured loader...")
        loader = DirectoryLoader(dir, loader_cls=UnstructuredWordDocumentLoader) #, loader_kwargs={"mode": "elements"})

        logging.info("loading documents...")
        docs = loader.load()
        
        logging.info(f"{len(docs)} docs loaded.")

        self.embed_docs(docs=docs)
    def add_any_documents(self,dir:str) -> None:
        logging.info("defining a new Unstructured File Loader...")
        loader = DirectoryLoader(dir , loader_cls=UnstructuredFileLoader)

        logging.info("loading documents...")
        docs = loader.load()
        logging.info(f"{len(docs)} docs loaded.")
        self.embed_docs(docs=docs)

        
    def add_csv(self, dir: str) -> None:
        logging.info("defining a new csv loader...")
        loader = CSVLoader(file_path=dir)
        
        logging.info("loading documents...")
        docs = loader.load()

        logging.info(f"{len(docs)} docs loaded.")

        self.embed_docs(docs=docs)

    def add_html(self, dir: str) -> None:
        logging.info("defining html loader")
        loader = DirectoryLoader(dir, glob="**/*.html", loader_cls=UnstructuredHTMLLoader)

        docs = loader.load()

        logging.info(f"{len(docs)} docs loaded.")

        self.embed_docs(docs=docs)
        
    def embed_docs(self, docs: List[Document]):
        logging.info(r"splitting....")
        splitter = RecursiveCharacterTextSplitter(chunk_size=self.config.chunk_size, chunk_overlap=self.config.chunk_overlap)
        docs = splitter.split_documents(documents=docs)

        logging.info(f"now we have {len(docs)} docs")
        logging.info(docs[:5])

        logging.info("adding documents to index...")
        
        batch_size=1000
        start_index=0
        end_index=0
        while start_index < len(docs):
            end_index= min(start_index + batch_size, len(docs))
            
            logging.info(f"adding from {start_index} to {end_index}")

            d = docs[start_index:end_index]
            self.db.add_documents(d)

            start_index = end_index

            logging.info("sleeping 60 seconds...")
            time.sleep(60)
        # self.db.add_documents(docs)

        logging.info(f"persisting to {self.config.persistent_dir}...")
        self.db.persist()

    def size(self) -> int:
        output = self.db.get().get("documents")
        return len(output) #type: ignore

    def delete_index(self):
        self.db.delete_collection()
        
    def get_relevant_docs(self, query: str) -> List[Document]:
        retriever = self.db.as_retriever(search_kwargs={"k": self.config.top_k})

        return retriever.get_relevant_documents(query=query)

    def get_similar_docs(self, query: str) -> List[Tuple[Document, float]]:
        docs = self.db.similarity_search_with_score(query)

        return docs

