import streamlit as st
from influxdb_client import InfluxDBClient
import pandas as pd
import plotly.express as px
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from PIL import Image

# Configuración desde archivo local
from config import INFLUX_URL, INFLUX_TOKEN, ORG, BUCKET

# Función para consultar múltiples campos de un mismo measurement
def query_accelerometer_data(range_minutes=60):
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=ORG)
    query_api = client.query_api()

    query = f'''
    import "math"
    from(bucket: "{BUCKET}")
      |> range(start: -{range_minutes}m)
      |> filter(fn: (r) => r["_measurement"] == "accelerometer" and r["_field"] == "ax" or r["_field"] == "ay" or r["_field"] == "az")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> sort(columns: ["_time"])
    '''

    result = query_api.query_data_frame(query)
    if result.empty:
        return pd.DataFrame()

    # Renombrar y calcular magnitud
    result = result.rename(columns={"_time": "time"})
    result["accel_magnitude"] = np.sqrt(result["ax"]**2 + result["ay"]**2 + result["az"]**2)
    result["time"] = pd.to_datetime(result["time"])
    return result[["time", "accel_magnitude"]]
 
 #Rotoscopio
def query_gyroscope_data(range_minutes=60):
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=ORG)
    query_api = client.query_api()

    query = f'''
    import "math"
    from(bucket: "{BUCKET}")
      |> range(start: -{range_minutes}m)
      |> filter(fn: (r) => r["_measurement"] == "accelerometer" and r["_field"] == "gx" or r["_field"] == "gy" or r["_field"] == "gz")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> sort(columns: ["_time"])
    '''

    result = query_api.query_data_frame(query)
    if result.empty:
        return pd.DataFrame()

    # Renombrar y calcular magnitud
    result = result.rename(columns={"_time": "time"})
    result["gyro_magnitude"] = np.sqrt(result["gx"]**2 + result["gy"]**2 + result["gz"]**2)
    result["time"] = pd.to_datetime(result["time"])
    return result[["time", "gyro_magnitude"]]
    
# Consulta simple de un solo campo
def query_data(measurement, field, range_minutes=60):
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=ORG)
    query_api = client.query_api()

    query = f'''
    from(bucket: "{BUCKET}")
      |> range(start: -{range_minutes}m)
      |> filter(fn: (r) => r["_measurement"] == "{measurement}" and r["_field"] == "{field}")
      |> sort(columns: ["_time"])
    '''

    result = query_api.query(query)
    data = []

    for table in result:
        for record in table.records:
            data.append({"time": record.get_time(), field: record.get_value()})

    df = pd.DataFrame(data)
    if not df.empty:
        df["time"] = pd.to_datetime(df["time"])
    return df

def estado_planta(humedad):
    if humedad > 70:
        return "feliz"
    elif 40 <= humedad <= 70:
        return "normal"
    else:
        return "triste"
        
def dibujar_planta(estado):
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')
    maceta = plt.Rectangle((3.5, 1), 3, 2, color="saddlebrown")
    ax.add_patch(maceta)
    ax.plot([5, 5], [3, 7], color="green", linewidth=5)
    if estado == "feliz":
        ax.plot([5, 6], [6, 7], color="green", linewidth=4)
        ax.plot([5, 4], [6, 7], color="green", linewidth=4)
        ax.plot([5, 6.5], [5, 6], color="green", linewidth=4)
        cara = ":D"
    elif estado == "normal":
        ax.plot([5, 6], [6, 6.5], color="green", linewidth=4)
        ax.plot([5, 4], [6, 6.5], color="green", linewidth=4)
        cara = ":|"
    else:
        ax.plot([5, 6], [6, 5.5], color="green", linewidth=4)
        ax.plot([5, 4], [6, 5.5], color="green", linewidth=4)
        cara = ":("
    ax.text(5, 1.5, cara, fontsize=20, ha='center', va='center')
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches='tight')
    buf.seek(0)
    img = Image.open(buf)
    plt.close(fig)
    return img


# Configuración de la app
st.set_page_config(page_title="🌿 Koru – Jardín Inteligente", layout="wide")
st.title("🌿 Koru – Jardín Inteligente para la Calma")
st.markdown("Monitorea en tiempo real los datos de tu planta: temperatura, humedad y movimiento.")

# Selector de tiempo
range_minutes = st.slider("Selecciona el rango de tiempo (en minutos):", 10, 180, 60)

# Consultas
temp_df = query_data("airSensor", "temperature", range_minutes)
hum_df = query_data("airSensor", "humidity", range_minutes)
mov_df = query_accelerometer_data(range_minutes)
gyr_df = query_gyroscope_data(range_minutes)

# Visualización
col1, col2 = st.columns(2)

with col1:
    st.subheader("🌡️ Temperatura (°C)")
    if not temp_df.empty:
        st.plotly_chart(px.line(temp_df, x="time", y="temperature", title="Temperatura"), use_container_width=True)
    else:
        st.info("Sin datos de temperatura en este rango.")

with col2:
    st.subheader("💧 Humedad (%)")
    if not hum_df.empty:
        st.plotly_chart(px.line(hum_df, x="time", y="humidity", title="Humedad"), use_container_width=True)
    else:
        st.info("Sin datos de humedad en este rango.")

st.subheader("📈 Movimiento (magnitud del acelerómetro)")
if not mov_df.empty:
    st.plotly_chart(px.line(mov_df, x="time", y="accel_magnitude", title="Movimiento"), use_container_width=True)
else:
    st.info("Sin datos de movimiento en este rango.")

st.subheader("📈 Gyroscopio (magnitud del Gyroscopio)")
if not gyr_df.empty:
    st.plotly_chart(px.line(gyr_df, x="time", y="gyro_magnitude", title="Gyroscopio"), use_container_width=True)
else:
    st.info("Sin datos de movimiento en este rango.")

st.subheader("🪴 Estado de la Planta según la Humedad")
if not hum_df.empty:
    humedad_actual = hum_df["humidity"].iloc[-1]
    estado = estado_planta(humedad_actual)
    st.markdown(f"**Humedad actual:** {humedad_actual:.1f}% – Estado: **{estado}**")
    imagen_planta = dibujar_planta(estado)
    st.image(imagen_planta, caption=f"Planta {estado}", use_column_width=False)
else:
    st.info("Sin datos recientes de humedad para mostrar el estado de la planta.")
