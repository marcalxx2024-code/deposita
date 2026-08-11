# Deposita

Sistema de gestão de estoque para portfólio, com frontend React/Vite e API
FastAPI. O projeto inclui autenticação JWT, RBAC, produtos, fornecedores,
movimentações, dashboard, estoque baixo e auditoria.

## Demonstração online

**Status:** preparada para deploy; a URL pública será adicionada somente depois
da publicação.

A demonstração usa uma conta pública com role `operator`, dados inteiramente
fictícios e um banco SQLite exclusivo. Ela permite consultar o inventário e
registrar entradas e saídas, mas não expõe controles administrativos.

Em hospedagens gratuitas, o backend pode hibernar. Ao entrar na demonstração, o
frontend consulta `/health`, mostra a mensagem de preparação e realiza um número
limitado de tentativas antes de liberar uma nova tentativa manual.

## Stack

- Backend: Python 3.13, FastAPI, Uvicorn, SQLAlchemy, Alembic e SQLite.
- Segurança: JWT HS256, Argon2 e RBAC com roles `admin` e `operator`.
- Frontend: React 19, Vite, React Router e Fetch API.
- Qualidade: Pytest, Vitest, Testing Library e Oxlint.
- Deploy preparado: Render Web Service e Static Site via `render.yaml`.

## Estrutura

```text
backend/       API, migrations, seed demo e testes Python
frontend/      aplicação React, serviços e testes de interface
render.yaml    definição declarativa dos serviços, ainda não publicada
```

## Configuração

### Backend

| Variável | Uso |
| --- | --- |
| `DEPOSITA_SECRET_KEY` | Segredo JWT forte, exclusivo e com pelo menos 32 caracteres. |
| `DATABASE_URL` | URL SQLAlchemy. Localmente, o padrão é `sqlite:///./deposita.db`. |
| `CORS_ORIGINS` | Origins explícitas do frontend, separadas por vírgula. |
| `DEMO_MODE` | Ativa recursos da demonstração; padrão `false`. |
| `DEMO_USERNAME` | Usuário `operator` usado por `/auth/demo`; padrão `demo`. |
| `PORT` | Porta do serviço hospedado; o entrypoint usa `8000` quando ausente. |

### Frontend

| Variável | Uso |
| --- | --- |
| `VITE_API_URL` | URL pública da API. Use HTTPS no build hospedado. Não é segredo. |

Variáveis `VITE_*` são incorporadas ao bundle e nunca devem conter credenciais,
tokens ou chaves privadas.

## Execução local normal

No backend:

```powershell
cd backend
Copy-Item .env.example .env
python -m pip install -r requirements-test.txt
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

No frontend, em outro terminal:

```powershell
cd frontend
Copy-Item .env.example .env
npm ci
npm run dev
```

## Modo demo local

Use sempre um banco dedicado cujo nome contenha `demo`. Essa convenção é uma
proteção adicional do seed e do reset.

```powershell
cd backend
$env:DEMO_MODE = "true"
$env:DEMO_USERNAME = "demo"
$env:DATABASE_URL = "sqlite:///./deposita_demo.db"
$env:CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
python -m alembic upgrade head
python -m app.seed_demo
python -m uvicorn app.main:app --reload
```

Para recriar explicitamente o dataset fictício:

```powershell
python -m app.seed_demo --reset
```

O reset não possui endpoint HTTP e é recusado quando `DEMO_MODE=false` ou quando
o nome do banco conectado não contém `demo`.

## Preparação para deploy

O backend usa:

```text
Build: python -m pip install -r requirements.txt
Start: python -m app.start
```

O entrypoint executa, em ordem:

1. `python -m alembic upgrade head`;
2. `seed_demo(reset=True)` somente com `DEMO_MODE=true`;
3. Uvicorn em `0.0.0.0:$PORT`, com um único worker.

Falhas em migrations ou seed interrompem o startup. Um worker é obrigatório
enquanto a demonstração usar SQLite.

O frontend estático usa:

```text
Build: npm ci && npm run build
Publish: frontend/dist
```

O `render.yaml` inclui rewrite de `/*` para `/index.html`, necessário para
recarregar rotas do React Router diretamente.

## Variáveis da demo hospedada

Configuração conceitual, sem valores secretos no repositório:

```env
DEMO_MODE=true
DEMO_USERNAME=demo
DATABASE_URL=sqlite:///./deposita_demo.db
CORS_ORIGINS=<URL HTTPS FINAL DO FRONTEND>
DEPOSITA_SECRET_KEY=<SEGREDO FORTE CONFIGURADO NO PROVEDOR>
VITE_API_URL=<URL HTTPS FINAL DO BACKEND>
```

## Testes

Última verificação desta preparação:

- Backend: `137 passed` com `python -m pytest -q`.
- Frontend: `26 passed` em 9 arquivos com `npm test -- --run`.

Comandos completos:

```powershell
cd backend
python -m pytest -q

cd ..\frontend
npm test -- --run
npm run lint
npm run build
```

## Segurança e limitações

- `.env`, `*.db`, `node_modules` e `dist` permanecem ignorados pelo Git.
- O banco demo não cria administrador; a conta pública é `operator`.
- CORS aceita apenas as origins configuradas, sem wildcard.
- Swagger permanece público em `/docs` para facilitar a avaliação técnica.
- Não existe endpoint público de reset.
- O SQLite hospedado é intencionalmente efêmero e adequado somente à demo.
- Nenhum deploy é realizado apenas pela presença do `render.yaml`; ainda é
  necessário conectar o repositório e confirmar as variáveis no provedor.

Documentação detalhada: [backend](backend/README.md) e
[frontend](frontend/README.md).
