"""
player_gui.py — Giao diện so sánh 2 cầu thủ Premier League bằng biểu đồ radar
Tác giả  : Sinh viên (bài tập đại học)
Yêu cầu  : pip install requests matplotlib
API Flask : http://127.0.0.1:5000/api/player?name=<tên>
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import subprocess
import time
import os
import sys
import requests
import math
import re

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

# ─────────────────────────────────────────────
# HẰNG SỐ CẤU HÌNH
# ─────────────────────────────────────────────
API_BASE   : str       = "http://127.0.0.1:5000"
API_PLAYER : str       = f"{API_BASE}/api/player"
WIN_W      : int       = 1320
WIN_H      : int       = 860

CLR_BG      : str = "#0f1117"
CLR_PANEL   : str = "#1a1d27"
CLR_CARD    : str = "#22263a"
CLR_ACCENT  : str = "#38bdf8"
CLR_PLAYER1 : str = "#f97316"
CLR_PLAYER2 : str = "#a78bfa"
CLR_TEXT    : str = "#e2e8f0"
CLR_SUB     : str = "#94a3b8"
CLR_OK      : str = "#4ade80"
CLR_ERR     : str = "#f87171"
CLR_BTN     : str = "#2563eb"
CLR_CMP     : str = "#7c3aed"

NON_NUMERIC_KEYS: set[str] = {
    "player", "squad", "team", "nation", "nationality",
    "pos", "position", "age", "born", "comp", "league",
    "name", "club", "country",
}

FONT_TITLE : tuple = ("Segoe UI", 14, "bold")
FONT_LABEL : tuple = ("Segoe UI", 10)
FONT_SMALL : tuple = ("Segoe UI", 9)
FONT_BTN   : tuple = ("Segoe UI", 10, "bold")
FONT_MONO  : tuple = ("Consolas", 9)


# ─────────────────────────────────────────────
# TIỆN ÍCH
# ─────────────────────────────────────────────
def normalize_for_radar(values: list) -> list[float]:
    """
    Chuẩn hoá danh sách giá trị sang đoạn [0, 1] theo phương pháp min-max.

    Hỗ trợ các định dạng đầu vào:
        - Số thường : 12, 3.5
        - Số có dấu phẩy ngàn : "2,450" → 2450.0
        - Tỉ lệ phần trăm : "68.3%" → 68.3

    Args:
        values (list): Danh sách giá trị thô cần chuẩn hoá.

    Returns:
        list[float]: Danh sách giá trị float đã chuẩn hoá về [0, 1].
            Trả về [0.5, 0.5, ...] nếu tất cả giá trị bằng nhau (tránh chia 0).
    """
    parsed: list[float] = []
    for v in values:
        s = str(v).replace(",", "").replace("%", "").strip()
        try:
            parsed.append(float(s))
        except ValueError:
            parsed.append(0.0)

    mn, mx = min(parsed), max(parsed)
    if mx == mn:
        return [0.5] * len(parsed)
    return [(x - mn) / (mx - mn) for x in parsed]


def check_api_alive() -> bool:
    """
    Kiểm tra xem Flask API có đang lắng nghe tại API_BASE không.

    Returns:
        bool: True nếu API phản hồi với status code < 500, False nếu không kết nối được.
    """
    try:
        r = requests.get(API_BASE, timeout=2)
        return r.status_code < 500
    except Exception:
        return False


def start_api_if_needed() -> tuple[bool, str]:
    """
    Tự động khởi động Flask API nếu cổng 5000 chưa có dịch vụ.

    Tìm kiếm các file Flask theo thứ tự ưu tiên:
    app.py → server.py → api.py → flask_app.py

    Returns:
        tuple[bool, str]: Tuple gồm trạng thái thành công và thông báo tương ứng.
            - (True, "API đã chạy sẵn") nếu API đang chạy.
            - (True, "Đã khởi động API từ <file>") nếu tự khởi động thành công.
            - (False, <lý do lỗi>) nếu không thể khởi động.
    """
    if check_api_alive():
        return True, "API đã chạy sẵn"

    candidates: list[str] = ["app.py", "server.py", "api.py", "flask_app.py"]
    found: str | None = next((c for c in candidates if os.path.exists(c)), None)

    if not found:
        return False, "Không tìm thấy file Flask (app.py / server.py)"

    try:
        subprocess.Popen(
            [sys.executable, found],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(10):
            time.sleep(0.5)
            if check_api_alive():
                return True, f"Đã khởi động API từ {found}"
        return False, "API không phản hồi sau 5 giây"
    except Exception as e:
        return False, str(e)


# ─────────────────────────────────────────────
# WIDGET PHỤ: Toast thông báo tạm thời
# ─────────────────────────────────────────────
class Toast:
    """
    Hiển thị thông báo nhỏ góc dưới-phải cửa sổ, tự biến mất sau 2.5 giây.

    Args:
        master (tk.Widget): Cửa sổ cha để tính toán vị trí hiển thị.
        message (str): Nội dung thông báo cần hiển thị.
        color (str): Màu chữ của thông báo. Mặc định là CLR_ERR (đỏ).
    """

    def __init__(self, master: tk.Widget, message: str, color: str = CLR_ERR) -> None:
        self.win = tk.Toplevel(master)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg=CLR_CARD)

        master.update_idletasks()
        mx = master.winfo_x() + master.winfo_width()
        my = master.winfo_y() + master.winfo_height()
        w, h = 340, 50
        self.win.geometry(f"{w}x{h}+{mx - w - 20}+{my - h - 30}")

        tk.Label(
            self.win, text=message, bg=CLR_CARD, fg=color,
            font=FONT_LABEL, wraplength=320, padx=12, pady=10,
        ).pack(fill="both", expand=True)

        self.win.after(2500, self.win.destroy)


# ─────────────────────────────────────────────
# WIDGET PHỤ: Panel một cầu thủ (trái / phải)
# ─────────────────────────────────────────────
class PlayerPanel(ttk.Frame):
    """
    Panel hiển thị thông tin tìm kiếm và thống kê của một cầu thủ.

    Bao gồm:
        - Ô nhập tên + nút Tìm kiếm
        - Label trạng thái kết quả
        - Danh sách chỉ số có tickbox (scrollable)
        - Nút Chọn tất cả / Bỏ chọn

    Args:
        master (tk.Widget): Widget cha chứa panel này.
        side (str): Nhãn vị trí, ví dụ "Trái" hoặc "Phải".
        color (str): Màu nhấn đặc trưng của cầu thủ (hex color).
        root_ref (tk.Tk): Tham chiếu đến cửa sổ gốc để hiển thị Toast.
    """

    def __init__(self, master: tk.Widget, side: str, color: str,
                 root_ref: tk.Tk, **kw) -> None:
        super().__init__(master, **kw)
        self.side       : str      = side
        self.color      : str      = color
        self.root_ref   : tk.Tk   = root_ref
        self.player_data: dict     = {}
        self.check_vars : dict     = {}
        self.select_all_var        = tk.BooleanVar(value=True)
        self._build_ui()

    def _build_ui(self) -> None:
        """Khởi tạo toàn bộ các widget trong panel."""
        self.configure(style="Card.TFrame")

        header = tk.Label(
            self, text=f"⬤  Cầu thủ {self.side}",
            bg=CLR_PANEL, fg=self.color,
            font=("Segoe UI", 13, "bold"), anchor="w", padx=12, pady=8,
        )
        header.pack(fill="x")

        search_frame = tk.Frame(self, bg=CLR_PANEL, pady=8, padx=10)
        search_frame.pack(fill="x")

        self.entry = tk.Entry(
            search_frame, font=FONT_LABEL,
            bg=CLR_CARD, fg=CLR_TEXT, insertbackground=CLR_TEXT,
            relief="flat", bd=6,
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=5)
        self.entry.bind("<Return>", lambda e: self._search())

        self.btn_search = tk.Button(
            search_frame, text="🔍 Tìm",
            bg=CLR_BTN, fg="white", font=FONT_BTN,
            relief="flat", cursor="hand2", padx=12,
            command=self._search,
        )
        self.btn_search.pack(side="left", padx=(8, 0), ipady=4)

        self.lbl_status = tk.Label(
            self, text="Chưa tìm kiếm",
            bg=CLR_PANEL, fg=CLR_SUB, font=FONT_SMALL,
            anchor="w", padx=12,
        )
        self.lbl_status.pack(fill="x")

        ctrl_frame = tk.Frame(self, bg=CLR_PANEL, padx=10, pady=4)
        ctrl_frame.pack(fill="x")

        self.cb_all = tk.Checkbutton(
            ctrl_frame, text="Chọn tất cả",
            variable=self.select_all_var,
            bg=CLR_PANEL, fg=CLR_SUB,
            selectcolor=CLR_CARD, activebackground=CLR_PANEL,
            font=FONT_SMALL, cursor="hand2",
            command=self._toggle_all,
        )
        self.cb_all.pack(side="left")

        tk.Button(
            ctrl_frame, text="Bỏ chọn",
            bg=CLR_CARD, fg=CLR_SUB, font=FONT_SMALL,
            relief="flat", cursor="hand2", padx=8,
            command=self._deselect_all,
        ).pack(side="right")

        list_wrapper = tk.Frame(self, bg=CLR_PANEL, padx=10, pady=4)
        list_wrapper.pack(fill="both", expand=True)

        canvas = tk.Canvas(list_wrapper, bg=CLR_CARD, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_wrapper, orient="vertical", command=canvas.yview)
        self.scroll_frame = tk.Frame(canvas, bg=CLR_CARD)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))
        self._canvas = canvas

    def _search(self) -> None:
        """
        Khởi động luồng tìm kiếm cầu thủ từ ô nhập liệu.
        Hiển thị Toast nếu ô nhập trống.
        """
        name = self.entry.get().strip()
        if not name:
            Toast(self.root_ref, "Vui lòng nhập tên cầu thủ!")
            return
        self.btn_search.config(state="disabled", text="Đang tìm…")
        self.lbl_status.config(text="Đang tìm kiếm…", fg=CLR_SUB)
        threading.Thread(target=self._do_search, args=(name,), daemon=True).start()

    def _do_search(self, name: str) -> None:
        """
        Gọi Flask API để tìm kiếm cầu thủ. Chạy trong thread riêng.

        Args:
            name (str): Tên hoặc từ khóa tìm kiếm cầu thủ.
        """
        try:
            resp = requests.get(API_PLAYER, params={"name": name}, timeout=5)
            data = resp.json()
        except requests.exceptions.ConnectionError:
            self.root_ref.after(0, lambda: self._on_error("Không kết nối được API. Hãy khởi động Flask!"))
            return
        except Exception as e:
            self.root_ref.after(0, lambda: self._on_error(f"Lỗi: {e}"))
            return

        status  = data.get("trang_thai", "")
        records = data.get("du_lieu", [])

        if status == "khong_tim_thay" or resp.status_code == 404 or not records:
            self.root_ref.after(0, lambda: self._on_not_found(name))
            return

        player = records[0]
        self.root_ref.after(0, lambda: self._on_found(player))

    def _on_found(self, player: dict) -> None:
        """
        Cập nhật UI sau khi tìm thấy cầu thủ.

        Args:
            player (dict): Dict chứa toàn bộ thông số của cầu thủ từ API.
        """
        self.player_data = player
        pname = player.get("Player", player.get("name", "Không rõ"))
        team  = player.get("Squad", player.get("team", ""))
        self.lbl_status.config(text=f"✔ {pname}  |  {team}", fg=CLR_OK)
        self.btn_search.config(state="normal", text="🔍 Tìm")
        self._populate_stats(player)

    def _on_not_found(self, name: str) -> None:
        """
        Cập nhật UI khi không tìm thấy cầu thủ.

        Args:
            name (str): Từ khóa tìm kiếm không có kết quả.
        """
        self.player_data = {}
        self.lbl_status.config(text=f'✘ Không tìm thấy: "{name}"', fg=CLR_ERR)
        self.btn_search.config(state="normal", text="🔍 Tìm")
        Toast(self.root_ref, f'Không tìm thấy cầu thủ: "{name}"')
        self._clear_stats()

    def _on_error(self, msg: str) -> None:
        """
        Cập nhật UI khi gặp lỗi kết nối hoặc lỗi hệ thống.

        Args:
            msg (str): Thông báo lỗi cần hiển thị.
        """
        self.lbl_status.config(text=f"✘ {msg}", fg=CLR_ERR)
        self.btn_search.config(state="normal", text="🔍 Tìm")
        Toast(self.root_ref, msg)

    def _populate_stats(self, player: dict) -> None:
        """
        Vẽ danh sách chỉ số có tickbox từ dữ liệu cầu thủ.

        Args:
            player (dict): Dict chứa các cặp key-value thống kê cầu thủ.
        """
        self._clear_stats()
        self.check_vars = {}

        for key, val in player.items():
            var = tk.BooleanVar(value=True)
            self.check_vars[key] = var

            row = tk.Frame(self.scroll_frame, bg=CLR_CARD)
            row.pack(fill="x", padx=4, pady=1)

            cb = tk.Checkbutton(
                row, variable=var,
                bg=CLR_CARD, selectcolor=CLR_PANEL,
                activebackground=CLR_CARD, cursor="hand2",
            )
            cb.pack(side="left")

            is_num = _is_numeric(val)
            fg_key = self.color if is_num else CLR_SUB
            fg_val = CLR_TEXT  if is_num else CLR_SUB

            tk.Label(row, text=f"{key}:", bg=CLR_CARD, fg=fg_key,
                     font=FONT_MONO, width=22, anchor="w").pack(side="left")
            tk.Label(row, text=str(val), bg=CLR_CARD, fg=fg_val,
                     font=FONT_MONO, anchor="w").pack(side="left", fill="x", expand=True)

        self.select_all_var.set(True)

    def _clear_stats(self) -> None:
        """Xoá toàn bộ widget trong vùng scroll và reset check_vars."""
        for w in self.scroll_frame.winfo_children():
            w.destroy()
        self.check_vars = {}

    def _toggle_all(self) -> None:
        """Đồng bộ trạng thái tick của tất cả chỉ số theo checkbox 'Chọn tất cả'."""
        state = self.select_all_var.get()
        for var in self.check_vars.values():
            var.set(state)

    def _deselect_all(self) -> None:
        """Bỏ chọn toàn bộ chỉ số và cập nhật checkbox 'Chọn tất cả'."""
        self.select_all_var.set(False)
        for var in self.check_vars.values():
            var.set(False)

    def get_selected_stats(self) -> dict:
        """
        Trả về các chỉ số đang được tick chọn.

        Returns:
            dict: Dict {key: value} chỉ chứa những chỉ số đang được tick.
        """
        return {
            k: self.player_data[k]
            for k, var in self.check_vars.items()
            if var.get() and k in self.player_data
        }

    def get_player_name(self) -> str:
        """
        Trả về tên cầu thủ hiện tại của panel.

        Returns:
            str: Tên cầu thủ, hoặc "Cầu thủ" nếu chưa có dữ liệu.
        """
        return self.player_data.get("Player", self.player_data.get("name", "Cầu thủ"))


# ─────────────────────────────────────────────
# CỬA SỔ RADAR
# ─────────────────────────────────────────────
class RadarWindow(tk.Toplevel):
    """
    Cửa sổ popup hiển thị biểu đồ radar so sánh 2 cầu thủ.

    Args:
        master (tk.Widget): Cửa sổ cha.
        name1 (str): Tên cầu thủ thứ nhất.
        stats1 (dict): Dict chỉ số đã được tick của cầu thủ thứ nhất.
        name2 (str): Tên cầu thủ thứ hai.
        stats2 (dict): Dict chỉ số đã được tick của cầu thủ thứ hai.
    """

    def __init__(self, master: tk.Widget, name1: str, stats1: dict,
                 name2: str, stats2: dict) -> None:
        super().__init__(master)
        self.title(f"Radar — {name1}  vs  {name2}")
        self.configure(bg=CLR_BG)
        self.resizable(True, True)

        common_keys: list[str] = [
            k for k in stats1
            if k in stats2
            and _is_numeric(stats1[k]) and _is_numeric(stats2[k])
            and k.lower() not in NON_NUMERIC_KEYS
        ]

        if len(common_keys) < 3:
            tk.Label(
                self,
                text="⚠ Cần ít nhất 3 chỉ số số chung để vẽ radar!\nHãy tick thêm chỉ số ở cả 2 cột.",
                bg=CLR_BG, fg=CLR_ERR, font=FONT_TITLE,
            ).pack(padx=40, pady=40)
            return

        vals1: list[float] = [_parse_numeric(stats1[k]) for k in common_keys]
        vals2: list[float] = [_parse_numeric(stats2[k]) for k in common_keys]

        norm1: list[float] = []
        norm2: list[float] = []
        for v1, v2 in zip(vals1, vals2):
            mn = min(v1, v2)
            mx = max(v1, v2)
            if mx == mn:
                norm1.append(0.5)
                norm2.append(0.5)
            else:
                norm1.append((v1 - mn) / (mx - mn))
                norm2.append((v2 - mn) / (mx - mn))

        self._draw_radar(common_keys, norm1, norm2, name1, name2, vals1, vals2)

    def _draw_radar(self, labels: list[str], norm1: list[float], norm2: list[float],
                    name1: str, name2: str, raw1: list[float], raw2: list[float]) -> None:
        """
        Vẽ biểu đồ radar và nhúng vào cửa sổ Toplevel.

        Args:
            labels (list[str]): Danh sách nhãn các trục radar.
            norm1 (list[float]): Giá trị chuẩn hoá [0,1] của cầu thủ 1.
            norm2 (list[float]): Giá trị chuẩn hoá [0,1] của cầu thủ 2.
            name1 (str): Tên cầu thủ 1 (hiển thị trên legend).
            name2 (str): Tên cầu thủ 2 (hiển thị trên legend).
            raw1 (list[float]): Giá trị thực của cầu thủ 1 (hiển thị trên điểm).
            raw2 (list[float]): Giá trị thực của cầu thủ 2 (hiển thị trên điểm).
        """
        N      : int         = len(labels)
        angles : list[float] = [n / float(N) * 2 * math.pi for n in range(N)]
        angles += angles[:1]

        n1 = norm1 + norm1[:1]
        n2 = norm2 + norm2[:1]

        fig = plt.Figure(figsize=(8, 7), facecolor=CLR_BG)
        ax  = fig.add_subplot(111, polar=True, facecolor=CLR_PANEL)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels, color=CLR_TEXT, size=8.5, wrap=True)
        ax.set_yticks([0.25, 0.5, 0.75, 1.0])
        ax.set_yticklabels(["25%", "50%", "75%", "100%"], color=CLR_SUB, size=7)
        ax.set_ylim(0, 1)
        ax.spines["polar"].set_color(CLR_CARD)
        ax.grid(color=CLR_SUB, linestyle="--", linewidth=0.5, alpha=0.4)

        ax.plot(angles, n1, color=CLR_PLAYER1, linewidth=2, linestyle="solid")
        ax.fill(angles, n1, color=CLR_PLAYER1, alpha=0.28)
        ax.plot(angles, n2, color=CLR_PLAYER2, linewidth=2, linestyle="solid")
        ax.fill(angles, n2, color=CLR_PLAYER2, alpha=0.28)

        ax.scatter(angles[:-1], norm1, color=CLR_PLAYER1, s=40, zorder=5)
        ax.scatter(angles[:-1], norm2, color=CLR_PLAYER2, s=40, zorder=5)

        for ang, nv, rv in zip(angles[:-1], norm1, raw1):
            ax.annotate(_format_val(rv), xy=(ang, nv), xytext=(ang, nv + 0.08),
                        color=CLR_PLAYER1, fontsize=7, ha="center")

        for ang, nv, rv in zip(angles[:-1], norm2, raw2):
            ax.annotate(_format_val(rv), xy=(ang, nv), xytext=(ang, nv - 0.12),
                        color=CLR_PLAYER2, fontsize=7, ha="center")

        patch1 = mpatches.Patch(color=CLR_PLAYER1, label=name1)
        patch2 = mpatches.Patch(color=CLR_PLAYER2, label=name2)
        ax.legend(
            handles=[patch1, patch2],
            loc="upper right", bbox_to_anchor=(1.3, 1.15),
            facecolor=CLR_CARD, edgecolor=CLR_SUB,
            labelcolor=CLR_TEXT, fontsize=10,
        )

        fig.suptitle(f"{name1}  vs  {name2}",
                     color=CLR_TEXT, fontsize=13, fontweight="bold", y=0.98)

        canvas = FigureCanvasTkAgg(fig, master=self)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        tk.Button(
            self, text="💾 Lưu ảnh PNG",
            bg=CLR_BTN, fg="white", font=FONT_BTN,
            relief="flat", cursor="hand2", padx=16, pady=6,
            command=lambda: self._save(fig, name1, name2),
        ).pack(pady=(0, 10))

    def _save(self, fig: plt.Figure, n1: str, n2: str) -> None:
        """
        Lưu biểu đồ radar ra file PNG trong thư mục hiện tại.

        Args:
            fig (plt.Figure): Đối tượng Figure cần lưu.
            n1 (str): Tên cầu thủ 1 (dùng để đặt tên file).
            n2 (str): Tên cầu thủ 2 (dùng để đặt tên file).
        """
        path = f"radar_{n1[:6]}_vs_{n2[:6]}.png".replace(" ", "_")
        fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=CLR_BG)
        Toast(self.master, f"Đã lưu: {path}", color=CLR_OK)


# ─────────────────────────────────────────────
# CỬA SỔ CHÍNH
# ─────────────────────────────────────────────
class PlayerCompareGUI:
    """
    Lớp chính quản lý toàn bộ ứng dụng so sánh cầu thủ.

    Bố cục gồm:
        - Header: tiêu đề + trạng thái API
        - Body: 2 PlayerPanel (trái/phải) + nút Compare ở giữa
        - Footer: hướng dẫn sử dụng
    """

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Premier League — So sánh cầu thủ")
        self.root.geometry(f"{WIN_W}x{WIN_H}")
        self.root.configure(bg=CLR_BG)
        self.root.resizable(True, True)
        self._setup_styles()
        self._build_ui()
        self._check_api_startup()

    def _setup_styles(self) -> None:
        """Cấu hình ttk Style cho toàn bộ ứng dụng theo dark theme."""
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame",      background=CLR_BG)
        style.configure("Card.TFrame", background=CLR_PANEL)
        style.configure("TScrollbar",
                         troughcolor=CLR_CARD, background=CLR_ACCENT,
                         arrowcolor=CLR_TEXT)

    def _build_ui(self) -> None:
        """Khởi tạo toàn bộ layout: header, body 2 cột, footer."""
        header = tk.Frame(self.root, bg=CLR_CARD, height=56)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="⚽  Premier League  —  Player Comparison Tool",
            bg=CLR_CARD, fg=CLR_TEXT,
            font=("Segoe UI", 15, "bold"), anchor="w", padx=20,
        ).pack(side="left", fill="y")

        self.lbl_api_status = tk.Label(
            header, text="◉ Đang kiểm tra API…",
            bg=CLR_CARD, fg=CLR_SUB, font=FONT_SMALL, padx=16,
        )
        self.lbl_api_status.pack(side="right", fill="y")

        body = tk.Frame(self.root, bg=CLR_BG)
        body.pack(fill="both", expand=True, padx=16, pady=10)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=0)
        body.columnconfigure(2, weight=1)
        body.rowconfigure(0, weight=1)

        self.panel_left = PlayerPanel(
            body, side="Trái", color=CLR_PLAYER1,
            root_ref=self.root, style="Card.TFrame",
        )
        self.panel_left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        mid = tk.Frame(body, bg=CLR_BG, width=120)
        mid.grid(row=0, column=1, sticky="ns")
        mid.pack_propagate(False)

        tk.Label(mid, text="VS", bg=CLR_BG, fg=CLR_ACCENT,
                 font=("Segoe UI", 22, "bold")).pack(expand=True)

        tk.Button(
            mid, text="⚡\nSo sánh",
            bg=CLR_CMP, fg="white",
            font=("Segoe UI", 11, "bold"),
            relief="flat", cursor="hand2",
            padx=10, pady=14,
            command=self._compare,
        ).pack(expand=True)

        self.panel_right = PlayerPanel(
            body, side="Phải", color=CLR_PLAYER2,
            root_ref=self.root, style="Card.TFrame",
        )
        self.panel_right.grid(row=0, column=2, sticky="nsew", padx=(8, 0))

        footer = tk.Frame(self.root, bg=CLR_CARD, height=30)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        tk.Label(
            footer,
            text="Tick cùng chỉ số ở cả 2 cột  →  Bấm So sánh  →  Biểu đồ radar",
            bg=CLR_CARD, fg=CLR_SUB, font=FONT_SMALL,
        ).pack(expand=True)

    def _check_api_startup(self) -> None:
        """Kiểm tra và khởi động API trong thread riêng để không block UI."""
        def _run() -> None:
            ok, msg = start_api_if_needed()
            color = CLR_OK  if ok else CLR_ERR
            icon  = "◉"    if ok else "◎"
            self.root.after(0, lambda: self.lbl_api_status.config(
                text=f"{icon} {msg}", fg=color
            ))
        threading.Thread(target=_run, daemon=True).start()

    def _compare(self) -> None:
        """
        Xử lý sự kiện nhấn nút So sánh.

        Kiểm tra dữ liệu 2 panel, lọc chỉ số chung có tick,
        rồi mở RadarWindow nếu có đủ ít nhất 3 chỉ số số.
        """
        if not self.panel_left.player_data:
            Toast(self.root, "Chưa tìm cầu thủ cột TRÁI!")
            return
        if not self.panel_right.player_data:
            Toast(self.root, "Chưa tìm cầu thủ cột PHẢI!")
            return

        stats1: dict = self.panel_left.get_selected_stats()
        stats2: dict = self.panel_right.get_selected_stats()

        common: dict = {k: stats1[k] for k in stats1 if k in stats2}
        if not common:
            Toast(self.root, "Không có chỉ số nào được tick ở cả 2 cột!")
            return

        numeric_common: dict = {
            k: v for k, v in common.items()
            if _is_numeric(v) and k.lower() not in NON_NUMERIC_KEYS
        }
        stats2_filtered: dict = {k: stats2[k] for k in numeric_common}

        if len(numeric_common) < 3:
            Toast(self.root, "Cần ít nhất 3 chỉ số số chung. Hãy tick thêm!")
            return

        RadarWindow(
            self.root,
            self.panel_left.get_player_name(),  numeric_common,
            self.panel_right.get_player_name(), stats2_filtered,
        )

    def run(self) -> None:
        """Khởi động vòng lặp sự kiện chính của tkinter."""
        self.root.mainloop()


# ─────────────────────────────────────────────
# HÀM TIỆN ÍCH NỘI BỘ
# ─────────────────────────────────────────────
def _is_numeric(value) -> bool:
    """
    Kiểm tra một giá trị có thể chuyển đổi thành số thực không.

    Args:
        value: Giá trị cần kiểm tra (bất kỳ kiểu nào).

    Returns:
        bool: True nếu có thể parse thành float, False nếu không.
    """
    s = str(value).replace(",", "").replace("%", "").strip()
    try:
        float(s)
        return True
    except ValueError:
        return False


def _parse_numeric(value) -> float:
    """
    Chuyển đổi giá trị sang float, hỗ trợ định dạng "2,450" và "68.3%".

    Args:
        value: Giá trị cần parse (số, chuỗi có dấu phẩy hoặc ký hiệu %).

    Returns:
        float: Giá trị số thực tương ứng, hoặc 0.0 nếu không parse được.
    """
    s = str(value).replace(",", "").replace("%", "").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


def _format_val(v: float) -> str:
    """
    Định dạng giá trị số để hiển thị ngắn gọn trên biểu đồ.

    Args:
        v (float): Giá trị cần định dạng.

    Returns:
        str: Chuỗi số nguyên nếu không có phần thập phân, ngược lại 1 chữ số thập phân.
    """
    if v == int(v):
        return str(int(v))
    return f"{v:.1f}"


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = PlayerCompareGUI()
    app.run()