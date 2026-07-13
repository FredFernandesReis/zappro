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
        DJANGO_WEBHOOK_URL: "http://127.0.0.1:8000/whatsapp/webhook/",
      },
    },
  ],
};
