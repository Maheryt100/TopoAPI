#!/usr/bin/env python3
"""
Script de diagnostic JWT pour FastAPI
Usage: python debug_jwt.py
"""

import sys
import jwt
from datetime import datetime, timedelta, timezone

# Importer la config
try:
    from app.core.config import get_settings
    settings = get_settings()
except Exception as e:
    print(f"❌ Erreur import config: {e}")
    sys.exit(1)

print("=" * 60)
print("🔍 DIAGNOSTIC JWT FASTAPI")
print("=" * 60)
print()

# 1. Vérifier la configuration
print("1️⃣  CONFIGURATION FASTAPI")
print("-" * 60)

jwt_secret = settings.jwt_secret
jwt_algorithm = settings.jwt_algorithm

if not jwt_secret:
    print("❌ JWT_SECRET non configuré dans .env")
    print("   Ajoutez: JWT_SECRET=votre_cle_secrete")
    sys.exit(1)

print("✅ JWT_SECRET configuré")
print(f"   Longueur: {len(jwt_secret)} caractères")
print(f"   Preview: {jwt_secret[:20]}...")
print(f"   Algorithm: {jwt_algorithm}")
print()

# 2. Créer un token de test
print("2️⃣  TEST CRÉATION TOKEN")
print("-" * 60)

try:
    test_payload = {
        'iss': 'http://localhost',
        'sub': 1,
        'iat': datetime.now(timezone.utc),
        'exp': datetime.now(timezone.utc) + timedelta(hours=8),
        'user': {
            'id': 1,
            'email': 'test@example.com',
            'name': 'Test User',
            'role': 'admin',
            'id_district': 1
        }
    }
    
    test_token = jwt.encode(test_payload, jwt_secret, algorithm=jwt_algorithm)
    
    print("✅ Token créé avec succès")
    print(f"   Longueur: {len(test_token)} caractères")
    print(f"   Token complet:")
    print(f"   {test_token}")
    print()
    
except Exception as e:
    print(f"❌ Erreur création token: {e}")
    sys.exit(1)

# 3. Tester le décodage
print("3️⃣  TEST DÉCODAGE TOKEN")
print("-" * 60)

try:
    decoded = jwt.decode(test_token, jwt_secret, algorithms=[jwt_algorithm])
    
    print("✅ Token décodé avec succès")
    print("   Payload:")
    import json
    print(json.dumps(decoded, indent=2, default=str))
    print()
    
except jwt.ExpiredSignatureError:
    print("❌ Token expiré")
    sys.exit(1)
except jwt.InvalidSignatureError:
    print("❌ Signature invalide")
    sys.exit(1)
except Exception as e:
    print(f"❌ Erreur décodage: {e}")
    sys.exit(1)

# 4. Afficher la clé pour comparaison
print("4️⃣  CLÉ À VÉRIFIER DANS LARAVEL")
print("-" * 60)
print("Dans Laravel .env, vérifiez que JWT_SECRET_KEY est:")
print(jwt_secret)
print()

# 5. Tester avec un token Laravel (si fourni)
print("5️⃣  TEST TOKEN LARAVEL")
print("-" * 60)
print("Pour tester un token généré par Laravel:")
print()
print("1. Exécutez dans Laravel: php debug_jwt.php")
print("2. Copiez le token généré")
print("3. Testez ici:")
print()
print("   python3 -c \"")
print("   import jwt")
print(f"   token = 'COLLEZ_LE_TOKEN_ICI'")
print(f"   secret = '{jwt_secret}'")
print(f"   decoded = jwt.decode(token, secret, algorithms=['{jwt_algorithm}'])")
print("   print(decoded)")
print("   \"")
print()

print("=" * 60)
print("✅ DIAGNOSTIC TERMINÉ")
print("=" * 60)
print()
print("📝 VÉRIFICATIONS À FAIRE:")
print("   1. Les JWT_SECRET sont-ils identiques dans les 2 .env ?")
print("   2. FastAPI a-t-il été redémarré après modification .env ?")
print("   3. Le token Laravel est-il au format Bearer dans le header ?")
print()