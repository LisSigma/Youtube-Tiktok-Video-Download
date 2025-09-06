
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import uuid
import re

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
DOWNLOAD_FOLDER = 'downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Clean up old files (older than 1 hour)
def cleanup_old_files():
    import time
    current_time = time.time()
    for filename in os.listdir(DOWNLOAD_FOLDER):
        file_path = os.path.join(DOWNLOAD_FOLDER, filename)
        if os.path.isfile(file_path):
            # Delete files older than 1 hour
            if current_time - os.path.getctime(file_path) > 3600:
                os.remove(file_path)

@app.route('/video-info', methods=['POST'])
def get_video_info():
    try:
        data = request.get_json()
        url = data.get('url')
        platform = data.get('platform', 'youtube')
        
        if not url:
            return jsonify({'success': False, 'message': 'URL is required'})
        
        # Validate URL based on platform
        if platform == 'youtube' and not re.match(r'^.*(youtube\.com\/watch\?v=|youtu\.be\/).*', url):
            return jsonify({'success': False, 'message': 'Invalid YouTube URL'})
        elif platform == 'tiktok' and not re.match(r'^.*(tiktok\.com\/@.+\/video\/|vm\.tiktok\.com\/).*', url):
            return jsonify({'success': False, 'message': 'Invalid TikTok URL'})
        
        # Get video information
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            return jsonify({
                'success': True,
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'formats': info.get('formats', [])
            })
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/download', methods=['POST'])
def download_video():
    try:
        data = request.get_json()
        url = data.get('url')
        format_type = data.get('format', 'mp4')
        platform = data.get('platform', 'youtube')
        
        if not url:
            return jsonify({'success': False, 'message': 'URL is required'})
        
        # Generate a unique filename
        filename = f"{str(uuid.uuid4())}.{format_type}"
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)
        
        # Set download options based on format
        ydl_opts = {
            'outtmpl': filepath,
            'quiet': True,
        }
        
        if format_type == 'mp3':
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        elif format_type == 'low':
            ydl_opts['format'] = 'worst[ext=mp4]'
        else:  # mp4 or default
            ydl_opts['format'] = 'best[ext=mp4]'
        
        # Download the video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # Clean up old files
        cleanup_old_files()
        
        # Return the download URL
        download_url = f"/download-file/{filename}"
        return jsonify({
            'success': True,
            'download_url': download_url,
            'filename': filename
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/download-file/<filename>')
def download_file(filename):
    filepath = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    else:
        return jsonify({'success': False, 'message': 'File not found'}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)
