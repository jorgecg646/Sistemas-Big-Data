import polars as pl
import os
import re

os.makedirs("data_output", exist_ok=True)

# ── IPC ─────────────────────────────────────────────────────────────────────
df_ipc = pl.read_csv("data_output/Evolucion_IPC.csv")

df_ipc_clean = df_ipc.with_columns([
    pl.col("Fecha").cast(pl.Datetime("ms")).cast(pl.Date).alias("Fecha_Fecha"),
    pl.col("Valor").round(4).alias("IPC_Variacion_Anual"),
    pl.col("Variacion_Interanual_IPC")
      .cast(pl.Float64, strict=False)
      .map_elements(lambda x: None if x is not None and abs(x) == float('inf') else x, return_dtype=pl.Float64)
      .round(4)
]).select([
    "Anyo", "FK_Periodo", "Fecha_Fecha",
    "IPC_Variacion_Anual", "Variacion_Interanual_IPC"
])

# Exportar con ; y luego sustituir punto decimal por coma
df_ipc_clean.write_csv("data_output/ipc_clean.csv", separator=";")
with open("data_output/ipc_clean.csv", "r", encoding="utf-8") as f:
    texto = f.read()
# Reemplaza punto decimal numérico por coma (las fechas YYYY-MM-DD no se ven afectadas)
texto = re.sub(r'(\d)\.(\d)', r'\1,\2', texto)
with open("data_output/ipc_clean.csv", "w", encoding="utf-8") as f:
    f.write(texto)
print("ipc_clean.csv exportado con coma decimal")

# ── IPV ─────────────────────────────────────────────────────────────────────
df_ipv = pl.read_csv("data_output/Evolucion_IPV.csv")

df_ipv_clean = df_ipv.with_columns([
    pl.col("Fecha").cast(pl.Datetime("ms")).cast(pl.Date).alias("Fecha_Fecha"),
    pl.col("Nombre").str.split(". ").list.get(0).str.strip_chars().alias("CCAA"),
    pl.col("Nombre").str.split(". ").list.get(1).str.strip_chars().alias("Tipo_Vivienda"),
    pl.col("Nombre").str.split(". ").list.get(2).str.strip_chars().alias("Metrica"),
    pl.col("Valor").round(4),
    pl.col("Variacion_Interanual_IPV")
      .cast(pl.Float64, strict=False)
      .map_elements(lambda x: None if x is not None and abs(x) == float('inf') else x, return_dtype=pl.Float64)
      .round(4)
]).select([
    "COD", "CCAA", "Tipo_Vivienda", "Metrica",
    "Anyo", "FK_Periodo", "Fecha_Fecha",
    "Valor", "Variacion_Interanual_IPV"
])

df_ipv_clean.write_csv("data_output/ipv_clean.csv", separator=";")
with open("data_output/ipv_clean.csv", "r", encoding="utf-8") as f:
    texto = f.read()
texto = re.sub(r'(\d)\.(\d)', r'\1,\2', texto)
with open("data_output/ipv_clean.csv", "w", encoding="utf-8") as f:
    f.write(texto)
print("ipv_clean.csv exportado con coma decimal")
