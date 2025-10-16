import yt_dlp
import re
import json
import os
import tempfile
import time

class SubtitleError(Exception):
    pass

def get_subtitles(video_id, format_type='txt', language='fr'):
    """
    Récupère les sous-titres avec yt-dlp et cookies YouTube uniquement
    """
    try:
        url = f'https://www.youtube.com/watch?v={video_id}'
        
        # Configuration yt-dlp optimisée pour YouTube
        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': [language, 'en', 'fr'],
            'quiet': False,
            'no_warnings': False,
            'socket_timeout': 60,
            'extract_flat': False,
            'retries': 5,
            'fragment_retries': 5,
            'skip_unavailable_fragments': True,
            'ignoreerrors': False,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            },
            # Paramètres spécifiques YouTube
            'extractor_args': {
                'youtube': {
                    'player_client': ['web', 'android'],
                    'player_skip': ['configs', 'webpage'],
                }
            }
        }
        
        # Gestion OBLIGATOIRE des cookies
        cookies_file = setup_cookies_robust()
        if not cookies_file:
            raise SubtitleError('Cookies YouTube requis - configurez YOUTUBE_COOKIES')
        
        ydl_opts['cookiefile'] = cookies_file
        print(f"🔐 Utilisation des cookies: {cookies_file}")
        
        # Valider que les cookies sont frais
        if not are_cookies_fresh(cookies_file):
            print("⚠️  Attention: Les cookies semblent anciens")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extraire les infos avec gestion d'erreur détaillée
            try:
                info = ydl.extract_info(url, download=False)
            except yt_dlp.utils.DownloadError as e:
                error_msg = str(e)
                if 'Sign in to confirm' in error_msg:
                    raise SubtitleError('Cookies expirés ou invalides - régénérez les cookies YouTube')
                elif 'Video unavailable' in error_msg:
                    raise SubtitleError('Vidéo non disponible')
                elif 'Private video' in error_msg:
                    raise SubtitleError('Vidéo privée')
                else:
                    raise SubtitleError(f'Erreur YouTube: {error_msg}')
            
            # Récupérer les sous-titres disponibles
            subtitles = info.get('subtitles', {})
            automatic_captions = info.get('automatic_captions', {})
            
            print(f"📊 Sous-titres manuels: {list(subtitles.keys())}")
            print(f"📊 Sous-titres auto: {list(automatic_captions.keys())}")
            
            # Combiner les deux sources
            all_subs = {**automatic_captions, **subtitles}
            
            if not all_subs:
                raise SubtitleError('Aucun sous-titre disponible pour cette vidéo')
            
            # Chercher la langue demandée
            selected_lang = None
            is_auto = False
            
            # Priorité 1: Langue exacte manuelle
            if language in subtitles:
                selected_lang = language
                subtitle_data = subtitles[language]
                is_auto = False
                print(f"✅ Sous-titres manuels trouvés en {language}")
            
            # Priorité 2: Langue exacte auto-générée
            elif language in automatic_captions:
                selected_lang = language
                subtitle_data = automatic_captions[language]
                is_auto = True
                print(f"✅ Sous-titres auto-générés trouvés en {language}")
            
            # Priorité 3: Anglais manuel
            elif 'en' in subtitles:
                selected_lang = 'en'
                subtitle_data = subtitles['en']
                is_auto = False
                print(f"🔀 Fallback sur sous-titres anglais manuels")
            
            # Priorité 4: Anglais auto-généré
            elif 'en' in automatic_captions:
                selected_lang = 'en'
                subtitle_data = automatic_captions['en']
                is_auto = True
                print(f"🔀 Fallback sur sous-titres anglais auto-générés")
            
            # Priorité 5: Première langue disponible
            else:
                selected_lang = list(all_subs.keys())[0]
                subtitle_data = all_subs[selected_lang]
                is_auto = selected_lang in automatic_captions
                print(f"🔀 Utilisation de la première langue disponible: {selected_lang}")
            
            # Télécharger les sous-titres au format JSON3
            json3_format = None
            for fmt in subtitle_data:
                if fmt.get('ext') == 'json3':
                    json3_format = fmt
                    break
            
            if not json3_format:
                # Fallback sur le premier format disponible
                json3_format = subtitle_data[0]
                print(f"⚠️  Format JSON3 non disponible, utilisation de: {json3_format.get('ext')}")
            
            # Télécharger le contenu
            import urllib.request
            try:
                response = urllib.request.urlopen(json3_format['url'])
                json_data = json.loads(response.read().decode('utf-8'))
            except Exception as e:
                raise SubtitleError(f'Erreur téléchargement sous-titres: {str(e)}')
            
            # Parser le JSON YouTube
            transcript_data = parse_youtube_json(json_data)
            
            if not transcript_data:
                raise SubtitleError('Impossible de parser les sous-titres - format non supporté')
            
            print(f"✅ {len(transcript_data)} segments de sous-titres extraits")
            
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
                'isAutoGenerated': is_auto,
                'method': 'yt-dlp_with_cookies'
            }
    
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if 'Sign in to confirm' in error_msg:
            raise SubtitleError('ERREUR: Cookies YouTube expirés. Régénérez les cookies et mettez à jour YOUTUBE_COOKIES')
        raise SubtitleError(f'Erreur YouTube: {error_msg}')
    
    except Exception as e:
        import traceback
        print(f"🔥 Erreur détaillée: {traceback.format_exc()}")
        raise SubtitleError(f'Erreur inattendue: {type(e).__name__} - {str(e)}')

