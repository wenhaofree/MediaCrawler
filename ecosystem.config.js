module.exports = {
  apps: [
    {
      name: "mediacrawler-sign-service",
      script: "services/sign_srv/server.js",
      cwd: "./",
      interpreter: "node",
      env: {
        NODE_ENV: "production",
        SIGN_SRV_PORT: 8999,
      },
      autorestart: true,
      restart_delay: 3000,
      max_restarts: 10,
      watch: false,
    },
    {
      name: "mediacrawler-webui-api",
      script: "uv",
      args: "run uvicorn api.main:app --host 0.0.0.0 --port 8080",
      cwd: "./",
      interpreter: "none",
      env: {
        PYTHONUNBUFFERED: "1",
      },
      autorestart: true,
      restart_delay: 3000,
      max_restarts: 10,
      watch: false,
    },
  ],
};

