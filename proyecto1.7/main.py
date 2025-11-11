import requests
import pandas as pd

def obtener_datos(columnas=None, URL_API="NONE"):
    """
    Obtiene datos de la API del INE y devuelve un DataFrame solo con las columnas especificadas.
    
    Args:
        columnas: Lista de columnas a devolver. Si es None, devuelve todas las columnas.
        URL_API: Endpoint de la API del INE. Puede ser DATOS_TABLA o DATOS_SERIE.
    
    Returns:
        DataFrame filtrado por las columnas indicadas.
    """
    data = requests.get(URL_API).json()
    contenido = []

    # Estructura para DATOS_TABLA (list de series con 'Data')
    if isinstance(data, list):
        for serie in data:
            for d in serie.get("Data", []):
                fila = dict(d)
                # Añade información de la serie si existe
                if "Nombre" in serie:
                    fila["Nombre"] = serie["Nombre"]
                contenido.append(fila)
    # Estructura para DATOS_SERIE (dict con 'Data')
    elif isinstance(data, dict) and "Data" in data:
        contenido = data["Data"]

    # DataFrame puro
    df = pd.DataFrame(contenido)

    # Filtra las columnas específicas si se indica
    if columnas:
        columnas_existentes = [col for col in columnas if col in df.columns]
        df = df[columnas_existentes]

    return df

# Ejemplos de uso:

URL1 = "https://servicios.ine.es/wstempus/jsCache/ES/DATOS_TABLA/25171"
print(obtener_datos(columnas=["Nombre", "Anyo", "Valor"], URL_API=URL1).head())

URL2 = "https://servicios.ine.es/wstempus/js/ES/DATOS_SERIE/ECV3959?nult=100"
print(obtener_datos(columnas=["Anyo", "Valor"], URL_API=URL2).head())

URL3 = "https://servicios.ine.es/wstempus/js/ES/DATOS_SERIE/IPC251856?nult=100"
print(obtener_datos(columnas=["Anyo", "Valor"], URL_API=URL3).head())
