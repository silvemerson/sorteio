import sqlite3
import random
import os
import re
import qrcode
import base64
from io import BytesIO
from functools import wraps
from flask import Flask, render_template, request, jsonify, g, session, redirect, url_for, send_from_directory

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-sorteio-key')
DATABASE = 'sorteio.db'

ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('ADMIN_PASS', 'admin123')
EVENTOS = ['dougbrazil', 'cncf']


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS participantes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT NOT NULL,
                evento TEXT NOT NULL,
                consentimento INTEGER NOT NULL DEFAULT 1,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(email, evento)
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS sorteados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                participante_id INTEGER,
                evento TEXT NOT NULL,
                sorteado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(participante_id) REFERENCES participantes(id)
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS sorteios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                descricao TEXT DEFAULT '',
                evento TEXT NOT NULL,
                num_ganhadores INTEGER NOT NULL DEFAULT 1,
                slug TEXT NOT NULL UNIQUE,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS ganhadores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sorteio_id INTEGER NOT NULL,
                participante_id INTEGER NOT NULL,
                posicao INTEGER NOT NULL,
                sorteado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(sorteio_id) REFERENCES sorteios(id),
                FOREIGN KEY(participante_id) REFERENCES participantes(id)
            )
        ''')
        db.commit()


def gerar_qrcode_base64(url):
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=8, border=3)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


def slugify(text):
    text = text.lower().strip()
    for src, dst in [('àáâãä','a'),('èéêë','e'),('ìíîï','i'),('òóôõö','o'),('ùúûü','u'),('ç','c'),('ñ','n')]:
        for c in src:
            text = text.replace(c, dst)
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text.strip('-') or 'sorteio'


def unique_slug(db, base):
    slug, n = base, 1
    while db.execute('SELECT id FROM sorteios WHERE slug=?', (slug,)).fetchone():
        slug, n = f'{base}-{n}', n + 1
    return slug


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


# ─── Public routes ────────────────────────────────────────────────────────────

@app.route('/img/<path:filename>')
def serve_img(filename):
    return send_from_directory('img', filename)


@app.route('/')
def index():
    qr_cncf = gerar_qrcode_base64('https://linktr.ee/cncfcampinas')
    qr_doug = gerar_qrcode_base64('https://linktr.ee/dougbrazil')
    return render_template('index.html', qr_cncf=qr_cncf, qr_doug=qr_doug)


@app.route('/sorteio/<slug>')
def sorteio_publico(slug):
    db = get_db()
    sorteio = db.execute('SELECT * FROM sorteios WHERE slug=?', (slug,)).fetchone()
    if not sorteio:
        return 'Sorteio não encontrado.', 404
    sorteio = dict(sorteio)
    ganhadores = db.execute('''
        SELECT g.posicao, p.nome, p.email
        FROM ganhadores g JOIN participantes p ON p.id=g.participante_id
        WHERE g.sorteio_id=? ORDER BY g.posicao
    ''', (sorteio['id'],)).fetchall()
    total = db.execute('SELECT COUNT(*) as c FROM participantes WHERE evento=?',
                       (sorteio['evento'],)).fetchone()['c']
    sorteio_url = url_for('sorteio_publico', slug=sorteio['slug'], _external=True)
    linktree_url = 'https://linktr.ee/dougbrazil' if sorteio['evento'] == 'dougbrazil' else 'https://linktr.ee/cncfcampinas'
    qr_inscricao = gerar_qrcode_base64(sorteio_url)
    qr_contatos  = gerar_qrcode_base64(linktree_url)
    return render_template('sorteio.html', sorteio=sorteio,
                           ganhadores=[dict(g) for g in ganhadores],
                           qr_inscricao=qr_inscricao, qr_contatos=qr_contatos,
                           sorteio_url=sorteio_url, linktree_url=linktree_url,
                           total=total)


@app.route('/sorteio/<slug>/status')
def sorteio_status(slug):
    db = get_db()
    sorteio = db.execute('SELECT * FROM sorteios WHERE slug=?', (slug,)).fetchone()
    if not sorteio:
        return jsonify({'erro': 'Não encontrado.'}), 404
    sorteio = dict(sorteio)
    ganhadores = db.execute('''
        SELECT g.posicao, p.nome, p.email
        FROM ganhadores g JOIN participantes p ON p.id=g.participante_id
        WHERE g.sorteio_id=? ORDER BY g.posicao
    ''', (sorteio['id'],)).fetchall()
    total = db.execute('SELECT COUNT(*) as c FROM participantes WHERE evento=?',
                       (sorteio['evento'],)).fetchone()['c']
    return jsonify({'ganhadores': [dict(g) for g in ganhadores], 'total_participantes': total})


@app.route('/cadastrar', methods=['POST'])
def cadastrar():
    data = request.get_json()
    nome = data.get('nome', '').strip()
    email = data.get('email', '').strip().lower()
    evento = data.get('evento', '').strip()
    consentimento = data.get('consentimento', False)

    if not nome or not email or not evento:
        return jsonify({'erro': 'Preencha todos os campos.'}), 400
    if not consentimento:
        return jsonify({'erro': 'É necessário aceitar os termos para participar.'}), 400
    if evento not in EVENTOS:
        return jsonify({'erro': 'Evento inválido.'}), 400

    db = get_db()
    try:
        db.execute('INSERT INTO participantes (nome, email, evento, consentimento) VALUES (?,?,?,?)',
                   (nome, email, evento, 1))
        db.commit()
        total = db.execute('SELECT COUNT(*) as c FROM participantes WHERE evento=?',
                           (evento,)).fetchone()['c']
        return jsonify({'sucesso': True, 'mensagem': f'✅ {nome}, você está inscrito!', 'total': total})
    except sqlite3.IntegrityError:
        return jsonify({'erro': 'Este e-mail já está cadastrado neste evento.'}), 409


@app.route('/participantes/<evento>')
def participantes(evento):
    if evento not in EVENTOS:
        return jsonify({'erro': 'Evento inválido.'}), 400
    db = get_db()
    rows = db.execute('SELECT id, nome, email FROM participantes WHERE evento=? ORDER BY criado_em',
                      (evento,)).fetchall()
    return jsonify({'participantes': [dict(r) for r in rows], 'total': len(rows)})


@app.route('/sortear', methods=['POST'])
def sortear():
    data = request.get_json()
    evento = data.get('evento', '').strip()
    if evento not in EVENTOS:
        return jsonify({'erro': 'Evento inválido.'}), 400
    db = get_db()
    ja_sorteados = [r['participante_id'] for r in
                    db.execute('SELECT participante_id FROM sorteados WHERE evento=?', (evento,)).fetchall()]
    todos = db.execute('SELECT id, nome, email FROM participantes WHERE evento=?', (evento,)).fetchall()
    disponiveis = [p for p in todos if p['id'] not in ja_sorteados]
    if not disponiveis:
        return jsonify({'erro': 'Todos os participantes já foram sorteados! Reinicie o sorteio se desejar.'}), 400
    vencedor = random.choice(disponiveis)
    db.execute('INSERT INTO sorteados (participante_id, evento) VALUES (?,?)', (vencedor['id'], evento))
    db.commit()
    return jsonify({
        'sucesso': True,
        'vencedor': {'id': vencedor['id'], 'nome': vencedor['nome'], 'email': vencedor['email']},
        'participantes': [{'id': p['id'], 'nome': p['nome']} for p in todos]
    })


@app.route('/deletar-dados', methods=['POST'])
def deletar_dados():
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    evento = data.get('evento', '').strip()

    if not email or not evento:
        return jsonify({'erro': 'Informe e-mail e evento.'}), 400
    if evento not in EVENTOS:
        return jsonify({'erro': 'Evento inválido.'}), 400

    db = get_db()
    participante = db.execute(
        'SELECT id FROM participantes WHERE email=? AND evento=?', (email, evento)
    ).fetchone()

    if not participante:
        return jsonify({'erro': 'E-mail não encontrado neste evento.'}), 404

    pid = participante['id']
    db.execute('DELETE FROM ganhadores WHERE participante_id=?', (pid,))
    db.execute('DELETE FROM sorteados  WHERE participante_id=?', (pid,))
    db.execute('DELETE FROM participantes WHERE id=?', (pid,))
    db.commit()

    return jsonify({'sucesso': True, 'mensagem': 'Seus dados foram removidos com sucesso.'})


@app.route('/resetar', methods=['POST'])
def resetar():
    data = request.get_json()
    evento = data.get('evento', '').strip()
    if evento not in EVENTOS:
        return jsonify({'erro': 'Evento inválido.'}), 400
    db = get_db()
    db.execute('DELETE FROM sorteados WHERE evento=?', (evento,))
    db.commit()
    return jsonify({'sucesso': True, 'mensagem': 'Sorteio resetado! Todos podem ser sorteados novamente.'})


# ─── Admin routes ─────────────────────────────────────────────────────────────

@app.route('/admin')
def admin_index():
    return redirect(url_for('admin_dashboard') if session.get('admin_logged_in') else url_for('admin_login'))


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))
    error = None
    if request.method == 'POST':
        if request.form.get('usuario') == ADMIN_USER and request.form.get('senha') == ADMIN_PASS:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        error = 'Usuário ou senha incorretos.'
    return render_template('admin/login.html', error=error)


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    db = get_db()
    sorteios = db.execute('''
        SELECT s.*,
            (SELECT COUNT(*) FROM participantes WHERE evento=s.evento) as total_participantes,
            (SELECT COUNT(*) FROM ganhadores WHERE sorteio_id=s.id) as total_ganhadores
        FROM sorteios s ORDER BY s.criado_em DESC
    ''').fetchall()
    return render_template('admin/dashboard.html', sorteios=[dict(s) for s in sorteios])


@app.route('/admin/sorteio/criar', methods=['GET', 'POST'])
@login_required
def admin_criar():
    errors = []
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        descricao = request.form.get('descricao', '').strip()
        evento = request.form.get('evento', '').strip()
        try:
            num = int(request.form.get('num_ganhadores', 1))
            if num < 1:
                raise ValueError
        except ValueError:
            errors.append('Número de ganhadores inválido.')
            num = 1
        if not nome:
            errors.append('Nome é obrigatório.')
        if evento not in EVENTOS:
            errors.append('Selecione um evento válido.')
        if not errors:
            db = get_db()
            slug = unique_slug(db, slugify(nome))
            db.execute('INSERT INTO sorteios (nome, descricao, evento, num_ganhadores, slug) VALUES (?,?,?,?,?)',
                       (nome, descricao, evento, num, slug))
            db.commit()
            novo = db.execute('SELECT id FROM sorteios WHERE slug=?', (slug,)).fetchone()
            return redirect(url_for('admin_sorteio', sorteio_id=novo['id']))
    return render_template('admin/criar.html', errors=errors,
                           form=request.form if request.method == 'POST' else {})


@app.route('/admin/sorteio/<int:sorteio_id>')
@login_required
def admin_sorteio(sorteio_id):
    db = get_db()
    sorteio = db.execute('SELECT * FROM sorteios WHERE id=?', (sorteio_id,)).fetchone()
    if not sorteio:
        return 'Sorteio não encontrado.', 404
    sorteio = dict(sorteio)
    participantes_rows = db.execute(
        'SELECT id, nome, email FROM participantes WHERE evento=? ORDER BY criado_em',
        (sorteio['evento'],)
    ).fetchall()
    ganhadores_rows = db.execute('''
        SELECT g.posicao, p.nome, p.email, g.sorteado_em
        FROM ganhadores g JOIN participantes p ON p.id=g.participante_id
        WHERE g.sorteio_id=? ORDER BY g.posicao
    ''', (sorteio_id,)).fetchall()
    ganhou_ids = {r['participante_id'] for r in
                  db.execute('SELECT participante_id FROM ganhadores WHERE sorteio_id=?',
                             (sorteio_id,)).fetchall()}
    disponiveis = [p for p in participantes_rows if p['id'] not in ganhou_ids]
    sorteio_url = url_for('sorteio_publico', slug=sorteio['slug'], _external=True)
    qr_sorteio = gerar_qrcode_base64(sorteio_url)
    return render_template('admin/sorteio.html',
        sorteio=sorteio,
        participantes=[dict(p) for p in participantes_rows],
        ganhadores=[dict(g) for g in ganhadores_rows],
        disponiveis=len(disponiveis),
        pode_sortear=len(ganhadores_rows) < sorteio['num_ganhadores'] and len(disponiveis) > 0,
        sorteio_url=sorteio_url,
        qr_sorteio=qr_sorteio
    )


@app.route('/admin/sorteio/<int:sorteio_id>/sortear', methods=['POST'])
@login_required
def admin_sortear(sorteio_id):
    db = get_db()
    sorteio = db.execute('SELECT * FROM sorteios WHERE id=?', (sorteio_id,)).fetchone()
    if not sorteio:
        return jsonify({'erro': 'Sorteio não encontrado.'}), 404
    ganhou_ids = [r['participante_id'] for r in
                  db.execute('SELECT participante_id FROM ganhadores WHERE sorteio_id=?',
                             (sorteio_id,)).fetchall()]
    total_g = len(ganhou_ids)
    if total_g >= sorteio['num_ganhadores']:
        return jsonify({'erro': f'Todos os {sorteio["num_ganhadores"]} ganhadores já foram sorteados.'}), 400
    todos = db.execute('SELECT id, nome, email FROM participantes WHERE evento=?',
                       (sorteio['evento'],)).fetchall()
    disponiveis = [p for p in todos if p['id'] not in ganhou_ids]
    if not disponiveis:
        return jsonify({'erro': 'Nenhum participante disponível.'}), 400
    vencedor = random.choice(disponiveis)
    posicao = total_g + 1
    db.execute('INSERT INTO ganhadores (sorteio_id, participante_id, posicao) VALUES (?,?,?)',
               (sorteio_id, vencedor['id'], posicao))
    db.commit()
    return jsonify({
        'sucesso': True,
        'vencedor': {'nome': vencedor['nome'], 'email': vencedor['email']},
        'posicao': posicao,
        'participantes': [{'id': p['id'], 'nome': p['nome']} for p in todos]
    })


@app.route('/admin/sorteio/<int:sorteio_id>/resetar', methods=['POST'])
@login_required
def admin_resetar(sorteio_id):
    db = get_db()
    if not db.execute('SELECT id FROM sorteios WHERE id=?', (sorteio_id,)).fetchone():
        return jsonify({'erro': 'Não encontrado.'}), 404
    db.execute('DELETE FROM ganhadores WHERE sorteio_id=?', (sorteio_id,))
    db.commit()
    return jsonify({'sucesso': True})


@app.route('/admin/sorteio/<int:sorteio_id>/deletar', methods=['POST'])
@login_required
def admin_deletar(sorteio_id):
    db = get_db()
    db.execute('DELETE FROM ganhadores WHERE sorteio_id=?', (sorteio_id,))
    db.execute('DELETE FROM sorteios WHERE id=?', (sorteio_id,))
    db.commit()
    return redirect(url_for('admin_dashboard'))


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
