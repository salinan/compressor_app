import customtkinter as ctk
from ui.app import CompressorApp

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = CompressorApp()
    app.mainloop()
