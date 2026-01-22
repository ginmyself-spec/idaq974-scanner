import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import re
import os
import platform

class ScannerPanel(ttk.Frame):
    def __init__(self, parent, os_mode, exe_path):
        super().__init__(parent, padding="10")
        self.os_mode = os_mode
        self.exe_path = exe_path
        self.found_ip = None
        
        self.init_ui()

    def init_ui(self):
        # --- Top Control Area ---
        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.btn_scan = ttk.Button(control_frame, text="Scan Device", command=self.start_scan)
        self.btn_scan.pack(side=tk.LEFT, padx=5)
        
        self.btn_copy = ttk.Button(control_frame, text="Copy IP", command=self.copy_to_clipboard, state=tk.DISABLED)
        self.btn_copy.pack(side=tk.LEFT, padx=5)
        
        self.lbl_status = ttk.Label(control_frame, text="Ready", foreground="blue")
        self.lbl_status.pack(side=tk.LEFT, padx=10)

        # --- Path Display ---
        path_frame = ttk.Frame(self)
        path_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(path_frame, text=f"Target Path ({self.os_mode}):", font=("Arial", 8, "italic")).pack(anchor=tk.W)
        self.entry_path = ttk.Entry(path_frame, width=60)
        self.entry_path.insert(0, self.exe_path)
        self.entry_path.pack(fill=tk.X)
        self.entry_path.config(state='readonly')

        # --- Result Area ---
        result_frame = ttk.LabelFrame(self, text="Scan Result", padding="10")
        result_frame.pack(fill=tk.X, pady=5)
        
        self.lbl_result_ip = ttk.Label(result_frame, text="No Scan Yet", font=("Helvetica", 12, "bold"))
        self.lbl_result_ip.pack(anchor=tk.CENTER)
        
        self.lbl_return_code = ttk.Label(result_frame, text="Return Code: -", font=("Consolas", 10), foreground="gray")
        self.lbl_return_code.pack(anchor=tk.CENTER, pady=(5,0))

        # --- Log Area ---
        log_frame = ttk.LabelFrame(self, text="CLI Raw Output", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.txt_log = tk.Text(log_frame, height=10, font=("Consolas", 9))
        self.txt_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.txt_log.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_log['yscrollcommand'] = scrollbar.set

    def start_scan(self):
        self.btn_scan.config(state=tk.DISABLED)
        self.btn_copy.config(state=tk.DISABLED)
        self.found_ip = None
        
        self.lbl_status.config(text="Scanning...", foreground="orange")
        self.txt_log.delete(1.0, tk.END)
        self.lbl_result_ip.config(text="Scanning...", foreground="black")
        self.lbl_return_code.config(text="Return Code: ...", foreground="gray")
        
        current_path = self.entry_path.get()
        
        thread = threading.Thread(target=self.run_cli_command, args=(current_path,))
        thread.daemon = True
        thread.start()

    def run_cli_command(self, target_path):
        if not os.path.exists(target_path):
            pass 

        try:
            cmd = [target_path, "/ecns"]
            
            kwargs = {
                "capture_output": True,
                "text": True,
                "errors": "replace"
            }
            
            if self.os_mode == "Windows":
                kwargs["encoding"] = "cp950"
                if platform.system() == "Windows":
                    kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            else:
                kwargs["encoding"] = "utf-8"
            
            result = subprocess.run(cmd, **kwargs)
            code = result.returncode

            if code == 0:
                self.update_ui_success(result.stdout, code)
            else:
                error_msg = f"STDERR:\n{result.stderr}\n\nSTDOUT:\n{result.stdout}"
                self.update_ui_error(error_msg, code)

        except FileNotFoundError:
             self.update_ui_error(f"Error: Executable not found at\n{target_path}", -1)
        except Exception as e:
            self.update_ui_error(f"Exception Occurred:\n{str(e)}", -1)

    def extract_idaq_ip(self, text):
        """
        修正後的邏輯：針對 "IP:數值" 的結構進行抓取。
        Target format: "IP:fe80::76fe:48ff:febd:fe0%9,"
        """
        lines = text.splitlines()
        device_regex = r'(?i)iDAQ[-]?974'

        for line in lines:
            # 1. 確認該行是否為 iDAQ-974
            if re.search(device_regex, line):
                
                # 2. 針對結構抓取：尋找 "IP:" 之後的內容
                # regex 解釋:
                # IP:\s* -> 匹配字串 "IP:" 加上選擇性的空白
                # ([^,\s]+) -> 捕捉群組：只要 "不是逗號" 且 "不是空白" 的所有字元
                # 這樣就能完整抓到 fe80::...%9，並在遇到逗號時停止
                match = re.search(r'IP:\s*([^,\s]+)', line)
                
                if match:
                    # group(1) 就是我們要的完整 IP 字串
                    return match.group(1), line
        
        return None, None

    def update_ui_success(self, output_text, code):
        found_ip, found_line = self.extract_idaq_ip(output_text)
        self.found_ip = found_ip
        
        def _update():
            self.txt_log.insert(tk.END, output_text)
            self.lbl_return_code.config(text=f"Return Code: {code}", foreground="blue")

            if found_ip:
                self.lbl_result_ip.config(text=f"Detected: {found_ip}", foreground="green")
                self.lbl_status.config(text="Target Device Detected", foreground="green")
                self.btn_copy.config(state=tk.NORMAL)
            else:
                self.lbl_result_ip.config(text="IDAQ-974* Not Found", foreground="red")
                self.lbl_status.config(text="Scan Complete (Target Missing)", foreground="black")
                self.btn_copy.config(state=tk.DISABLED)
                
            self.btn_scan.config(state=tk.NORMAL)
            
        self.after(0, _update)

    def update_ui_error(self, error_text, code):
        def _update():
            self.txt_log.insert(tk.END, error_text)
            self.lbl_return_code.config(text=f"Return Code: {code}", foreground="red")
            self.lbl_result_ip.config(text="Scan Error", foreground="red")
            self.lbl_status.config(text="Error", foreground="red")
            self.btn_scan.config(state=tk.NORMAL)
            
        self.after(0, _update)

    def copy_to_clipboard(self):
        if self.found_ip:
            self.clipboard_clear()
            self.clipboard_append(self.found_ip)
            self.update()
            messagebox.showinfo("Copied", f"IP {self.found_ip} copied to clipboard!")

class IDAQScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("iDAQ-974 IP Scanner (Context Aware)")
        self.root.geometry("650x580")
        
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # --- Page 1: Windows ---
        win_path = r"C:\Advantech\DAQNavi\DeviceManager(Console)\dndev.exe"
        self.tab_win = ScannerPanel(self.notebook, os_mode="Windows", exe_path=win_path)
        self.notebook.add(self.tab_win, text="  Windows System  ")
        
        # --- Page 2: Linux ---
        linux_path = "/opt/advantech/tools/dndev"
        self.tab_linux = ScannerPanel(self.notebook, os_mode="Linux", exe_path=linux_path)
        self.notebook.add(self.tab_linux, text="  Linux System  ")

if __name__ == "__main__":
    root = tk.Tk()
    app = IDAQScannerApp(root)
    root.mainloop()
