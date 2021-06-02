import os
import glob
import psycopg2
import pandas as pd
from sql_queries import *


def process_song_file(cur, filepath):
    """
    Performs ETL on the song_data dataset and creates
    the songs and artists dimensional tables.
    
    args:
        cur: cursor to enable Python code to execute PostgreSQL 
             command in a database session
        filepath: file path to the song_data dataset
    """
    # open song file
    df = pd.read_json(filepath, lines=True)

    # insert song record
    song_data = df[['song_id', 'title', 'artist_id', 'year', 'duration']].values.tolist()[0]
    cur.execute(song_table_insert, song_data)
    
    # insert artist record
    artist_data = df[['artist_id', 'artist_name', 'artist_location', 'artist_latitude',
                      'artist_longitude']].values.tolist()[0]
    cur.execute(artist_table_insert, artist_data)


def process_log_file(cur, filepath):
    """
    Performs ETL on the log_data dataset and creates the time and 
    users dimensional tables and the songplays fact table.
    
    args:
        cur: cursor to enable Python code to execute PostgreSQL 
             command in a database session
        filepath: file path to the log_data dataset
    """
    # open log file
    df = pd.read_json(filepath, lines=True)

    # filter by NextSong action
    df = df[df.page=="NextSong"]

    # convert timestamp column to datetime
    t = pd.to_datetime(df["ts"], unit="ms")
    
    # insert time data records
    time_data = [t, t.dt.hour, t.dt.day, t.dt.week, t.dt.month, t.dt.year, t.dt.weekday]
    column_labels = ["start_time", "hour", "day", "week", "month", "year", "weekday"] 
    time_df = pd.DataFrame.from_dict(dict(zip(column_labels, time_data)))

    for i, row in time_df.iterrows():
        cur.execute(time_table_insert, list(row))

    # load user table
    user_df = df[['userId', 'firstName', 'lastName', 'gender', 'level']]

    # insert user records
    for i, row in user_df.iterrows():
        cur.execute(user_table_insert, list(row))

    # insert songplay records
    for index, row in df.iterrows():
        
        # get songid and artistid from song and artist tables
        cur.execute(song_select, (row.song, row.artist, row.length))
        results = cur.fetchone()
        
        if results:
            songid, artistid = results
        else:
            songid, artistid = None, None

        # insert songplay record
        # insert songplay record
        row.userId = None  # used to insert "None" to the database when the entry is None, given that the column type is "int"
        songplay_data = (row.ts, row.userId, row.level, songid, artistid, row.sessionId, row.location, row.userAgent)
        cur.execute(songplay_table_insert, songplay_data)


def process_data(cur, conn, filepath, func):
    """
    Extracts all files from the song_data and log_data datasets
    with .json extension, which are passed to process_song_file
    and process_log_file functions to perform ETL on the files.
    
    args:
        cur: cursor to enable Python code to execute PostgreSQL 
             command in a database session
        conn: connection to Sparkify database
        filepath: file path to dataset (i.e. song_data and log_data)
        func: functions to perform ETL on the json files.    
    """
    
    # get all files matching extension from directory
    all_files = []
    for root, dirs, files in os.walk(filepath):
        files = glob.glob(os.path.join(root,'*.json'))
        for f in files :
            all_files.append(os.path.abspath(f))

    # get total number of files found
    num_files = len(all_files)
    print('{} files found in {}'.format(num_files, filepath))

    # iterate over files and process
    for i, datafile in enumerate(all_files, 1):
        func(cur, datafile)
        conn.commit()
        print('{}/{} files processed.'.format(i, num_files))


def main():
    """
    - Establishes connection with the sparkify database and gets
      cursor to it.  
      
    - Performs ETL on the songs and logs datasets
    
    - Finally, closes the connection. 
    """
    conn = psycopg2.connect("host=127.0.0.1 dbname=sparkifydb user=student password=student")
    cur = conn.cursor()

    process_data(cur, conn, filepath='data/song_data', func=process_song_file)
    process_data(cur, conn, filepath='data/log_data', func=process_log_file)

    conn.close()


if __name__ == "__main__":
    main()