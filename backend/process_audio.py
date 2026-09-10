from main import Process_audio
import sqlite3

# set up db
conn = sqlite3.connect('example.db')
cursor = conn.cursor()

# conn.execute("BEGIN")
# # Drop the GEEK table if it already exists (for clean setup)
# cursor.execute("DROP TABLE IF EXISTS FINGERPRINT")

# # SQL query to create the table
# table_creation_query = """
#     CREATE TABLE FINGERPRINT (
#         hash INT,
#         time INT,
#         song_id INT
#     );
# """

# # Execute the table creation query
# cursor.execute(table_creation_query)
# # perform database operations
# conn.commit()  # or conn.rollback() if something fails
song_lib = [""]
data_set = {}

id = 0
for song in song_lib:
    process = Process_audio(song)
    signal = process.convert_stereo_to_mono()
    waveform = process.low_pass_filter_tensor()
    resampled_filename = process.resample()
    spectogram,peaks = process.caclulate_spectogram(resampled_filename)
    process.calculate_hashes(peaks,5,id,data_set)
    id += 1
print(len(data_set))
conn.execute("BEGIN")
for hash,value in data_set.items():
    for point in value:
        cursor.execute(f"INSERT INTO FINGERPRINT VALUES ({hash},{point[0]},{point[1]})")
conn.commit()

conn.execute("BEGIN")
cursor.execute(f"SELECT * FROM FINGERPRINT")
for row in cursor.fetchall():
    print(row)

conn.commit()

