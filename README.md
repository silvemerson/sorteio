<div align="center">

# 🎲 Sorteio de Eventos

**Plataforma open source de sorteios ao vivo para comunidades tech**

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-black?logo=flask)](https://flask.palletsprojects.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Open Source](https://img.shields.io/badge/Open%20Source-%E2%9D%A4-red)](https://github.com)

Feito com ❤️ para comunidades como **DougBrazil**, **CNCF Campinas** e qualquer grupo tech que queira realizar sorteios ao vivo de forma simples, bonita e em conformidade com a LGPD.

</div>

---

## O que é isso?

Um sistema web completo para sorteios em eventos presenciais ou online. O participante acessa uma URL, se cadastra pelo celular via QR Code e o apresentador executa o sorteio ao vivo pelo painel admin — com animação de roleta, revelação dramática do ganhador e suporte a múltiplos prêmios em ordem (1º, 2º, 3º lugar...).

**Totalmente gratuito, open source e pronto para uso pela sua comunidade.**

---

## Funcionalidades

### Para participantes
- Inscrição via QR Code (nome + e-mail)
- Página dedicada por sorteio com URL única
- Consentimento LGPD obrigatório no cadastro
- Direito ao esquecimento — remoção de dados via formulário (Art. 18, LGPD)
- Atualização automática ao vivo dos ganhadores (sem precisar recarregar a página)

### Para o admin / apresentador
- Login protegido por usuário e senha
- Dashboard com todos os sorteios e barra de progresso
- Criar sorteios: nome, evento, número de ganhadores, descrição
- QR Code gerado automaticamente para cada sorteio
- Botão de copiar link para colar no chat ou projetar na tela
- Roleta animada com revelação do ganhador
- Sorteio por posição: 1º lugar, 2º lugar, 3º lugar...
- Resetar ou deletar sorteio

---

## Eventos suportados

| Comunidade | Cores | Fonte | Link |
|------------|-------|-------|------|
| **DougBrazil** | Verde `#009B3A` + Amarelo `#FFD700` | Inter | [linktr.ee/dougbrazil](https://linktr.ee/dougbrazil) |
| **CNCF Campinas** | Azul `#0078D7` + Ciano `#00D1FF` | Inter | [linktr.ee/cncfcampinas](https://linktr.ee/cncfcampinas) |

> Quer adicionar sua comunidade?  Faça um fork e fortaleça o role 
> Melhorias? Abra um PR ou uma issue — são bem-vindos!

---

## Estrutura do projeto

```
sorteio/
├── app.py                      # Aplicação Flask — rotas, banco, helpers
├── requirements.txt            # Dependências Python
├── .gitignore
├── img/
│   ├── doug.png                # Logo DougBrazil
│   └── cncf.png                # Logo CNCF Campinas
└── templates/
    ├── index.html              # Página pública principal (abas por evento)
    ├── sorteio.html            # Página pública de um sorteio específico
    └── admin/
        ├── base.html           # Layout base admin (nav, estilos compartilhados)
        ├── login.html          # Tela de login
        ├── dashboard.html      # Lista de sorteios
        ├── criar.html          # Formulário de criação
        └── sorteio.html        # Painel de execução do sorteio
```

---

## Banco de dados

SQLite gerado automaticamente na primeira execução. Quatro tabelas:

```
participantes   id, nome, email, evento, consentimento, criado_em
                UNIQUE(email, evento)

sorteados       id, participante_id, evento, sorteado_em
                (histórico da roleta da página principal)

sorteios        id, nome, descricao, evento, num_ganhadores, slug, criado_em
                UNIQUE(slug)

ganhadores      id, sorteio_id, participante_id, posicao, sorteado_em
```

Participantes são registrados **por evento**. Todos os sorteios do mesmo evento compartilham o mesmo pool de participantes.

---

## Rotas

### Públicas

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/` | Página principal com abas por evento |
| `GET` | `/sorteio/<slug>` | Página pública do sorteio com QR Code e inscrição |
| `GET` | `/sorteio/<slug>/status` | JSON com ganhadores e total (usado para polling ao vivo) |
| `POST` | `/cadastrar` | Inscreve um participante |
| `GET` | `/participantes/<evento>` | Lista participantes do evento |
| `POST` | `/sortear` | Executa sorteio na roleta da página principal |
| `POST` | `/resetar` | Reseta a roleta da página principal |
| `POST` | `/deletar-dados` | Remove dados do participante (LGPD Art. 18) |
| `GET` | `/img/<filename>` | Serve logos da pasta `img/` |

### Admin (requerem login)

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET/POST` | `/admin/login` | Tela de login |
| `GET` | `/admin/logout` | Encerra a sessão |
| `GET` | `/admin/dashboard` | Lista todos os sorteios |
| `GET/POST` | `/admin/sorteio/criar` | Cria novo sorteio |
| `GET` | `/admin/sorteio/<id>` | Painel de execução do sorteio |
| `POST` | `/admin/sorteio/<id>/sortear` | Sorteia o próximo ganhador |
| `POST` | `/admin/sorteio/<id>/resetar` | Reseta todos os ganhadores do sorteio |
| `POST` | `/admin/sorteio/<id>/deletar` | Deleta o sorteio permanentemente |

---

## Instalação

### Pré-requisitos

- Python 3.9 ou superior

### Passos

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/sorteio.git
cd sorteio

# Crie e ative um ambiente virtual (recomendado)
python3 -m venv .venv
source .venv/bin/activate      # Linux/macOS
.venv\Scripts\activate         # Windows

# Instale as dependências
pip install -r requirements.txt

# Inicie a aplicação (cria o banco automaticamente)
python3 app.py
```

Acesse em: [http://localhost:5000](http://localhost:5000)  
Admin em: [http://localhost:5000/admin](http://localhost:5000/admin)

---

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `ADMIN_USER` | `admin` | Usuário do painel admin |
| `ADMIN_PASS` | `admin123` | Senha do painel admin |
| `SECRET_KEY` | `dev-sorteio-key` | Chave de sessão Flask |

**Troque antes de subir para produção:**

```bash
export ADMIN_USER=meu_usuario
export ADMIN_PASS=senha_forte_aqui
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

python3 app.py
```

Ou crie um arquivo `.env` (não commitado pelo `.gitignore`):

```env
ADMIN_USER=meu_usuario
ADMIN_PASS=senha_forte_aqui
SECRET_KEY=gere_uma_chave_aleatoria_aqui
```

---

## Deploy gratuito

### Fly.io (recomendado — sempre no ar)

```bash
# Instale a CLI
curl -L https://fly.io/install.sh | sh

# Login e criação do app
fly launch

# Volume persistente para o banco SQLite
fly volumes create sorteio_data --size 1

# Configure as variáveis
fly secrets set ADMIN_USER=admin ADMIN_PASS=senha_forte SECRET_KEY=chave_aleatoria

# Deploy
fly deploy
```

### Railway (deploy via GitHub)

1. Suba o projeto no GitHub
2. Acesse [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
3. Configure as variáveis de ambiente no painel
4. O `requirements.txt` é detectado automaticamente

### Render

1. Acesse [render.com](https://render.com) → **New Web Service**
2. Conecte o repositório GitHub
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Configure as variáveis de ambiente

> O plano gratuito do Render hiberna após 15 min sem acesso. Para eventos ao vivo, prefira Fly.io ou Railway.

---

## Conformidade LGPD

| Requisito | Implementação |
|-----------|---------------|
| Consentimento explícito | Checkbox obrigatório antes do cadastro |
| Finalidade declarada | Texto informando uso exclusivo para sorteio |
| Direito ao esquecimento | Endpoint `POST /deletar-dados` com UI integrada |
| Minimização de dados | Coleta apenas nome e e-mail |
| Transparência | Dados não são compartilhados com terceiros |

---

## Dependências

| Pacote | Versão | Uso |
|--------|--------|-----|
| `flask` | ≥ 3.0 | Framework web |
| `qrcode[pil]` | ≥ 7.4 | Geração de QR Codes |
| `Pillow` | ≥ 10.0 | Renderização de imagens |
| `gunicorn` | ≥ 21.0 | Servidor WSGI para produção |

---

## Contribuindo

Contribuições são muito bem-vindas! Este projeto nasceu dentro da comunidade tech e é para a comunidade.

```bash
# Fork o repositório e clone
git clone https://github.com/seu-usuario/sorteio.git
cd sorteio

# Crie uma branch para sua feature
git checkout -b feat/minha-feature

# Faça suas alterações e commit
git commit -m "feat: descrição da minha feature"

# Envie e abra um Pull Request
git push origin feat/minha-feature
```

**Ideias de contribuição:**
- Adicionar nova comunidade/evento
- Suporte a múltiplos idiomas (i18n)
- Temas visuais personalizáveis
- Exportar lista de ganhadores em CSV
- Notificação por e-mail ao ganhador
- Autenticação mais robusta (OAuth)

---

## Licença

Este projeto é distribuído sob a licença **MIT** — use, modifique e distribua livremente, inclusive em eventos comerciais, desde que mantenha os créditos.

```
MIT License — Copyright (c) 2025 DougBrazil & CNCF Campinas Community
```

---

<div align="center">

Feito com ❤️ pela comunidade, para a comunidade.

**[DougBrazil](https://linktr.ee/dougbrazil)** • **[CNCF Campinas](https://linktr.ee/cncfcampinas)**

</div>
