import pandas as pd
import matplotlib.pyplot as plt
from influxdb_client import InfluxDBClient

INFLUX_URL = "http://192.168.1.253:8086"
INFLUX_TOKEN = "YSHMaYi6ZtfwL9j2mGPSlOWa5udBMTPD8J3dX3bz4Ef4LB98205HxIpRQZ_-pb_o_McJU96R-qFtQvDZZaUOfg=="
INFLUX_ORG = "Sky"
INFLUX_BUCKET = "proxmox"

flux_query = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: -24h)  
  |> filter(fn: (r) => r._measurement == "cpustat")
  |> filter(fn: (r) => r._field == "avg1")
  |> filter(fn: (r) => r.host == "skymyname")
  |> map(fn: (r) => ({{
      _time: r._time,
      _value: r._value / 4.0 * 100.0,
      _field: "CPU Load %"
  }}))
  |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
  |> fill(usePrevious: true)
'''

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
query_api = client.query_api()
result_tables = query_api.query(flux_query, org=INFLUX_ORG)

data = []
for table in result_tables:
    for record in table.records:
        data.append((record.get_time(), record.get_value()))

df = pd.DataFrame(data, columns=['time', 'cpu_load'])
df = df.set_index('time')

if len(df) < 50:
    print(f"Không đủ dữ liệu ({len(df)} điểm).")
    exit()
else:
    print(f"Đã tải về {len(df)} điểm dữ liệu.")

window_size = 30
k_factor = 2.5

df['ma'] = df['cpu_load'].rolling(window=window_size).mean()
df['std'] = df['cpu_load'].rolling(window=window_size).std()

df['upper_band'] = df['ma'] + (df['std'] * k_factor)
df['lower_band'] = df['ma'] - (df['std'] * k_factor)

df['anomaly'] = (df['cpu_load'] > df['upper_band']) | (df['cpu_load'] < df['lower_band'])
anomalies = df[df['anomaly'] == True]

print(f"Phát hiện được {len(anomalies)} điểm bất thường.")

plt.figure(figsize=(15, 7))

plt.plot(df.index, df['cpu_load'], label='CPU Load (Gốc)', color='blue', alpha=0.8)

plt.plot(df.index, df['ma'], label=f'MA ({window_size} min)', color='orange', linestyle='--')
plt.plot(df.index, df['upper_band'], label=f'Dải trên (K={k_factor})', color='gray', linestyle=':')
plt.plot(df.index, df['lower_band'], label=f'Dải dưới (K={k_factor})', color='gray', linestyle=':')

plt.fill_between(df.index, df['lower_band'], df['upper_band'], color='gray', alpha=0.1, label='Vùng bình thường')

plt.scatter(anomalies.index, anomalies['cpu_load'], 
            color='red', 
            marker='o', 
            s=100, 
            label='Bất thường')

plt.title('Phân tích DSP: Phát hiện Bất thường (Bollinger Bands)')
plt.ylabel('CPU Load %')
plt.xlabel('Thời gian')
plt.legend()
plt.grid(True)
plt.show()