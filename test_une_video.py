# test_une_video.py
import sys
sys.path.insert(0, 'api')
from subtitles import get_subtitles
import time

video_id = '0ZZ6WpkoAww'

print(f"Test vidéo {video_id}...")
print("Attente de 3 secondes pour éviter rate limit...")
time.sleep(3)

try:
    result = get_subtitles(video_id, 'txt', 'fr')
    print(f"\n✅ SUCCÈS !")
    print(f"Langue: {result['language']}")
    print(f"Lignes: {result['lineCount']}")
    print(f"\nAperçu:\n{result['content'][:500]}...")
except Exception as e:
    print(f"\n❌ Erreur: {e}")