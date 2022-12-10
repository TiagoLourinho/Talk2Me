import sys
import socket
import json
import os
from datetime import datetime
import time
from threading import Thread, Lock

# Hyperparameters
PORT = 9999
LOGGING = True if os.getenv("TALK2ME_LOG") == "on" else False
TERMINAL_WIDTH = os.get_terminal_size().columns

# Multithreading
shutdown = False
lock = Lock()

# Macros
SUCCESS = "Success"
FAILURE = "Failure"


#################### Available functionalities ####################


def register(conn: socket.socket, username: str, password: str) -> None:
    """Sends a `register` request"""

    request = {"operation": "register", "username": username, "password": password}

    answer = send_request(conn, request)

    print_with_format(
        answer["info"], formats=["green"] if answer["rpl"] == SUCCESS else ["red"]
    )


def create_chat(
    conn: socket.socket, username: str, password: str, chat_name: str, users: list[str]
) -> None:
    """Sends a `createchat` request"""

    request = {
        "operation": "createchat",
        "username": username,
        "password": password,
        "chatname": chat_name,
        "users": users,
    }

    answer = send_request(conn, request)

    print_with_format(
        answer["info"], formats=["green"] if answer["rpl"] == SUCCESS else ["red"]
    )


def chat(conn: socket.socket, username: str, password: str, chat_name: str) -> None:
    """Sends a `login` request and then enters chat mode"""

    request = {
        "operation": "login",
        "username": username,
        "password": password,
        "chatname": chat_name,
    }

    answer = send_request(conn, request)

    if answer["rpl"] == SUCCESS:
        token = answer["token"]

        print_with_format("=" * TERMINAL_WIDTH, formats=["blue"])
        print_with_format(f"{chat_name:^{TERMINAL_WIDTH}}", formats=["bold"])
        print_with_format("=" * TERMINAL_WIDTH + "\n", formats=["blue"])

        send_thread = Thread(target=send_new_messages, args=(conn, chat_name, token))
        recv_thread = Thread(
            target=check_fow_new_messages, args=(conn, chat_name, token)
        )

        send_thread.start()
        recv_thread.start()

        send_thread.join()
        recv_thread.join()

    else:
        print_with_format(answer["info"], formats=["red"])


def leave_chat(
    conn: socket.socket, username: str, password: str, chat_name: str
) -> None:
    """Sends a `leavechat` request"""

    request = {
        "operation": "leavechat",
        "username": username,
        "password": password,
        "chatname": chat_name,
    }

    answer = send_request(conn, request)

    print_with_format(
        answer["info"], formats=["green"] if answer["rpl"] == SUCCESS else ["red"]
    )


def list_users(conn: socket.socket) -> None:
    """Sends a `listusers` request"""

    request = {"operation": "listusers"}

    answer = send_request(conn, request)

    if answer["rpl"] == SUCCESS:
        users = answer["users"]

        if len(users):
            print("The registed users are:")
            for user in users:
                print(user)
        else:
            print("There are no users registered yet")
    else:
        print_with_format(answer["info"], formats=["red"])


def list_chats(conn: socket.socket) -> None:
    """Sends a `listchats` request"""

    request = {"operation": "listchats"}

    answer = send_request(conn, request)

    if answer["rpl"] == SUCCESS:
        chats = answer["chats"]

        if len(chats):
            print("The available chats are:")
            for chat in chats:
                print(chat)
        else:
            print("There are no chats created yet")
    else:
        print_with_format(answer["info"], formats=["red"])


def stats(conn: socket.socket) -> None:
    """Sends a `stats` request"""

    request = {"operation": "stats"}

    answer = send_request(conn, request)

    if answer["rpl"] == SUCCESS:
        print(
            f"Talk2Me currently has "
            f'{answer["stats"]["number_of_users"]} users, '
            f'{answer["stats"]["number_of_chats"]} chats, '
            f'{answer["stats"]["number_of_sent_messages"]} sent messages '
            f'and an average operation latency of {round(float(answer["stats"]["average_operation_latency"])*1000,1)} ms'
        )

    else:
        print_with_format(answer["info"], formats=["red"])


#################### Server interaction ####################


def send_request(conn: socket.socket, request: object) -> object:
    """Sends a request to the server and returns the answer"""

    request = json.dumps(request)

    log(request, sent=True)

    conn.sendall(bytes(request + "\r\n", "utf-8"))

    answer = wait_for_server_answer(conn)

    answer = json.loads(answer)

    return answer


def wait_for_server_answer(conn: socket.socket) -> str:
    """Waits for an answer from the server and returns it"""

    data = ""
    while True:
        data += conn.recv(4096).decode("utf-8")

        # Check if message is complete
        if "\r\n" in data:
            data = data.strip()

            log(data, sent=False)

            return data


#################### Thread methods ####################


def send_new_messages(conn: socket.socket, chat_name: str, token: str) -> None:
    """While in chat mode, sends new messages written by the user to the chat"""

    MOVE_UP = "\033[1A"
    DELETE_LINE = "\033[K"

    global shutdown
    while not shutdown:
        message = input("")

        print(MOVE_UP + DELETE_LINE)

        # Leave chat mode
        if message.strip() == "exit":
            shutdown = True
            return

        print_with_format(message, formats=["bold"])
        print_with_format(
            datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n", formats=["dark grey"]
        )

        request = {
            "operation": "sendmsg",
            "token": token,
            "chatname": chat_name,
            "msg": message,
        }

        with lock:
            answer = send_request(conn, request)

        if answer["rpl"] == FAILURE:
            print_with_format(answer["info"], formats=["red"])
            shutdown = True
            return


