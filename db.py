from functools import wraps
import os
from re import I
import jwt

from flask import jsonify, request
import psycopg2

UNAUTHORIZED_CODE = 401


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


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')

        if not token:
            return jsonify({"error": "token em falta"}), UNAUTHORIZED_CODE

        try:
            
            if token.startswith("Bearer "):
                token = token.split(" ")[1]
            
           
            secret = os.getenv('SECRET_KEY', 'mysecretkey')
            
            data = jwt.decode(token, secret, algorithms=["HS256"])
            current_user_id = data["user_id"]
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "token expirado"}), UNAUTHORIZED_CODE
        except Exception as e:
           
            return jsonify({"error": "token inválido", "details": str(e)}), UNAUTHORIZED_CODE

        return f(current_user_id, *args, **kwargs)
    return decorated

