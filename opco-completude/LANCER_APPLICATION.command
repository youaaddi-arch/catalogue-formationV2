#!/bin/bash
cd "$(dirname "$0")/catalogue-formationV2/opco-completude"
echo "==================================="
echo " Lancement de l'application OPCO EP"
echo "==================================="
echo ""
echo "Ne fermez pas cette fenetre !"
echo ""
python3 app.py
echo ""
echo "L'application s'est arretee. Appuyez sur une touche pour fermer."
read -n 1
