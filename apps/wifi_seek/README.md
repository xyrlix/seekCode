# WiFi 连接工具

一个用 Python 编写的 WiFi 连接工具，可以扫描周围的 WiFi 热点，并从密码库中尝试连接指定的 WiFi 网络。

## 功能特点

1. **WiFi 热点扫描**：扫描并显示周围所有可用的 WiFi 热点名称(SSID)
2. **密码库连接**：从密码文件中读取密码列表，自动尝试连接指定的 WiFi 热点
3. **连接结果反馈**：明确显示连接成功或失败状态
4. **成功凭证保存**：自动保存成功连接的 SSID 和密码到本地文件

## 支持的操作系统

- **Linux**
- **Windows**
- **macOS**

## 安装要求

- Python 3.10 或更高版本
- 管理员权限（部分系统需要）
- 依赖库：
  - pywifi

安装依赖库：
```bash
pip install pywifi
```

## 使用方法

### 1. 准备密码文件

创建一个名为 `password.txt` 的文件，每行包含一个密码：

```
12345678
password
88888888
87654321
```

### 2. 运行程序

```bash
python wifi_seek.py
```

### 3. 程序选项

- **选项 1**：搜索 WiFi 网络
- **选项 2**：使用密码连接 WiFi
- **选项 3**：顺序破解 WiFi (使用密码文件)
- **选项 4**：显示已成功连接的 WiFi 网络
- **选项 5**：退出程序

### 4. 连接 WiFi 步骤

1. 选择选项 2/3 开始连接过程
2. 输入要连接的 WiFi 名称
3. 对于选项 3，可指定密码文件路径（默认为 config/password.txt）
4. 程序将自动尝试连接 WiFi
5. 连接成功后，SSID 和密码将自动保存到 `config/successful_connections.json`，包含最后连接时间

## 文件说明

- `wifi_seek.py`：主程序文件，包含所有WiFi连接相关功能
- `config/password.txt`：密码库文件（需要手动创建）
- `config/successful_connections.json`：成功连接的WiFi信息（自动生成，JSON格式）

## 注意事项

### Linux 系统

- 需要安装 nmcli（通常在 NetworkManager 包中）
- 可能需要 root 权限：`sudo python wifi_seek.py`

### Windows 系统

- 需要以管理员身份运行命令提示符
- 确保 WLAN 服务已启动
- 程序使用 pywifi 库进行 WiFi 连接

### macOS 系统

- 需要允许终端访问 WiFi 权限
- 可能需要输入管理员密码

## 故障排除

### 扫描不到 WiFi

- 检查 WiFi 适配器是否已启用
- 确保您有足够的权限
- 尝试重新启动网络服务

### 连接失败

- 检查密码库中是否包含正确的密码
- 确认 WiFi 名称是否正确
- 检查 WiFi 信号强度
- 尝试手动连接验证密码是否正确
- 确保以管理员权限运行程序

### pywifi 错误

如果遇到 "Open handle failed" 错误：
- 确保以管理员权限运行程序
- 关闭可能正在使用 WiFi 的其他程序
- 重启 WLAN 服务

## 安全提示

1. 密码文件包含敏感信息，请妥善保管
2. successful_connections.json 文件会保存成功连接的密码，请确保文件权限安全
3. 仅在您有权访问的 WiFi 网络上使用此工具

## 许可证

MIT