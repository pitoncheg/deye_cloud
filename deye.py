import requests
import json
import os
import time
from dotenv import load_dotenv

# Загружаем конфигурацию из файла .env
load_dotenv()
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")

if not ACCESS_TOKEN:
    print("ACCESS_TOKEN не найден в файле .env. Пожалуйста, добавьте его.")
    exit(1)

# Словарь для перевода ключей метрик на русский язык
METRIC_TRANSLATIONS = {
    "GridVoltageL1L2": "Напряжение сети L1-L2",
    "GridCurrentL1L2": "Ток сети L1-L2",
    "ExternalCTPowerL1L2": "Мощность внешнего трансформатора тока L1-L2",
    "TotalGridPower": "Общая мощность сети",
    "BatteryVoltage": "Напряжение батареи",
    "BatteryCurrent": "Ток батареи",
    "BatteryPower": "Мощность батареи",
    "SOC": "Уровень заряда батареи (SOC)",
    "GridFrequency": "Частота сети",
    "GeneratorFrequency": "Частота генератора",
    "GenVoltage": "Напряжение генератора",
    "TotalGeneratorProduction": "Общая генерация генератора",
    "LoadVoltageL1L2": "Напряжение нагрузки L1-L2",
    "CumulativeEnergyPurchased": "Накопленная потреблённая энергия",
    "RatedPower": "Номинальная мощность",
    "DCVoltagePV1": "Напряжение DC PV1",
    "DCVoltagePV2": "Напряжение DC PV2",
    "DCVoltagePV3": "Напряжение DC PV3",
    "DCCurrentPV1": "Ток DC PV1",
    "DCCurrentPV2": "Ток DC PV2",
    "DCCurrentPV3": "Ток DC PV3",
    "DCPowerPV1": "Мощность DC PV1",
    "DCPowerPV2": "Мощность DC PV2",
    "DCPowerPV3": "Мощность DC PV3",
    "ACVoltageRUA": "Напряжение AC R-U-A",
    "ACCurrentRUA": "Ток AC R-U-A",
    "ACOutputFrequencyR": "Частота выхода AC",
    "TotalActiveProduction": "Общая активная генерация",
    "DailyActiveProduction": "Дневная активная генерация",
    "InverterOutputPowerL1L2": "Выходная мощность инвертора L1-L2",
    "CumulativeGridFeedIn": "Накопленная подача в сеть",
    "DailyGridFeedIn": "Дневная подача в сеть",
    "DailyEnergyPurchased": "Дневная потреблённая энергия",
    "CumulativeConsumption": "Накопленное потребление",
    "TotalConsumptionPower": "Общая потребляемая мощность",
    "DailyConsumption": "Дневное потребление",
    "TotalChargeEnergy": "Общая зарядная энергия",
    "TotalDischargeEnergy": "Общая разрядная энергия",
    "DailyChargingEnergy": "Дневная зарядная энергия",
    "DailyDischargingEnergy": "Дневная разрядная энергия",
}

def fetch_station_data(access_token):
    """
    Получает данные о станциях и устройствах из API DeyeCloud.
    """
    url = 'https://eu1-developer.deyecloud.com/v1.0/station/listWithDevice'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json;charset=UTF-8'
    }
    data = {
        "deviceType": "INVERTER",
        "page": 1,
        "size": 20
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json().get('stationList', [])
    except Exception as e:
        print(f"Ошибка при получении данных о станциях: {e}")
        exit(1)

def fetch_device_metrics(access_token, device_sn):
    """
    Получает последние метрики для указанного устройства.
    """
    url = 'https://eu1-developer.deyecloud.com/v1.0/device/latest'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json;charset=UTF-8'
    }
    data = {
        "deviceList": [device_sn]
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json().get('deviceDataList', [])
    except Exception as e:
        print(f"Ошибка при получении метрик для устройства {device_sn}: {e}")
        return []

def convert_to_number(value):
    """
    Преобразует строковое значение в число, если возможно.
    """
    try:
        return float(value)
    except ValueError:
        return value

def main():
    # Получаем данные о станциях и устройствах
    stations = fetch_station_data(ACCESS_TOKEN)
    if not stations:
        print("Станции не найдены.")
        return

    for station in stations:
        print(f"\nСтанция: {station['name']} ({station['locationAddress']})")
        print(f"Тип сети: {station['gridInterconnectionType']}, Установленная мощность: {station['installedCapacity']} кВт")

        devices = station.get("deviceListItems", [])
        if not devices:
            print("  Нет подключенных устройств.")
            continue

        print("  Подключенные устройства:")
        for device in devices:
            device_sn = device['deviceSn']
            print(f"    Серийный номер: {device_sn}, Тип: {device['deviceType']}")

            # Получаем и выводим метрики
            metrics = fetch_device_metrics(ACCESS_TOKEN, device_sn)
            if not metrics:
                print("      Метрики недоступны.")
                continue

            print("      Метрики:")
            no_input_power = no_output_power = low_battery = False

            for metric in metrics:
                for data in metric.get('dataList', []):
                    key = data['key']
                    value = convert_to_number(data['value'])
                    unit = data.get('unit', '')
                    translated_key = METRIC_TRANSLATIONS.get(key, key)  # Переводим ключ на русский, если возможно
                    print(f"        {translated_key}: {value} {unit}")

                    # Проверка метрик на условия
                    if key in ["GridVoltageL1L2", "GridCurrentL1L2"] and value == 0:
                        no_input_power = True
                    if key == "TotalGridPower" and value == 0:
                        no_output_power = True
                    if key == "SOC" and isinstance(value, (int, float)) and value < 50:
                        low_battery = True

            # Сообщение об условиях
            if no_input_power:
                print("      ⚠ Входящее питание отсутствует!")
            if no_output_power:
                print("      ⚠ Исходящее питание отсутствует!")
            if low_battery:
                print("      ⚠ Уровень заряда батареи менее 50%!")

if __name__ == '__main__':
    main()

