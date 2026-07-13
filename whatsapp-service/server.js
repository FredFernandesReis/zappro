/**
 * ZapPro - Serviço WhatsApp com Baileys 7 (suporte LID)
 * Cada usuário possui sessão isolada em sessoes/usuario_{id}/
 */

import express from 'express';
import path from 'path';
import fs from 'fs';
import axios from 'axios';
import QRCode from 'qrcode';
import pino from 'pino';
import { fileURLToPath } from 'url';

import makeWASocket, {
    useMultiFileAuthState,
    DisconnectReason,
    fetchLatestBaileysVersion,
    makeCacheableSignalKeyStore,
} from '@whiskeysockets/baileys';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 3001;
const API_SECRET = process.env.API_SECRET || 'um-segredo-forte';
const DJANGO_WEBHOOK_URL = process.env.DJANGO_WEBHOOK_URL || 'http://127.0.0.1:8000/whatsapp/webhook/';
const SESSIONS_DIR = path.join(__dirname, '..', 'sessoes');
const MAX_RECONNECT_ATTEMPTS = 5;

const sessions = {};
const reconnectAttempts = {};
/** Cache de mensagens enviadas para getMessage (obrigatório no Baileys 7 / retries) */
const messageStores = {};

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

if (!fs.existsSync(SESSIONS_DIR)) {
    fs.mkdirSync(SESSIONS_DIR, { recursive: true });
}

function authMiddleware(req, res, next) {
    const secret = req.headers['x-api-secret'];
    if (secret !== API_SECRET) {
        return res.status(401).json({ success: false, error: 'Unauthorized' });
    }
    next();
}

async function notifyDjango(data) {
    try {
        await axios.post(DJANGO_WEBHOOK_URL, data, {
            headers: {
                'Content-Type': 'application/json',
                'X-API-Secret': API_SECRET,
            },
            timeout: 60000,
            validateStatus: (status) => status >= 200 && status < 300,
        });
    } catch (err) {
        const status = err.response?.status;
        const detail = err.response?.data ? JSON.stringify(err.response.data) : '';
        console.error(
            `Erro ao notificar Django [${DJANGO_WEBHOOK_URL}] status=${status || 'n/a'}: ${err.message} ${detail}`
        );
    }
}

async function generateQRBase64(qrString) {
    return QRCode.toDataURL(qrString, { width: 256, margin: 2 });
}

function getSessionPath(userId) {
    return path.join(SESSIONS_DIR, `usuario_${userId}`);
}

function clearSessionFiles(userId) {
    const sessionPath = getSessionPath(userId);
    if (fs.existsSync(sessionPath)) {
        fs.rmSync(sessionPath, { recursive: true, force: true });
    }
}

function getMessageStore(userId) {
    if (!messageStores[userId]) {
        messageStores[userId] = new Map();
    }
    return messageStores[userId];
}

function rememberOutgoingMessage(userId, sent) {
    if (!sent?.key?.id || !sent.message) return;
    const store = getMessageStore(userId);
    store.set(sent.key.id, sent.message);
    // evita crescimento infinito
    if (store.size > 200) {
        const firstKey = store.keys().next().value;
        store.delete(firstKey);
    }
}

async function resolveTargetJid(sock, phone, jid) {
    const cleanPhone = String(phone || '').replace(/\D/g, '');
    const candidates = [];

    if (jid && String(jid).includes('@')) {
        candidates.push(String(jid).trim());
    }

    if (cleanPhone && cleanPhone.length >= 10 && cleanPhone.length <= 15) {
        const pnJid = `${cleanPhone}@s.whatsapp.net`;
        try {
            const lid =
                (await sock.signalRepository?.lidMapping?.getLIDForPN?.(pnJid)) ||
                null;
            if (lid) candidates.push(lid);
        } catch (err) {
            console.warn('getLIDForPN falhou:', err.message);
        }
        candidates.push(pnJid);
    }

    return [...new Set(candidates.filter(Boolean))];
}

