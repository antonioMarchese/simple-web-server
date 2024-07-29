from datetime import datetime

page = """
    <html>
        <body>
            <p>Generated {0}</p>
        </body>
    <html>
""".format(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

print(page)
