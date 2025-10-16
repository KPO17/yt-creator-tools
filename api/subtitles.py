import yt_dlp
import re
import json
import os

class SubtitleError(Exception):
    pass

def get_subtitles(video_id, format_type='txt', language='fr'):
    """
    Récupère les sous-titres avec yt-dlp (méthode originale)
    """
    try:
        url = f'https://www.youtube.com/watch?v={video_id}'
        
        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': [language, 'en'],
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # [Le reste de votre code existant...]
            # Gardez votre implémentation originale ici
            
    except Exception as e:
        raise SubtitleError(f'Erreur yt-dlp: {str(e)}')