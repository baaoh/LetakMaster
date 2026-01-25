import xlwings as xw

def verify_row_6():
    app = xw.App(visible=False)
    try:
        book = app.books.open("Copy of letak prodejna 2026 NEW FINAL.xls")
        sheet = book.sheets["04.02 - 10.02"]
        
        # Row 6 (Index 6 in 1-based, or we can just read the range)
        headers = sheet.range("A6:W6").value
        print("Headers at Row 6:")
        for i, h in enumerate(headers):
            print(f"Col {chr(65+i)} (Index {i}): {h}")
            
    except Exception as e:
        print(e)
    finally:
        app.quit()

if __name__ == "__main__":
    verify_row_6()
