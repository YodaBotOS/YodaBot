import datetime
import hashlib
import json
import os
import shutil
import time
from urllib.parse import urlencode

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36"
# SP_DC = os.getenv('SP_DC') if os.getenv('SP_DC') else keys.get_sp_dc()
# SP_KEY = os.getenv('SP_KEY') if os.getenv('SP_KEY') else keys.get_sp_key()
# PROXY = {"http": "127.0.0.1:8080", "https": "127.0.0.1:8080"}
# PROXY = {}
VERIFY_SSL = True
