import tkinter as tk
import customtkinter as ctk
import numpy as np
import os
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

ctk.set_appearance_mode("light")


class BaseStationSimulator(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Symulator Stacji Bazowej")
        self.geometry("1400x900")

        self.running = False
        self.paused = False
        self.current_time = 0
        self.channels = []
        self.queue = []
        self.rejected_count = 0
        self.handled_count = 0

        self.full_log = []

        self.history_q, self.history_w, self.history_ro, self.time_axis = [], [], [], []

        self.setup_ui()

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)  # Parametry i Tabela
        self.grid_columnconfigure(1, weight=2)  # Kanały i Wykresy


        left_panel = ctk.CTkFrame(self)
        left_panel.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(left_panel, text="Parametry", font=("Arial", 16, "bold")).pack(pady=5)
        self.p_s = self.create_input(left_panel, "Liczba kanałów:", "10")
        self.p_q_len = self.create_input(left_panel, "Długość kolejki:", "10")
        self.p_lam = self.create_input(left_panel, "Natężenie ruchu [lambda]:", "1.0")
        self.p_n = self.create_input(left_panel, "Średnia rozmowa [N]:", "20")
        self.p_sig = self.create_input(left_panel, "Odchylenie [sigma]:", "5")
        self.p_min = self.create_input(left_panel, "Minimalny czas [s]:", "10")
        self.p_max = self.create_input(left_panel, "Maksymalny czas [s]:", "30")
        self.p_sim = self.create_input(left_panel, "Czas symulacji [s]:", "30")

        ctk.CTkLabel(left_panel, text="Wyniki", font=("Arial", 16, "bold")).pack(pady=10)


        self.table_frame = ctk.CTkScrollableFrame(left_panel, height=300)
        self.table_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.headers = ["Pois.", "Gaus.", "Klienci", "T.Przyj", "T.Obsł", "Lambda", "Mii", "Roi"]
        for i, h in enumerate(self.headers):
            ctk.CTkLabel(self.table_frame, text=h, font=("Arial", 10, "bold"), width=55).grid(row=0, column=i)


        btn_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        btn_frame.pack(pady=10)

        self.start_btn = ctk.CTkButton(btn_frame, text="START", width=100, command=self.toggle_simulation)
        self.start_btn.grid(row=0, column=0, padx=5, rowspan=2)

        ctk.CTkButton(btn_frame, text="Pause", width=60, command=lambda: setattr(self, 'paused', True)).grid(row=0,
                                                                                                             column=1,
                                                                                                             pady=2)
        ctk.CTkButton(btn_frame, text="Play", width=60, command=lambda: setattr(self, 'paused', False)).grid(row=1,
                                                                                                             column=1,
                                                                                                             pady=2)

        self.show_res_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(left_panel, text="Pokaż wyniki", variable=self.show_res_var).pack()

        right_panel = ctk.CTkFrame(self)
        right_panel.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(right_panel, text="Kanały (Czas do końca obsługi)", font=("Arial", 14, "bold")).pack(pady=5)
        self.canvas_ch = tk.Canvas(right_panel, height=100, bg="#eeeeee", highlightthickness=0)
        self.canvas_ch.pack(fill="x", padx=20)

        stats_txt_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        stats_txt_frame.pack(pady=5)
        self.lbl_stats = ctk.CTkLabel(stats_txt_frame, text="Obsłużone: 0  |  Odrzucone: 0  |  W kolejce: 0")
        self.lbl_stats.pack()

        self.fig = Figure(figsize=(6, 6), dpi=90)
        self.ax_q = self.fig.add_subplot(311);
        self.ax_w = self.fig.add_subplot(312);
        self.ax_ro = self.fig.add_subplot(313)
        self.fig.tight_layout(pad=2.0)
        self.canvas_plot = FigureCanvasTkAgg(self.fig, master=right_panel)
        self.canvas_plot.get_tk_widget().pack(fill="both", expand=True)

        self.lbl_time = ctk.CTkLabel(right_panel, text="Czas symulacji: 0 / 0", font=("Arial", 12, "bold"))
        self.lbl_time.pack(pady=5)

    def create_input(self, parent, text, default):
        f = ctk.CTkFrame(parent, fg_color="transparent");
        f.pack(fill="x", padx=20, pady=1)
        ctk.CTkLabel(f, text=text, width=170, anchor="w").pack(side="left")
        e = ctk.CTkEntry(f, width=60);
        e.insert(0, default);
        e.pack(side="right")
        return e

    def toggle_simulation(self):
        if not self.running:
            self.start_sim()
        else:
            self.stop_sim()

    def start_sim(self):
        try:
            self.S = int(self.p_s.get());
            self.max_q = int(self.p_q_len.get());
            self.lam = float(self.p_lam.get())
            self.sim_t = int(self.p_sim.get());
            self.N = float(self.p_n.get());
            self.sigma = float(self.p_sig.get())
            self.m_min = float(self.p_min.get());
            self.m_max = float(self.p_max.get())
        except:
            return

        self.channels = [0] * self.S
        self.queue = [];
        self.current_time = 0;
        self.full_log = []
        self.rejected_count = 0;
        self.handled_count = 0
        self.history_q, self.history_w, self.history_ro, self.time_axis = [], [], [], []

        for w in self.table_frame.winfo_children():
            if int(w.grid_info()["row"]) > 0: w.destroy()

        self.running = True;
        self.paused = False
        self.start_btn.configure(text="STOP", fg_color="red")
        self.run_step()

    def stop_sim(self):
        self.running = False
        self.start_btn.configure(text="START", fg_color=["#3B8ED0", "#1F6AA5"])
        self.save_to_txt()

    def run_step(self):
        if not self.running or self.current_time >= self.sim_t:
            self.stop_sim();
            return

        if not self.paused:
            self.current_time += 1

            for i in range(self.S):
                if self.channels[i] > 0: self.channels[i] -= 1


            arrivals = np.random.poisson(self.lam)
            last_gauss = 0

            for _ in range(arrivals):
                dur = int(max(self.m_min, min(self.m_max, np.random.normal(self.N, self.sigma))))
                last_gauss = dur


                placed = False
                for i in range(self.S):
                    if self.channels[i] == 0:
                        self.channels[i] = dur;
                        self.handled_count += 1;
                        placed = True;
                        break

                if not placed:
                    if len(self.queue) < self.max_q:
                        self.queue.append(dur)
                    else:
                        self.rejected_count += 1


            for i in range(self.S):
                if self.channels[i] == 0 and self.queue:
                    self.channels[i] = self.queue.pop(0);
                    self.handled_count += 1


            busy = sum(1 for c in self.channels if c > 0)
            roi = round(busy / self.S, 3) if self.S > 0 else 0
            mii = round(sum(self.channels) / busy, 2) if busy > 0 else 0
            q_avg = len(self.queue)
            w_avg = round(sum(self.queue) / q_avg, 2) if q_avg > 0 else 0

            step_data = [arrivals, last_gauss, q_avg, self.current_time, sum(self.channels), self.lam, mii, roi]
            self.full_log.append(step_data)

            if self.show_res_var.get():
                row_idx = len(self.full_log)
                for col, val in enumerate(step_data):
                    ctk.CTkLabel(self.table_frame, text=str(val), font=("Arial", 9)).grid(row=row_idx, column=col)

            self.time_axis.append(self.current_time)
            self.history_q.append(q_avg);
            self.history_w.append(w_avg);
            self.history_ro.append(roi)
            self.update_plots()
            self.update_channels_canvas()
            self.lbl_stats.configure(
                text=f"Obsłużone: {self.handled_count}  |  Odrzucone: {self.rejected_count}  |  W kolejce: {len(self.queue)}")
            self.lbl_time.configure(text=f"Czas symulacji: {self.current_time} / {self.sim_t}")

        self.after(600, self.run_step)

    def update_channels_canvas(self):
        self.canvas_ch.delete("all")
        for i in range(self.S):
            x = 10 + i * 55
            color = "#27ae60" if self.channels[i] > 0 else "#bdc3c7"
            self.canvas_ch.create_rectangle(x, 20, x + 45, 70, fill=color, outline="white")
            if self.channels[i] > 0:
                self.canvas_ch.create_text(x + 22, 45, text=str(self.channels[i]), fill="white",
                                           font=("Arial", 10, "bold"))

    def update_plots(self):
        self.ax_q.clear();
        self.ax_q.plot(self.time_axis, self.history_q, 'r');
        self.ax_q.set_title("Q (Średnia długość kolejki)")
        self.ax_w.clear();
        self.ax_w.plot(self.time_axis, self.history_w, 'b');
        self.ax_w.set_title("W (Średni czas oczekiwania)")
        self.ax_ro.clear();
        self.ax_ro.plot(self.time_axis, self.history_ro, 'g');
        self.ax_ro.set_title("Ro (obiążenie)")
        self.canvas_plot.draw()

    def save_to_txt(self):
        path = "wyniki_stacja_bazowa.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write("=== PARAMETRY SYMULACJI ===\n")
            f.write(f"S (Kanaly): {self.S}, Lambda: {self.lam}, N: {self.N}, Sigma: {self.sigma}, Max Q: {self.max_q}\n")
            f.write(f"Zakres rozmow: {self.m_min} - {self.m_max}, Czas calkowity: {self.sim_t}s\n\n")

            header_line = f"{'Pois':<6} {'Gaus':<6} {'Klienci':<8} {'T.Przy':<8} {'T.Obsl':<8} {'Lam':<6} {'Mii':<6} {'Roi':<6}\n"
            f.write(header_line)
            f.write("-" * len(header_line) + "\n")

            for row in self.full_log:
                f.write(" ".join(f"{str(val):<7}" for val in row) + "\n")

        print(f"Dane zapisano pomyślnie w: {os.path.abspath(path)}")


if __name__ == "__main__":
    BaseStationSimulator().mainloop()