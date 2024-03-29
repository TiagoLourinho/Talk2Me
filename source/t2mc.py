import sys
import socket
import json
from datetime import datetime
import time
from threading import Thread, Lock
from cryptography.fernet import Fernet

from config import *

SESSION_ENCRYPTION_KEY = None
############################## Available functionalities ##############################


def register(conn: socket.socket, username: str, password: str) -> None:
    """Sends a `register` request"""

    request = {"operation": "register", "username": username, "password": password}

    answer = send_request(conn, request)

    # Lost connection to the server
    if not answer:
        print_with_format("Lost connection to the server", formats=["red"])
        return

    print_with_format(
        answer["feedback"], formats=["green"] if answer["rpl"] == SUCCESS else ["red"]
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

    # Lost connection to the server
    if not answer:
        print_with_format("Lost connection to the server", formats=["red"])
        return

    print_with_format(
        answer["feedback"], formats=["green"] if answer["rpl"] == SUCCESS else ["red"]
    )


def chat(conn: socket.socket, username: str, password: str, chat_name: str) -> None:
    """Sends a `login` request and then enters chat mode"""

    terminal_width = os.get_terminal_size().columns

    request = {
        "operation": "login",
        "username": username,
        "password": password,
        "chatname": chat_name,
    }

    answer = send_request(conn, request)

    # Lost connection to the server
    if not answer:
        print_with_format("Lost connection to the server", formats=["red"])
        return

    if answer["rpl"] == SUCCESS:
        token = answer["token"]

        global SESSION_ENCRYPTION_KEY
        SESSION_ENCRYPTION_KEY = answer["encryption_key"]

        # Chat header
        print_with_format("=" * terminal_width, formats=["blue"])
        print_with_format(f"{chat_name:^{terminal_width}}", formats=["bold"])
        print_with_format("=" * terminal_width + "\n", formats=["blue"])

        # Print old messages
        for msg in answer["messages"]:
            if msg["sender"] != username:
                print_with_format(f'{msg["msg"]:>{terminal_width}}', formats=["bold"])
                print_with_format(
                    f'{msg["sender"]:>{terminal_width}}', formats=["light grey"]
                )
                print_with_format(
                    f'{msg["time"]:>{terminal_width}}' + "\n",
                    formats=["dark grey"],
                )
            else:
                print_with_format(msg["msg"], formats=["bold"])
                print_with_format(msg["time"] + "\n", formats=["dark grey"])

        # Start threads to receive and send the messages

        send_thread = Thread(target=send_new_messages, args=(conn, chat_name, token))
        recv_thread = Thread(
            target=check_fow_new_messages, args=(conn, chat_name, token)
        )

        send_thread.start()
        recv_thread.start()

        try:
            send_thread.join()
            recv_thread.join()

        except KeyboardInterrupt:
            global thread_shutdown
            thread_shutdown = True
            send_thread.join()
            recv_thread.join()
            return

    # Redirect to other server
    elif answer.get("redirect") is not None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as new_conn:
            try:
                new_conn.connect((answer["redirect"], PORT))
            except ConnectionRefusedError:
                print_with_format("Couldn't connect to the server", formats=["red"])
                return

            chat(new_conn, username, password, chat_name)
    else:
        print_with_format(answer["feedback"], formats=["red"])


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

    # Lost connection to the server
    if not answer:
        print_with_format("Lost connection to the server", formats=["red"])
        return

    print_with_format(
        answer["feedback"], formats=["green"] if answer["rpl"] == SUCCESS else ["red"]
    )


def list_users(conn: socket.socket) -> None:
    """Sends a `listusers` request"""

    request = {"operation": "listusers"}

    answer = send_request(conn, request)

    # Lost connection to the server
    if not answer:
        print_with_format("Lost connection to the server", formats=["red"])
        return

    if answer["rpl"] == SUCCESS:
        users = answer["users"]

        if len(users):
            print("The registed users are:\n")
            for user in users:
                print("- " + user)
        else:
            print("There are no users registered yet")
    else:
        print_with_format(answer["feedback"], formats=["red"])


def list_chats(conn: socket.socket) -> None:
    """Sends a `listchats` request"""

    request = {"operation": "listchats"}

    answer = send_request(conn, request)

    # Lost connection to the server
    if not answer:
        print_with_format("Lost connection to the server", formats=["red"])
        return

    if answer["rpl"] == SUCCESS:
        chats = answer["chats"]

        if len(chats):
            print("The available chats are:\n")
            for chat in chats:
                print("- " + chat)
        else:
            print("There are no chats created yet")
    else:
        print_with_format(answer["feedback"], formats=["red"])


def stats(conn: socket.socket) -> None:
    """Sends a `stats` request"""

    request = {"operation": "stats"}

    answer = send_request(conn, request)

    # Lost connection to the server
    if not answer:
        print_with_format("Lost connection to the server", formats=["red"])
        return

    if answer["rpl"] == SUCCESS:
        print(
            f"Talk2Me currently has "
            f'{answer["stats"]["number_of_users"]} users, '
            f'{answer["stats"]["number_of_chats"]} chats, '
            f'{answer["stats"]["number_of_sent_messages"]} sent messages '
            f'and an average operation latency of {round(float(answer["stats"]["average_operation_latency"])*1000,1)} ms'
        )

    else:
        print_with_format(answer["feedback"], formats=["red"])


############################## Thread methods ##############################


def send_new_messages(conn: socket.socket, chat_name: str, token: str) -> None:
    """While in chat mode, sends new messages written by the user to the chat"""

    MOVE_UP = "\033[1A"

    global thread_shutdown
    while not thread_shutdown:
        message = input("")

        if thread_shutdown:
            return

        print(MOVE_UP, end="\r")

        # Leave chat mode
        if message.strip() == "exit":
            thread_shutdown = True
            return

        # Print sent message
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

        # Lost connection to the server
        if not answer:
            print_with_format("Lost connection to the server", formats=["red"])
            thread_shutdown = True
            return

        if answer["rpl"] == FAILURE:
            print_with_format(answer["feedback"], formats=["red"])
            thread_shutdown = True
            return


def check_fow_new_messages(conn: socket.socket, chat_name: str, token: str) -> None:
    """While in chat mode, checks for new messages written by others users in the chat"""

    terminal_width = os.get_terminal_size().columns

    global thread_shutdown
    while not thread_shutdown:
        time.sleep(0.1)

        if thread_shutdown:
            return

        request = {"operation": "recvmsg", "token": token, "chatname": chat_name}

        with lock:
            answer = send_request(conn, request)

        # Lost connection to the server
        if not answer:
            print_with_format("Lost connection to the server", formats=["red"])
            thread_shutdown = True
            return

        if answer["rpl"] == SUCCESS:

            # To handle the case where the user receives a message while is writing
            if answer["messages"]:
                print(end="\r")

            # Print other users messages
            for message in answer["messages"]:
                print_with_format(
                    f'{message["msg"]:>{terminal_width}}', formats=["bold"]
                )
                print_with_format(
                    f'{message["sender"]:>{terminal_width}}', formats=["light grey"]
                )
                print_with_format(
                    f'{message["time"]:>{terminal_width}}' + "\n",
                    formats=["dark grey"],
                )

        else:
            print_with_format(answer["feedback"], formats=["red"])
            thread_shutdown = True
            return


############################## Server interaction ##############################


def send_request(conn: socket.socket, request: object) -> object | bool:
    """Sends a request to the server and returns the answer"""

    fernet = Fernet(
        SESSION_ENCRYPTION_KEY
        if SESSION_ENCRYPTION_KEY is not None
        else BASE_ENCRYPTION_KEY
    )
    request = json.dumps(request)

    log(request, sent=True)

    request = fernet.encrypt(request.encode()).decode()

    conn.sendall((request + "\r\n").encode())

    return wait_for_server_answer(conn)


def wait_for_server_answer(conn: socket.socket) -> object | bool:
    """Waits for an answer from the server and returns it"""

    fernet = Fernet(
        SESSION_ENCRYPTION_KEY
        if SESSION_ENCRYPTION_KEY is not None
        else BASE_ENCRYPTION_KEY
    )

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

            log(answer, sent=False)

            return json.loads(answer)


############################## Utilities ##############################


def log(string: str, sent: bool) -> None:
    """Logs the request receibev or the answer sent"""

    BLUE = "\033[94m"
    CYAN = "\033[96m"
    RESET = "\033[0m"

    if LOGGING:
        now = datetime.now()
        now = now.strftime("%Y-%m-%d %H:%M:%S")

        format = CYAN if sent else BLUE

        print(format + f'[{now}][{"SENT" if sent else "RECEIVED"}]: {string}' + RESET)


def print_with_format(string: str, formats: str = [], end="\n") -> None:
    """Normal print statement but with colors and others formats"""

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
            if len(sys.argv) < 6:
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
        "- python t2mc.py <server address> createchat <username> <password> <chatname> <username1>, ..., <usernameN>"
    )
    print("- python t2mc.py <server address> chat <username> <password> <chatname>")
    print(
        "- python t2mc.py <server address> leavechat <username> <password> <chatname>"
    )
    print("- python t2mc.py <server address> listusers")
    print("- python t2mc.py <server address> listchats")
    print("- python t2mc.py <server address> stats")


############################## Main ##############################


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

    thread_shutdown = False
    lock = Lock()

    main()