def check_fow_new_messages(conn: socket.socket, chat_name: str, token: str) -> None:
    """While in chat mode, checks for new messages written by others users in the chat"""

    global shutdown
    while not shutdown:
        time.sleep(0.1)

        request = {"operation": "recvmsg", "token": token, "chatname": chat_name}

        with lock:
            answer = send_request(conn, request)

        if answer["rpl"] == SUCCESS:

            # Print other users messages
            for message in answer["messages"]:
                print_with_format(
                    f'{message["msg"]:>{TERMINAL_WIDTH}}', formats=["bold"]
                )
                print_with_format(
                    f'{message["sender"]:>{TERMINAL_WIDTH}}', formats=["light grey"]
                )
                print_with_format(
                    f'{message["time"]:>{TERMINAL_WIDTH}}' + "\n",
                    formats=["dark grey"],
                )

        else:
            print_with_format(answer["info"], formats=["red"])
            shutdown = True
            return


#################### Utilities ####################


def log(string: str, sent: bool) -> None:
    """Logs the request sent or the answer received"""

    if LOGGING:
        now = datetime.now()
        now = now.strftime("%Y-%m-%d %H:%M:%S")
        print_with_format(f"[{now}]: {string}", formats=["cyan"] if sent else ["blue"])


def print_with_format(string: str, formats: str = [], end="\n"):
    """Normal print statement but with colors"""

    CYAN = "\033[96m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    LIGHTGREY = "\033[37m"
    DARKGREY = "\033[90m"
    BOLD = "\033[01m"
    UNDERLINE = "\033[04m"
    RESET = "\033[0m"

    final_format = ""
    for f in formats:
        match f.lower().strip():
            case "cyan":
                final_format += CYAN
            case "blue":
                final_format += BLUE
            case "green":
                final_format += GREEN
            case "red":
                final_format += RED
            case "dark grey":
                final_format += DARKGREY
            case "light grey":
                final_format += LIGHTGREY
            case "bold":
                final_format += BOLD
            case "underline":
                final_format += UNDERLINE
            case _:
                pass

    print(final_format + string + RESET, end=end)


def check_invocation() -> bool:
    """Check if the invocation of the program was valid"""

    try:
        host = sys.argv[1]
    except IndexError:
        print_with_format("Server address wasn't provided", formats=["red"])
        return False

    try:
        socket.inet_aton(host)
    except OSError:
        print_with_format("Server address isn't valid", formats=["red"])
        return False

    try:
        operation = sys.argv[2]
    except IndexError:
        print_with_format("Desired operation wasn't provided", formats=["red"])
        return False

    match operation:
        case "register":
            if len(sys.argv) != 5:
                print_with_format("Invalid number of arguments", formats=["red"])
                return False
        case "createchat":
            if len(sys.argv) < 5:
                print_with_format("Too few arguments", formats=["red"])
                return False
        case "chat":
            if len(sys.argv) != 6:
                print_with_format("Invalid number of arguments", formats=["red"])
                return False
        case "leavechat":
            if len(sys.argv) != 6:
                print_with_format("Invalid number of arguments", formats=["red"])
                return False
        case "listusers":
            if len(sys.argv) != 3:
                print_with_format("Invalid number of arguments", formats=["red"])
                return False
        case "listchats":
            if len(sys.argv) != 3:
                print_with_format("Invalid number of arguments", formats=["red"])
                return False
        case "stats":
            if len(sys.argv) != 3:
                print_with_format("Invalid number of arguments", formats=["red"])
                return False
        case _:
            print_with_format("Invalid operation", formats=["red"])
            return False

    return True


def print_client_usage() -> None:
    """Prints the usage of the program"""

    print_with_format("\nTalk2Me client correct usage:", formats=["bold"])
    print("- python t2mc.py <server address> register <username> <password>")
    print(
        "- python t2mc.py <server address> createchat <username> <password> <username1>, ..., <usernameN>"
    )
    print("- python t2mc.py <server address> chat <username> <password> <chatname>")
    print(
        "- python t2mc.py <server address> leavechat <username> <password> <chatname>"
    )
    print("- python t2mc.py <server address> listusers")
    print("- python t2mc.py <server address> listchats")
    print("- python t2mc.py <server address> stats")


#################### Main ####################


def main() -> None:

    if not check_invocation():
        print_client_usage()
        return

    host = sys.argv[1]
    operation = sys.argv[2]

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:
        try:
            conn.connect((host, PORT))
        except ConnectionRefusedError:
            print_with_format("Couldn't connect to the server", formats=["red"])
            return

        match operation:
            case "register":
                register(conn, sys.argv[3], sys.argv[4])
            case "createchat":
                create_chat(
                    conn,
                    sys.argv[3],
                    sys.argv[4],
                    sys.argv[5],
                    [sys.argv[i] for i in range(6, len(sys.argv))],
                )
            case "chat":
                chat(conn, sys.argv[3], sys.argv[4], sys.argv[5])
            case "leavechat":
                leave_chat(conn, sys.argv[3], sys.argv[4], sys.argv[5])
            case "listusers":
                list_users(conn)
            case "listchats":
                list_chats(conn)
            case "stats":
                stats(conn)


if __name__ == "__main__":
    main()
