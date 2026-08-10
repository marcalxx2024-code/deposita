# Deposita — Backend

API para controle de estoque, desenvolvida como projeto de portfólio. O backend
oferece cadastro de produtos e fornecedores, movimentação de estoque,
autenticação JWT, autorização por papéis e trilha de auditoria.

## Funcionalidades

- Autenticação com JWT e papéis `ADMIN` e `OPERATOR`.
- Produtos com SKU único, fornecedor opcional, estoque mínimo e preço.
- Entrada e saída de estoque, com bloqueio de saída acima da quantidade atual.
- Fornecedores vinculados a produtos.
- Auditoria de operações administrativas e movimentações de estoque.
- Dashboard resumido, consulta de movimentações e itens com estoque baixo.
- Listagem de produtos com busca por nome/SKU, filtros, paginação e ordenação
  segura.
- Respostas de erro padronizadas e validação de entrada com Pydantic.
- CORS configurável para integração com o frontend.

## Stack

- Python 3.13, FastAPI e Uvicorn
- SQLAlchemy e SQLite
- Alembic
- Pydantic e python-dotenv
- PyJWT e pwdlib/Argon2
- Pytest e HTTPX

## Estrutura

```text
app/
  config.py       # Variáveis de ambiente e parsing de CORS
  database.py     # Engine, sessão e funções SQLite
  errors.py       # Erros públicos padronizados
  main.py         # Rotas, handlers e dependências
  models.py       # Modelos SQLAlchemy
  schemas.py      # Schemas e validações Pydantic
  security.py     # Hash de senha e JWT
migrations/       # Histórico Alembic
tests/            # Suíte automatizada
```

## Configuração local (Windows)

Clone o repositório e entre na pasta do backend:

```powershell
git clone <URL_DO_REPOSITORIO>
cd Deposita\backend
```

Crie e ative o ambiente virtual:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Se a execução de scripts estiver bloqueada apenas para a sessão atual:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Instale as dependências da aplicação e de testes:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements-test.txt
```

Crie a configuração local. Nunca versione o arquivo `.env`.

```powershell
Copy-Item .env.example .env
```

Edite `.env` e configure:

| Variável | Obrigatória | Descrição |
| --- | --- | --- |
| `DEPOSITA_SECRET_KEY` | Sim | Chave longa, aleatória e exclusiva para assinar JWTs. |
| `DATABASE_URL` | Não | URL SQLAlchemy; o padrão local é `sqlite:///./deposita.db`. |
| `CORS_ORIGINS` | Não | Origins do frontend separadas por vírgula. |

Exemplo de CORS local: `http://localhost:5173,http://127.0.0.1:5173`.
Variáveis já definidas no sistema operacional têm prioridade sobre valores do
`.env`.

## Banco de dados e execução

As migrations são controladas pelo Alembic. Em um banco novo, aplique-as antes
de iniciar a API:

```powershell
python -m alembic upgrade head
```

Em um banco novo, crie manualmente o primeiro ADMIN. O comando solicita a senha
sem colocá-la no histórico do terminal e recusa execução se já existir ADMIN:

```powershell
python -m app.bootstrap_admin --username admin
```

Inicie o servidor:

```powershell
python -m uvicorn app.main:app --reload
```

A documentação interativa Swagger estará em [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

## Autorização e auditoria

- `ADMIN`: administra produtos, fornecedores e contas OPERATOR, além de
  consultar auditoria.
- `OPERATOR`: pode registrar entradas e saídas de estoque, sem administrar
  produtos ou fornecedores.

As leituras operacionais exigem autenticação para evitar expor catálogo,
fornecedores, níveis de estoque, dashboard e histórico de movimentações. ADMIN
e OPERATOR podem consultar esses dados; a diferença entre os papéis se aplica
às operações administrativas e de escrita.

- Públicos: `GET /health`, `POST /auth/login` e documentação automática.
- Autenticados: `GET /auth/me`, produtos, low-stock, dashboard, movimentações
  e fornecedores.
- OPERATOR+: entradas e saídas de estoque.
- ADMIN: usuários, auditoria, administração de produtos e fornecedores, além
  de inativação e reativação de produtos.

`POST /users` exige ADMIN e sempre cria uma conta `OPERATOR`. A API não cria
ADMINs: o primeiro é criado pelo comando de bootstrap para evitar auto-registro
com permissão operacional ou escalada de privilégio por payload.

As ações de criação, atualização, inativação de produtos e exclusão de fornecedores, além das
movimentações de estoque, geram registros de auditoria vinculados ao usuário.

## Produtos, fornecedores e estoque

Cada produto possui SKU único, normalizado em maiúsculas. Um produto pode ter
um fornecedor opcional; fornecedores com produtos associados não podem ser
excluídos. `DELETE /products/{id}` inativa o produto e preserva seu histórico;
produtos inativos não aceitam movimentações nem atualização até serem reativados
por ADMIN em `POST /products/{id}/reactivate`. As saídas de estoque são rejeitadas
quando a quantidade solicitada é maior que o saldo disponível.

### `GET /products`

A listagem retorna `items`, `page`, `page_size`, `total` e `pages`.

- Paginação: `page` começa em 1; `page_size` tem padrão 20 e máximo 100.
- Filtros: `search` (nome e SKU), `category`, `supplier_id`, `low_stock`,
  `min_price`, `max_price` e `include_inactive`.
- Ordenação: `sort_by` aceita `name`, `sku`, `price`, `quantity` ou `id`;
  `sort_order` aceita `asc` ou `desc`.

## CORS

`CORS_ORIGINS` aceita uma lista separada por vírgulas. Apenas origins explícitas
são aceitas; `*` é rejeitado. Como a API usa JWT Bearer no header
`Authorization`, CORS não habilita credenciais de cookies. Se
`CORS_ORIGINS` estiver vazia, nenhum navegador de outra origin recebe permissão
de acesso.

## Testes e verificações

O repositório possui CI no GitHub Actions para `push` e `pull_request` em
`main`. O workflow usa Ubuntu, Python 3.13 e um banco SQLite temporário, sem
ler arquivos `.env` locais.

Execute a suíte:

```powershell
python -m pytest -q
```

Verifique se os modelos e migrations estão sincronizados:

```powershell
python -m alembic check
```

Para consultar a revisão aplicada no banco:

```powershell
python -m alembic current
```

## Segurança de arquivos

`.env`, ambientes virtuais, bancos SQLite locais e caches Python são ignorados
pelo Git. O repositório inclui somente `.env.example`, sem segredo real.
