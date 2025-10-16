from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sys

# Ajouter le répertoire courant au path Python
sys.path.append(os.path.dirname(__file__))

app = Flask(__name__, static_folder='..', static_url_path='')

CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Import des fonctions de sous-titres
try:
    from subtitles import get_subtitles, SubtitleError, get_available_languages
    subtitles_available = True
    print("✅ Module subtitles chargé avec support cookies")
except ImportError as e:
    print(f"❌ Erreur: subtitles non disponible: {e}")
    subtitles_available = False

# Routes...
@app.route('/')
def serve_index():
    return send_from_directory('..', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('..', path)

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'service': 'YT Creator Tools API',
        'version': '2.0.0',
        'subtitles_available': subtitles_available,
        'cookies_method': 'yt-dlp_with_cookies'
    }), 200

@app.route('/api/subtitles', methods=['POST', 'OPTIONS'])
def get_video_subtitles():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Corps de requête manquant'}), 400
        
        video_id = data.get('videoId')
        format_type = data.get('format', 'txt')
        language = data.get('language', 'fr')
        
        if not video_id:
            return jsonify({'error': 'videoId manquant'}), 400
        
        valid_formats = ['txt', 'srt', 'vtt']
        if format_type not in valid_formats:
            return jsonify({
                'error': f'Format invalide. Formats acceptés: {", ".join(valid_formats)}'
            }), 400
        
        if not subtitles_available:
            return jsonify({'error': 'Service de sous-titres temporairement indisponible'}), 503
        
        try:
            print(f"🎯 Demande de sous-titres avec cookies: {video_id}")
            result = get_subtitles(video_id, format_type, language)
            print(f"✅ Sous-titres récupérés: {result['lineCount']} lignes")
            return jsonify(result), 200
        except SubtitleError as e:
            print(f"❌ Erreur sous-titres: {e}")
            return jsonify({
                'error': f'Impossible de récupérer les sous-titres: {str(e)}'
            }), 404
    
    except Exception as e:
        print(f"🔥 Erreur serveur: {e}")
        return jsonify({
            'error': 'Erreur interne du serveur',
            'details': str(e) if os.getenv('FLASK_ENV') == 'development' else None
        }), 500

@app.route('/api/subtitles/languages/<video_id>', methods=['GET'])
def get_available_languages_route(video_id):
    try:
        if not subtitles_available:
            return jsonify({'error': 'Service indisponible'}), 503
            
        languages = get_available_languages(video_id)
        return jsonify({
            'videoId': video_id,
            'languages': languages
        }), 200
    
    except SubtitleError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({
            'error': 'Erreur lors de la récupération des langues',
            'details': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)