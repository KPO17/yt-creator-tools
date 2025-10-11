import yt_dlp
import re
import json
import time

class SubtitleError(Exception):
    """Exception personnalisée pour les erreurs de sous-titres"""
    pass

def get_subtitles(video_id, format_type='txt', language='fr'):
    """
    Récupère les sous-titres avec yt-dlp (avec contournement du bot detection)
    """
    try:
        url = f'https://www.youtube.com/watch?v={video_id}'
        
        # Configuration yt-dlp optimisée pour éviter le bot detection
        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': [language, 'en', 'auto'],
            'quiet': True,
            'no_warnings': True,
            
            # Headers pour sembler humain
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0',
            },
            
            # Pause entre les requêtes
            'socket_timeout': 30,
            'retries': 3,
            
            # Proxy rotationnel (optional - uncomment si vous avez des proxies)
            # 'proxy': 'http://proxy.example.com:8080',
        }
        
        print(f"[INFO] Extraction des sous-titres pour {video_id}...")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Ajouter un délai avant la requête
            time.sleep(2)
            
            info = ydl.extract_info(url, download=False)
            
            # Récupérer les sous-titres disponibles
            subtitles = info.get('subtitles', {})
            automatic_captions = info.get('automatic_captions', {})
            
            # Combiner les deux sources
            all_subs = {**automatic_captions, **subtitles}
            
            if not all_subs:
                raise SubtitleError('Aucun sous-titre disponible pour cette vidéo')
            
            print(f"[INFO] Langues trouvées: {list(all_subs.keys())}")
            
            # Chercher la langue demandée
            selected_lang = None
            is_auto = False
            
            if language in subtitles:
                selected_lang = language
                subtitle_data = subtitles[language]
                print(f"[INFO] Sous-titres trouvés en {language}")
            elif language in automatic_captions:
                selected_lang = language
                subtitle_data = automatic_captions[language]
                is_auto = True
                print(f"[INFO] Sous-titres auto-générés trouvés en {language}")
            elif 'en' in subtitles:
                selected_lang = 'en'
                subtitle_data = subtitles['en']
                print(f"[INFO] Fallback en anglais (manuel)")
            elif 'en' in automatic_captions:
                selected_lang = 'en'
                subtitle_data = automatic_captions['en']
                is_auto = True
                print(f"[INFO] Fallback en anglais (auto-généré)")
            else:
                # Prendre le premier disponible
                selected_lang = list(all_subs.keys())[0]
                subtitle_data = all_subs[selected_lang]
                is_auto = selected_lang in automatic_captions
                print(f"[INFO] Utilisation de {selected_lang}")
            
            # Trouver le format JSON3
            json3_format = None
            for fmt in subtitle_data:
                if fmt.get('ext') == 'json3':
                    json3_format = fmt
                    break
            
            if not json3_format:
                raise SubtitleError('Format de sous-titres JSON3 non trouvé')
            
            # Télécharger les sous-titres avec headers appropriés
            import urllib.request
            import urllib.error
            
            print(f"[INFO] Téléchargement des sous-titres depuis {json3_format['url'][:50]}...")
            
            # Créer une requête avec headers de navigateur
            req = urllib.request.Request(json3_format['url'])
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            req.add_header('Accept-Language', 'en-US,en;q=0.9,fr;q=0.8')
            req.add_header('Accept', 'application/json')
            req.add_header('Referer', f'https://www.youtube.com/watch?v={video_id}')
            req.add_header('Origin', 'https://www.youtube.com')
            
            try:
                response = urllib.request.urlopen(req, timeout=10)
                json_data = json.loads(response.read().decode('utf-8'))
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    raise SubtitleError('Trop de requêtes. YouTube a bloqué temporairement les accès. Réessayez dans quelques minutes.')
                elif e.code == 403:
                    raise SubtitleError('Accès refusé. YouTube détecte les téléchargements automatisés.')
                else:
                    raise SubtitleError(f'Erreur HTTP {e.code} lors du téléchargement')
            
            # Parser le JSON YouTube
            transcript_data = parse_youtube_json(json_data)
            
            if not transcript_data:
                raise SubtitleError('Impossible de parser les sous-titres')
            
            print(f"[INFO] {len(transcript_data)} lignes de sous-titres trouvées")
            
            # Formater selon le type demandé
            if format_type == 'txt':
                content = format_as_text(transcript_data)
            elif format_type == 'srt':
                content = format_as_srt(transcript_data)
            elif format_type == 'vtt':
                content = format_as_vtt(transcript_data)
            else:
                content = format_as_text(transcript_data)
            
            return {
                'videoId': video_id,
                'language': selected_lang,
                'format': format_type,
                'content': content,
                'lineCount': len(transcript_data),
                'isAutoGenerated': is_auto
            }
    
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        print(f"[ERROR] DownloadError: {error_msg}")
        
        if 'Video unavailable' in error_msg or 'not available' in error_msg:
            raise SubtitleError('Vidéo non disponible ou supprimée')
        elif 'Sign in to confirm' in error_msg or 'bot' in error_msg.lower():
            raise SubtitleError('YouTube a détecté un accès automatisé. Réessayez dans quelques minutes.')
        elif 'Private video' in error_msg:
            raise SubtitleError('Vidéo privée - impossible d\'accéder aux sous-titres')
        else:
            raise SubtitleError(f'Erreur YouTube: {error_msg[:100]}')
    
    except SubtitleError as e:
        print(f"[ERROR] SubtitleError: {str(e)}")
        raise
    
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"[ERROR] Exception: {error_msg}")
        raise SubtitleError(f'Erreur: {type(e).__name__} - {str(e)[:100]}')

