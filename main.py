import asyncio
import pandas as pd
import logging
logging.getLogger("prophet.plot").disabled = True
from prophet import Prophet
from sf_platform import ServerlessPlatform
from heuristic import ServerlessScheduler
from datetime import datetime
from utils import load_azure_data, preprocess_azure_data


def new_prophet():
    prophet = Prophet(changepoint_prior_scale=1)
    prophet.add_seasonality(name='seconds_level', period=60, fourier_order=20)
    prophet.add_seasonality(name="minute_level", period=3600, fourier_order=5)
    return prophet

async def process_trace_dataframe(sch: ServerlessScheduler, df: pd.DataFrame, function_name: str):
    for idx, row in df.iterrows():
        target_time = row["ds"]
        value = row["y"]

        now = datetime.now()
        if target_time > now:
            await asyncio.sleep((target_time - now).total_seconds())
        
        for _ in range(int(value)):
            print("RUNNING FUNCTION")
            asyncio.create_task(sch.platform.run_function(function_name, query_params="t=3.0"))

        if (idx + 1) % 10 == 0: # idk whatever lmao
            new_model = new_prophet()
            new_model.fit(df.iloc[:idx])
            sch.models[function_name] = new_model
            asyncio.create_task(sch.adjust_scheduling())

async def main() -> None:
    sp = ServerlessPlatform()
    await sp.register_function("sleep", "./sf_platform/examples/sleep/entry.py", "./sf_platform/examples/sleep/requirements.txt")

    scheduler = ServerlessScheduler(sp, { "sleep": new_prophet() })

    # uncomment if you don't have the data
    # load_azure_data()
    trace = preprocess_azure_data(num_samples=100, bin_size=1)
    print(trace.head())
    await process_trace_dataframe(scheduler, trace, "sleep")
    
    sp.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
