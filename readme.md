# Account JSON to Token JSON

这是一个单文件 HTML 工具，用来把账号类 JSON 批量转换成 token JSON，并支持将结果打包为 ZIP 下载。

对应页面文件：[`sub2api_to_cpa.html`](/c:/Projects/WebCosmos/sub2api_to_cpa.html)

## 功能概览

- 提供左右双栏界面：左侧粘贴源 JSON，右侧显示转换结果。
- 支持点击 `Convert` 执行转换。
- 支持点击 `Download ZIP` 将转换后的多个 JSON 文件一次性打包下载。
- 使用 `JSZip` CDN 在浏览器端完成 ZIP 打包，无需后端。

## 页面结构总结

这个 HTML 是一个纯前端页面，主要由三部分组成：

- 顶部标题区：说明这是一个 “Account JSON to Token JSON” 转换工具。
- 中间双文本框区域：输入原始 JSON，输出转换后的 JSON。
- 底部操作区：包含转换按钮、下载 ZIP 按钮，以及状态提示文本。

样式上采用浅色卡片布局、圆角边框和响应式双栏设计，在窄屏下会自动切换为单栏。

## 支持的输入格式

脚本会从以下几种结构中提取账号对象：

- 直接传入对象数组：`[{...}, {...}]`
- 传入带 `accounts` 字段的对象：`{ "accounts": [...] }`
- 直接传入单个账号对象，并且对象内存在 `credentials`

如果没有识别到可用账号对象，页面会报错：

`No account object found. Expected object.accounts[] or direct account object.`

## 转换逻辑

每个账号对象会读取其 `credentials` 字段，并输出一个新的 token 对象，主要字段如下：

- `id_token`
- `refresh_token`
- `account_id`
- `last_refresh`
- `email`
- `type`
- `expired`

转换细节：

- `account_id` 优先使用 `credentials.chatgpt_account_id`，没有则退回到 `credentials.account_id`
- `email` 优先使用 `credentials.email`，没有则使用 `account.name`
- `type` 固定写为 `codex`
- `expired` 通过 `expires_at` 转成 ISO UTC 时间，无法解析时输出空字符串
- `last_refresh` 由 `_token_version` 推导时间戳；如果缺失，则退回到当前时间

## 文件命名规则

下载 ZIP 时，每个 JSON 文件会按以下格式命名：

`{proxyPrefix}_{email}_{tokenEpoch}.json`

其中：

- `proxyPrefix` 从 `account.proxy_key` 中提取数字
- `email` 会做文件名安全处理，例如把 `@` 替换为 `_`
- `tokenEpoch` 为秒级时间戳

如果 `proxy_key` 中无法提取数字，则默认使用 `token` 作为前缀。

## 下载行为

- 转换成功后，结果会显示在右侧文本框
- 点击 `Download ZIP` 后，会把当前转换结果全部写入 ZIP
- ZIP 文件名格式为：`tokens_时间戳.zip`
- 如果 `JSZip` 加载失败，页面会提示检查网络

## 运行方式

这是一个静态 HTML 文件，直接用浏览器打开即可运行。

注意：

- 由于 `JSZip` 通过 CDN 引入，首次使用需要浏览器能够访问外网资源
- 所有转换都在本地浏览器内完成，不依赖服务端
