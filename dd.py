#-*- coding:utf-8 -*-

import os
from flask import Flask,request,Response,render_template

app = Flask(__name__)


def gen(path):
    with open(path,'rb') as f:
        f.seek(0)
        b = f.read(1024)
        while b:
            yield b
            b = f.read(1024)


@app.route('/')
def index():
    return render_template('test.html')

@app.route('/video')
def video():
    file = request.args.get('file')
    root = os.path.expanduser('D:/filesystem')
    path = os.path.join(root, file)
    size = os.path.getsize(path)
    start = 0
    end = size - start + 1
    resp = Response(gen(path))
    resp.headers.add('accept-ranges','bytes')
    resp.headers.add('content-length',size)
    resp.headers.add('content-range',"bytes {0}-{1}/{2}".format(start,end,size))
    resp.headers.add('content-type','video/mp4')
    return resp

if __name__ == '__main__':
    #app.run(port=8000)
    app.run(debug=True, host='0.0.0.0',port=8000)