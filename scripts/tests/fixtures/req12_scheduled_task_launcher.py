import os
import sys

from dotenv import dotenv_values
from waitress import serve

env_path, repo, port = sys.argv[1], sys.argv[2], int(sys.argv[3])
os.environ.update({str(k): str(v) for k, v in dotenv_values(env_path).items() if v is not None})
os.chdir(repo)
sys.path.insert(0, repo)
from backend import create_app

serve(create_app(skip_startup=True), host="127.0.0.1", port=port, threads=2)
