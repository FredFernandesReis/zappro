"""Modelos prontos de respostas automáticas por segmento."""

PRESETS = {
    "loja": {
        "nome": "Loja e comércio",
        "icone": "shop",
        "descricao": "Produtos, preços, entrega, pagamento e endereço.",
        "cor": "success",
        "boas_vindas": [
            (
                "Oi! Que bom ter você por aqui 😊\n\n"
                "Escolha uma opção:\n"
                "▪️ 1 — Produtos\n▪️ 2 — Preços\n▪️ 3 — Entrega\n\n"
                "Responda com o número ou o nome."
            ),
            (
                "Olá! Posso te ajudar com a nossa loja.\n\n"
                "Digite 1 para produtos, 2 para preços ou 3 para entrega."
            ),
            (
                "Opa, seja bem-vindo! 👋\n"
                "Quer ver produtos, consultar preços ou saber sobre entrega? "
                "Pode responder 1, 2 ou 3."
            ),
        ],
        "respostas": [
            {
                "palavra_chave": "1 | produtos | catálogo",
                "resposta": (
                    "Claro! Me diga qual produto você procura e eu te ajudo "
                    "com as opções disponíveis."
                ),
            },
            {
                "palavra_chave": "2 | preço | preços | valor",
                "resposta": (
                    "Consigo te passar o valor certinho. Qual produto você quer consultar?"
                ),
            },
            {
                "palavra_chave": "3 | entrega | frete",
                "resposta": (
                    "Fazemos entrega sim! Envie seu bairro ou CEP para confirmarmos "
                    "o prazo e o valor do frete."
                ),
            },
            {
                "palavra_chave": "pagamento | pix | cartão",
                "resposta": (
                    "Temos opções de pagamento para facilitar. Me diga se prefere "
                    "Pix ou cartão que explico os detalhes."
                ),
            },
            {
                "palavra_chave": "endereço | localização | onde fica",
                "resposta": (
                    "Te passo a localização certinha. Só um instante que confirmamos "
                    "o endereço aqui no atendimento."
                ),
            },
        ],
    },
    "clinica": {
        "nome": "Clínica e consultório",
        "icone": "heart-pulse",
        "descricao": "Serviços, agendamento, convênios, endereço e preparo.",
        "cor": "danger",
        "boas_vindas": [
            (
                "Olá! Seja bem-vindo à nossa clínica.\n\n"
                "Escolha uma opção:\n"
                "▪️ 1 — Serviços\n▪️ 2 — Agendar\n▪️ 3 — Convênios\n\n"
                "Responda com o número ou o nome."
            ),
            (
                "Oi! Como podemos ajudar? 😊\n"
                "Digite 1 para serviços, 2 para agendamento ou 3 para convênios."
            ),
            (
                "Olá, tudo bem? Você quer conhecer nossos serviços, marcar um horário "
                "ou consultar convênios? Responda 1, 2 ou 3."
            ),
        ],
        "respostas": [
            {
                "palavra_chave": "1 | serviços | atendimento",
                "resposta": (
                    "Claro! Me conte qual atendimento você procura para indicarmos "
                    "a opção adequada."
                ),
            },
            {
                "palavra_chave": "2 | agendar | consulta | horário",
                "resposta": (
                    "Vamos agendar! Envie seu nome e o melhor dia ou período para você."
                ),
            },
            {
                "palavra_chave": "3 | convênio | plano",
                "resposta": (
                    "Me diga o nome do seu convênio para confirmarmos a cobertura "
                    "com a equipe."
                ),
            },
            {
                "palavra_chave": "endereço | localização | como chegar",
                "resposta": (
                    "Te enviamos a localização certinha. Só um instante enquanto "
                    "confirmamos o endereço."
                ),
            },
            {
                "palavra_chave": "preparo | exame | jejum",
                "resposta": (
                    "As orientações dependem do procedimento. Informe qual exame "
                    "ou consulta foi agendado para confirmarmos o preparo correto."
                ),
            },
        ],
    },
    "barbearia": {
        "nome": "Barbearia e salão",
        "icone": "scissors",
        "descricao": "Serviços, preços, horários, endereço e formas de pagamento.",
        "cor": "primary",
        "boas_vindas": [
            (
                "Fala! Seja bem-vindo 👋\n\n"
                "Escolha uma opção:\n"
                "▪️ 1 — Serviços\n▪️ 2 — Preços\n▪️ 3 — Agendar\n\n"
                "Responda com o número ou o nome."
            ),
            (
                "Opa! Bora cuidar do visual?\n"
                "Digite 1 para serviços, 2 para preços ou 3 para marcar um horário."
            ),
            (
                "Oi! Como posso ajudar hoje? 😊\n"
                "Você pode responder serviços, preços ou agendar."
            ),
        ],
        "respostas": [
            {
                "palavra_chave": "1 | serviços | corte | barba",
                "resposta": (
                    "Temos opções de corte, barba e combos. Qual serviço você quer fazer?"
                ),
            },
            {
                "palavra_chave": "2 | preço | preços | valor",
                "resposta": (
                    "Te passo o valor certinho! Você procura corte, barba ou um combo?"
                ),
            },
            {
                "palavra_chave": "3 | agendar | horário | marcar",
                "resposta": (
                    "Fechou! Envie seu nome e o melhor dia ou período para verificarmos "
                    "os horários livres."
                ),
            },
            {
                "palavra_chave": "endereço | localização | onde fica",
                "resposta": (
                    "Te mando a localização certinha. Só um instante que confirmamos "
                    "o endereço."
                ),
            },
            {
                "palavra_chave": "pagamento | pix | cartão",
                "resposta": (
                    "Aceitamos diferentes formas de pagamento. Me diga se prefere "
                    "Pix ou cartão para confirmarmos."
                ),
            },
        ],
    },
}
