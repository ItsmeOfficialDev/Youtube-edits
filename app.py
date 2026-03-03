from flask import Flask, request, jsonify, send_file, render_template_string
import yt_dlp
import os
import uuid
import threading
import time
import re
from urllib.parse import quote

app = Flask(__name__)

# Configuration
DOWNLOAD_FOLDER = 'downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# HTML Template - Minimal, Clean, Professional
HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fast YouTube Downloader</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }
        .container {
            max-width: 1000px;
            margin: 40px auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 { font-size: 28px; margin-bottom: 20px; color: #000; }
        h2 { font-size: 20px; margin: 20px 0 10px; color: #444; }
        .input-group {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        input[type="text"] {
            flex: 1;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
        }
        button {
            padding: 12px 24px;
            background: #000;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            transition: background 0.2s;
        }
        button:hover { background: #333; }
        button:disabled { background: #999; cursor: not-allowed; }
        .options {
            display: flex;
            gap: 30px;
            margin: 20px 0;
            padding: 15px 0;
            border-top: 1px solid #eee;
            border-bottom: 1px solid #eee;
        }
        .quality-selector, .format-selector {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        select {
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        .info-box {
            background: #f9f9f9;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
        }
        .video-item {
            border: 1px solid #eee;
            padding: 15px;
            margin: 10px 0;
            border-radius: 4px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .video-title {
            flex: 1;
            font-size: 15px;
            color: #333;
        }
        .video-size {
            margin: 0 20px;
            color: #666;
            font-size: 14px;
            font-weight: 500;
        }
        .video-actions {
            display: flex;
            gap: 8px;
        }
        .btn-small {
            padding: 6px 12px;
            font-size: 13px;
            background: #f0f0f0;
            color: #333;
            border: 1px solid #ddd;
        }
        .btn-small:hover { background: #e0e0e0; }
        .progress {
            display: none;
            margin: 20px 0;
            padding: 15px;
            background: #f0f0f0;
            border-radius: 4px;
        }
        .error {
            color: #d32f2f;
            margin: 10px 0;
            padding: 10px;
            background: #ffebee;
            border-radius: 4px;
        }
        .success {
            color: #2e7d32;
            margin: 10px 0;
            padding: 10px;
            background: #e8f5e8;
            border-radius: 4px;
        }
        .footer {
            margin-top: 30px;
            text-align: center;
            color: #666;
            font-size: 13px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚡ Fast YouTube Downloader</h1>
        
        <div class="input-group">
            <input type="text" id="url" placeholder="Paste YouTube URL or Playlist link here...">
            <button onclick="fetchInfo()" id="fetchBtn">Analyze</button>
        </div>

        <div class="options">
            <div class="format-selector">
                <label>Format:</label>
                <select id="format">
                    <option value="mp4" selected>MP4 Video</option>
                    <option value="mp3">MP3 Audio</option>
                </select>
            </div>
            <div class="quality-selector">
                <label>Quality:</label>
                <select id="quality">
                    <option value="2160p">4K (2160p)</option>
                    <option value="1440p">2K (1440p)</option>
                    <option value="1080p">1080p</option>
                    <option value="720p" selected>720p</option>
                    <option value="480p">480p</option>
                    <option value="360p">360p</option>
                </select>
            </div>
        </div>

        <div id="progress" class="progress">
            <p id="progressMessage">Processing...</p>
        </div>
        <div id="error" class="error" style="display: none;"></div>
        <div id="success" class="success" style="display: none;"></div>

        <div id="playlistInfo" class="info-box" style="display: none;">
            <h2 id="playlistTitle"></h2>
            <p id="playlistStats"></p>
            <button onclick="downloadAllPlaylist()" id="downloadAllBtn">Download All Videos (MP4)</button>
            <button onclick="downloadAllPlaylistAudio()" id="downloadAllAudioBtn">Download All as MP3</button>
        </div>

        <div id="videoList"></div>

        <div class="footer">
            Open Source • No ads • Fast downloads
        </div>
    </div>

    <script>
        let currentPlaylist = null;
        let currentVideo = null;

        function showError(msg) {
            document.getElementById('error').style.display = 'block';
            document.getElementById('error').textContent = msg;
            document.getElementById('success').style.display = 'none';
        }

        function showSuccess(msg) {
            document.getElementById('success').style.display = 'block';
            document.getElementById('success').textContent = msg;
            document.getElementById('error').style.display = 'none';
        }

        function showProgress(msg) {
            document.getElementById('progress').style.display = 'block';
            document.getElementById('progressMessage').textContent = msg;
        }

        function hideProgress() {
            document.getElementById('progress').style.display = 'none';
        }

        function formatBytes(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        async function fetchInfo() {
            const url = document.getElementById('url').value;
            if (!url) {
                showError('Please enter a URL');
                return;
            }

            document.getElementById('fetchBtn').disabled = true;
            showProgress('Analyzing URL...');
            document.getElementById('videoList').innerHTML = '';
            document.getElementById('playlistInfo').style.display = 'none';

            try {
                const response = await fetch('/info', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url: url})
                });
                const data = await response.json();
                
                if (data.error) {
                    showError(data.error);
                } else if (data.is_playlist) {
                    showPlaylist(data);
                } else {
                    showVideo(data);
                }
            } catch (err) {
                showError('Failed to fetch info');
            } finally {
                document.getElementById('fetchBtn').disabled = false;
                hideProgress();
            }
        }

        function showVideo(video) {
            currentVideo = video;
            document.getElementById('videoList').innerHTML = '';
            addVideoToList(video, true);
        }

        function showPlaylist(playlist) {
            currentPlaylist = playlist;
            document.getElementById('playlistTitle').textContent = playlist.title;
            document.getElementById('playlistStats').textContent = 
                `${playlist.videos.length} videos • Total size: ${formatBytes(playlist.total_size)}`;
            document.getElementById('playlistInfo').style.display = 'block';
            
            document.getElementById('videoList').innerHTML = '';
            playlist.videos.forEach(video => addVideoToList(video, false));
        }

        function addVideoToList(video, singleMode) {
            const div = document.createElement('div');
            div.className = 'video-item';
            
            const quality = document.getElementById('quality').value;
            const format = document.getElementById('format').value;
            
            let size = format === 'mp4' ? video.sizes[quality] : video.audio_size;
            let sizeText = size ? formatBytes(size) : 'Size unknown';

            div.innerHTML = `
                <div class="video-title">${video.title}</div>
                <div class="video-size">${sizeText}</div>
                <div class="video-actions">
                    <button class="btn-small" onclick="downloadVideo('${video.url}', 'mp4')">MP4</button>
                    <button class="btn-small" onclick="downloadVideo('${video.url}', 'mp3')">MP3</button>
                </div>
            `;
            document.getElementById('videoList').appendChild(div);
        }

        async function downloadVideo(url, format) {
            const quality = document.getElementById('quality').value;
            showProgress(`Downloading ${format.toUpperCase()}...`);
            
            try {
                const response = await fetch('/download', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        url: url,
                        format: format,
                        quality: quality
                    })
                });
                
                if (response.ok) {
                    const blob = await response.blob();
                    const downloadUrl = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = downloadUrl;
                    a.download = response.headers.get('filename') || 'video.' + format;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(downloadUrl);
                    showSuccess('Download completed!');
                } else {
                    const error = await response.json();
                    showError(error.error);
                }
            } catch (err) {
                showError('Download failed');
            } finally {
                hideProgress();
            }
        }

        async function downloadAllPlaylist() {
            if (!currentPlaylist) return;
            await downloadAllPlaylistItems('mp4');
        }

        async function downloadAllPlaylistAudio() {
            if (!currentPlaylist) return;
            await downloadAllPlaylistItems('mp3');
        }

        async function downloadAllPlaylistItems(format) {
            const quality = document.getElementById('quality').value;
            showProgress(`Preparing to download all as ${format.toUpperCase()}...`);
            
            try {
                const response = await fetch('/download-all', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        playlist_url: document.getElementById('url').value,
                        format: format,
                        quality: quality
                    })
                });
                
                if (response.ok) {
                    const blob = await response.blob();
                    const downloadUrl = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = downloadUrl;
                    a.download = 'playlist.zip';
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(downloadUrl);
                    showSuccess('All downloads completed!');
                } else {
                    const error = await response.json();
                    showError(error.error);
                }
            } catch (err) {
                showError('Failed to download all');
            } finally {
                hideProgress();
            }
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
            'no_warnings': True,
            'extract_flat': False,
            'ignoreerrors': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if 'entries' in info:  # Playlist
                videos = []
                total_size = 0
                
                for entry in info['entries']:
                    if not entry:
                        continue
                    
                    video_url = entry.get('webpage_url', f"https://youtube.com/watch?v={entry['id']}")
                    video_info = {
                        'title': entry.get('title', 'Unknown'),
                        'url': video_url,
                        'sizes': {},
                        'audio_size': 0
                    }
                    
                    # Get sizes for different qualities
                    if 'formats' in entry:
                        for f in entry['formats']:
                            if f.get('height'):
                                height = f.get('height')
                                if height and f.get('filesize'):
                                    video_info['sizes'][f'{height}p'] = f['filesize']
                                    if f'{height}p' == '720p' or not video_info['sizes']:
                                        total_size += f.get('filesize', 0)
                    
                    # Audio size
                    if entry.get('requested_formats'):
                        for f in entry['requested_formats']:
                            if f.get('acodec') != 'none' and f.get('filesize'):
                                video_info['audio_size'] = f['filesize']
                    
                    videos.append(video_info)
                
                return jsonify({
                    'is_playlist': True,
                    'title': info.get('title', 'Playlist'),
                    'videos': videos,
                    'total_size': total_size
                })
            else:  # Single video
                sizes = {}
                audio_size = 0
                
                if 'formats' in info:
                    for f in info['formats']:
                        if f.get('height'):
                            height = f.get('height')
                            if height and f.get('filesize'):
                                sizes[f'{height}p'] = f['filesize']
                
                if info.get('requested_formats'):
                    for f in info['requested_formats']:
                        if f.get('acodec') != 'none' and f.get('filesize'):
                            audio_size = f['filesize']
                
                return jsonify({
                    'is_playlist': False,
                    'title': info.get('title', 'Video'),
                    'url': url,
                    'sizes': sizes,
                    'audio_size': audio_size
                })
                
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/download', methods=['POST'])
def download():
    try:
        url = request.json['url']
        format_type = request.json.get('format', 'mp4')
        quality = request.json.get('quality', '720p')
        
        # Extract quality number
        quality_num = int(re.sub(r'[^0-9]', '', quality)) if quality != 'best' else 1080
        
        unique_id = str(uuid.uuid4())
        
        if format_type == 'mp3':
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': os.path.join(DOWNLOAD_FOLDER, f'%(title)s_{unique_id}.%(ext)s'),
                'quiet': True,
                'no_warnings': True
            }
        else:  # mp4
            # Try to get requested quality, fallback to next best
            format_spec = f'best[height<={quality_num}][ext=mp4]/best[height<={quality_num}]/best[ext=mp4]/best'
            ydl_opts = {
                'format': format_spec,
                'outtmpl': os.path.join(DOWNLOAD_FOLDER, f'%(title)s_{unique_id}.%(ext)s'),
                'quiet': True,
                'no_warnings': True
            }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            if format_type == 'mp3':
                filename = filename.rsplit('.', 1)[0] + '.mp3'
            
            if os.path.exists(filename):
                return send_file(
                    filename,
                    as_attachment=True,
                    download_name=f"{info['title']}.{format_type}",
                    mimetype='audio/mpeg' if format_type == 'mp3' else 'video/mp4'
                )
            else:
                return jsonify({'error': 'File not found'}), 404
                
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/download-all', methods=['POST'])
def download_all():
    try:
        playlist_url = request.json['playlist_url']
        format_type = request.json.get('format', 'mp4')
        quality = request.json.get('quality', '720p')
        
        quality_num = int(re.sub(r'[^0-9]', '', quality)) if quality != 'best' else 1080
        unique_id = str(uuid.uuid4())
        
        if format_type == 'mp3':
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': os.path.join(DOWNLOAD_FOLDER, f'%(title)s_{unique_id}.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': True
            }
        else:
            format_spec = f'best[height<={quality_num}][ext=mp4]/best[height<={quality_num}]/best[ext=mp4]/best'
            ydl_opts = {
                'format': format_spec,
                'outtmpl': os.path.join(DOWNLOAD_FOLDER, f'%(title)s_{unique_id}.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': True
            }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([playlist_url])
            
        # Create zip file
        import zipfile
        zip_filename = os.path.join(DOWNLOAD_FOLDER, f'playlist_{unique_id}.zip')
        
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for file in os.listdir(DOWNLOAD_FOLDER):
                if unique_id in file and file.endswith(f'.{format_type}'):
                    filepath = os.path.join(DOWNLOAD_FOLDER, file)
                    zipf.write(filepath, os.path.basename(filepath))
                    os.remove(filepath)
        
        if os.path.exists(zip_filename):
            return send_file(
                zip_filename,
                as_attachment=True,
                download_name='playlist.zip',
                mimetype='application/zip'
            )
        else:
            return jsonify({'error': 'No files downloaded'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Clean old files every hour
def clean_old_files():
    while True:
        time.sleep(3600)
        for filename in os.listdir(DOWNLOAD_FOLDER):
            filepath = os.path.join(DOWNLOAD_FOLDER, filename)
            if os.path.isfile(filepath):
                if time.time() - os.path.getctime(filepath) > 3600:
                    os.remove(filepath)

threading.Thread(target=clean_old_files, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
