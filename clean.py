import os
import psutil
import customtkinter as ctk
from threading import Thread
from tkinter import messagebox, Menu
import subprocess

# Устанавливаем общую тему
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class DiskAnalyzer(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- НАСТРОЙКИ ОКНА ---
        self.title("Cleaner v1.5")
        self.geometry("950x650")
        self.resizable(False, False) # Окно фиксированное, чтобы интерфейс не плыл

        # --- ЛОГИЧЕСКИЕ ПЕРЕМЕННЫЕ ---
        self.is_scanning = False
        self.categories = {
            "Видео": [".mp4", ".mkv", ".mov", ".avi"],
            "Архивы": [".zip", ".rar", ".7z", ".tar"],
            "Образы/EXE": [".iso", ".exe", ".msi"],
            "Музыка": [".mp3", ".wav", ".flac"]
        }
        self.check_vars = {} # Здесь будем хранить состояния галочек

        # --- СЕТКА (GRID) ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- БОКОВАЯ ПАНЕЛЬ (SIDEBAR) ---
        self.sidebar = ctk.CTkFrame(self, width=260, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        # Логотип
        self.logo = ctk.CTkLabel(self.sidebar, text="Cleaner PC", 
                                font=ctk.CTkFont(size=22, weight="bold"))
        self.logo.pack(pady=(30, 20))

        # Выбор диска
        ctk.CTkLabel(self.sidebar, text="Выберите область:").pack()
        self.disk_var = ctk.StringVar(value="Все диски")
        self.disk_menu = ctk.CTkOptionMenu(self.sidebar, values=self.get_disks(), variable=self.disk_var)
        self.disk_menu.pack(pady=10, padx=20)

        # ФИЛЬТРЫ (Галочки)
        ctk.CTkLabel(self.sidebar, text="Фильтр типов:", font=ctk.CTkFont(weight="bold")).pack(pady=(15, 5))
        for cat in self.categories.keys():
            var = ctk.BooleanVar(value=True)
            cb = ctk.CTkCheckBox(self.sidebar, text=cat, variable=var, checkbox_width=20, checkbox_height=20)
            cb.pack(padx=30, pady=3, anchor="w")
            self.check_vars[cat] = var

        # РАЗДЕЛИТЕЛЬ
        ctk.CTkFrame(self.sidebar, height=2, fg_color="#333").pack(fill="x", padx=20, pady=15)

        # ГАЛОЧКА "ВЕСЬ ДИСК" (Режим без фильтров)
        self.all_files_var = ctk.BooleanVar(value=False)
        self.all_files_cb = ctk.CTkCheckBox(self.sidebar, text="ВЕСЬ ДИСК (без фильтров)", 
                                           variable=self.all_files_var, text_color="#ffcc00",
                                           font=ctk.CTkFont(size=12, weight="bold"))
        self.all_files_cb.pack(padx=20, pady=5, anchor="w")

        # КНОПКИ УПРАВЛЕНИЯ
        self.scan_btn = ctk.CTkButton(self.sidebar, text="Начать поиск", 
                                     command=self.start_scan_thread, fg_color="#24a1de", height=40)
        self.scan_btn.pack(pady=(25, 5), padx=20)
        
        self.stop_btn = ctk.CTkButton(self.sidebar, text="Остановить", 
                                     command=self.stop_scan, state="disabled", fg_color="#c0392b")
        self.stop_btn.pack(pady=5, padx=20)

        # --- ОСНОВНАЯ ПАНЕЛЬ ---
        self.main_frame = ctk.CTkFrame(self, corner_radius=15, fg_color="#1a1a1a")
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        
        self.status_label = ctk.CTkLabel(self.main_frame, text="Настройте фильтры и нажмите поиск", text_color="gray")
        self.status_label.pack(pady=10)

        # Текстовое поле для вывода файлов
        self.log_box = ctk.CTkTextbox(self.main_frame, state="disabled", border_width=1, border_color="#333", font=("Consolas", 12))
        self.log_box.pack(padx=20, pady=(0, 20), fill="both", expand=True)

        # КОНТЕКСТНОЕ МЕНЮ (ПКМ)
        self.context_menu = Menu(self, tearoff=0, bg="#2b2b2b", fg="white", borderwidth=0)
        self.context_menu.add_command(label="📂 Открыть папку", command=self.open_path)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🗑️ Удалить файл", command=self.delete_file)
        
        self.log_box.bind("<Button-3>", self.show_menu)

    # --- ЛОГИКА ПРОГРАММЫ ---

    def get_disks(self):
        """Сканирует систему на наличие дисков"""
        disks = [d.device for d in psutil.disk_partitions() if 'fixed' in d.opts or d.fstype]
        return ["Все диски"] + disks

    def show_menu(self, event):
        """Вызов меню правой кнопкой мыши"""
        self.context_menu.tk_popup(event.x_root, event.y_root)

    def stop_scan(self):
        """Остановка процесса"""
        self.is_scanning = False
        self.status_label.configure(text="🛑 Остановка процесса...")

    def start_scan_thread(self):
        """Запуск сканирования в отдельном потоке"""
        self.is_scanning = True
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        
        self.scan_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        
        Thread(target=self.scan_disk, daemon=True).start()

    def scan_disk(self):
        selection = self.disk_var.get()
        scan_all_mode = self.all_files_var.get()
        
        # Определяем цели сканирования
        if selection == "Все диски":
            targets = [d.device for d in psutil.disk_partitions() if 'fixed' in d.opts or d.fstype]
        else:
            targets = [selection]

        # Собираем список разрешенных расширений
        allowed_exts = []
        if not scan_all_mode:
            for cat, var in self.check_vars.items():
                if var.get():
                    allowed_exts.extend(self.categories[cat])

        try:
            for target in targets:
                if not self.is_scanning: break
                self.status_label.configure(text=f"🔍 Сканирую: {target}")

                for root, dirs, files in os.walk(target):
                    if not self.is_scanning: break
                    
                    for name in files:
                        if not self.is_scanning: break
                        
                        # Проверка на режим "Весь диск" или фильтры
                        ext = os.path.splitext(name)[1].lower()
                        if not scan_all_mode and ext not in allowed_exts:
                            continue

                        filepath = os.path.join(root, name)
                        try:
                            size = os.path.getsize(filepath)
                            # Выводим только файлы больше 50МБ, чтобы не засорять память
                            if size > 5 * 1024 * 1024:
                                mb_size = size / (1024 * 1024)
                                self.log_box.configure(state="normal")
                                self.log_box.insert("end", f"📁 {mb_size:.1f} MB | {filepath}\n")
                                self.log_box.see("end")
                                self.log_box.configure(state="disabled")
                        except: continue
            
            self.status_label.configure(text="✅ Поиск завершен успешно!")
        except Exception as e:
            self.status_label.configure(text=f"⚠️ Ошибка: {str(e)}")
        
        self.scan_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.is_scanning = False

    def get_selected_path(self):
        """Парсит выделенную строку в логе для получения пути"""
        try:
            line = self.log_box.get("sel.first", "sel.last")
            return line.split("|")[-1].strip()
        except:
            messagebox.showwarning("Внимание", "Сначала выделите строку с файлом мышкой")
            return None

    def open_path(self):
        """Открывает проводник на нужном файле"""
        path = self.get_selected_path()
        if path and os.path.exists(path):
            subprocess.run(['explorer', '/select,', os.path.normpath(path)])

    def delete_file(self):
        """Удаляет выбранный файл"""
        path = self.get_selected_path()
        if path and os.path.exists(path):
            if messagebox.askyesno("Удаление", f"Удалить файл безвозвратно?\n\n{path}"):
                try:
                    os.remove(path)
                    messagebox.showinfo("Готово", "Файл успешно удален")
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось удалить: {e}")

if __name__ == "__main__":
    app = DiskAnalyzer()
    app.mainloop()