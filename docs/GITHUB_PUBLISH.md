# GitHub 发布指南

## 一、创建远程仓库

由于本机未安装 `gh` CLI，需要你在 GitHub 网页上创建仓库（也可用命令行，见下方"方式二"）。

### 方式一：网页创建（推荐）

1. 登录 https://github.com/mfphp
2. 右上角 **+** → **New repository**
3. 填写：
   - Repository name: `ip_to_city`
   - Description: `多源融合的高精度开源 IP 地理位置库（支持 Go/Java/PHP/Python）`
   - 选择 **Public**（公开，开源项目）
   - ⚠️ **不要**勾选 "Add a README"、"Add .gitignore"、"Add a license"（本项目已自带，避免冲突）
4. 点击 **Create repository**

### 方式二：命令行（需先装 gh）

```bash
gh auth login        # 登录 mfphp 账号
gh repo create ip_to_city --public --description "多源融合的高精度开源 IP 地理位置库"
```

## 二、推送本地代码

创建仓库后，在本地项目目录执行：

```bash
cd E:\pro\ipgeo
git remote add origin https://github.com/mfphp/ip_to_city.git
git branch -M main
git push -u origin main
```

> 如果本地默认分支是 `master`，用 `git branch -M main` 统一为 `main`。

## 三、配置 GitHub Actions 密钥（用于自动周更）

为了让 GitHub Actions 能在海外 runner 上下载 GeoLite2 并自动构建，需要配置密钥：

1. 仓库页面 → **Settings** → **Secrets and variables** → **Actions**
2. 点击 **New repository secret**，添加两个：
   - 名称 `MAXMIND_ACCOUNT_ID`，值填你的 MaxMind Account ID
   - 名称 `MAXMIND_LICENSE_KEY`，值填你的 MaxMind License Key

> ⚠️ 密钥切勿明文写入代码或文档（GitHub 会触发 Push Protection 拦截）。
> 请从 MaxMind 账号后台的 Manage License Keys 页面复制。

> 这样 GitHub Actions（美国服务器）就能下载 GeoLite2（绕过国内 451 限制），
> 每周自动构建并发 Release。

## 四、手动触发首次构建

配置好密钥后：

1. 仓库页面 → **Actions** 标签
2. 左侧选择 **build-and-release**
3. 点击 **Run workflow** → **Run workflow**

首次构建会下载数据源、融合、产出 `ipgeo-city.mmdb` 并自动发布 Release。

## 五、验证

构建成功后：
- **Actions** 显示绿色 ✓
- **Releases** 出现 `IP 数据库 <run_id>`，含 `ipgeo-city.mmdb`、`ipgeo-city.csv`

## 注意事项

- 纯真 `qqwry.dat` **不提交**到仓库（License 限制），仅本地校验用。已在 `.gitignore` 中排除 `data/raw/`。
- 数据 License 为 CC BY-SA 4.0（见 LICENSE-DATA），保留各数据源署名。
