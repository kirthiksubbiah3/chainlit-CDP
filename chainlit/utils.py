import chainlit as cl


def get_username(user: cl.PersistedUser) -> str:
    username = "there"
    if user.display_name is not None:
        username = user.display_name.title()
    return username
