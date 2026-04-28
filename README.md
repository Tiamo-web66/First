# First

> 微信小程序安全调试工具 —— 基于 Frida + CDP 代理，支持 Windows / macOS 双平台，GUI 与 CLI 双模式

---

## 截图预览

### 控制台

![控制台](docs/screenshots/control.png)

### 路由导航

![路由导航](docs/screenshots/navigator.png)

### 云扫描

![云扫描](docs/screenshots/cloud.png)

### 调试开关（JSRPC / wx.cloud 调用）

![调试开关](docs/screenshots/debug-switches.png)

### 敏感信息提取

![敏感信息提取](docs/screenshots/extract.png)

### 常见问题

![常见问题](docs/screenshots/faq.png)
---

## 功能特性

- Frida 动态注入微信客户端，转发小程序调试协议
- CDP 代理桥接，Chrome DevTools 直连调试
- 路由枚举、分类与一键跳转
- 云函数调用监控与参数分析（动态 Hook + 静态扫描）
- UserScript 自动注入（支持 URL 匹配、run-at 时机控制）
- wxapkg 解密解包 + 敏感信息扫描（IP / 密钥 / 云存储 / JWT 等）
- 深色 / 浅色主题切换
- GUI（PySide6）与 CLI 双模式

---

## 环境要求

| 依赖 | 版本 |
|------|------|
| Python | >= 3.10 |
| frida | >= 17.0.0 |
| websockets | >= 12.0 |
| protobuf | >= 4.0.0 |
| PySide6 | >= 6.5.0 |
| pycryptodome | 最新版 |

安装依赖：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 支持的微信版本

### Windows

- WMPF 版本：11581, 11633, 13331, 13341, 13487, 13639, 13655, 13871, 13909, 14161, 14199, 14315, 16133, 16203, 16389, 16467, 16771, 16815, 16965, 17037, 17071, 17127, 18055, 18151, 18787, 18891, 18955, 19027, 19201
- 推荐微信版本：**4.1.0.30**
- 下载地址：[weixin/4.1.0.30](https://github.com/vs-olitus/wx-version/releases/tag/4.1.0.30)

### macOS

- WMPF 版本：18152, 18788
- 推荐微信版本：**4.1.7.30**
- 下载地址：[weixin/4.1.7.30](https://github.com/vs-olitus/wx-version/releases/tag/4.1.7.30)

---

## 快速开始

### Windows

**一键启动：** 双击 `启动.bat`，首次运行会自动安装依赖。

**手动启动：**

```bash
python gui.py
```

### macOS

**一键启动：** 终端执行 `./启动.sh`，首次运行会自动安装依赖。

**手动启动：**

```bash
python3 gui.py
```

启动后在主界面点击 **启动调试**，然后再打开小程序即可（请勿在启动调试前打开小程序）。

### CLI 模式

```bash
# 默认端口启动
python main.py

# 自定义端口
python main.py --cdp-port 62000

# 开启详细日志
python main.py --debug-main --debug-frida
```

### 连接 Chrome DevTools

启动后，在 Chrome 地址栏输入：

```
devtools://devtools/bundled/inspector.html?ws=127.0.0.1:62000
```

---

## macOS 注意事项

如果 Frida 注入报错，需要解除系统对进程附加的限制，任选其一：

**方案一：关闭 SIP（系统完整性保护）**

> 关闭后 Frida 才能正常注入进程。参考教程：[macOS SIP 开启关闭教程](https://cloud.tencent.com/developer/article/1496058)

**方案二：强制重签名 WeChat**

```bash
sudo codesign --force --deep --sign - /Applications/WeChat.app
```

---

## 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--debug-port` | `9421` | 远程调试服务端口 |
| `--cdp-port` | `62000` | CDP 代理监听端口 |
| `--debug-main` | 关闭 | 输出主进程调试日志 |
| `--debug-frida` | 关闭 | 输出 Frida 客户端日志 |
| `--scripts-dir` | `./userscripts` | UserScript 目录路径 |
| `--script` | — | 指定单个 .js 文件注入（可多次使用） |

---

## UserScript 注入

将 `.js` 脚本放入 `userscripts/` 目录，启动时自动加载并注入。也可手动指定：

```bash
python main.py --script ./my_hook.js --script ./another.js
```

---

## 打包为可执行文件

```bash
pyinstaller WMPFDebugger.spec
```

---

## 常见问题

**Q: Frida 已连接，但小程序端显示未连接或无法断点调试？**

确认操作顺序无误后，尝试以下步骤：

1. 彻底卸载微信并重启电脑（重要聊天记录请提前备份）
2. 删除 `C:\Users\用户名\AppData\Roaming\Tencent\xwechat\XPlugin\Plugins\RadiumWMPF` 下所有数字命名的文件夹
3. 再次重启后安装微信 4.1.0.30 版本
4. 检查上述路径，确认文件夹编号为 `16389`

---

## 参考项目

- [evi0s/WMPFDebugger](https://github.com/evi0s/WMPFDebugger)
- [0xsdeo/HeartK](https://github.com/0xsdeo/HeartK)
- [残笑/FindSomething](https://github.com/momosecurity/FindSomething)
- [进击的HACK / JSRPC 与调用 wx.cloud](https://mp.weixin.qq.com/s/hTlekrCPiMJCvsHYx7CAxw)
- [linguo2625469/WMPFDebugger-mac](https://github.com/linguo2625469/WMPFDebugger-mac)

---

## 致谢

感谢 **0xsdeo** 师傅的大力支持与思路提供。

---

## 交流群

群满 200 人后需要手动邀请，请加我拉群：

![微信二维码](https://s1.galgame.fun/imgb/u55/20260413_69dcaf1310fc4.jpg)

---

## 免责声明

本工具仅供安全研究与学习使用，请勿用于未授权的目标，使用者须自行承担相关法律责任。
