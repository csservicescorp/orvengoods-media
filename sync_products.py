#!/usr/bin/env python3
"""Refresh data/products.json and images/<handle>/NN.jpg from the live store.
Run locally (the cloud sandbox cannot reach orvengoods.com) whenever products change:
    python sync_products.py
"""
import json, os, re, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "Mozilla/5.0"}


def get(url):
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except Exception:
            time.sleep(5 * (i + 1))
    raise RuntimeError(url)


def main():
    data = json.loads(get("https://orvengoods.com/products.json?limit=250"))["products"]
    out = []
    for p in sorted(data, key=lambda p: p["title"].lower()):
        imgs = [i["src"].split("?")[0] for i in p["images"]][:6]
        if len(imgs) < 2:
            continue
        d = os.path.join(HERE, "images", p["handle"])
        os.makedirs(d, exist_ok=True)
        local = []
        for n, src in enumerate(imgs):
            f = os.path.join(d, f"{n:02d}.jpg")
            if not os.path.exists(f):
                open(f, "wb").write(get(src + "?width=1200"))
                time.sleep(0.5)
            local.append(f"images/{p['handle']}/{n:02d}.jpg")
        desc = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", p["body_html"] or "")).strip()
        out.append({"handle": p["handle"], "title": p["title"],
                    "url": f"https://orvengoods.com/products/{p['handle']}",
                    "price": p["variants"][0]["price"], "description": desc[:1200],
                    "image_urls": imgs, "local_images": local})
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    with open(os.path.join(HERE, "data", "products.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(len(out), "products")


if __name__ == "__main__":
    main()
