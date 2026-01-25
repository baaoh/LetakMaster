import xlwings as xw

def check_headers():
    app = xw.App(visible=False)
    try:
        book = app.books.open("Copy of letak prodejna 2026 NEW FINAL.xls")
        sheet = book.sheets["04.02 - 10.02"]
        
        # Read first row
        headers = sheet.range("A1:Z1").value
        print("Headers:")
        for i, h in enumerate(headers):
            print(f"Col {chr(65+i)} (Index {i}): {h}")
            
    except Exception as e:
        print(e)
    finally:
        app.quit()

if __name__ == "__main__":
    check_headers()
