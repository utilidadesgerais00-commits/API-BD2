import os
from re import I

import psycopg2


def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "aid.estgoh.ipc.pt"),
        database=os.getenv("DB_NAME", "db2021153931"),
        user=os.getenv("DB_USER", "a2021153931"),
        password=os.getenv("DB_PASSWORD")
    )

def user_exists(user):
    count = 0
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM utilizadores WHERE nome = %s", [user["nome"]])
                count = cur.fetchone()[0]
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL", error)
    return count > 0


def login(nome, passwordhash):
    user = None
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM utilizadores WHERE nome = %s AND password = crypt(%s, passwordhash)", [nome, passwordhash])
                user_tuple = cur.fetchone()
                if user_tuple is not None:
                    user = {
                        "utilizadorid": user_tuple[0],
                        "nome": user_tuple[1],
                        "email": user_tuple[2],
                        "passwordhash": user_tuple[3]
                    }
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL", error)
    return user

