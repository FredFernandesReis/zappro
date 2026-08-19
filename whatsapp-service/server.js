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
const DJANGO_WEBHOOK_URL = process.env.DJANGO_WEBHOOK_URL || 'http://127.0.0.1:8001/whatsapp/webhook/';
const SESSIONS_DIR = path.join(__dirname, '..', 'sessoes');
const MAX_RECONNECT_ATTEMPTS = 5;

const sessions = {};
const reconnectAttempts = {};
/** Cache de mensagens enviadas para getMessage (obrigatório no Baileys 7 / retries) */
const messageStores = {};
/** IDs recebidos recentemente, para ignorar reentregas do mesmo evento. */
const incomingMessageIds = {};
/** Fila por conta: impede dois envios simultâneos do mesmo WhatsApp. */
const sendQueues = {};
const lastSentAt = {};

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function isDuplicateIncoming(userId, messageId) {
    if (!messageId) return false;

    const now = Date.now();
    const ttlMs = 10 * 60 * 1000;
    const seen = incomingMessageIds[userId] || new Map();

    // Limpeza leve e limitada para não crescer memória indefinidamente.
    if (seen.size > 500) {
        for (const [id, timestamp] of seen.entries()) {
            if (now - timestamp > ttlMs) seen.delete(id);
        }
    }

    if (seen.has(messageId)) return true;
    seen.set(messageId, now);
    incomingMessageIds[userId] = seen;
    return false;
}

function enqueueSend(userId, job) {
    const previous = sendQueues[userId] || Promise.resolve();
    const current = previous.catch(() => {}).then(job);
    sendQueues[userId] = current;

    current
        .finally(() => {
            if (sendQueues[userId] === current) delete sendQueues[userId];
        })
        .catch(() => {});

    return current;
}

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

function looksLikeRealPhone(digits) {
    if (!digits || digits.length < 10 || digits.length > 15) return false;
    if (digits.startsWith('55')) {
        return digits.length === 12 || digits.length === 13;
    }
    return digits.length <= 13;
}

/**
 * Destino simples e estável:
 * 1) número @s.whatsapp.net (melhor entrega)
 * 2) jid da conversa (fallback — inclusive @lid)
 */
async function resolveTargetJid(sock, phone, jid) {
    const cleanPhone = String(phone || '').replace(/\D/g, '');
    const rawJid = jid && String(jid).includes('@') ? String(jid).trim() : '';
    const candidates = [];

    if (looksLikeRealPhone(cleanPhone)) {
        candidates.push(`${cleanPhone}@s.whatsapp.net`);
    }

    if (rawJid && !candidates.includes(rawJid)) {
        candidates.push(rawJid);
    }

    if (!candidates.length && cleanPhone) {
        candidates.push(`${cleanPhone}@s.whatsapp.net`);
    }

    return [...new Set(candidates.filter(Boolean))];
}

function audioMimetypeFromPath(filePath) {
    const ext = path.extname(String(filePath || '')).toLowerCase();
    const map = {
        '.ogg': 'audio/ogg; codecs=opus',
        '.opus': 'audio/ogg; codecs=opus',
        '.mp3': 'audio/mpeg',
        '.m4a': 'audio/mp4',
        '.aac': 'audio/aac',
        '.wav': 'audio/wav',
        '.webm': 'audio/webm',
    };
    return map[ext] || 'audio/ogg; codecs=opus';
}

function isSafeAudioPath(filePath) {
    const resolved = path.resolve(String(filePath || ''));
    const mediaRoot = path.resolve(path.join(__dirname, '..', 'media'));
    return resolved === mediaRoot || resolved.startsWith(mediaRoot + path.sep);
}

