from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from battleship import Board, CellState, Pal17Engine, PlayerEngine, RandomEngine


DEFAULT_FLEET = "5,4,4,3,3,3,3,3"
ENGINE_TYPES = {
    RandomEngine.name: RandomEngine,
    Pal17Engine.name: Pal17Engine,
}


class GameSession:
    def __init__(
        self,
        rows: int,
        cols: int,
        fleet: list[int],
        mode: int,
        left_engine: PlayerEngine | None,
        right_engine: PlayerEngine,
    ):
        self.rows = rows
        self.cols = cols
        self.fleet = fleet
        self.mode = mode
        self.left_board = Board(rows, cols, fleet)
        self.right_board = Board(rows, cols, fleet)
        self.left_engine = left_engine
        self.right_engine = right_engine
        self.turn = "human" if mode == 1 else "left_ai"
        self.game_over = False
        self.left_moves = 0
        self.right_moves = 0

        if self.left_engine:
            self.left_engine.new_game(rows, cols, fleet)
        self.right_engine.new_game(rows, cols, fleet)


class BoardCanvas(tk.Canvas):
    WATER = "#d8eef8"
    SHIP = "#87909a"
    MISS = "#ffffff"
    HIT = "#e35b4f"
    SUNK = "#1f2933"
    GRID = "#8294a3"
    TEXT = "#111827"

    def __init__(self, parent: tk.Widget, title: str, on_click=None):
        super().__init__(parent, bg="#f7fafc", highlightthickness=0)
        self.title = title
        self.on_click = on_click
        self.board: Board | None = None
        self.reveal_ships = False
        self.interactive = False
        self.cell_size = 24
        self.margin = 28
        self.bind("<Button-1>", self._handle_click)
        self.bind("<Configure>", lambda _event: self.redraw())

    def set_board(self, board: Board, reveal_ships: bool, interactive: bool) -> None:
        self.board = board
        self.reveal_ships = reveal_ships
        self.interactive = interactive
        self.redraw()

    def redraw(self) -> None:
        self.delete("all")
        if not self.board:
            return

        board = self.board
        width = max(self.winfo_width(), 200)
        height = max(self.winfo_height(), 200)
        usable_w = width - self.margin * 2
        usable_h = height - self.margin * 2 - 22
        self.cell_size = max(5, min(usable_w // board.cols, usable_h // board.rows))
        grid_w = self.cell_size * board.cols
        grid_h = self.cell_size * board.rows
        start_x = (width - grid_w) // 2
        start_y = self.margin + 20

        self.create_text(
            width // 2,
            16,
            text=self.title,
            fill=self.TEXT,
            font=("Segoe UI", 12, "bold"),
        )

        for row in range(board.rows):
            for col in range(board.cols):
                x1 = start_x + col * self.cell_size
                y1 = start_y + row * self.cell_size
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size
                fill = self._cell_fill(board, row, col)
                self.create_rectangle(x1, y1, x2, y2, fill=fill, outline=self.GRID)
                self._draw_marker(board, row, col, x1, y1, x2, y2)

        self._grid_origin = (start_x, start_y)

    def _cell_fill(self, board: Board, row: int, col: int) -> str:
        state = board.shots[row][col]
        if state == CellState.MISS:
            return self.MISS
        if state == CellState.HIT:
            return self.HIT
        if state == CellState.SUNK:
            return self.SUNK
        if self.reveal_ships and board.ship_grid[row][col] is not None:
            return self.SHIP
        return self.WATER

    def _draw_marker(self, board: Board, row: int, col: int, x1: int, y1: int, x2: int, y2: int) -> None:
        state = board.shots[row][col]
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        radius = max(2, self.cell_size // 5)
        if state == CellState.MISS:
            self.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, fill="#64748b", outline="")
        elif state == CellState.HIT:
            self.create_text(cx, cy, text="X", fill="white", font=("Segoe UI", max(7, self.cell_size // 2), "bold"))
        elif state == CellState.SUNK:
            self.create_text(cx, cy, text="X", fill="#f8fafc", font=("Segoe UI", max(7, self.cell_size // 2), "bold"))

    def _handle_click(self, event) -> None:
        if not self.interactive or not self.board or not self.on_click:
            return
        start_x, start_y = getattr(self, "_grid_origin", (0, 0))
        col = (event.x - start_x) // self.cell_size
        row = (event.y - start_y) // self.cell_size
        if self.board.in_bounds(row, col):
            self.on_click(row, col)


class BattleshipApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sänka skepp")
        self.minsize(900, 620)
        self.configure(bg="#eef2f6")
        self.session: GameSession | None = None
        self.running_auto = False
        self.speed_ms = tk.IntVar(value=350)
        self.mode_var = tk.IntVar(value=1)
        self.rows_var = tk.IntVar(value=10)
        self.cols_var = tk.IntVar(value=10)
        self.fleet_var = tk.StringVar(value=DEFAULT_FLEET)
        self.human_vs_ai_engine_var = tk.StringVar(value=RandomEngine.name)
        self.machine_a_engine_var = tk.StringVar(value=RandomEngine.name)
        self.machine_b_engine_var = tk.StringVar(value=RandomEngine.name)
        self.status_var = tk.StringVar(value="Starta ett nytt spel.")
        self._build_ui()
        self.new_game()

    def _build_ui(self) -> None:
        controls = ttk.Frame(self, padding=10)
        controls.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(controls, text="Läge").pack(side=tk.LEFT)
        ttk.Radiobutton(
            controls,
            text="Människa mot maskin",
            variable=self.mode_var,
            value=1,
            command=self._sync_engine_controls,
        ).pack(side=tk.LEFT, padx=(6, 10))
        ttk.Radiobutton(
            controls,
            text="Maskin mot maskin",
            variable=self.mode_var,
            value=2,
            command=self._sync_engine_controls,
        ).pack(side=tk.LEFT, padx=(0, 18))

        ttk.Label(controls, text="Rader").pack(side=tk.LEFT)
        ttk.Spinbox(controls, from_=1, to=100, textvariable=self.rows_var, width=5).pack(side=tk.LEFT, padx=(4, 10))
        ttk.Label(controls, text="Kolumner").pack(side=tk.LEFT)
        ttk.Spinbox(controls, from_=1, to=100, textvariable=self.cols_var, width=5).pack(side=tk.LEFT, padx=(4, 10))
        ttk.Label(controls, text="Flotta").pack(side=tk.LEFT)
        ttk.Entry(controls, textvariable=self.fleet_var, width=20).pack(side=tk.LEFT, padx=(4, 10))

        ttk.Button(controls, text="Nytt spel", command=self.new_game).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(controls, text="Start/paus", command=self.toggle_auto).pack(side=tk.LEFT)

        self.engines_container = ttk.Frame(self, padding=(10, 0, 10, 10))
        self.engines_container.pack(side=tk.TOP, fill=tk.X)
        engine_names = tuple(ENGINE_TYPES)

        self.mode1_engine_frame = ttk.Frame(self.engines_container)
        ttk.Label(self.mode1_engine_frame, text="Maskin").pack(side=tk.LEFT)
        ttk.Combobox(
            self.mode1_engine_frame,
            textvariable=self.human_vs_ai_engine_var,
            values=engine_names,
            state="readonly",
            width=10,
        ).pack(side=tk.LEFT, padx=(6, 0))

        self.mode2_engine_frame = ttk.Frame(self.engines_container)
        ttk.Label(self.mode2_engine_frame, text="Maskin A").pack(side=tk.LEFT)
        ttk.Combobox(
            self.mode2_engine_frame,
            textvariable=self.machine_a_engine_var,
            values=engine_names,
            state="readonly",
            width=10,
        ).pack(side=tk.LEFT, padx=(6, 16))

        ttk.Label(self.mode2_engine_frame, text="Maskin B").pack(side=tk.LEFT)
        ttk.Combobox(
            self.mode2_engine_frame,
            textvariable=self.machine_b_engine_var,
            values=engine_names,
            state="readonly",
            width=10,
        ).pack(side=tk.LEFT, padx=(6, 0))
        self._sync_engine_controls()

        boards = ttk.Frame(self, padding=(10, 0, 10, 10))
        boards.pack(fill=tk.BOTH, expand=True)
        boards.columnconfigure(0, weight=1)
        boards.columnconfigure(1, weight=1)
        boards.rowconfigure(0, weight=1)

        self.left_canvas = BoardCanvas(boards, "Spelarens bräde")
        self.right_canvas = BoardCanvas(boards, "Maskinens bräde", on_click=self.human_shot)
        self.left_canvas.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.right_canvas.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        bottom = ttk.Frame(self, padding=(10, 0, 10, 10))
        bottom.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Label(bottom, text="Hastighet").pack(side=tk.LEFT)
        ttk.Scale(bottom, from_=60, to=1200, variable=self.speed_ms, orient=tk.HORIZONTAL, length=180).pack(side=tk.LEFT, padx=8)
        ttk.Label(bottom, textvariable=self.status_var).pack(side=tk.LEFT, padx=(14, 0))

    def new_game(self) -> None:
        try:
            rows = int(self.rows_var.get())
            cols = int(self.cols_var.get())
            fleet = self._parse_fleet()
            mode = int(self.mode_var.get())
            session = GameSession(
                rows=rows,
                cols=cols,
                fleet=fleet,
                mode=mode,
                left_engine=self._create_engine(self.machine_a_engine_var.get()) if mode == 2 else None,
                right_engine=self._create_engine(
                    self.machine_b_engine_var.get() if mode == 2 else self.human_vs_ai_engine_var.get()
                ),
            )
        except ValueError as exc:
            messagebox.showerror("Kan inte starta spel", str(exc))
            return

        self.running_auto = False
        self.session = session
        self._sync_canvases()
        self.status_var.set("Din tur: klicka på maskinens bräde." if mode == 1 else "Maskin mot maskin redo. Tryck Start/paus.")

    def _parse_fleet(self) -> list[int]:
        values = [part.strip() for part in self.fleet_var.get().split(",") if part.strip()]
        fleet = [int(value) for value in values]
        if not fleet or any(length <= 0 for length in fleet):
            raise ValueError("Flottan måste vara en kommaseparerad lista med positiva heltal.")
        return fleet

    def _create_engine(self, name: str) -> PlayerEngine:
        engine_type = ENGINE_TYPES.get(name)
        if engine_type is None:
            raise ValueError(f"Okänd spelmotor: {name}")
        return engine_type()

    def _sync_canvases(self) -> None:
        if not self.session:
            return
        mode = self.session.mode
        self._sync_engine_controls()
        left_title = "Spelarens bräde" if mode == 1 else "Maskin A"
        right_title = "Maskinens bräde" if mode == 1 else "Maskin B"
        self.left_canvas.title = f"{left_title} - drag: {self.session.left_moves}"
        self.right_canvas.title = f"{right_title} - drag: {self.session.right_moves}"
        self.left_canvas.set_board(self.session.left_board, reveal_ships=True, interactive=False)
        self.right_canvas.set_board(
            self.session.right_board,
            reveal_ships=(mode == 2),
            interactive=(mode == 1 and self.session.turn == "human" and not self.session.game_over),
        )

    def _sync_engine_controls(self) -> None:
        self.mode1_engine_frame.pack_forget()
        self.mode2_engine_frame.pack_forget()
        if int(self.mode_var.get()) == 1:
            self.mode1_engine_frame.pack(side=tk.LEFT)
        else:
            self.mode2_engine_frame.pack(side=tk.LEFT)

    def human_shot(self, row: int, col: int) -> None:
        session = self.session
        if not session or session.mode != 1 or session.game_over or session.turn != "human":
            return

        result = session.right_board.receive_shot(row, col)
        if result.already_tried:
            self.status_var.set("Den rutan är redan skjuten på.")
            return

        session.left_moves += 1
        self.status_var.set(self._describe_result("Du", result))
        self._sync_canvases()
        if self._check_winner("Du", session.right_board):
            return

        session.turn = "right_ai"
        self.after(450, self._computer_turn_mode1)

    def _computer_turn_mode1(self) -> None:
        session = self.session
        if not session or session.game_over or session.mode != 1:
            return

        row, col = session.right_engine.choose_shot(session.left_board.public_view())
        result = session.left_board.receive_shot(row, col)
        session.right_engine.observe_result(result, session.left_board.public_view())
        session.right_moves += 1
        self.status_var.set(self._describe_result("Maskinen", result))
        self._sync_canvases()

        if self._check_winner("Maskinen", session.left_board):
            return
        session.turn = "human"
        self._sync_canvases()

    def toggle_auto(self) -> None:
        if not self.session:
            return
        self.running_auto = not self.running_auto
        if self.running_auto:
            self._auto_step()

    def _auto_step(self) -> None:
        session = self.session
        if not session or not self.running_auto or session.game_over:
            return

        if session.mode == 1:
            if session.turn == "right_ai":
                self._computer_turn_mode1()
            self.running_auto = False
            return

        attacker_name = "Maskin A" if session.turn == "left_ai" else "Maskin B"
        attacker = session.left_engine if session.turn == "left_ai" else session.right_engine
        defender = session.right_board if session.turn == "left_ai" else session.left_board
        if attacker is None:
            return

        row, col = attacker.choose_shot(defender.public_view())
        result = defender.receive_shot(row, col)
        attacker.observe_result(result, defender.public_view())
        if session.turn == "left_ai":
            session.left_moves += 1
        else:
            session.right_moves += 1
        self.status_var.set(self._describe_result(attacker_name, result))
        self._sync_canvases()

        if self._check_winner(attacker_name, defender):
            self.running_auto = False
            return

        session.turn = "right_ai" if session.turn == "left_ai" else "left_ai"
        self.after(int(self.speed_ms.get()), self._auto_step)

    def _check_winner(self, attacker_name: str, defender: Board) -> bool:
        if defender.all_ships_sunk():
            if self.session:
                self.session.game_over = True
            self.status_var.set(f"{attacker_name} vann. Alla skepp är sänkta.")
            self._sync_canvases()
            return True
        return False

    def _describe_result(self, name: str, result) -> str:
        position = f"({result.row + 1}, {result.col + 1})"
        if result.sunk:
            return f"{name} sköt {position}: träff och sänkt."
        if result.hit:
            return f"{name} sköt {position}: träff."
        return f"{name} sköt {position}: bom."


def main() -> None:
    app = BattleshipApp()
    app.mainloop()


if __name__ == "__main__":
    main()
