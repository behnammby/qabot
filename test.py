import os
import sys
import json
import logging
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

ans = qa.answer("چطوری میتونم سرویس انتقال مکالمه رو غیر فعال کنم؟")
print(ans)