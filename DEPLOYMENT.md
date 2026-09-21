# Streamlit Community Cloud 部署说明

## 仓库要求

将本目录的全部项目文件上传到 GitHub 仓库根目录：

```text
app.py
requirements.txt
.streamlit/config.toml
table_cleaner/
data/
tests/
```

Community Cloud 会在仓库根目录执行应用，并从 `requirements.txt` 安装依赖。

## 部署步骤

1. 登录 [Streamlit Community Cloud](https://share.streamlit.io/)。
2. 使用 GitHub 账号授权访问目标仓库。
3. 点击 `Create app`。
4. 选择 GitHub 仓库：

   ```text
   excel表格数据统计可视化程序
   ```

5. 分支选择：

   ```text
   main
   ```

6. Main file path 填写：

   ```text
   app.py
   ```

7. 打开 `Advanced settings`，Python 版本选择 `3.13`。Cloud 当前默认是 3.12，本项目同时支持 3.12 和 3.13。
8. 自定义一个易记的 App URL，例如：

   ```text
   excel-data-statistics
   ```

9. 点击 `Deploy`。
10. 部署完成后访问：

    ```text
    https://excel-data-statistics.streamlit.app
    ```

## 公开应用注意事项

- 应用公开后，任何拿到链接的人都可以打开页面并上传文件。
- 上传文件会发送到 Streamlit Cloud 运行实例，不再只保存在运行应用的电脑上。
- 不要把身份证、手机号、财务记录、客户隐私等敏感数据上传到公开应用。
- 免费实例不适合处理几百 MB 以上的大文件。
- 应用重启后，之前的上传文件和会话状态不会保证保留。
- `.streamlit/secrets.toml` 已被 `.gitignore` 排除，不应提交到公开仓库。

## 本地与云端运行差异

本地运行：

```powershell
.\run_app.ps1
```

云端由 Streamlit Community Cloud 自动执行：

```bash
streamlit run app.py --server.headless=true
```

功能代码共用 `app.py` 和 `table_cleaner/`，无需维护两个版本。
