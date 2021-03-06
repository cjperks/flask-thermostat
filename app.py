from flask import Flask, g, render_template, request
import sqlite3
import datetime
from datetime import timezone


app = Flask(__name__)

# database name/location
DATABASE = 'thermostat.sqlite3'


# Database connection
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


# Get records
def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


# Write to db
def write_db(query, args=()):
    db = get_db()
    db.cursor().execute(query, args)
    db.commit()
    db.cursor().close()


# Homepage
@app.route('/', methods=['POST', 'GET'])
def home():

    err_msg = ""

    # if we're setting or cancelling an override
    if request.method == "POST":
        # set a new override
        if 'override_expiry' in request.form:
            try:
                # write row into db
                oTemp = request.form['override_temp']
                oTime = request.form['override_expiry']
                oTime = datetime.datetime.now().replace(
                    hour=int(oTime[0:2]), minute=int(oTime[3:5]))
                oStamp = query_db("SELECT datetime('now')", one=True)[0]
                values = (str(oTime).split(".")[0], str(oTemp), oStamp)
                write_db('INSERT INTO override (expires, temp, timestamp)'
                    ' VALUES (?, ?, ?)', values)

            except Exception as e:
                err_msg = "error creating the overrides: " + str(e)

        # cancel an override
        elif 'override_cancel' in request.form:
            try:
                write_db('DELETE FROM override;')

            except Exception as e:
                err_msg = "error deleting the overrides: " + str(e)

        else:
            return "at least its a POST..."

    # get the most current timestamp
    dbd = query_db("SELECT datetime('now')")
    server_now = datetime.datetime.strptime(dbd[0][0], '%Y-%m-%d %H:%M:%S')

    # get the current boiler state
    boiler_current = query_db('SELECT * FROM control_log '
        'ORDER BY ROWID DESC', one=True)

    # get the current setpoint
    setpoint_current = query_db("SELECT * FROM schedule WHERE start_time "
        "< time('now') ORDER BY start_time DESC", one=True)

    # get the average temperature and check sensor status
    rooms = query_db('SELECT * FROM location')
    temp = 0
    new_rooms = ()
    for room in rooms:
        roomtime = datetime.datetime.strptime(room[4], '%Y-%m-%d %H:%M:%S')
        roomtime = roomtime.replace(tzinfo=datetime.timezone.utc)
        tDiff = datetime.datetime.now(timezone.utc) - roomtime
        # if the timestamp is older than 2 minutes, something might be wrong,
        # so ignore and mark as error
        if tDiff.seconds < 120:
            new_rooms = new_rooms + (room + ("live",),)
            temp = temp + room[3]

        else:
            new_rooms = new_rooms + (room + ("error",),)

    temp = round(temp / len(rooms), 1)
    rooms = new_rooms

    # Get the override details
    oride = query_db("SELECT * FROM override ORDER BY expires DESC", one=True)
    # oride = dbd[0]

    server_now = str(server_now.hour) + ":" + str(server_now.minute).zfill(2)

    # Pass it all to the template
    data = {'err_msg': err_msg,
            'temp': temp,
            'rooms': rooms,
            'boiler_current': boiler_current,
            'setpoint_current': setpoint_current,
            'server_now': server_now,
            'oride': oride}

    # Render the page
    return render_template('home.html', data=data)


# Page to control the basic schedule
@app.route('/schedule/', methods=['POST', 'GET'])
def schedule():

    err_msg = ""

    # if we've got new data...
    if request.method == "POST":
        # return request.form
        # delete a row
        if 'delete' in request.form:
            try:
                write_db("DELETE FROM schedule WHERE id = ?;", (request.form['delete'],))

            except Exception as e:
                err_msg = "Error deleting the requested entry: " + str(e)

        # update a temp
        elif 'update' in request.form:
            try:
                write_db("UPDATE schedule SET min_temp = ? WHERE id = ?;", (request.form['new_temp'], request.form['update']))

            except Exception as e:
                err_msg = "Error updating the requested entry: " + str(e)

        # add a new row
        elif 'start' in request.form:
            try:
                write_db("INSERT INTO schedule (start_time, min_temp) VALUES (?, ?);", (request.form['start'] + ":00", request.form['new_temp']))

            except Exception as e:
                err_msg = "Error adding the new entry: " + str(e)

    sched = query_db('SELECT * FROM schedule ORDER BY start_time ASC')
    data = {'err_msg': err_msg,
            'sched': sched}
    return render_template('schedule.html', data=data)


# Page to display statistics about heating usage
@app.route('/statistics/')
def statistics():
    return 'This is where the stats would be'


# Main program
if __name__ == '__main__':
    app.debug = True
    app.run()
