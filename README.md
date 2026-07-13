# ZapPro - SaaS de Autoresposta WhatsApp

Sistema multiusuário para pequenas empresas conectarem seu WhatsApp via QR Code e configurarem respostas automáticas.

## Tecnologias

- **Backend:** Django 4.2 + SQLite
- **Frontend:** HTML, CSS, Bootstrap 5, JavaScript
- **WhatsApp:** Baileys (Node.js)
- **Autenticação:** Django Authentication

## Estrutura do Projeto

```
ZapPro/
├── accounts/          # Login, cadastro, perfil, senha
├── dashboard/         # Dashboard principal
├── whatsapp/          # Conexão WhatsApp e mensagens
├── subscriptions/     # Planos e assinaturas
├── autorespostas/     # Respostas automáticas, boas-vindas, horário
├── reports/           # Relatórios
├── whatsapp-service/  # Serviço Node.js (Baileys)
├── sessoes/           # Sessões WhatsApp por usuário
├── templates/         # Templates HTML
└── static/            # CSS e JS
```

## Instalação

### 1. Backend Django

```bash
# Criar ambiente virtual (recomendado)
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux

# Instalar dependências
pip install -r requirements.txt

# Migrar banco de dados
python manage.py migrate

# Criar planos e superusuário
python manage.py setup_planos

# Iniciar servidor
python manage.py runserver
```

### 2. Serviço WhatsApp (Node.js)

```bash
cd whatsapp-service
npm install
npm start
```

> **Requisito:** Node.js 18+ instalado no sistema.

### 3. Acessar o sistema

- **URL:** http://localhost:8000
- **Admin:** admin / admin123

## Planos

| Plano    | WhatsApp | Respostas    | Horário | Preço      |
|----------|----------|--------------|---------|------------|
| Gratuito | 1        | Até 10       | Não     | R$ 0       |
| Básico   | 1        | Ilimitadas   | Sim     | R$ 29,90   |
| Premium  | 3        | Ilimitadas   | Sim     | R$ 59,90   |

## Funcionalidades

- Login, cadastro, recuperação de senha, perfil
- Dashboard com métricas em tempo real
- Conexão WhatsApp via QR Code (sessão isolada por usuário)
- CRUD de respostas automáticas por palavra-chave
- Mensagem de boas-vindas configurável
- Horário de atendimento com mensagem automática
- Gerenciamento manual de assinaturas (admin)
- Relatórios de mensagens e usuários
- Middleware de verificação de assinatura ativa

## Sessões WhatsApp

Cada usuário possui sessão isolada:

```
sessoes/
├── usuario_1/
├── usuario_2/
└── usuario_3/
```

## Deploy em VPS Linux

```bash
# Instalar dependências do sistema
sudo apt update
sudo apt install python3-pip python3-venv nginx nodejs npm

# Configurar Django com Gunicorn
pip install gunicorn
gunicorn zappro.wsgi:application --bind 0.0.0.0:8000

# Serviço WhatsApp com PM2
npm install -g pm2
cd whatsapp-service && pm2 start server.js --name zappro-whatsapp
```

## Futuras Integrações

O código está preparado para:

- **Mercado Pago** — campos comentados em `subscriptions/models.py`
- **WhatsApp API Oficial** — campos comentados em `whatsapp/models.py`

## Segurança

- CSRF protection em todos os formulários
- Cada usuário acessa apenas seus próprios dados
- Middleware de verificação de assinatura
- API Secret entre Django e serviço Baileys
- Sessões WhatsApp isoladas por usuário

## Licença

Projeto privado - ZapPro © 2026
