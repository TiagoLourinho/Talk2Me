import socket
import json
from cryptography.fernet import Fernet
import random
import string
import time
from threading import Thread
import sys

PORT = 9999
N_USERS = 10
MESSAGES_LENGTH = 1000000

BASE_ENCRYPTION_KEY = "Ms_I0iVjanNosloNcbssrsCk-7MxGSQZNt5_C8UT66E="

thread_shutdown = False


def send_request(
    conn: socket.socket, request: object, key=BASE_ENCRYPTION_KEY
) -> object | bool:
    """Sends a request to the server and returns the answer"""

    fernet = Fernet(key)
    request = json.dumps(request)

    request = fernet.encrypt(request.encode()).decode()

    conn.sendall((request + "\r\n").encode())

    return wait_for_server_answer(conn, key)


def wait_for_server_answer(
    conn: socket.socket, key=BASE_ENCRYPTION_KEY
) -> object | bool:
    """Waits for an answer from the server and returns it"""

    fernet = Fernet(key)

    answer = ""
    while True:
        answer += conn.recv(4096).decode()

        # Connection was closed
        if not answer:
            return False

        # Check if message is complete
        if "\r\n" in answer:
            answer = answer.strip()

            answer = fernet.decrypt(answer.encode()).decode()

            return json.loads(answer)


def get_random_string(length):
    """Generates a random string"""

    return "".join(
        [random.choice(string.ascii_letters + string.digits) for _ in range(length)]
    )


def spam(host, user, chatname):
    """Function to run in a thread, sending messages to the server"""

    global thread_shutdown
    global MESSAGES_LENGTH
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:
        conn.connect((host, PORT))

        # Login
        request = {
            "operation": "login",
            "username": user["username"],
            "password": user["password"],
            "chatname": chatname,
        }
        answer = send_request(conn, request)
        user["token"] = answer["token"]
        user["key"] = answer["encryption_key"]
        message = get_random_string(MESSAGES_LENGTH)
        # Send messages
        while not thread_shutdown:
            try:
                request = {
                    "operation": "sendmsg",
                    "token": user["token"],
                    "chatname": chatname,
                    "msg": message,
                }
                answer = send_request(conn, request, user["key"])

            except Exception as e:
                print(e)
                thread_shutdown = True


def main(host, spam_time):

    global thread_shutdown

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:

        conn.connect((host, PORT))

        print(f"Press CTRL+C to stop spam or wait {spam_time}s")
        print(
            f"{N_USERS} users sending messages ininterruptly with {MESSAGES_LENGTH} characters each"
        )

        chatname = get_random_string(20)

        users = []

        # Generate random users
        for _ in range(N_USERS):
            random_name = get_random_string(20)
            random_pass = get_random_string(10)
            users.append(
                {
                    "username": random_name,
                    "password": random_pass,
                    "token": None,
                    "key": None,
                }
            )

        # Register
        for user in users:
            request = {
                "operation": "register",
                "username": user["username"],
                "password": user["password"],
            }

            send_request(conn, request)

        # Create chat
        request = {
            "operation": "createchat",
            "username": users[-1]["username"],
            "password": users[-1]["password"],
            "chatname": chatname,
            "users": [user["username"] for user in users],
        }

        send_request(conn, request)

        threads = [Thread(target=spam, args=(host, user, chatname)) for user in users]

        for t in threads:
            t.start()

        start = time.time()

        # Start spam
        try:
            while True:
                if time.time() - start > spam_time:
                    thread_shutdown = True
                    break
        except KeyboardInterrupt:
            thread_shutdown = True

        for t in threads:
            t.join()


if __name__ == "__main__":
    try:
        main(sys.argv[1], int(sys.argv[2]))
    except IndexError:
        print("Usage:")
        print(f"- python3 {sys.argv[0]} <server IP> <seconds to spam>")
