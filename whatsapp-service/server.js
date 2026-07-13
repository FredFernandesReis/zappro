/**
 * ZapPro - Serviço WhatsApp com Baileys
 * Cada usuário possui sessão isolada em sessoes/usuario_{id}/
 */

const express = require('express');
const path = require('path');
const fs = require('fs');
const axios = require('axios');
const QRCode = require('qrcode');
const pino = require('pino');

const {
    default: makeWASocket,
    useMultiFileAuthState,
    DisconnectReason,
    fetchLatestBaileysVersion,
} = require('@whiskeysockets/baileys');

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 3001;
const API_SECRET = process.env.API_SECRET || 'zappro-secret-key-change-in-production';
const DJANGO_WEBHOOK_URL = process.env.DJANGO_WEBHOOK_URL || 'http://localhost:8000/whatsapp/webhook/';
const SESSIONS_DIR = path.join(__dirname, '..', 'sessoes');

// Armazena sockets ativos por userId
const sessions = {};

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// Garante diretório de sessões
if (!fs.existsSync(SESSIONS_DIR)) {
    fs.mkdirSync(SESSIONS_DIR, { recursive: true });
}

/**
 * Middleware de autenticação por API Secret
 */
function authMiddleware(req, res, next) {
    const secret = req.headers['x-api-secret'];
    if (secret !== API_SECRET) {
        return res.status(401).json({ success: false, error: 'Unauthorized' });
    }
    next();
}

/**
 * Envia evento para webhook Django
 */
async function notifyDjango(data) {
    try {
        await axios.post(DJANGO_WEBHOOK_URL, data, {
            headers: {
                'Content-Type': 'application/json',
                'X-API-Secret': API_SECRET,
            },
            timeout: 60000,
        });
    } catch (err) {
        console.error('Erro ao notificar Django:', err.message);
    }
}

/**
 * Gera QR Code em base64
 */
async function generateQRBase64(qrString) {
    return QRCode.toDataURL(qrString, { width: 256, margin: 2 });
}

/**
 * Obtém caminho da sessão do usuário
 */
function getSessionPath(userId) {
    return path.join(SESSIONS_DIR, `usuario_${userId}`);
}

/**
 * Cria ou reconecta socket WhatsApp para um usuário
 */
async function createSession(userId) {
    const sessionPath = getSessionPath(userId);

    if (!fs.existsSync(sessionPath)) {
        fs.mkdirSync(sessionPath, { recursive: true });
    }

    const { state, saveCreds } = await useMultiFileAuthState(sessionPath);
    const { version } = await fetchLatestBaileysVersion();

    const logger = pino({ level: 'silent' });

    const sock = makeWASocket({
        version,
        auth: state,
        printQRInTerminal: false,
        logger,
        browser: ['ZapPro', 'Chrome', '1.0.0'],
    });

    sessions[userId] = {
        sock,
        status: 'conectando',
        qrCode: null,
        phone: null,
    };

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect, qr } = update;
        const session = sessions[userId];

        // Ignora eventos de sockets antigos ou sessões já removidas
        if (!session || session.sock !== sock) {
            return;
        }

        if (qr) {
            const qrBase64 = await generateQRBase64(qr);
            session.status = 'aguardando_qr';
            session.qrCode = qrBase64;

            await notifyDjango({
                type: 'connection.update',
                userId,
                status: 'aguardando_qr',
                qrCode: qrBase64,
            });
        }

        if (connection === 'open') {
            session.status = 'conectado';
            session.qrCode = null;

            const phone = sock.user?.id?.split(':')[0] || '';
            session.phone = phone;

            await notifyDjango({
                type: 'connection.update',
                userId,
                status: 'conectado',
                phone,
            });

            console.log(`Usuário ${userId} conectado: ${phone}`);
        }

        if (connection === 'close') {
            const statusCode = lastDisconnect?.error?.output?.statusCode;
            const shouldReconnect = statusCode !== DisconnectReason.loggedOut;

            session.status = 'desconectado';

            await notifyDjango({
                type: 'connection.update',
                userId,
                status: 'desconectado',
            });

            if (shouldReconnect) {
                console.log(`Reconectando usuário ${userId}...`);
                setTimeout(() => createSession(userId), 3000);
            } else {
                delete sessions[userId];
                // Remove sessão ao deslogar
                if (fs.existsSync(sessionPath)) {
                    fs.rmSync(sessionPath, { recursive: true, force: true });
                }
            }
        }
    });

    // Recebe mensagens
    sock.ev.on('messages.upsert', async ({ messages }) => {
        for (const msg of messages) {
            if (msg.key.fromMe) continue;

            const jid = msg.key.remoteJid;
            if (!jid || jid.endsWith('@g.us')) continue; // Ignora grupos

            const messageContent =
                msg.message?.conversation ||
                msg.message?.extendedTextMessage?.text ||
                '';

            if (!messageContent) continue;

            // WhatsApp recente usa @lid; senderPn traz o número real quando disponível
            const senderPn = msg.key.senderPn || '';
            const phone = senderPn
                ? senderPn.split('@')[0].split(':')[0]
                : jid.split('@')[0];
            const pushName = msg.pushName || '';

            await notifyDjango({
                type: 'message.received',
                userId,
                from: phone,
                jid,
                message: messageContent,
                pushName,
            });
        }
    });

    return sessions[userId];
}

