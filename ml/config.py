import os
from typing import Union
# from mysql.connector import connect as mysql_connect, MySQLConnection
# from mysql.connector.pooling import PooledMySQLConnection

from configparser import ConfigParser, SectionProxy


from yaml import load, YAMLError
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


class Config():
    def __init__(self) -> None:
        self.method: str
        self.model: str
        self.top_k: int
        self.open_ai_key: str
        self.chunk_size: int
        self.chunk_overlap: int
        self.persistent_dir: str
        self.tpl_dir: str
        self.default_lang: str
        self.default_temprature: float
        # self.db: Union[MySQLConnection, PooledMySQLConnection]
        self.database_host: str
        self.database_user: str
        self.database_pass: str

    def read(self, path: str) -> str:
        content = ""
        with open(path, "r") as f:
            content = f.read()

        return content

    def tpl(self, name: str) -> str:
        file_path = os.path.join(
            self.tpl_dir, f"{name}.{self.default_lang}.tpl")
        return self.read(file_path)

    @staticmethod
    def load(data: SectionProxy):
        config = Config()

        config.method = data.get("Method", "refine")
        config.model = data.get("Model", "gpt3.5turbo")

        config.open_ai_key = data.get("OpenAIKey", "")

        config.top_k = data.getint("TopK", 1)
        config.chunk_size = data.getint("ChunkSize", 900)
        config.chunk_overlap = data.getint("ChunkOverlap", 100)

        config.persistent_dir = data.get("PersistentDir", "db")

        config.tpl_dir = data.get("TemplatesDir", "prompts")
        config.default_lang = data.get("DefaultLang", "en")
        config.default_temprature = data.getfloat("DefaultTemprature", 0)

        # config.db = mysql_connect(
        #     host= data.get("DatabaseHost"),
        #     user= data.get("DatabaseUser"),
        #     password= data.get("DatabasePassword")
        # )

        return config


def get_config_file_path(script_dir: str) -> str:
    file_name = os.getenv("ml_config_name", "config")
    abs_file_path = os.path.join(script_dir, "configs", f"{file_name}.ini")

    return abs_file_path


def load_config(script_dir: str) -> Config:
    file_path = get_config_file_path(script_dir)
    config = ConfigParser()
    config.read(file_path)

    return Config.load(config["chains.qa"])
