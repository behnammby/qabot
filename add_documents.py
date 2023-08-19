import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "ml"))

from ml.config import load_config
from ml.vectordb import VectorDB

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("docs path not passed")

        exit(1)

    doc_path = sys.argv[1]
    config = load_config(os.path.dirname(__file__))
    
    db = VectorDB(config)

    db.add_any_documents(doc_path)