/**
 * POST /connect - Inicia conexão WhatsApp
 */
app.post('/connect', authMiddleware, async (req, res) => {
    const { userId } = req.body;
    if (!userId) {
        return res.status(400).json({ success: false, error: 'userId obrigatório' });
    }

    try {
        if (sessions[userId]?.status === 'conectado') {
            return res.json({
                success: true,
                status: 'conectado',
                phone: sessions[userId].phone,
            });
        }

        const session = await createSession(userId);

        // Aguarda QR Code por até 10 segundos
        let attempts = 0;
        while (!session.qrCode && session.status !== 'conectado' && attempts < 20) {
            await new Promise((r) => setTimeout(r, 500));
            attempts++;
        }

        res.json({
            success: true,
            status: session.status,
            qrCode: session.qrCode,
            phone: session.phone,
        });
    } catch (err) {
        console.error('Erro ao conectar:', err);
        res.status(500).json({ success: false, error: err.message });
    }
});

/**
 * POST /disconnect - Desconecta sessão
 */
app.post('/disconnect', authMiddleware, async (req, res) => {
    const { userId } = req.body;
    if (!userId) {
        return res.status(400).json({ success: false, error: 'userId obrigatório' });
    }

    try {
        const session = sessions[userId];
        if (session?.sock) {
            await session.sock.logout();
        }
        delete sessions[userId];

        const sessionPath = getSessionPath(userId);
        if (fs.existsSync(sessionPath)) {
            fs.rmSync(sessionPath, { recursive: true, force: true });
        }

        await notifyDjango({
            type: 'connection.update',
            userId,
            status: 'desconectado',
        });

        res.json({ success: true, status: 'desconectado' });
    } catch (err) {
        console.error('Erro ao desconectar:', err);
        res.status(500).json({ success: false, error: err.message });
    }
});

/**
 * GET /status/:userId - Status da conexão
 */
app.get('/status/:userId', authMiddleware, (req, res) => {
    const userId = req.params.userId;
    const session = sessions[userId];

    if (!session) {
        return res.json({
            success: true,
            status: 'desconectado',
            qrCode: null,
            phone: null,
        });
    }

    res.json({
        success: true,
        status: session.status,
        qrCode: session.qrCode,
        phone: session.phone,
    });
});

/**
 * POST /send - Envia mensagem (com atraso e indicador digitando opcionais)
 */
app.post('/send', authMiddleware, async (req, res) => {
    const { userId, phone, jid, message, delaySeconds = 0, showTyping = false } = req.body;

    if (!userId || !message || (!phone && !jid)) {
        return res.status(400).json({ success: false, error: 'Parâmetros incompletos' });
    }

    const session = sessions[userId];
    if (!session || session.status !== 'conectado') {
        return res.status(400).json({ success: false, error: 'WhatsApp não conectado' });
    }

    try {
        const targetJid = jid || (phone.includes('@') ? phone : `${phone}@s.whatsapp.net`);
        const delayMs = Math.min(Math.max(Number(delaySeconds) || 0, 0), 60) * 1000;

        if (showTyping && delayMs > 0) {
            try {
                await session.sock.presenceSubscribe(targetJid);
                await session.sock.sendPresenceUpdate('composing', targetJid);
            } catch (presenceErr) {
                console.warn('Aviso ao enviar presença digitando:', presenceErr.message);
            }
            await sleep(delayMs);
            try {
                await session.sock.sendPresenceUpdate('paused', targetJid);
            } catch (presenceErr) {
                console.warn('Aviso ao pausar presença:', presenceErr.message);
            }
        } else if (delayMs > 0) {
            await sleep(delayMs);
        }

        await session.sock.sendMessage(targetJid, { text: message });
        console.log(
            `Mensagem enviada para ${targetJid} (user ${userId}, atraso ${delayMs}ms, digitando ${!!showTyping})`
        );
        res.json({ success: true });
    } catch (err) {
        console.error('Erro ao enviar:', err);
        res.status(500).json({ success: false, error: err.message });
    }
});

/**
 * GET /health - Health check
 */
app.get('/health', (req, res) => {
    res.json({ status: 'ok', sessions: Object.keys(sessions).length });
});

app.listen(PORT, () => {
    console.log(`ZapPro WhatsApp Service rodando na porta ${PORT}`);
    console.log(`Sessões em: ${SESSIONS_DIR}`);
});
