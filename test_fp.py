import flet as ft

def main(page: ft.Page):
    print("Page init:", type(page))
    picker = ft.FilePicker()
    print("FilePicker created:", type(picker))
    page.overlay.append(picker)
    print("Appended FilePicker to page overlay")
    page.add(ft.Text("Testing FilePicker"))
    print("Done")
    page.window_destroy()

if __name__ == "__main__":
    ft.app(target=main)
