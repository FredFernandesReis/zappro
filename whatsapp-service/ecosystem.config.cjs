module.exports = {
  apps: [
    {
      name: "zappro-whatsapp",
      script: "server.js",
      cwd: __dirname,
      instances: 1,
      exec_mode: "fork",
      autorestart: true,
      watch: false,
      max_memory_restart: "500M",
      env: {
        PORT: 3001,
        API_SECRET: "um-segredo-forte",
        // VPS: Django ZapPro está em 8001 (8000 é outro projeto)
        DJANGO_WEBHOOK_URL: "http://127.0.0.1:8001/whatsapp/webhook/",
      },
    },
  ],
};
