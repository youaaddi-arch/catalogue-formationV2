#!/bin/bash
cd "$(dirname "$0")"
echo "==================================="
echo " Lancement de l'application OPCO EP"
echo "==================================="
echo ""
echo "Ne fermez pas cette fenetre !"
echo ""
export FLASK_APP=app.py
python3 -m flask run --host=0.0.0.0 --port=8080
echo ""
echo "L'application s'est arretee. Appuyez sur une touche pour fermer."
read -n 1
