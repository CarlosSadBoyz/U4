# Lab RESTCONF con Python - Parte 2 (PUT)

import json       # Manejo de datos JSON
import requests   # Peticiones HTTP/REST

# Oculta advertencias SSL (certificado autofirmado)
requests.packages.urllib3.disable_warnings()
