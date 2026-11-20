# 部署清单

站点是纯静态的：`build.py` 产出的 `dist/` 整目录放到静态根目录即可，不需要后端。
下面按顺序走一遍，每步都有验收方式。

站点的核心思想是「需求即提示词」：每条提示词都要把做什么、对谁、达成什么、怎么验收说清楚（详见根目录 `README.md` 与 `docs/philosophy.md`）。部署后仍是纯静态页面。

## 0. 当前状态

`prompt.guanjihuan.com` **还没有 DNS 记录**，下面第 1 步做完之前，页面里的
canonical、og:url、sitemap 都还只是「预埋好的指向」，外部访问不了。

## 1. DNS 解析

在域名 DNS 服务商处添加一条 A 记录：

| 类型 | 主机 | 值 | TTL |
| --- | --- | --- | --- |
| A | `prompt` | 服务器公网 IP | 600 |

解析生效后确认：

```bash
nslookup prompt.guanjihuan.com     # 应返回服务器公网 IP
curl -I http://prompt.guanjihuan.com/   # 证书还没签发时返回 301/200 均可
```

DNS 未生效时签发证书会失败（`Let's Encrypt` 校验不到），这一步不能跳过。

## 2. 服务器准备

```bash
sudo apt update && sudo apt install -y nginx rsync
sudo mkdir -p /var/www/prompt.guanjihuan.com
```

## 3. 证书

```bash
sudo certbot --nginx -d prompt.guanjihuan.com
sudo certbot renew --dry-run      # 确认自动续期可用
```

签发前 80 端口必须能从公网访问（`deploy/nginx.conf` 里的 80 端口块就是为此准备的）。

## 4. Nginx 配置

```bash
sudo cp deploy/nginx.conf /etc/nginx/conf.d/prompt.guanjihuan.com.conf
# 按注释替换证书路径与 root 目录
sudo nginx -t && sudo systemctl reload nginx
```

## 5. 发布

```bash
python build.py                          # 本地构建
bash deploy/deploy.sh user@host          # 上传 dist/ 并在远端校验
```

`deploy/deploy.sh` 会先本地构建，再 `rsync --delete` 同步，最后在远端确认
`index.html` 与 `404.html` 都在。

## 6. 验收清单

- [ ] `https://prompt.guanjihuan.com/` 打开正常，浏览器控制台无报错
- [ ] `https://prompt.guanjihuan.com/robots.txt` 与 `/sitemap.xml` 可访问
- [ ] `https://prompt.guanjihuan.com/assets/og.png` 可访问（分享预览图）
- [ ] 任意不存在的路径返回自带的 404 页面，而不是 Nginx 默认页
- [ ] `https://prompt.guanjihuan.com/#<条目 id>` 能直接定位到对应条目
- [ ] 分享到社交平台时能看到预览图与标题
- [ ] 证书有效期与自动续期正常（`certbot renew --dry-run`）

## 7. 日常维护

- 内容改动后跑 `python build.py && python -m pytest tests/` 再发布
- `dist/` 已纳入版本管理，也可以直接在服务器上 `git pull && python build.py`
- GitHub Actions（`.github/workflows/ci.yml`）会在每次推送与 PR 上跑校验、
  测试、构建与文案审计，并上传 `dist/` 作为构建产物
