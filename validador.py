# Autor: Carlos Antonio Frias Juarez
# Valida si un texto tiene formato de correo electrónico.
 
def es_correo_valido(correo):
    """Devuelve True si el correo tiene una sola @, usuario y un punto en el dominio."""
    if "@" not in correo:          # sin arroba
        return False
    usuario, dominio = correo.split("@", 1)
    if usuario == "" or "." not in dominio:   # sin usuario o dominio sin punto
        return False
    if "@" in dominio:             # más de una arroba
        return False
    return True