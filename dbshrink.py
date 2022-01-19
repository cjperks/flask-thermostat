#!/usr/bin/env python3

# Imports
import sqlite3
import shutil
import datetime

# Global settings

# how many rows to keep0
rowkeep = 500


# copy the db
def archive_db(src):
    try:
        # generate todays date
        dt = datetime.datetime.now()
        date_string = dt.strftime('%Y-%m-%d')

        # set the target for the copy
        dst = src + "." + date_string

        # copy the db file
        shutil.copyfile(src, dst)

    except Exception as e:
        raise e


# remove the old data
def shrink_db(src, ttable):
    try:
        # connect to the db
        conn = sqlite3.connect(src)
        cur = conn.cursor()

        # find what the highest number row is
        sql = "SELECT * FROM " + ttable + " ORDER BY ROWID DESC LIMIT 1"
        cur.execute(sql)

        # get the record
        record = cur.fetchall()

        # calculate the ones to keep
        target = record[0][0] - rowkeep

        # write delete line
        sql = "DELETE FROM " + ttable + " WHERE ROWID < " + str(target) + ""

        # execute the sql
        cur.execute(sql)

        # commit the change
        conn.commit()

        # clear up the unused space - THIS IS IMPORTANT!!!
        conn.execute("VACUUM")

        # close the connection to the db
        conn.close()

    except Exception as e:
        raise e