def setup_cookies_robust():
    """
    Configuration robuste des cookies - ÉCHEC si pas de cookies valides
    """
    # 1. Variable d'environnement (Render) - PRIORITÉ
    cookies_env = os.getenv('YOUTUBE_COOKIES')
    if cookies_env:
        try:
            # Validation stricte des cookies
            cleaned_cookies = clean_and_validate_cookies(cookies_env)
            if not cleaned_cookies:
                print("❌ ERREUR: Cookies environment vides ou invalides")
                return None
                
            # Créer fichier temporaire
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(cleaned_cookies)
                cookies_path = f.name
                print(f"✅ Cookies environment chargés: {len(cleaned_cookies)} caractères")
                return cookies_path
        except Exception as e:
            print(f"❌ ERREUR configuration cookies: {e}")
            return None
    
    # 2. Fichiers locaux (développement seulement)
    possible_paths = [
        'cookies.txt',
        os.path.join(os.path.dirname(__file__), 'cookies.txt'),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    content = f.read().strip()
                    if content and validate_cookies_strict(content):
                        print(f"✅ Cookies locaux chargés: {path}")
                        return path
                    else:
                        print(f"❌ Cookies locaux invalides: {path}")
            except Exception as e:
                print(f"❌ Erreur lecture cookies {path}: {e}")
    
    print("❌ AUCUN COOKIE VALIDE TROUVÉ")
    return None

def clean_and_validate_cookies(content):
    """
    Nettoie et valide STRICTEMENT le contenu des cookies
    """
    if not content or not content.strip():
        return None
    
    lines = content.strip().split('\n')
    valid_lines = []
    
    # Filtrage strict
    for line in lines:
        line = line.strip()
        # Format Netscape cookies: domain, flag, path, secure, expiration, name, value
        if line and not line.startswith('#') and len(line.split('\t')) >= 7:
            valid_lines.append(line)
    
    if not valid_lines:
        print("❌ Aucune ligne de cookie valide")
        return None
    
    # Vérifier les cookies YouTube essentiels
    essential_cookies = [
        'CONSENT',           # Consentement
        'VISITOR_INFO1_LIVE', # Session utilisateur
        'PREF',              # Préférences
        'YSC',               # Session YouTube
        'LOGIN_INFO',        # Info connexion
    ]
    
    found_cookies = []
    for line in valid_lines:
        for cookie in essential_cookies:
            if cookie in line:
                found_cookies.append(cookie)
    
    print(f"🔍 Cookies essentiels trouvés: {found_cookies}")
    
    # Requiert au moins CONSENT et un cookie de session
    if 'CONSENT' not in found_cookies:
        print("❌ Cookie CONSENT manquant - ESSENTIEL")
        return None
    
    if len(found_cookies) < 2:
        print("❌ Pas assez de cookies essentiels")
        return None
    
    return '\n'.join(valid_lines)

def validate_cookies_strict(content):
    """
    Validation STRICTE des cookies
    """
    return clean_and_validate_cookies(content) is not None

def are_cookies_fresh(cookies_file):
    """
    Vérifie si les cookies sont récents (moins de 24h)
    """
    try:
        if not os.path.exists(cookies_file):
            return False
        
        file_mtime = os.path.getmtime(cookies_file)
        current_time = time.time()
        hours_old = (current_time - file_mtime) / 3600
        
        if hours_old > 24:
            print(f"⚠️  Cookies créés il y a {hours_old:.1f} heures")
            return False
        
        print(f"✅ Cookies frais ({hours_old:.1f} heures)")
        return True
        
    except Exception as e:
        print(f"❌ Erreur vérification fraîcheur: {e}")
        return False

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
            
            # Concaténer tous les segments de texte
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
        print(f"Erreur parsing JSON: {e}")
        return []

def get_available_languages(video_id):
    """Récupère la liste des langues disponibles"""
    try:
        url = f'https://www.youtube.com/watch?v={video_id}'
        
        ydl_opts = {
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
        }
        
        # Cookies OBLIGATOIRES
        cookies_file = setup_cookies_robust()
        if not cookies_file:
            raise SubtitleError('Cookies requis pour récupérer les langues')
        
        ydl_opts['cookiefile'] = cookies_file
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            subtitles = info.get('subtitles', {})
            automatic_captions = info.get('automatic_captions', {})
            
            languages = []
            
            # Sous-titres manuels
            for lang in subtitles.keys():
                languages.append({
                    'code': lang,
                    'name': get_language_name(lang),
                    'isAutoGenerated': False,
                    'isTranslatable': True
                })
            
            # Sous-titres auto-générés
            for lang in automatic_captions.keys():
                if lang not in subtitles:
                    languages.append({
                        'code': lang,
                        'name': f"{get_language_name(lang)} (Auto)",
                        'isAutoGenerated': True,
                        'isTranslatable': True
                    })
            
            return languages
    
    except Exception as e:
        raise SubtitleError(f'Erreur récupération langues: {str(e)}')

def get_language_name(code):
    """Convertit le code langue en nom complet"""
    names = {
        'fr': 'Français', 'en': 'English', 'es': 'Español',
        'de': 'Deutsch', 'it': 'Italiano', 'pt': 'Português',
        'ru': 'Русский', 'ja': '日本語', 'ko': '한국어',
        'zh': '中文', 'ar': 'العربية'
    }
    return names.get(code, code.upper())

# Fonctions de formatage existantes
def format_as_text(transcript_data):
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
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def format_timestamp_vtt(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"