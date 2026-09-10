import sqlite3
conn = sqlite3.connect('example.db')
cursor = conn.cursor()
conn.execute("BEGIN")
conn.execute("INSERT INTO SONG_DATA VALUES (?, ?)", (0, "Levitating"))
conn.execute("INSERT INTO SONG_DATA VALUES (?, ?)", (1, "Wolves"))
conn.execute("INSERT INTO SONG_DATA VALUES (?, ?)", (2, "Love Me or Not"))
conn.execute("INSERT INTO SONG_DATA VALUES (?, ?)", (3, "Shake It Off"))
conn.commit()

