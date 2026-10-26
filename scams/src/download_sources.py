"""Download the public source files for the scam analysis into data/raw/.

FTC Consumer Sentinel Data Books (PDF, 2019 to 2024) and US Census Bureau national population estimates (xlsx).
The FTC publishes these figures only as PDF tables and an interactive dashboard, so tables are parsed by src/ftc.py.
"""
from pathlib import Path
from urllib.request import Request, urlopen

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
FTC = "https://search.ftc.gov/system/files/"
SOURCES = {
    "csn_2019.pdf": FTC + "documents/reports/consumer-sentinel-network-data-book-2019/consumer_sentinel_network_data_book_2019.pdf",
    "csn_2020.pdf": FTC + "documents/reports/consumer-sentinel-network-data-book-2020/csn_annual_data_book_2020.pdf",
    "csn_2021.pdf": FTC + "ftc_gov/pdf/CSN%20Annual%20Data%20Book%202021%20Final%20PDF.pdf",
    "csn_2022.pdf": FTC + "ftc_gov/pdf/CSN-Data-Book-2022.pdf",
    "csn_2023.pdf": FTC + "ftc_gov/pdf/CSN-Annual-Data-Book-2023.pdf",
    "csn_2024.pdf": FTC + "ftc_gov/pdf/csn-annual-data-book-2024.pdf",
    "census_2010_2019.xlsx": "https://www2.census.gov/programs-surveys/popest/tables/2010-2019/state/totals/nst-est2019-01.xlsx",
    "census_2020_2024.xlsx": "https://www2.census.gov/programs-surveys/popest/tables/2020-2024/state/totals/NST-EST2024-POP.xlsx",
}

if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    for name, url in SOURCES.items():
        req = Request(url, headers={"User-Agent": "research-script (portfolio analysis)"})
        data = urlopen(req, timeout=120).read()
        (RAW / name).write_bytes(data)
        print(f"{name}: {len(data):,} bytes")
