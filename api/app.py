from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from subtitles import get_subtitles, SubtitleError

app = Flask(__name__, static_folder='..', static_url_path='')

# Configuration CORS pour permettre l'accès depuis votre domaine
CORS(app, resources={
    r"/api/*": {
        "origins": "*",  # En production, remplacez par votre domaine
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Route pour servir les fichiers statiques (HTML, JS, CSS)
@app.route('/')
def serve_index():
    return send_from_directory('..', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('..', path)

# Route santé pour vérifier que le serveur fonctionne
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'service': 'YT Creator Tools API',
        'version': '2.0.0'
    }), 200

# Route principale pour récupérer les sous-titres
@app.route('/api/subtitles', methods=['POST', 'OPTIONS'])
def get_video_subtitles():
    # Gérer les requêtes OPTIONS (preflight CORS)
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Récupérer les données de la requête
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Corps de requête manquant'}), 400
        
        video_id = data.get('videoId')
        format_type = data.get('format', 'txt')  # txt, srt, vtt
        language = data.get('language', 'fr')
        
        if not video_id:
            return jsonify({'error': 'videoId manquant'}), 400
        
        # Valider le format
        valid_formats = ['txt', 'srt', 'vtt']
        if format_type not in valid_formats:
            return jsonify({
                'error': f'Format invalide. Formats acceptés: {", ".join(valid_formats)}'
            }), 400
        
        # Récupérer les sous-titres
        result = get_subtitles(video_id, format_type, language)
        
        return jsonify(result), 200
    
    except SubtitleError as e:
        return jsonify({'error': str(e)}), 404
    
    except Exception as e:
        print(f"Erreur serveur: {e}")
        return jsonify({
            'error': 'Erreur interne du serveur',
            'details': str(e) if os.getenv('FLASK_ENV') == 'development' else None
        }), 500

# Route pour lister les langues disponibles pour une vidéo
@app.route('/api/subtitles/languages/<video_id>', methods=['GET'])
def get_available_languages(video_id):
    try:
        from subtitles import get_available_languages as get_langs
        languages = get_langs(video_id)
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

# Gestion des erreurs 404
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Route non trouvée'}), 404

# Gestion des erreurs 500
@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Erreur interne du serveur'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)