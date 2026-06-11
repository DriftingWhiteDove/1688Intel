# 导出 1688 Cookie 使用指南

本工具需要 1688 登录 Cookie 才能抓取商品数据。请按以下步骤操作：

## 方法一：使用 Chrome 开发者工具（推荐）

1. 打开 Chrome 浏览器，登录 [1688.com](https://www.1688.com)
2. 按 F12 打开开发者工具
3. 切换到 **Application**（应用）标签
4. 左侧找到 **Cookies** → 点击 `https://www.1688.com`
5. 点击任意 Cookie 条目，按 Ctrl+A 全选，再按 Ctrl+C 复制
6. 打开 [Cookie-Editor 扩展](https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)（推荐安装），点击扩展图标 → Export → Export as JSON
7. 将导出的 JSON 保存到 `backend/cookies.json`

## 方法二：手动创建 cookies.json

在 `backend/` 目录下创建 `cookies.json`，格式如下：

```json
[
    {"name": "cna", "value": "xxxx", "domain": ".1688.com"},
    {"name": "_m_h5_tk", "value": "xxxx", "domain": ".1688.com"},
    {"name": "_m_h5_tk_enc", "value": "xxxx", "domain": ".1688.com"},
    {"name": "x5sec", "value": "xxxx", "domain": ".1688.com"},
    {"name": "JSESSIONID", "value": "xxxx", "domain": ".1688.com"},
    {"name": "lid", "value": "xxxx", "domain": ".1688.com"}
]
```

> 注意：Cookie 有有效期，登录过期后需要重新导出。
