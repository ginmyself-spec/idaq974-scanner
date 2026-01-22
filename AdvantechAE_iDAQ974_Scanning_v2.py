import customtkinter as ctk
import tkinter.messagebox as tkmb
import subprocess
import threading
import re
import os
import platform

# ==========================================
# [設定區] 請在此處調整字體大小與縮放比例
# ==========================================

# 1. 全域縮放比例 (預設 1.0, 想要放大 20% 請設為 1.2, 想要超大請設 1.5)
# 這是最快讓介面變大且不跑版的方法
UI_SCALING_FACTOR = 1.2 

# 2. 個別字體設定 (字型, 大小, 粗細)
FONTS = {
    "button": ("Roboto Medium", 16),      # 按鈕文字
    "label": ("Roboto", 14),              # 一般標籤
    "label_bold": ("Roboto", 14, "bold"), # 粗體標籤
    "result_ip": ("Roboto", 28, "bold"),  # 掃描到的 IP (特大)
    "log": ("Consolas", 13),              # 下方 Log 文字 (等寬字體)
    "code": ("Consolas", 12)              # Return Code 顯示
}

# ==========================================

# 設定外觀與縮放
ctk.set_appearance_mode("System") 
ctk.set_default_color_theme("blue")
ctk.set_widget_scaling(UI_SCALING_FACTOR) # 套用全域縮放

