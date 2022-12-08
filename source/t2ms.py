users = set()
chats = set()


def register(username: str, password: str) -> bool:
    pass


def login(username: str, password: str) -> str | bool:
    pass


def create_chat(username: str, password: str, chat_name: str, users: list[str]) -> bool:
    pass


def send_msg(user_token: str, chat_name: str, msg: str) -> bool:
    pass


def recv_msg(user_token: str, chat_name: str) -> list[dict[str:str]] | bool:
    pass


def leave_chat(username: str, password: str, chat_name: str) -> bool:
    pass


def list_users() -> list[str]:
    pass


def list_chats() -> list[str]:
    pass


def stats() -> dict[str : int | float]:
    pass


def main() -> None:
    pass


if __name__ == "__main__":
    main()
