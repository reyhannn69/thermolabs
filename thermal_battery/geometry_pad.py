"""Small interactive Tkinter Canvas drawing pad for Experiment 7."""

import tkinter as tk
from tkinter import ttk


class GeometryPad(tk.Toplevel):
    """A tiny drawing window with rectangle, oval and line tools."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("ThermoLab | Canvas Geometry Pad")
        self.geometry("680x470")
        self.minsize(480, 350)
        self.configure(bg="#172630")
        self.tool = tk.StringVar(value="rectangle")
        self.start_x = None
        self.start_y = None
        self.preview_id = None

        toolbar = ttk.Frame(self, padding=10)
        toolbar.pack(fill="x")
        ttk.Label(toolbar, text="DRAW SHAPE:").pack(side="left", padx=(0, 8))
        for label, value in (("Rectangle", "rectangle"), ("Oval", "oval"), ("Line", "line")):
            ttk.Radiobutton(toolbar, text=label, value=value, variable=self.tool).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Clear canvas", command=self.clear).pack(side="right")

        self.canvas = tk.Canvas(self, bg="#f7fafc", highlightthickness=1,
                                highlightbackground="#8ca2af", cursor="crosshair")
        self.canvas.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.canvas.bind("<ButtonPress-1>", self._begin_shape)
        self.canvas.bind("<B1-Motion>", self._resize_shape)
        self.canvas.bind("<ButtonRelease-1>", self._finish_shape)

    def _begin_shape(self, event):
        self.start_x, self.start_y = event.x, event.y
        options = {"outline": "#176b87", "width": 3}
        if self.tool.get() == "rectangle":
            self.preview_id = self.canvas.create_rectangle(
                event.x, event.y, event.x, event.y, **options
            )
        elif self.tool.get() == "oval":
            self.preview_id = self.canvas.create_oval(
                event.x, event.y, event.x, event.y, **options
            )
        else:
            self.preview_id = self.canvas.create_line(
                event.x, event.y, event.x, event.y, fill="#176b87", width=3
            )

    def _resize_shape(self, event):
        if self.preview_id is not None:
            self.canvas.coords(self.preview_id, self.start_x, self.start_y, event.x, event.y)

    def _finish_shape(self, event):
        if self.preview_id is not None:
            self.canvas.coords(self.preview_id, self.start_x, self.start_y, event.x, event.y)
        self.preview_id = None

    def clear(self):
        self.canvas.delete("all")
