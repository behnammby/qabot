import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "ml"))

from ml.config import load_config
from ml.vectordb import VectorDB

if __name__ == "__main__":
    config = load_config(os.path.dirname(__file__))
    
    db = VectorDB(config)

    size = db.size()
    print(f"total docs in index= {size}")