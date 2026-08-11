# Deposita — Frontend

Interface web do Deposita, um sistema de gestão de estoque integrado a uma API FastAPI. O projeto combina operações administrativas claras com uma identidade visual inspirada em terminal industrial e interfaces 16-bit de gerenciamento de inventário.

## Stack

- React
- Vite
- React Router
- Fetch API
- CSS responsivo com tokens globais

## Funcionalidades

- Autenticação e restauração de sessão
- Dashboard com resumo de estoque, alertas e movimentações recentes
- Cadastro, edição, inativação e reativação de produtos
- Registro e histórico de entradas e saídas
- Cadastro, edição e exclusão de fornecedores
- Painel de produtos com estoque baixo
- Tabelas compactas no desktop e cards adaptados para telas menores
- Feedbacks de loading, sucesso, erro e estados vazios

## Requisitos

- Node.js 20 ou superior
- npm
- Backend do Deposita em execução

O frontend depende dos endpoints de autenticação, produtos, movimentações, fornecedores e dashboard fornecidos pelo backend FastAPI localizado no diretório irmão `../backend` deste projeto.

## Configuração

Copie o arquivo de exemplo e ajuste a URL da API quando necessário:

```bash
cp .env.example .env
```

No Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Variável disponível:

```env
VITE_API_URL=http://127.0.0.1:8000
```

Em desenvolvimento, essa também é a URL padrão quando `VITE_API_URL` não é definida. Em produção, configure a variável conforme o endereço público do backend.

## Instalação e execução

```bash
npm install
npm run dev
```

O Vite exibirá no terminal o endereço local da aplicação.

## Validação

```bash
npm run build
npm run lint
npm test -- --run
```

Para visualizar o build de produção localmente:

```bash
npm run preview
```

## Estrutura principal

```text
src/
├── contexts/   # autenticação compartilhada
├── hooks/      # acesso aos contexts
├── layouts/    # estrutura autenticada e navegação
├── pages/      # telas da aplicação
├── routes/     # rotas públicas e protegidas
├── services/   # comunicação com a API
├── styles/     # tokens e sistema visual global
└── utils/      # formatação de dados
```

## Responsividade e acessibilidade

A interface mantém tabelas em telas amplas e usa cards compactos quando não há espaço horizontal suficiente. O menu mobile preserva estado expandido, labels e navegação por teclado.

Os principais fluxos incluem foco visível, labels associados, mensagens anunciadas, estados que não dependem apenas de cor, áreas de toque adequadas e um link para pular diretamente ao conteúdo principal.
