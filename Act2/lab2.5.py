# Lab RESTCONF con Python - Parte 2 (PUT)

import json       # Manejo de datos JSON
import requests   # Peticiones HTTP/REST

# Oculta advertencias SSL (certificado autofirmado)
requests.packages.urllib3.disable_warnings()

# URL que apunta a la interfaz Loopback99
api_url = "https://10.10.20.181/restconf/data/ietf-interfaces:interfaces/interface=Loopback99"

# Encabezados: formato JSON de YANG
headers = {
    "Accept": "application/yang-data+json",
    "Content-type": "application/yang-data+json"
}

# Credenciales del sandbox (usuario, contraseña)
basicauth = ("developer", "C1sco12345")

# Datos YANG de la nueva interfaz (en Python, true se escribe True)
yangConfig = {
    "ietf-interfaces:interface": {
        "name": "Loopback99",
        "description": "WHATEVER99",
        "type": "iana-if-type:softwareLoopback",
        "enabled": True,
        "ietf-ip:ipv4": {
            "address": [
                {
                    "ip": "99.99.99.99",
                    "netmask": "255.255.255.0"
                }
            ]
        },
        "ietf-ip:ipv6": {}
    }
}

# Envía el PUT para crear Loopback99
resp = requests.put(api_url, data=json.dumps(yangConfig), auth=basicauth,
                    headers=headers, verify=False)

# Revisa el código de estado de la respuesta
if (resp.status_code >= 200 and resp.status_code <= 299):
    print("STATUS OK: {}".format(resp.status_code))
else:
    print("Error code {}, reply: {}".format(resp.status_code, resp.text))