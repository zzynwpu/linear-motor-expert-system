# 从本机到 Render 上线：逐步操作清单

这份清单面向第一次部署 Python Web 应用的用户。目标是把当前项目部署到 Render，并获得一个可以直接发给其他人使用的网址。

---

## 1. 你最终会得到什么

完成后，你会得到一个公网地址，形式大致如下：

`https://linear-motor-expert-system.onrender.com`

别人只要打开这个网址，就能使用你的系统，不需要连接你的电脑，也不需要安装 Python。

---

## 2. 上线前准备

你需要准备以下账号：

1. GitHub 账号
2. Render 账号

建议准备以下资料：

1. 一个英文仓库名
2. 一个英文服务名
3. 可选：你自己的域名

---

## 3. 第一步：确认本地项目已经可运行

在 PowerShell 中进入项目目录：

```powershell
cd "D:\Codex project"
```

启动本地服务：

```powershell
python -m uvicorn app.web:app --reload
```

在浏览器打开：

`http://127.0.0.1:8000`

如果本地页面能正常打开，再继续下一步。

---

## 4. 第二步：把项目上传到 GitHub

### 4.1 在 GitHub 创建仓库

1. 打开 GitHub
2. 点击右上角 `+`
3. 点击 `New repository`
4. Repository name 填一个英文名，例如：
   `linear-motor-expert-system`
5. 选择 `Public`
6. 点击 `Create repository`

### 4.2 把本地项目推送到 GitHub

在项目目录打开 PowerShell，依次执行：

```powershell
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin 你的GitHub仓库地址
git push -u origin main
```

例如：

```powershell
git remote add origin https://github.com/yourname/linear-motor-expert-system.git
git push -u origin main
```

如果 Git 要求登录，就按照 GitHub 提示完成登录。

---

## 5. 第三步：在 Render 创建服务

### 5.1 连接 GitHub

1. 打开 Render 控制台
2. 点击 `New +`
3. 选择 `Web Service`
4. 选择 `Connect GitHub`
5. 按提示授权 Render 访问你的 GitHub 仓库

官方说明：

- [Connect GitHub](https://render.com/docs/github)

### 5.2 选择你的仓库

在仓库列表中找到你的项目：

`linear-motor-expert-system`

点击 `Connect`

### 5.3 填写服务参数

建议按下面填写：

- Name：`linear-motor-expert-system`
- Branch：`main`
- Runtime：`Python 3`
- Build Command：`pip install -r requirements.txt`
- Start Command：`uvicorn app.web:app --host 0.0.0.0 --port $PORT`

如果页面中出现 Python 版本相关设置，建议使用 `.python-version` 指定的版本。

官方说明：

- [Deploy a FastAPI App](https://render.com/docs/deploy-fastapi)
- [Setting Your Python Version](https://render.com/docs/python-version)

### 5.4 创建服务

点击 `Create Web Service`

接下来 Render 会自动：

1. 拉取你的 GitHub 代码
2. 安装依赖
3. 启动服务
4. 分配公网地址

---

## 6. 第四步：等待部署完成

部署成功后，Render 页面通常会显示：

- `Live`
- 一个 `onrender.com` 结尾的网址

例如：

`https://linear-motor-expert-system.onrender.com`

你现在就可以把这个网址发给别人使用。

---

## 7. 第五步：以后如何更新网站

以后你改完代码，不需要重新手动上传整个网站，只需要：

1. 改本地代码
2. 提交到 GitHub
3. Render 自动重新部署

命令如下：

```powershell
git add .
git commit -m "update"
git push
```

官方说明：

- [Deploying on Render](https://render.com/docs/deploys)

---

## 8. 第六步：如何绑定你自己的域名

如果你不想使用 `onrender.com` 的默认网址，可以绑定自己的域名，比如：

`motor.yourcompany.com`

操作步骤：

1. 在 Render 服务页面进入 `Settings`
2. 找到 `Custom Domains`
3. 点击 `Add Custom Domain`
4. 输入你的域名
5. 按 Render 提示去域名服务商配置 DNS
6. 返回 Render 点击 `Verify`

官方说明：

- [Custom Domains on Render](https://render.com/docs/custom-domains)

---

## 9. 常见报错与处理

### 9.1 部署日志里提示找不到模块

常见原因：

- 启动命令写错
- 项目目录结构和启动入口不一致

当前项目正确启动命令是：

```text
uvicorn app.web:app --host 0.0.0.0 --port $PORT
```

### 9.2 页面打开 404 或启动失败

检查：

1. Render 中是否真的部署成功
2. Start Command 是否正确
3. `requirements.txt` 是否已经上传

### 9.3 Python 版本异常

本项目根目录已经提供：

`/.python-version`

内容为：

`3.12`

如果 Render 仍使用了不同版本，可以在 Render 控制台里补充环境变量：

- Key：`PYTHON_VERSION`
- Value：`3.12.10` 或其他你想固定的 3.12.x 版本

### 9.4 改了代码但网站没更新

检查：

1. 是否已经 `git push`
2. Render 是否连接的是正确仓库和正确分支
3. Render 的自动部署是否开启

---

## 10. 推荐你第一次上线的最简路线

如果你想一步一步稳妥完成，建议按这个顺序：

1. 本地运行成功
2. GitHub 建仓库
3. 代码推送到 GitHub
4. Render 新建 Web Service
5. 填写 Build Command 和 Start Command
6. 等待生成公网地址
7. 打开公网地址自测
8. 发给别人使用

---

## 11. 当前项目里与你部署直接相关的文件

- [.python-version](D:\Codex project\.python-version)
- [requirements.txt](D:\Codex project\requirements.txt)
- [render.yaml](D:\Codex project\render.yaml)
- [Dockerfile](D:\Codex project\Dockerfile)
- [web.py](D:\Codex project\app\web.py)

---

## 12. 一句话总结

你只需要完成三件事：

1. 把项目推到 GitHub
2. 在 Render 连接这个 GitHub 仓库
3. 等它生成公网网址

之后把那个网址发给别人即可。
