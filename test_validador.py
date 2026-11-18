# Autor: Carlos Antonio Frias Juarez
# Pruebas de es_correo_valido. Ejecutar con: pytest -v

from validador import es_correo_valido


def test_correo_valido():
    assert es_correo_valido("alumno@escuela.org") == True


def test_sin_arroba():
    assert es_correo_valido("alumno.escuela.org") == False


def test_dominio_sin_punto():
    assert es_correo_valido("alumno@escuela") == False


def test_usuario_vacio():
    assert es_correo_valido("@escuela.org") == False


def test_dos_arrobas():
    assert es_correo_valido("alumno@@escuela.org") == False
