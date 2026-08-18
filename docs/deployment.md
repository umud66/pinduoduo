# Deployment

目标：小白用户一键运行。

正式版本使用 PyInstaller 打包 Windows 应用，不需要安装 Python、数据库、Docker。

运行数据：

```text
data/app.db
data/secret.key
data/images
data/backups
```

备份整个 data 目录即可。