def parse_youtube_json(json_data):
    """Parse le format JSON3 de YouTube"""
    transcript = []
    
    try:
        events = json_data.get('events', [])
        
        for event in events:
            if 'segs' not in event:
                continue
            
            start_time = event.get('tStartMs', 0) / 1000.0
            duration = event.get('dDurationMs', 0) / 1000.0
            
            text_parts = []
            for seg in event['segs']:
                if 'utf8' in seg:
                    text_parts.append(seg['utf8'])
            
            text = ''.join(text_parts).strip()
            
            if text:
                transcript.append({
                    'text': text,
                    'start': start_time,
                    'duration': duration
                })
        
        return transcript
    
    except Exception as e:
        print(f"[ERROR] Erreur parsing JSON: {e}")
        return []

def get_available_languages(video_id):
    """Récupère la liste des langues disponibles"""
    try:
        url = f'https://www.youtube.com/watch?v={video_id}'
        
        ydl_opts = {
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            subtitles = info.get('subtitles', {})
            automatic_captions = info.get('automatic_captions', {})
            
            languages = []
            
            for lang in subtitles.keys():
                languages.append({
                    'code': lang,
                    'name': lang.upper(),
                    'isAutoGenerated': False,
                    'isTranslatable': True
                })
            
            for lang in automatic_captions.keys():
                if lang not in subtitles:
                    languages.append({
                        'code': lang,
                        'name': f"{lang.upper()} (Auto)",
                        'isAutoGenerated': True,
                        'isTranslatable': True
                    })
            
            return languages
    
    except Exception as e:
        raise SubtitleError(f'Erreur: {str(e)}')

def format_as_text(transcript_data):
    """Formate en texte brut"""
    text_parts = []
    
    for entry in transcript_data:
        text = entry['text'].strip()
        text = re.sub(r'\[.*?\]', '', text)
        if text:
            text_parts.append(text)
    
    full_text = ' '.join(text_parts)
    full_text = re.sub(r'([.!?])\s+', r'\1\n\n', full_text)
    
    return full_text.strip()

def format_as_srt(transcript_data):
    """Formate en SRT"""
    srt_content = []
    
    for i, entry in enumerate(transcript_data, start=1):
        start_time = format_timestamp_srt(entry['start'])
        end_time = format_timestamp_srt(entry['start'] + entry['duration'])
        text = entry['text'].strip()
        
        srt_content.append(f"{i}")
        srt_content.append(f"{start_time} --> {end_time}")
        srt_content.append(text)
        srt_content.append("")
    
    return '\n'.join(srt_content)

def format_as_vtt(transcript_data):
    """Formate en WebVTT"""
    vtt_content = ["WEBVTT", ""]
    
    for entry in transcript_data:
        start_time = format_timestamp_vtt(entry['start'])
        end_time = format_timestamp_vtt(entry['start'] + entry['duration'])
        text = entry['text'].strip()
        
        vtt_content.append(f"{start_time} --> {end_time}")
        vtt_content.append(text)
        vtt_content.append("")
    
    return '\n'.join(vtt_content)

def format_timestamp_srt(seconds):
    """Format SRT : HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def format_timestamp_vtt(seconds):
    """Format VTT : HH:MM:SS.mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"