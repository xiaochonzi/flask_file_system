#-*- coding: UTF-8 -*-
from flask import Flask, make_response, request, session, render_template, send_file, Response,redirect,jsonify
from flask.views import MethodView
from datetime import datetime
import humanize
import os
import re
import stat
import json
import mimetypes
import sys
import shutil


app = Flask(__name__)

root = os.path.expanduser('D:/filesystem')

ignored = ['.bzr', '$RECYCLE.BIN', '.DAV', '.DS_Store', '.git', '.hg', '.htaccess', '.htpasswd', '.Spotlight-V100',
           '.svn', '__MACOSX', 'ehthumbs.db', 'robots.txt', 'Thumbs.db', 'thumbs.tps']
datatypes = {'audio': 'm4a,mp3,oga,ogg,webma,wav', 'archive': '7z,zip,rar,gz,tar',
             'image': 'gif,ico,jpe,jpeg,jpg,png,svg,webp', 'pdf': 'pdf', 'quicktime': '3g2,3gp,3gp2,3gpp,mov,qt',
             'source': 'atom,bat,bash,c,cmd,coffee,css,hml,js,json,java,less,markdown,md,php,pl,py,rb,rss,sass,scpt,swift,scss,sh,xml,yml,plist',
             'text': 'txt', 'video': 'mp4,m4v,ogv,webm,flv,MP4,FLV', 'website': 'htm,html,mhtm,mhtml,xhtm,xhtml'}
icontypes = {'fa-music': 'm4a,mp3,oga,ogg,webma,wav', 'fa-archive': '7z,zip,rar,gz,tar',
             'fa-picture-o': 'gif,ico,jpe,jpeg,jpg,png,svg,webp', 'fa-file-text': 'pdf',
             'fa-film': '3g2,3gp,3gp2,3gpp,mov,qt',
             'fa-code': 'atom,plist,bat,bash,c,cmd,coffee,css,hml,js,json,java,less,markdown,md,php,pl,py,rb,rss,sass,scpt,swift,scss,sh,xml,yml',
             'fa-file-text-o': 'txt', 'fa-film': 'mp4,m4v,ogv,webm', 'fa-globe': 'htm,html,mhtm,mhtml,xhtm,xhtml'}


@app.template_filter('size_fmt')
def size_fmt(size):
    return humanize.naturalsize(size)


@app.template_filter('time_fmt')
def time_desc(timestamp):
    mdate = datetime.fromtimestamp(timestamp)
    str = mdate.strftime('%Y-%m-%d %H:%M:%S')
    return str


@app.template_filter('data_fmt')
def data_fmt(filename):
    t = 'unknown'
    for type, exts in datatypes.items():
        if filename.split('.')[-1] in exts:
            t = type
    return t


@app.template_filter('icon_fmt')
def icon_fmt(filename):
    i = 'fa-file-o'
    for icon, exts in icontypes.items():
        if filename.split('.')[-1] in exts:
            i = icon
    return i


@app.template_filter('humanize')
def time_humanize(timestamp):
    mdate = datetime.utcfromtimestamp(timestamp)
    return humanize.naturaltime(mdate)


def get_type(mode):
    if stat.S_ISDIR(mode) or stat.S_ISLNK(mode):
        type = 'dir'
    else:
        type = 'file'
    return type


def partial_response(path, start, end=None):
    file_size = os.path.getsize(path)

    if end is None:
        end = file_size - start - 1
    end = min(end, file_size - 1)
    length = end - start + 1

    with open(path, 'rb') as fd:
        fd.seek(start)
        bytes = fd.read(length)

    response = Response(
        bytes,
        206,  # Partial Content
        mimetype=mimetypes.guess_type(path)[0],  # Content-Type must be correct
        direct_passthrough=True,  # Identity encoding
    )
    response.headers.add(
        'Content-Range', 'bytes {0}-{1}/{2}'.format(
            start, end, file_size,
        ),
    )
    response.headers.add(
        'Accept-Ranges', 'bytes'  # Accept request with Range header
    )
    return response

def get_range(request):
    range = request.headers.get('Range')
    m = re.match('bytes=(?P<start>\d+)-(?P<end>\d+)?', range)
    if m:
        start = m.group('start')
        end = m.group('end')
        start = int(start)
        if end is not None:
            end = int(end)
        return start, end
    else:
        return 0, None

class PathView(MethodView):
    def get(self, p=''):
        hide_dotfile = request.args.get('hide-dotfile', request.cookies.get('hide-dotfile', 'no'))

        path = os.path.join(root, p)
        if os.path.isdir(path):
            contents = []
            total = {'size': 0, 'dir': 0, 'file': 0}
            for filename in os.listdir(path):
                if filename in ignored:
                    continue
                if hide_dotfile == 'yes' and filename[0] == '.':
                    continue
                filepath = os.path.join(path, filename)
                stat_res = os.stat(filepath)
                info = {}
                info['name'] = filename
                info['mtime'] = stat_res.st_mtime
                ft = get_type(stat_res.st_mode)
                info['type'] = ft
                total[ft] += 1
                sz = stat_res.st_size
                info['size'] = sz
                total['size'] += sz
                contents.append(info)
            page = render_template('index.html', path=p, contents=contents, total=total, hide_dotfile=hide_dotfile)
            res = make_response(page, 200)
            res.set_cookie('hide-dotfile', hide_dotfile, max_age=16070400)
        elif os.path.isfile(path):
            video = datatypes['video']
            if p != '':
                subfix = p.split('.')[-1]
                if subfix in video:
                    page = render_template('player.html', video_file=p)
                    res = make_response(page, 200)
                else:
                    if 'Range' in request.headers:
                        start, end = get_range(request)
                        res = partial_response(path, start, end)
                    else:
                        res = send_file(path)
                        res.headers.add('Content-Disposition', 'attachment')
            else:
                return make_response('Not support', 404)
        else:
            res = make_response('Not found', 404)
        return res

@app.route('/del')
def delete():
    filelist = request.args.get('filelist')
    filelist = json.loads(filelist)
    for file in filelist:
        path = os.path.join(root,file)
        if os.path.isdir(path):
            shutil.rmtree(path)
        elif os.path.isfile(path):
            os.remove(path)
    ret = {
        "result":1
    }
    return jsonify(ret)

@app.route("/rename")
def rename():
    old_name = request.args.get("old_name")
    new_name = request.args.get("new_name")
    old_path = os.path.join(root,old_name)
    new_path = os.path.join(root,new_name)
    print(old_path,new_path)
    os.rename(old_path,new_path)
    ret = {
        "result": 1
    }
    return jsonify(ret)

def gen(path):
    size = os.path.getsize(path)
    with open(path,'rb') as f:
        b = f.read()
        while b:
            yield b

@app.route("/video")
def video():
    file = request.args.get('file')
    path = os.path.join(root,file)
    response = Response(
        gen(path),
        206,  # Partial Content
        mimetype=mimetypes.guess_type(path)[0],  # Content-Type must be correct
        direct_passthrough=True,  # Identity encoding
    )
    response.headers.add(
        'Accept-Ranges', 'bytes'  # Accept request with Range header
    )
    return response

@app.route('/test')
def test():
    return render_template('test.html')

path_view = PathView.as_view('path_view')
app.add_url_rule('/', view_func=path_view)
app.add_url_rule('/<path:p>', view_func=path_view)

if __name__ == '__main__':
    #app.run(port=8000)
    app.run(debug=True, host='0.0.0.0',port=8000)