async function createSession(userId) {
    const sessionPath = getSessionPath(userId);
    const existing = sessions[userId];

    if (existing?.sock) {
        try {
            existing.sock.ev.removeAllListeners();
            existing.sock.end?.(undefined);
        } catch (_) {
            // ignore
        }
    }

    if (!fs.existsSync(sessionPath)) {
        fs.mkdirSync(sessionPath, { recursive: true });
    }

    const { state, saveCreds } = await useMultiFileAuthState(sessionPath);
    const { version } = await fetchLatestBaileysVersion();
    const logger = pino({ level: 'silent' });
    const msgStore = getMessageStore(userId);

    const sock = makeWASocket({
        version,
        auth: {
            creds: state.creds,
            keys: makeCacheableSignalKeyStore(state.keys, logger),
        },
        printQRInTerminal: false,
        logger,
        browser: ['ZapPro', 'Chrome', '1.0.0'],
        syncFullHistory: false,
        markOnlineOnConnect: false,
        getMessage: async (key) => {
            const msg = msgStore.get(key.id);
            return msg || undefined;
        },
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
        if (!session || session.sock !== sock) return;

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
            reconnectAttempts[userId] = 0;
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
            const loggedOut = statusCode === DisconnectReason.loggedOut;
            const replaced = statusCode === DisconnectReason.connectionReplaced;
            const attempts = reconnectAttempts[userId] || 0;
            const shouldReconnect = !loggedOut && !replaced && attempts < MAX_RECONNECT_ATTEMPTS;

            session.status = 'desconectado';
            await notifyDjango({
                type: 'connection.update',
                userId,
                status: 'desconectado',
            });

            if (shouldReconnect) {
                reconnectAttempts[userId] = attempts + 1;
                const delay = Math.min(3000 * reconnectAttempts[userId], 30000);
                console.log(
                    `Reconectando usuário ${userId} (tentativa ${reconnectAttempts[userId]}/${MAX_RECONNECT_ATTEMPTS}) em ${delay}ms...`
                );
                setTimeout(() => createSession(userId), delay);
            } else {
                console.log(
                    `Sessão do usuário ${userId} encerrada (code=${statusCode}, tentativas=${attempts}).`
                );
                delete sessions[userId];
                delete reconnectAttempts[userId];
                if (loggedOut || attempts >= MAX_RECONNECT_ATTEMPTS) {
                    clearSessionFiles(userId);
                    delete messageStores[userId];
                }
            }
        }
    });

    sock.ev.on('messages.upsert', async ({ messages, type }) => {
        for (const msg of messages) {
            if (msg.key.fromMe) {
                // guarda próprias para retries cryptográficos
                if (msg.message && msg.key?.id) {
                    msgStore.set(msg.key.id, msg.message);
                }
                continue;
            }

            // ignora status/notificações
            if (type === 'append' && !msg.message) continue;

            const jid = msg.key.remoteJid;
            if (!jid || jid.endsWith('@g.us') || jid === 'status@broadcast') continue;

            const messageContent =
                msg.message?.conversation ||
                msg.message?.extendedTextMessage?.text ||
                msg.message?.ephemeralMessage?.message?.extendedTextMessage?.text ||
                msg.message?.ephemeralMessage?.message?.conversation ||
                '';

            if (!messageContent) continue;

            const senderPn = msg.key.senderPn || msg.key.remoteJidAlt || '';
            let phone = '';
            if (senderPn) {
                phone = String(senderPn).split('@')[0].split(':')[0].replace(/\D/g, '');
            } else if (jid.endsWith('@s.whatsapp.net')) {
                phone = jid.split('@')[0].split(':')[0].replace(/\D/g, '');
            }

            // Se chegou @lid e temos mapping, tenta PN
            if (!phone && jid.endsWith('@lid')) {
                try {
                    const pn = await sock.signalRepository?.lidMapping?.getPNForLID?.(jid);
                    if (pn) phone = String(pn).split('@')[0].replace(/\D/g, '');
                } catch (_) {
                    // ignore
                }
            }

            await notifyDjango({
                type: 'message.received',
                userId,
                from: phone || jid.split('@')[0],
                jid,
                message: messageContent,
                pushName: msg.pushName || '',
            });
        }
    });

    return sessions[userId];
}

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

        reconnectAttempts[userId] = 0;
        const session = await createSession(userId);

        let attempts = 0;
        while (!session.qrCode && session.status !== 'conectado' && attempts < 20) {
            await sleep(500);
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
        delete reconnectAttempts[userId];
        delete messageStores[userId];
        clearSessionFiles(userId);

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

app.post('/send', authMiddleware, async (req, res) => {
    const {
        userId,
        phone,
        jid,
        message,
        delaySeconds = 0,
        showTyping = false,
    } = req.body;

    if (!userId || !message || (!phone && !jid)) {
        return res.status(400).json({ success: false, error: 'Parâmetros incompletos' });
    }

    const session = sessions[userId];
    if (!session || session.status !== 'conectado' || !session.sock) {
        return res.status(400).json({ success: false, error: 'WhatsApp não conectado' });
    }

    try {
        const candidates = await resolveTargetJid(session.sock, phone, jid);
        if (!candidates.length) {
            return res.status(400).json({
                success: false,
                error: 'Não foi possível resolver o destinatário da mensagem',
            });
        }

        const delayMs = Math.min(Math.max(Number(delaySeconds) || 0, 0), 20) * 1000;
        let lastError = null;

        for (const targetJid of candidates) {
            try {
                // Digitando no mesmo JID que vai receber a mensagem
                if (showTyping) {
                    try {
                        await session.sock.presenceSubscribe(targetJid);
                        await session.sock.sendPresenceUpdate('composing', targetJid);
                    } catch (presenceErr) {
                        console.warn('Presença digitando ignorada:', presenceErr.message);
                    }
                }

                if (delayMs > 0) {
                    await sleep(delayMs);
                }

                if (showTyping) {
                    try {
                        await session.sock.sendPresenceUpdate('paused', targetJid);
                    } catch (_) {
                        // ignore
                    }
                }

                const sent = await session.sock.sendMessage(targetJid, {
                    text: String(message),
                });
                const messageId = sent?.key?.id;
                if (!messageId) {
                    throw new Error('WhatsApp não confirmou o envio da mensagem');
                }

                rememberOutgoingMessage(userId, sent);
                console.log(
                    `OK envio user=${userId} jid=${targetJid} id=${messageId} delay=${delayMs}ms typing=${!!showTyping}`
                );
                return res.json({ success: true, jid: targetJid, messageId });
            } catch (err) {
                lastError = err;
                console.warn(`Falha ao enviar para ${targetJid}: ${err.message}`);
            }
        }

        throw lastError || new Error('Falha ao enviar mensagem');
    } catch (err) {
        console.error('Erro ao enviar:', err);
        res.status(500).json({ success: false, error: err.message || String(err) });
    }
});

app.get('/health', (req, res) => {
    res.json({
        status: 'ok',
        baileys: '7',
        sessions: Object.keys(sessions).length,
        webhook: DJANGO_WEBHOOK_URL,
    });
});

app.listen(PORT, () => {
    console.log(`ZapPro WhatsApp Service (Baileys 7) na porta ${PORT}`);
    console.log(`Webhook Django: ${DJANGO_WEBHOOK_URL}`);
    console.log(`Sessões em: ${SESSIONS_DIR}`);
});
