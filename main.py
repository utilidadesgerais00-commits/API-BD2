import json
import os
from datetime import datetime, timedelta
from functools import wraps

import bcrypt
import jwt
import psycopg2
from dotenv import load_dotenv
from flask import Flask, jsonify, request

from db import get_connection, token_required

load_dotenv('.env.local')

app = Flask(__name__)
app.debug = True
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'mysecretkey')

NOT_FOUND_CODE = 401
OK_CODE = 200
SUCCESS_CODE = 201
NO_CONTENT_CODE = 204
BAD_REQUEST_CODE = 400
UNAUTHORIZED_CODE = 401
FORBIDDEN_CODE = 403
NOT_FOUND = 404
SERVER_ERROR = 500

@app.route("/")
def home():
    return jsonify({"message": "VoltExchange API online"})


# REGISTER

@app.route("/register", methods=['POST'])
def register():
    data = request.get_json()

    if "nome" not in data or "email" not in data or "password" not in data:
        return jsonify({"error": "invalid parameters"}), BAD_REQUEST_CODE

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM Utilizadores WHERE Email = %s", (data["email"],))
    if cur.fetchone():
        return jsonify({"error": "user already exists"}), BAD_REQUEST_CODE

    hashed = bcrypt.hashpw(
        data["password"].encode(),
        bcrypt.gensalt()
    ).decode()

    cur.execute("""
        INSERT INTO Utilizadores (Nome, Email, PasswordHash, Saldo)
        VALUES (%s, %s, %s, %s)
        RETURNING UtilizadorID, Nome, Email
    """, (data["nome"], data["email"], hashed, 0))

    user = cur.fetchone()
    conn.commit()

    return jsonify({
        "utilizadorid": user[0],
        "nome": user[1],
        "email": user[2]
    }), SUCCESS_CODE



# LOGIN

@app.route("/login", methods=['POST'])
def login():
    data = request.get_json()

    if "email" not in data or "password" not in data:
        return jsonify({"error": "invalid parameters"}), BAD_REQUEST_CODE

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT UtilizadorID, PasswordHash
        FROM Utilizadores
        WHERE Email = %s
    """, (data["email"],))

    user = cur.fetchone()

    if not user:
        return jsonify({"error": "user not found"}), NOT_FOUND_CODE

    if not bcrypt.checkpw(
        data["password"].encode(),
        user[1].encode()
    ):
        return jsonify({"error": "invalid password"}), UNAUTHORIZED_CODE


    token = jwt.encode(
        {
         "user_id": user[0],
         "exp": datetime.utcnow() + timedelta(hours=24)
        },
        app.config['SECRET_KEY'],
        algorithm="HS256"
    )

    return jsonify({"message": "login ok", "token": token}), SUCCESS_CODE   


# LEITURAS (JSONB)

@app.route("/meters/readings", methods=['POST'])
def add_reading():
    data = request.get_json()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO Leituras (ContadorID, DataHora, KWh_Leitura, DadosAudit)
        VALUES (%s, NOW(), %s, %s)
    """, (
        data["contador_id"],
        data["kwh"],
        json.dumps(data["dados_audit"])
    ))

    conn.commit()

    return jsonify({"message": "reading inserted"}), SUCCESS_CODE



# MARKET BUY (SP ACID)

@app.route("/market/buy", methods=['POST'])
@token_required
def buy(current_user_id):
    data = request.get_json()

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            CALL sp_ExecutarCompraDireta(%s, %s)
        """, (
            data["oferta_id"],
            current_user_id  # vem do token, não do body
        ))

        conn.commit()
        return jsonify({"message": "purchase executed"}), SUCCESS_CODE
    except psycopg2.errors.RaiseException as e:
        return jsonify({"error": str(e)}), BAD_REQUEST_CODE
    except (Exception, psycopg2.Error) as e:
        return jsonify({"error": str(e)}), SERVER_ERROR


# MATCH ENGINE

@app.route("/market/match", methods=['POST'])
def match():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("CALL sp_MatchingEngine()")

    conn.commit()

    return jsonify({"message": "matching executed"}), SUCCESS_CODE



# ANOMALIAS JSONB

@app.route("/admin/anomalies", methods=['GET'])
def anomalies():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT ContadorID, DataHora, KWh_Leitura, DadosAudit
        FROM Leituras
        WHERE 
            (DadosAudit->>'temperatura')::numeric > 80
            OR (DadosAudit->>'erro_codigo') IS NOT NULL
    """)
    
    rows = cur.fetchall()
    result = []
    for r in rows:
        result.append({
            "contador_id": r[0],
            "data_hora": r[1].isoformat() if r[1] else None,
            "kwh": float(r[2]),
            "dados_audit": r[3]
        })

    return jsonify(result), OK_CODE



# RUN SERVER
#if __name__ == "__main__":
#   app.run()


