from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import time
import random
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

app = FastAPI()

TOOL_API_URL = "https://buf-view-tiktok-ayacte.vercel.app/tiktokview"
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
]

class RunRequest(BaseModel):
    links: List[str]
    proxies: Optional[List[str]] = None
    delay_sec: int = 60
    max_workers: int = 500
    requests_per_link: int = 500


def buff_view(tiktok_url, proxies=None):
    try:
        headers = {
            "User-Agent": random.choice(USER_AGENTS)
        }
        proxy = None
        proxies_dict = None
        if proxies:
            proxy = random.choice(proxies)
            proxies_dict = {
                "http": proxy,
                "https": proxy
            }
        start_time = time.time()
        response = requests.get(TOOL_API_URL, params={'video': tiktok_url}, headers=headers, proxies=proxies_dict, timeout=60)
        elapsed = time.time() - start_time
        if response.status_code != 200:
            return {"success": False, "fail": 1, "time": elapsed, "proxy": proxy, "msg": f"HTTP {response.status_code}"}
        data = response.json()
        return {
            "success": data.get('sent_success', 0),
            "fail": data.get('sent_fail', 0),
            "time": data.get('time_used', elapsed),
            "proxy": data.get('proxy_used', proxy or 'Khong ro'),
            "msg": "OK"
        }
    except requests.exceptions.Timeout:
        return {"success": 0, "fail": 1, "time": 60, "proxy": proxy, "msg": "Timeout"}
    except Exception as e:
        return {"success": 0, "fail": 1, "time": 0, "proxy": proxy, "msg": str(e)}


def run_buff(links, delay_sec, max_workers, proxies, requests_per_link):
    link_stats = {link: {"success": 0, "fail": 0, "time": 0, "proxy": {}, "total": 0} for link in links}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_link = {}
        for link in links:
            for i in range(requests_per_link):
                future = executor.submit(buff_view, link, proxies)
                future_to_link[future] = link
        for future in as_completed(future_to_link):
            link = future_to_link[future]
            try:
                result = future.result()
                stat = link_stats[link]
                stat["success"] += result.get("success", 0)
                stat["fail"] += result.get("fail", 0)
                stat["time"] += result.get("time", 0)
                stat["total"] += 1
                if result.get("proxy"):
                    proxy_key = result["proxy"] if result["proxy"] else "Direct"
                    stat["proxy"][proxy_key] = stat["proxy"].get(proxy_key, 0) + 1
            except Exception as exc:
                stat = link_stats[link]
                stat["fail"] += 1
                stat["total"] += 1
    # Tổng kết
    summary = {}
    for link, stat in link_stats.items():
        proxy_most = max(stat["proxy"], key=stat["proxy"].get) if stat["proxy"] else "-"
        avg_time = round(stat["time"] / stat["total"], 2) if stat["total"] else 0
        summary[link] = {
            "success": stat["success"],
            "fail": stat["fail"],
            "proxy_most": proxy_most,
            "avg_time": avg_time,
            "total": stat["total"]
        }
    return summary

@app.post("/run")
def run(request: RunRequest):
    result = run_buff(
        links=request.links,
        delay_sec=request.delay_sec,
        max_workers=request.max_workers,
        proxies=request.proxies,
        requests_per_link=request.requests_per_link
    )
    return {"result": result} 