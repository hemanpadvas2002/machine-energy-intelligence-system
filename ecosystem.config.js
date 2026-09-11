module.exports = {
  apps: [
    {
      name: "digital-transformation-portal",
      cwd: __dirname,
      script: "launch.py",
      interpreter: "./.venv/Scripts/python.exe",
      env: {
        PYTHONIOENCODING: "utf-8",
        AMTDC_STREAM_HOST: "0.0.0.0",
      },
      watch: false,
      autorestart: true,
      max_restarts: 10,
    },
  ],
};
