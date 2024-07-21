import requests
import gzip
import shutil
import os

eth_urls = [
    f"https://api.coin.z.com/data/trades/ETH/2024/07/202407{str(day).zfill(2)}_ETH.csv.gz"
    for day in range(1, 32)
]
btc_urls = [
    f"https://api.coin.z.com/data/trades/BTC/2024/07/202407{str(day).zfill(2)}_BTC.csv.gz"
    for day in range(1, 32)
]
eth_file_paths = [f"202407{str(day).zfill(2)}_ETH.csv" for day in range(1, 32)]
btc_file_paths = [f"202407{str(day).zfill(2)}_BTC.csv" for day in range(1, 32)]

def download_and_save(urls, file_paths):
    for url, file_path in zip(urls, file_paths):
        response = requests.get(url)
        if response.status_code == 200:
            gz_file_path = file_path + ".gz"
            with open(gz_file_path, 'wb') as f:
                f.write(response.content)
            with gzip.open(gz_file_path, 'rb') as f_in:
                with open(file_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            os.remove(gz_file_path)
            print(f"Downloaded and saved: {file_path}")
        else:
            print(f"Failed to download: {url}")

# ETHとBTCのデータをダウンロード
download_and_save(eth_urls, eth_file_paths)
download_and_save(btc_urls, btc_file_paths)
