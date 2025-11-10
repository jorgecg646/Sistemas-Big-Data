import requests
#import pandas as pd
from datetime import datetime, timezone
import matplotlib.pyplot as plt

# Obtener los datos del INE
r = requests.get("https://servicios.ine.es/wstempus/js/ES/DATOS_SERIE/ECV3959?nult=100")
r = r.json()

for i in r:
    print(i)