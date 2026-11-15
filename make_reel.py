#!/usr/bin/env python3
"""Make a 9:16 Instagram Reel (MP4) from real product photos. No AI imagery.

Usage:
  python make_reel.py --out reels/2026-11-16-acacia.mp4 \
      --hook "The hostess gift that gets used" \
      --title "Mini Acacia Serving Boards" \
      --img URL_OR_PATH --img URL_OR_PATH ...   (3-6 images)

Needs ffmpeg on PATH, or `pip install imageio-ffmpeg`.
"""
import argparse, os, shutil, subprocess, sys, tempfile, textwrap, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SERIF = os.path.join(HERE, "fonts", "PlayfairDisplay.ttf")
SANS = os.path.join(HERE, "fonts", "Inter.ttf")
W, H, FPS = 1080, 1920, 30
BG = "0xF4EFE7"      # warm cream
INK = "0x1F3A2E"     # deep green (logo)
SEG = 2.8            # seconds per photo


def ffmpeg_bin():
    p = shutil.which("ffmpeg")
    if p:
        return p
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        sys.exit("ffmpeg not found: install it or `pip install imageio-ffmpeg`")


def fetch(src, dst):
    if os.path.exists(src):
        shutil.copy(src, dst)
        return
    req = urllib.request.Request(src.split("?")[0] + "?width=1200",
                                 headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r, open(dst, "wb") as f:
        f.write(r.read())


def fpath(p):
    # ffmpeg filter-safe path (Windows drive colon, backslashes)
    return p.replace("\\", "/").replace(":", "\\:")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--hook", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--cta", default="Shop → link in bio")
    ap.add_argument("--img", action="append", required=True)
    a = ap.parse_args()
    imgs = a.img[:6]
    if len(imgs) < 2:
        sys.exit("need at least 2 images")
    ff = ffmpeg_bin()
    tmp = tempfile.mkdtemp()
    files = []
    for i, src in enumerate(imgs):
        d = os.path.join(tmp, f"img{i}.jpg")
        fetch(src, d)
        files.append(d)

    # text files (drawtext textfile avoids escaping problems)
    def tf(name, txt):
        p = os.path.join(tmp, name)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(txt)
        return fpath(p)
    hook_lines = [tf(f"hook{i}.txt", l) for i, l in enumerate(textwrap.wrap(a.hook, 22)[:3])]
    title = tf("title.txt", a.title if len(a.title) <= 38 else a.title[:37].rstrip() + "…")
    cta = tf("cta.txt", a.cta)
    brand = tf("brand.txt", "O R V E N   G O O D S")

    n = len(files)
    total = n * SEG
    frames = int(SEG * FPS)
    inputs, parts = [], []
    for i, f in enumerate(files):
        inputs += ["-i", f]
        zin = "in" if i % 2 == 0 else "out"
        z = ("min(1+0.0009*on,1.08)" if zin == "in" else "max(1.08-0.0009*on,1)")
        parts.append(
            f"[{i}:v]scale=980:1180:force_original_aspect_ratio=decrease,"
            f"pad=980:1180:(ow-iw)/2:(oh-ih)/2:color={BG},setsar=1,"
            f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=980x1180:fps={FPS},"
            f"fade=t=in:st=0:d=0.35,fade=t=out:st={SEG-0.35}:d=0.35:color={BG}[s{i}]"
        )
    concat = "".join(f"[s{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[photos]"
    sf, ss = fpath(SERIF), fpath(SANS)
    draw = (
        f"color=c={BG}:s={W}x{H}:r={FPS}:d={total}[bg];"
        f"[bg][photos]overlay=(W-w)/2:430[v0];"
        + "".join(
            f"[h{i}]drawtext=fontfile='{sf}':textfile='{hl}':fontsize=72:fontcolor={INK}:"
            f"x=(w-text_w)/2:y={130 + i*92}:alpha='min(t/0.6,1)'[h{i+1}];"
            for i, hl in enumerate(hook_lines)).replace("[h0]", "[v0]", 1)
        + f"[h{len(hook_lines)}]null[v1];"
        f"[v1]drawtext=fontfile='{ss}':textfile='{title}':fontsize=44:fontcolor={INK}:"
        f"line_spacing=10:x=(w-text_w)/2:y=1650[v2];"
        f"[v2]drawbox=x=(iw-520)/2:y=1752:w=520:h=78:color={INK}:t=fill[v3];"
        f"[v3]drawtext=fontfile='{ss}':textfile='{cta}':fontsize=36:fontcolor={BG}:"
        f"x=(w-text_w)/2:y=1752+(78-text_h)/2[v4];"
        f"[v4]drawtext=fontfile='{ss}':textfile='{brand}':fontsize=26:fontcolor={INK}:"
        f"x=(w-text_w)/2:y=1862,format=yuv420p[v]"
    )
    fc = ";".join(parts) + ";" + concat + ";" + draw
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    cmd = [ff, "-y", "-loglevel", "error", *inputs,
           "-f", "lavfi", "-t", str(total), "-i", "anullsrc=r=44100:cl=stereo",
           "-filter_complex", fc, "-map", "[v]", "-map", f"{n}:a",
           "-c:v", "libx264", "-profile:v", "high", "-preset", "medium", "-crf", "21",
           "-c:a", "aac", "-b:a", "128k", "-r", str(FPS), "-movflags", "+faststart",
           "-shortest", a.out]
    subprocess.run(cmd, check=True)
    print(a.out, f"{total:.1f}s")


if __name__ == "__main__":
    main()