class ScannerPanel(ctk.CTkFrame):
    def __init__(self, parent, os_mode, exe_path):
        super().__init__(parent, fg_color="transparent")
        self.os_mode = os_mode
        self.exe_path = exe_path
        self.found_ip = None
        
        self.init_ui()

    def init_ui(self):
        # Grid Configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # --- Top Control Area ---
        self.control_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.control_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        # Scan Button
        self.btn_scan = ctk.CTkButton(
            self.control_frame, 
            text="Scan Device", 
            command=self.start_scan,
            font=FONTS["button"],
            height=45 # 稍微增加高度以容納大字體
        )
        self.btn_scan.pack(side="left", padx=(0, 10))
        
        # Copy Button
        self.btn_copy = ctk.CTkButton(
            self.control_frame, 
            text="Copy IP", 
            command=self.copy_to_clipboard, 
            state="disabled",
            fg_color="gray",
            font=FONTS["button"],
            height=45
        )
        self.btn_copy.pack(side="left", padx=10)
        
        # Status Label
        self.lbl_status = ctk.CTkLabel(
            self.control_frame, 
            text="Ready", 
            text_color=("gray60", "gray80"),
            font=FONTS["label"]
        )
        self.lbl_status.pack(side="left", padx=15)

        # --- Path Display ---
        self.path_frame = ctk.CTkFrame(self)
        self.path_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        
        lbl_path_title = ctk.CTkLabel(self.path_frame, text=f"Target Executable ({self.os_mode}):", font=FONTS["label_bold"])
        lbl_path_title.pack(anchor="w", padx=10, pady=(5,0))
        
        self.entry_path = ctk.CTkEntry(self.path_frame, font=FONTS["label"])
        self.entry_path.insert(0, self.exe_path)
        self.entry_path.configure(state='readonly')
        self.entry_path.pack(fill="x", padx=10, pady=5)

        # --- Result Area ---
        self.result_frame = ctk.CTkFrame(self, corner_radius=10)
        self.result_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=10)
        
        ctk.CTkLabel(self.result_frame, text="SCAN RESULT", font=FONTS["label_bold"], text_color="gray").pack(pady=(10,0))
        
        self.lbl_result_ip = ctk.CTkLabel(
            self.result_frame, 
            text="--", 
            font=FONTS["result_ip"],
            text_color=("black", "white")
        )
        self.lbl_result_ip.pack(pady=10)
        
        self.lbl_return_code = ctk.CTkLabel(self.result_frame, text="Code: -", font=FONTS["code"], text_color="gray")
        self.lbl_return_code.pack(pady=(0, 10))

        # --- Log Area ---
        ctk.CTkLabel(self, text="CLI Raw Output", font=FONTS["label_bold"]).grid(row=3, column=0, sticky="w", pady=(10, 0))
        
        self.txt_log = ctk.CTkTextbox(self, font=FONTS["log"])
        self.txt_log.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=5)
        
        self.grid_rowconfigure(4, weight=1)

    def start_scan(self):
        self.btn_scan.configure(state="disabled")
        self.btn_copy.configure(state="disabled", fg_color="gray")
        self.found_ip = None
        
        self.lbl_status.configure(text="Scanning...", text_color="#E67E22")
        self.txt_log.delete("1.0", "end")
        self.lbl_result_ip.configure(text="Scanning...", text_color=("black", "white"))
        self.lbl_return_code.configure(text="Code: ...", text_color="gray")
        
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
        lines = text.splitlines()
        device_regex = r'(?i)iDAQ[-]?974'

        for line in lines:
            if re.search(device_regex, line):
                # Regex logic from previous version (v6)
                match = re.search(r'IP:\s*([^,\s]+)', line)
                if match:
                    return match.group(1), line
        return None, None

    def update_ui_success(self, output_text, code):
        found_ip, found_line = self.extract_idaq_ip(output_text)
        self.found_ip = found_ip
        
        def _update():
            self.txt_log.insert("end", output_text)
            self.lbl_return_code.configure(text=f"Code: {code}", text_color="#3498DB")

            if found_ip:
                self.lbl_result_ip.configure(text=f"{found_ip}", text_color="#2ECC71")
                self.lbl_status.configure(text="Device Found", text_color="#2ECC71")
                self.btn_copy.configure(state="normal", fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])
            else:
                self.lbl_result_ip.configure(text="Not Found", text_color="#E74C3C")
                self.lbl_status.configure(text="Target Missing", text_color="gray")
                self.btn_copy.configure(state="disabled", fg_color="gray")
                
            self.btn_scan.configure(state="normal")
            
        self.after(0, _update)

    def update_ui_error(self, error_text, code):
        def _update():
            self.txt_log.insert("end", error_text)
            self.lbl_return_code.configure(text=f"Code: {code}", text_color="#E74C3C")
            self.lbl_result_ip.configure(text="Error", text_color="#E74C3C")
            self.lbl_status.configure(text="Execution Failed", text_color="#E74C3C")
            self.btn_scan.configure(state="normal")
            
        self.after(0, _update)

    def copy_to_clipboard(self):
        if self.found_ip:
            self.clipboard_clear()
            self.clipboard_append(self.found_ip)
            self.update()
            tkmb.showinfo("Copied", f"IP {self.found_ip} copied!")

class IDAQScannerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("iDAQ-974 Scanner Pro")
        # 根據縮放比例自動調整視窗初始大小，避免內容被切掉
        base_width = 700
        base_height = 650
        scaled_width = int(base_width * UI_SCALING_FACTOR)
        scaled_height = int(base_height * UI_SCALING_FACTOR)
        
        self.geometry(f"{scaled_width}x{scaled_height}")
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        self.tabview.add("Windows System")
        self.tabview.add("Linux System")
        
        # Windows Fonts are set slightly smaller usually, but CTK handles cross-platform well
        win_path = r"C:\Advantech\DAQNavi\DeviceManager(Console)\dndev.exe"
        self.panel_win = ScannerPanel(self.tabview.tab("Windows System"), os_mode="Windows", exe_path=win_path)
        self.panel_win.pack(fill="both", expand=True)

        linux_path = "/opt/advantech/tools/dndev"
        self.panel_linux = ScannerPanel(self.tabview.tab("Linux System"), os_mode="Linux", exe_path=linux_path)
        self.panel_linux.pack(fill="both", expand=True)

if __name__ == "__main__":
    app = IDAQScannerApp()
    app.mainloop()
