from flask import Flask, request, jsonify, send_file, render_template_string
import yt_dlp
import os
import uuid
import re

app = Flask(__name__)

DOWNLOAD_FOLDER = 'downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>YouTube Downloader</title>
    <style>
        body { font-family: Arial; max-width: 800px; margin: 50px auto; padding: 20px; }
        input, select, button { padding: 10px; margin: 5px; font-size: 16px; }
        input { width: 70%; }
        button { background: black; color: white; border: none; cursor: pointer; }
        .video-item { border: 1px solid #ddd; padding: 10px; margin: 10px 0; }
        .error { color: red; }
    </style>
</head>
<body>
    <h1>YouTube Downloader</h1>
    
    <input type="text" id="url" placeholder="Paste URL">
    <button onclick="fetchInfo()">Get Videos</button>
    
    <div style="margin: 10px 0">
        <select id="format">
            <option value="mp4">MP4</option>
            <option value="mp3">MP3</option>
        </select>
        <select id="quality">
            <option value="1080">1080p</option>
            <option value="720" selected>720p</option>
            <option value="480">480p</option>
        </select>
    </div>
    
    <div id="error" style="color: red"></div>
    <div id="videos"></div>

    <script>
        async function fetchInfo() {
            const url = document.getElementById('url').value;
            if(!url) return;
            
            const res = await fetch('/info', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({url})
            });
            
            const data = await res.json();
            
            if(data.error) {
                document.getElementById('error').innerHTML = data.error;
                return;
            }
            
            let html = '';
            if(data.is_playlist) {
                html += '<h3>' + data.title + ' (' + data.videos.length + ' videos)</h3>';
                data.videos.forEach(v => {
                    html += '<div class="video-item">';
                    html += '<div><b>' + v.title + '</b></div>';
                    html += '<button onclick="download(\'' + v.url + '\')">Download MP4</button> ';
                    html += '<button onclick="download(\'' + v.url + '\', \'mp3\')">Download MP3</button>';
                    html += '</div>';
                });
            } else {
                html += '<div class="video-item">';
                html += '<div><b>' + data.title + '</b></div>';
                html += '<button onclick="download(\'' + url + '\')">Download MP4</button> ';
                html += '<button onclick="download(\'' + url + '\', \'mp3\')">Download MP3</button>';
                html += '</div>';
            }
            
            document.getElementById('videos').innerHTML = html;
        }
        
        async function download(url, format = 'mp4') {
            const quality = document.getElementById('quality').value;
            const btn = event.target;
            btn.disabled = true;
            btn.innerHTML = 'Downloading...';
            
            const res = await fetch('/download', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({url, format, quality})
            });
            
            if(res.ok) {
                const blob = await res.blob();
                const a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = 'video.' + format;
                a.click();
            } else {
                alert('Download failed');
            }
            
            btn.disabled = false;
            btn.innerHTML = 'Download ' + format.toUpperCase();
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/info', methods=['POST'])
def get_info():
    try:
        url = request.json['url']
        
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if 'entries' in info:
                videos = []
                for entry in info['entries']:
                    if entry:
                        videos.append({
                            'title': entry.get('title', 'Unknown'),
                            'url': f"https://youtube.com/watch?v={entry['id']}"
                        })
                
                return jsonify({
                    'is_playlist': True,
                    'title': info.get('title', 'Playlist'),
                    'videos': videos
                })
            else:
                return jsonify({
                    'is_playlist': False,
                    'title': info.get('title', 'Video')
                })
                
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/download', methods=['POST'])
def download():
    try:
        url = request.json['url']
        format_type = request.json.get('format', 'mp4')
        quality = request.json.get('quality', '720')
        
        uid = str(uuid.uuid4())[:8]
        
        if format_type == 'mp3':
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                }],
                'outtmpl': os.path.join(DOWNLOAD_FOLDER, f'{uid}.%(ext)s'),
                'quiet': True,
            }
        else:
            ydl_opts = {
                'format': f'best[height<={quality}]/best',
                'outtmpl': os.path.join(DOWNLOAD_FOLDER, f'{uid}.%(ext)s'),
                'quiet': True,
            }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            for file in os.listdir(DOWNLOAD_FOLDER):
                if file.startswith(uid):
                    path = os.path.join(DOWNLOAD_FOLDER, file)
                    title = re.sub(r'[<>:"/\\|?*]', '', info.get('title', 'video'))
                    return send_file(path, as_attachment=True, download_name=f'{title}.{format_type}')
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
