import pandas as pd
import numpy as np
from datetime import datetime
import asyncio
import time

file_path = 'medical_diagnostic_devices_10000.xlsx'


def clean_data(df):
    if df['uptime_pct'].dtype == 'object':
        df['uptime_pct'] = df['uptime_pct'].str.replace(',', '.').astype(float)

    date_columns = ['install_date', 'warranty_until', 'last_calibration_date', 'last_service_date']
    for col in date_columns:
        df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True, format='mixed')

    status_mapping = {
        'operation': 'operational', 'op': 'operational', 'OK': 'operational',
        'planned_i': 'planned_installation', 'broken': 'faulty', 'faulty': 'faulty',
        'maintenance_scheduled': 'maintenance_scheduled'
    }
    df['status'] = df['status'].str.lower().str.strip().replace(status_mapping)

    mask = df['last_calibration_date'] < df['install_date']
    df.loc[mask, 'last_calibration_date'] = np.nan
    return df


# Синхронная версия
def run_sync():
    print("Начинаем синхронное выполнение...")
    start_time = time.time()

    df = pd.read_excel(file_path)
    df = clean_data(df)
    today = pd.Timestamp(datetime.now())

    expired_warranty = df[df['warranty_until'] < today].copy()
    expired_warranty.to_excel('sync_expired_warranty.xlsx', index=False)

    clinic_problems = df.groupby(['clinic_id', 'clinic_name'])['issues_reported_12mo'].sum().reset_index()
    top_problem_clinics = clinic_problems.sort_values(by='issues_reported_12mo', ascending=False)
    top_problem_clinics.to_excel('sync_clinic_issues.xlsx', index=False)

    df['days_since_calibration'] = (today - df['last_calibration_date']).dt.days
    calibration_report = df[df['days_since_calibration'] > 365][
        ['device_id', 'model', 'clinic_name', 'last_calibration_date', 'days_since_calibration']]
    calibration_report.to_excel('sync_calibration_alerts.xlsx', index=False)

    pivot_report = df.pivot_table(index=['clinic_name'], columns=['model'], values=['device_id', 'uptime_pct'],
                                  aggfunc={'device_id': 'count', 'uptime_pct': 'mean'}, fill_value=0)
    pivot_report.to_excel('sync_pivot_summary.xlsx')

    print(f"Синхронное время: {time.time() - start_time:.2f} сек.\n")


# Асинхронная версия

def task_warranty(df, today):
    expired = df[df['warranty_until'] < today].copy()
    expired.to_excel('async_expired_warranty.xlsx', index=False)


def task_issues(df):
    clinic_problems = df.groupby(['clinic_id', 'clinic_name'])['issues_reported_12mo'].sum().reset_index()
    top = clinic_problems.sort_values(by='issues_reported_12mo', ascending=False)
    top.to_excel('async_clinic_issues.xlsx', index=False)


def task_calibration(df, today):
    df['days_since_calibration'] = (today - df['last_calibration_date']).dt.days
    report = df[df['days_since_calibration'] > 365][
        ['device_id', 'model', 'clinic_name', 'last_calibration_date', 'days_since_calibration']]
    report.to_excel('async_calibration_alerts.xlsx', index=False)


def task_pivot(df):
    pivot_report = df.pivot_table(index=['clinic_name'], columns=['model'], values=['device_id', 'uptime_pct'],
                                  aggfunc={'device_id': 'count', 'uptime_pct': 'mean'}, fill_value=0)
    pivot_report.to_excel('async_pivot_summary.xlsx')


async def run_async():
    print("Начинаем асинхронное выполнение...")
    start_time = time.time()

    # Асинхронное чтение файла
    df = await asyncio.to_thread(pd.read_excel, file_path)
    df = clean_data(df)
    today = pd.Timestamp(datetime.now())

    # Создаем асинхронные задачи.
    tasks = [
        asyncio.to_thread(task_warranty, df.copy(), today),
        asyncio.to_thread(task_issues, df.copy()),
        asyncio.to_thread(task_calibration, df.copy(), today),
        asyncio.to_thread(task_pivot, df.copy())
    ]

    await asyncio.gather(*tasks)

    print(f"Асинхронное время: {time.time() - start_time:.2f} сек.\n")


if __name__ == "__main__":
    run_sync()

    asyncio.run(run_async())
