import random
from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3, qrcode, os

app = Flask(__name__)
app.secret_key = "chave_secreta"  # necessário para usar sessão
DB_NAME = "quiz.db"

# ---------------------
# BANCO
# ---------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS perguntas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        texto TEXT NOT NULL,
        op1 TEXT NOT NULL,
        op2 TEXT NOT NULL,
        op3 TEXT NOT NULL,
        op4 TEXT NOT NULL,
        resposta TEXT NOT NULL
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS resultados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        score INTEGER NOT NULL,
        total INTEGER NOT NULL,
        data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()


def get_pergunta(id_pergunta):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM perguntas WHERE id=?", (id_pergunta,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "texto": row[1],
            "opcoes": [row[2], row[3], row[4], row[5]],
            "resposta": row[6]
        }
    return None

def get_total_perguntas():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM perguntas")
    total = cur.fetchone()[0]
    conn.close()
    return total

def get_all_ids():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id FROM perguntas")
    ids = [row[0] for row in cur.fetchall()]
    conn.close()
    return ids

# ---------------------
# QUIZ
# ---------------------
@app.route("/quiz/<int:num>", methods=["GET", "POST"])
def quiz(num):
    total = get_total_perguntas()

    # primeira pergunta → gerar ordem aleatória e limpar sessão
    if num == 1:
        ids = get_all_ids()
        random.shuffle(ids)
        session["ordem"] = ids
        session["score"] = 0
        session["respostas"] = []  # guarda histórico

    ordem = session.get("ordem", [])
    if num > len(ordem):
        return "Erro: pergunta fora da ordem.", 400

    pergunta = get_pergunta(ordem[num-1])
    if not pergunta:
        return "Pergunta não encontrada!", 404

    # embaralhar alternativas
    opcoes = pergunta["opcoes"][:]
    random.shuffle(opcoes)

    if request.method == "POST":
        resposta = request.form.get("resposta")
        correta = pergunta["resposta"]

        # salva no histórico
        session["respostas"].append({
            "pergunta": pergunta["texto"],
            "resposta_usuario": resposta,
            "resposta_correta": correta,
            "acertou": resposta == correta
        })

        if resposta == correta:
            session["score"] += 1

        if num < total:
            return redirect(url_for("quiz", num=num+1))
        else:
            return redirect(url_for("resultado_quiz", total=total))

    return render_template("quiz_passo.html", pergunta=pergunta, opcoes=opcoes, num=num, total=total)


@app.route("/admin/ranking")
def ranking():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT nome, score, total, data FROM resultados ORDER BY score DESC, data ASC")
    ranking = cur.fetchall()
    conn.close()
    return render_template("ranking.html", ranking=ranking)


@app.route("/quiz/start", methods=["GET", "POST"])
def quiz_start():
    if request.method == "POST":
        nome = request.form.get("nome")
        if not nome:
            return "Por favor, digite seu nome.", 400
        session["nome"] = nome
        return redirect(url_for("quiz", num=1))
    return render_template("quiz_start.html")


# ---------------------
# QR CODE ÚNICO
# ---------------------
@app.route("/admin/qrcode")
def admin_qrcode():
    pasta = os.path.join("static", "qrcodes")
    os.makedirs(pasta, exist_ok=True)
    link = "http://127.0.0.1:5000/quiz/start"
    img = qrcode.make(link)
    caminho = os.path.join(pasta, "quiz.png")
    img.save(caminho)
    return render_template("qrcode.html", caminho="qrcodes/quiz.png")


# ---------------------
# ADMIN
# ---------------------
@app.route("/")
def home():
    # redireciona para o painel do admin
    return redirect(url_for("admin"))

@app.route("/admin")
def admin():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM perguntas")
    perguntas = cur.fetchall()
    conn.close()
    return render_template("admin.html", perguntas=perguntas)


@app.route("/resultado_quiz/<int:total>")
def resultado_quiz(total):
    score = session.get("score", 0)
    respostas = session.get("respostas", [])
    nome = session.get("nome", "Participante")

    # Salvar no ranking
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("INSERT INTO resultados (nome, score, total) VALUES (?, ?, ?)",
                (nome, score, total))
    conn.commit()
    conn.close()

    return render_template("resultado_quiz.html", score=score, total=total, respostas=respostas, nome=nome)


@app.route("/admin/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        texto = request.form["texto"]
        op1 = request.form["op1"]
        op2 = request.form["op2"]
        op3 = request.form["op3"]
        op4 = request.form["op4"]
        resposta = request.form["resposta"]

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("INSERT INTO perguntas (texto, op1, op2, op3, op4, resposta) VALUES (?, ?, ?, ?, ?, ?)",
                    (texto, op1, op2, op3, op4, resposta))
        conn.commit()
        conn.close()

        return redirect(url_for("admin"))
    return render_template("add.html")

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