/** Mantém "digitando..." ou "gravando áudio..." visível durante o atraso. */
async function runTypingIndicator(sock, jids, durationMs, presence = 'composing') {
    const targets = [...new Set((jids || []).filter(Boolean))];
    if (!targets.length || durationMs <= 0) return;
    const state = presence === 'recording' ? 'recording' : 'composing';

    try {
        await sock.sendPresenceUpdate('available');
    } catch (_) {
        // ignore
    }

    const composing = async () => {
        for (const target of targets) {
            try {
                await sock.presenceSubscribe(target);
                await sock.sendPresenceUpdate(state, target);
            } catch (err) {
                console.warn(`presença falhou em ${target}: ${err.message}`);
            }
        }
    };

    await composing();
    console.log(`${state} ${durationMs}ms -> ${targets.join(', ')}`);

    const started = Date.now();
    while (Date.now() - started < durationMs) {
        const remaining = durationMs - (Date.now() - started);
        await sleep(Math.min(2500, remaining));
        if (Date.now() - started >= durationMs) break;
        await composing();
    }

    for (const target of targets) {
        try {
            await sock.sendPresenceUpdate('paused', target);
        } catch (_) {
            // ignore
        }
    }
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
        // necessário para "digitando..." (presence) funcionar de forma confiável
        markOnlineOnConnect: true,
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
                    delete incomingMessageIds[userId];
                    delete sendQueues[userId];
                    delete lastSentAt[userId];
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

            if (isDuplicateIncoming(userId, msg.key?.id)) {
                console.log(`Mensagem recebida duplicada ignorada user=${userId} id=${msg.key?.id}`);
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
        delete incomingMessageIds[userId];
        delete sendQueues[userId];
        delete lastSentAt[userId];
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
        audioPath = '',
        audioPtt = false,
    } = req.body;

    const hasText = Boolean(message);
    const hasAudio = Boolean(audioPath);
    if (!userId || (!hasText && !hasAudio) || (!phone && !jid)) {
        return res.status(400).json({ success: false, error: 'Parâmetros incompletos' });
    }

    try {
        const result = await enqueueSend(userId, async () => {
            const session = sessions[userId];
            if (!session || session.status !== 'conectado' || !session.sock) {
                const error = new Error('WhatsApp não conectado');
                error.statusCode = 400;
                throw error;
            }

            const candidates = await resolveTargetJid(session.sock, phone, jid);
            if (!candidates.length) {
                const error = new Error('Não foi possível resolver o destinatário da mensagem');
                error.statusCode = 400;
                throw error;
            }

            let audioBuffer = null;
            let audioMimetype = '';
            if (hasAudio) {
                if (!isSafeAudioPath(audioPath)) {
                    const error = new Error('Caminho de áudio inválido');
                    error.statusCode = 400;
                    throw error;
                }
                const resolvedAudio = path.resolve(String(audioPath));
                if (!fs.existsSync(resolvedAudio)) {
                    const error = new Error('Arquivo de áudio não encontrado');
                    error.statusCode = 400;
                    throw error;
                }
                audioBuffer = fs.readFileSync(resolvedAudio);
                if (audioBuffer.length > 2.5 * 1024 * 1024) {
                    const error = new Error('Áudio acima de 2 MB');
                    error.statusCode = 400;
                    throw error;
                }
                audioMimetype = audioMimetypeFromPath(resolvedAudio);
            }

            // Mesmo com várias requisições concorrentes, mantém intervalo entre envios.
            const minGapMs = 2500 + Math.floor(Math.random() * 2500);
            const elapsed = Date.now() - (lastSentAt[userId] || 0);
            if (elapsed < minGapMs) {
                await sleep(minGapMs - elapsed);
            }

            // Digitando / gravando: mínimo 3s para ficar visível; máx 25s
            const requestedDelay = Math.min(Math.max(Number(delaySeconds) || 0, 0), 25);
            const typingMs = showTyping || hasAudio
                ? Math.max(requestedDelay, hasAudio ? 2 : 3) * 1000
                : requestedDelay * 1000;

            const chatJid = jid && String(jid).includes('@') ? String(jid).trim() : null;
            const typingTargets = [...new Set([chatJid, ...candidates].filter(Boolean))];

            if (showTyping || hasAudio) {
                await runTypingIndicator(
                    session.sock,
                    typingTargets,
                    typingMs,
                    hasAudio ? 'recording' : 'composing'
                );
            } else if (typingMs > 0) {
                await sleep(typingMs);
            }

            const content = audioBuffer
                ? {
                    audio: audioBuffer,
                    mimetype: audioMimetype,
                    ptt: Boolean(audioPtt),
                }
                : { text: String(message) };

            let lastError = null;

            for (const targetJid of candidates) {
                try {
                    const sent = await session.sock.sendMessage(targetJid, content);
                    const messageId = sent?.key?.id;
                    if (!messageId) {
                        throw new Error('WhatsApp não confirmou o envio da mensagem');
                    }

                    rememberOutgoingMessage(userId, sent);
                    lastSentAt[userId] = Date.now();
                    console.log(
                        `OK envio user=${userId} jid=${targetJid} id=${messageId} delay=${typingMs}ms typing=${!!showTyping} audio=${!!audioBuffer}`
                    );
                    return { success: true, jid: targetJid, messageId };
                } catch (err) {
                    lastError = err;
                    console.warn(`Falha ao enviar para ${targetJid}: ${err.message}`);
                }
            }

            throw lastError || new Error('Falha ao enviar mensagem');
        });

        return res.json(result);
    } catch (err) {
        console.error('Erro ao enviar:', err);
        res
            .status(err.statusCode || 500)
            .json({ success: false, error: err.message || String(err) });
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
