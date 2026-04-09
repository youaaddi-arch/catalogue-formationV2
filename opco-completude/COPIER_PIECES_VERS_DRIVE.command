#!/bin/bash
cd "$(dirname "$0")"
echo "============================================"
echo "  Mise à jour et lancement du script..."
echo "============================================"
git pull origin claude/download-interface-attachments-I50wg 2>/dev/null
pip3 install google-auth google-auth-oauthlib google-api-python-client 2>/dev/null
python3 COPIER_PIECES_VERS_DRIVE.py
