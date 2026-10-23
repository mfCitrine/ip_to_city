# GitHub 发布指南

## 一、创建远程仓库

由于本机未安装 `gh` CLI，需要你在 GitHub 网页上创建仓库（也可用命令行，见下方"方式二"）。

### 方式一：网页创建（推荐）

1. 登录 https://github.com/mfCitrine
2. 右上角 **+** → **New repository**
3. 填写：
   - Repository name: `ip_to_city`
   - Description: `多源融合的高精度开源 IP 地理位置库（支持 Go/Java/PHP/Python）`
   - 选择 **Public**（公开，开源项目）
   - ⚠️ **不要**勾选 "Add a README"、"Add .gitignore"、"Add a license"（本项目已自带，避免冲突）
4. 点击 **Create repository**

### 方式二：命令行（需先装 gh）

```bash
gh auth login        # 登录 mfCitrine 账号
gh repo create ip_to_city --public --description "多源融合的高精度开源 IP 地理位置库"
```

## 二、推送本地代码

创建仓库后，在本地项目目录执行：

```bash
cd E:\pro\ipgeo
git remote add origin https://github.com/mfCitrine/ip_to_city.git
git branch -M main
git push -u origin main
```

> 如果本地默认分支是 `master`，用 `git branch -M main` 统一为 `main`。

## 三、配置 GitHub Actions 密钥（可选，用于纯真增强）

新流程（`build_final.py`）自动下载 DB-IP CSV + iptoasn，无需 MaxMind 凭证即可构建。

唯一可选增强是**纯真 qqwry.dat**：因其 License 不允许打包进公开仓库再分发，
需自行托管到私有对象存储/私有 gist，再通过 Secret 传入 URL：

1. 仓库页面 → **Settings** → **Secrets and variables** → **Actions**
2. 点击 **New repository secret**，添加：
   - 名称 `CZ88_URL`，值填你的纯真 qqwry.dat 的私有下载 URL（可公开访问的直链）

> 不配置 `CZ88_URL` 也能正常构建：中国区会降级为 DB-IP 中国段兜底，
> 省市区精度略低于纯真，但流程全自动。

## 四、手动触发首次构建

1. 仓库页面 → **Actions** 标签
2. 左侧选择 **build-and-release**
3. 点击 **Run workflow** → **Run workflow**

首次构建会下载数据源、融合、产出 `ipgeo-city.mmdb` / `ipgeo-city.csv` 并自动发布 Release。

## 五、验证

构建成功后：
- **Actions** 显示绿色 ✓
- **Releases** 出现 `IP 数据库 <run_id>`，含 `ipgeo-city.mmdb`、`ipgeo-city.csv`

## 注意事项

- 纯真 `qqwry.dat` **不提交**到仓库（License 限制）。可通过 `CZ88_URL` Secret 在 CI 中可选拉取。
- `corrections.csv`（人工订正）**会提交**到仓库，构建时自动合并（最高优先级）。
- 数据 License 为 CC BY-SA 4.0（见 LICENSE-DATA），保留各数据源署名。
