import os
import logging
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "ml"))

from ml.config import load_config
from ml.vectordb import VectorDB


root = logging.getLogger()
root.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("no input dir passed")

        exit(1)

    input = sys.argv[1]

    config = load_config(os.path.dirname(__file__))

    db = VectorDB(config)
    db.add_html(input)

    