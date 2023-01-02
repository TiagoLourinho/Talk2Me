import os

# Common
PORT = 9999
LOGGING = True if os.getenv("TALK2ME_LOG") == "on" else False
BASE_ENCRYPTION_KEY = "Ms_I0iVjanNosloNcbssrsCk-7MxGSQZNt5_C8UT66E="
SUCCESS = "Success"
FAILURE = "Failure"

# Server
MAX_THREADS = 10  # Number of threads
SOCKET_TIMEOUT = 1  # seconds
CHAT_SERVERS = []
