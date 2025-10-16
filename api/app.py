# Dans la section des imports, commentez yt-dlp :
try:
    # from subtitles import get_subtitles, SubtitleError
    # subtitles_available = True
    subtitles_available = False  # Désactivé pour éviter les erreurs
except ImportError as e:
    print(f"Info: yt-dlp disabled: {e}")
    subtitles_available = False

try:
    from subtitles_fallback import get_subtitles_fallback
    fallback_available = True
except ImportError as e:
    print(f"❌ Erreur: subtitles_fallback non disponible: {e}")
    fallback_available = False

# Modifiez la route pour utiliser uniquement le fallback :
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
        
        # UTILISER UNIQUEMENT LA MÉTHODE FALLBACK
        if not fallback_available:
            return jsonify({'error': 'Service de sous-titres temporairement indisponible'}), 503
        
        try:
            result = get_subtitles_fallback(video_id, format_type, language)
            return jsonify(result), 200
        except Exception as fallback_error:
            return jsonify({
                'error': f'Impossible de récupérer les sous-titres: {str(fallback_error)}'
            }), 404
    
    except Exception as e:
        print(f"Erreur serveur: {e}")
        return jsonify({
            'error': 'Erreur interne du serveur',
            'details': str(e) if os.getenv('FLASK_ENV') == 'development' else None
        }), 500