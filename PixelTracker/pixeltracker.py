#!/usr/bin/env python
import os

import sqlite3
from flask import Flask, render_template, Response, request, redirect, url_for, send_from_directory, session, g, abort, flash
from werkzeug.local import LocalProxy
import time
from contextlib import closing
from trackr import Trackr
from flask_jsglue import JSGlue
from it import Iter
# let the madness begin >:)
app = Flask(__name__)
app.config.from_object('config')
jsglue = JSGlue(app)

mTrackr=None
rFlag=None


def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()


@app.before_first_request
def initialise_stuff():
    global mTrackr,rFlag
    mTrackr=Trackr()
    rFlag=0

@app.route('/')
def show_home():
    return render_template('console.html')

@app.route('/view/<runningFlag>')
def viewr(runningFlag):
    return Response(frameGen(runningFlag),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/heading')
def heading():
    # cur = g.db.execute('select id, heading from entries order by id desc')
    # row=cur.fetchone()
    # print(row)
    cheading = mTrackr.getCurrentHeading()
    return str(cheading)

@app.route('/initializefgbg')
def initializefgbg():
    global mTrackr
    mTrackr.initBGSubtraction()
    print('Initializing')
    return 'Initialized fgbg'

@app.route('/setplayarea/<onex>/<oney>/<twox>/<twoy>/<threex>/<threey>/<fourx>/<foury>')
def setplayarea(onex,oney,twox,twoy,threex,threey,fourx,foury):
    print('setting play area')
    global mTrackr
    mTrackr.setPlayArea(onex,oney,twox,twoy,threex,threey,fourx,foury)
    return 'Set Play Area'

@app.route('/setpixel/<onex>/<oney>/<twox>/<twoy>')
def setpixel(onex,oney,twox,twoy):
    print('Initializing pixel position')
    global mTrackr
    mTrackr.setPixel(onex,oney,twox,twoy)
    return 'Initialize Tracking'


def frameGen(runningFlag):
    global mTrackr
    db = LocalProxy(connect_db)
    while True:
        cheading = mTrackr.getCurrentHeading()
        print(cheading)
        db.execute('insert or replace into entries (id, heading) values (?,?)',
                  [1, int(cheading)])
        db.commit()
        frame, isImage = mTrackr.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')


if __name__ == '__main__':
    app.run( '0.0.0.0',threaded=True)
