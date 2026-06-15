"""
hud_display.py — Fullscreen Jarvis HUD rendered via Pygame.
Reads state from /tmp/jarvis_hud_state.json every frame.

Run as a SEPARATE PROCESS (not a thread) so the display loop
never blocks brain.py's audio pipeline:

    python hud_display.py &

Or launch it from brain.py's __main__ with subprocess:

    import subprocess, sys
    subprocess.Popen([sys.executable, "hud_display.py"])

INSTALL:
    pip install pygame requests pillow
"""

import pygame
import math
import time
import datetime
import json
import os
import io
import threading
import urllib.request

from hud_state import read_state

# ── PALETTE ───────────────────────────────────────────────────────────────────
BG           = (0,   0,   0)          # pure black
ACCENT       = (0,   200, 255)        # Jarvis cyan
ACCENT_DIM   = (0,   80,  120)
WHITE        = (220, 235, 245)
MUTED        = (80,  120, 140)
WARN         = (255, 180, 0)
GREEN        = (0,   220, 120)
RED          = (220, 60,  60)

# ── ORB STATE COLOURS ─────────────────────────────────────────────────────────
ORB_COLORS = {
    "idle":       (0,   80,  180),
    "listening":  (0,   200, 255),
    "thinking":   (255, 180,  0),
    "speaking":   (0,   220, 120),
    "whispering": (120, 100, 200),
}

# ── WEATHER ICONS (simple drawn shapes, no image files needed) ────────────────
def draw_weather_icon(surf, icon_name, cx, cy, size, color):
    s = size // 2
    if icon_name == "clear":
        pygame.draw.circle(surf, color, (cx, cy), s, 2)
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            x1 = cx + int((s + 2) * math.cos(rad))
            y1 = cy + int((s + 2) * math.sin(rad))
            x2 = cx + int((s + 8) * math.cos(rad))
            y2 = cy + int((s + 8) * math.sin(rad))
            pygame.draw.line(surf, color, (x1, y1), (x2, y2), 2)
    elif icon_name == "clouds":
        pygame.draw.circle(surf, color, (cx - s//3, cy), s//2, 2)
        pygame.draw.circle(surf, color, (cx + s//3, cy - s//5), s//3, 2)
        pygame.draw.circle(surf, color, (cx + s//2, cy + s//5), s//3, 2)
    elif icon_name == "rain":
        pygame.draw.circle(surf, color, (cx - s//4, cy - s//3), s//3, 2)
        pygame.draw.circle(surf, color, (cx + s//4, cy - s//2), s//4, 2)
        for i in range(4):
            rx = cx - s//2 + i * (s//3)
            pygame.draw.line(surf, color, (rx, cy + 2), (rx - 4, cy + s), 2)
    elif icon_name == "thunder":
        pts = [(cx, cy - s), (cx - s//3, cy), (cx, cy - s//6), (cx - s//4, cy + s)]
        for i in range(len(pts) - 1):
            pygame.draw.line(surf, WARN, pts[i], pts[i+1], 3)
    elif icon_name == "snow":
        for angle in range(0, 360, 60):
            rad = math.radians(angle)
            x2 = cx + int(s * math.cos(rad))
            y2 = cy + int(s * math.sin(rad))
            pygame.draw.line(surf, color, (cx, cy), (x2, y2), 2)
        pygame.draw.circle(surf, color, (cx, cy), 4, 2)
    elif icon_name == "mist":
        for i in range(4):
            y = cy - s + i * (s//2)
            pygame.draw.line(surf, color, (cx - s, y), (cx + s, y), 2)


# ── ALBUM ART LOADER (async, cached) ─────────────────────────────────────────
_art_cache = {}     # url -> pygame.Surface
_art_lock  = threading.Lock()

def _fetch_art(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = resp.read()
        from PIL import Image
        img = Image.open(io.BytesIO(data)).convert("RGB").resize((90, 90))
        arr = pygame.image.fromstring(img.tobytes(), img.size, "RGB")
        with _art_lock:
            _art_cache[url] = arr
    except Exception:
        pass

def get_album_art(url) -> pygame.Surface | None:
    if not url:
        return None
    with _art_lock:
        if url in _art_cache:
            return _art_cache[url]
    # kick off background fetch
    threading.Thread(target=_fetch_art, args=(url,), daemon=True).start()
    return None


# ── ORB RENDERER ─────────────────────────────────────────────────────────────
class JarvisOrb:
    def __init__(self, cx, cy, radius):
        self.cx, self.cy, self.r = cx, cy, radius
        self.phase    = 0.0
        self.pulse    = 0.0

    def update(self, state: str, dt: float):
        self.state = state
        if state in ("speaking", "thinking"):
            self.phase += dt * 3.0
        elif state == "listening":
            self.phase += dt * 1.5
        elif state == "whispering":
            self.phase += dt * 0.8
        else:
            self.phase += dt * 0.3
        self.pulse = (math.sin(self.phase) + 1) / 2   # 0–1

    def draw(self, surf):
        base_color = ORB_COLORS.get(self.state, ORB_COLORS["idle"])

        # Outer glow rings
        for i in range(3, 0, -1):
            alpha_surf = pygame.Surface((self.r * 4, self.r * 4), pygame.SRCALPHA)
            ring_r = self.r + i * 8 + int(self.pulse * 6)
            alpha  = int(40 - i * 10 + self.pulse * 20)
            pygame.draw.circle(alpha_surf, (*base_color, alpha),
                               (self.r * 2, self.r * 2), ring_r, 4)
            surf.blit(alpha_surf, (self.cx - self.r * 2, self.cy - self.r * 2))

        # Core circle (solid)
        pygame.draw.circle(surf, base_color, (self.cx, self.cy), self.r)

        # Inner highlight
        hilight_r = int(self.r * 0.55)
        hilight_surf = pygame.Surface((hilight_r * 2, hilight_r * 2), pygame.SRCALPHA)
        alpha = int(50 + self.pulse * 60)
        pygame.draw.circle(hilight_surf, (255, 255, 255, alpha),
                           (hilight_r, hilight_r), hilight_r)
        surf.blit(hilight_surf, (self.cx - hilight_r, self.cy - hilight_r - self.r // 5))

        # State label below orb
        return base_color   # so caller can tint surrounding UI


# ── WAVEFORM RENDERER ─────────────────────────────────────────────────────────
def draw_waveform(surf, bars, x, y, w, h, color):
    if not bars:
        bars = [0.03] * 32
    n = len(bars)
    bar_w = max(2, (w - n) // n)
    gap   = max(1, (w - n * bar_w) // n)
    for i, val in enumerate(bars):
        bar_h = max(2, int(val * h))
        bx    = x + i * (bar_w + gap)
        by    = y + (h - bar_h) // 2
        # Symmetrical bars (reflect top and bottom)
        alpha_surf = pygame.Surface((bar_w, bar_h), pygame.SRCALPHA)
        brightness = int(180 + val * 75)
        bar_color  = tuple(min(255, int(c * (brightness / 255))) for c in color)
        pygame.draw.rect(alpha_surf, (*bar_color, 210), (0, 0, bar_w, bar_h),
                         border_radius=bar_w // 2)
        surf.blit(alpha_surf, (bx, by))


# ── PROGRESS BAR ─────────────────────────────────────────────────────────────
def draw_progress(surf, x, y, w, h, progress, color_fg, color_bg):
    pygame.draw.rect(surf, color_bg, (x, y, w, h), border_radius=h // 2)
    fill_w = int(w * max(0.0, min(1.0, progress)))
    if fill_w > 0:
        pygame.draw.rect(surf, color_fg, (x, y, fill_w, h), border_radius=h // 2)
    dot_x = x + fill_w
    pygame.draw.circle(surf, color_fg, (dot_x, y + h // 2), h)


# ── MAIN DISPLAY LOOP ─────────────────────────────────────────────────────────
def main():
    pygame.init()
    pygame.mouse.set_visible(False)

    info   = pygame.display.Info()
    W, H   = info.current_w, info.current_h
    screen = pygame.display.set_mode((W, H), pygame.FULLSCREEN | pygame.NOFRAME)
    pygame.display.set_caption("Jarvis HUD")

    # Fonts
    def font(size, bold=False):
        return pygame.font.SysFont("dejavusansmono" if bold else "dejavusans", size, bold=bold)

    f_giant  = font(96, bold=True)   # clock
    f_large  = font(36, bold=True)
    f_med    = font(24)
    f_small  = font(18)
    f_tiny   = font(14)

    clock   = pygame.time.Clock()
    orb     = JarvisOrb(W // 2, H - 160, 54)
    prev_t  = time.time()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit(); return

        now  = time.time()
        dt   = now - prev_t
        prev_t = now

        state = read_state()
        screen.fill(BG)

        # ── subtle scanline texture ─────────────────────────────────────────
        scan_surf = pygame.Surface((W, H), pygame.SRCALPHA)
        for sy in range(0, H, 4):
            pygame.draw.line(scan_surf, (0, 160, 255, 6), (0, sy), (W, sy))
        screen.blit(scan_surf, (0, 0))

        # ── thin top border ─────────────────────────────────────────────────
        pygame.draw.line(screen, ACCENT_DIM, (0, 0), (W, 0), 1)
        pygame.draw.line(screen, ACCENT_DIM, (0, H - 1), (W, H - 1), 1)

        # ────────────────────────────────────────────────────────────────────
        # CLOCK  (top-center)
        # ────────────────────────────────────────────────────────────────────
        now_dt    = datetime.datetime.now()
        time_str  = now_dt.strftime("%H:%M")
        sec_str   = now_dt.strftime(":%S")
        date_str  = now_dt.strftime("%A, %B %d")

        t_surf = f_giant.render(time_str, True, WHITE)
        s_surf = f_large.render(sec_str,  True, MUTED)
        d_surf = f_small.render(date_str, True, MUTED)

        total_w = t_surf.get_width() + s_surf.get_width()
        tx = (W - total_w) // 2
        ty = 36
        screen.blit(t_surf, (tx, ty))
        screen.blit(s_surf, (tx + t_surf.get_width(), ty + t_surf.get_height() - s_surf.get_height() - 8))
        screen.blit(d_surf, ((W - d_surf.get_width()) // 2, ty + t_surf.get_height() + 4))

        # ────────────────────────────────────────────────────────────────────
        # WEATHER  (top-left)
        # ────────────────────────────────────────────────────────────────────
        wx    = 50
        wy    = 50
        wdata = state["weather"]

        draw_weather_icon(screen, wdata["icon"], wx + 28, wy + 28, 48, ACCENT)

        temp_surf = f_large.render(wdata["temp"], True, WHITE)
        cond_surf = f_small.render(wdata["condition"], True, MUTED)
        screen.blit(temp_surf, (wx + 66, wy + 8))
        screen.blit(cond_surf, (wx + 68, wy + 50))

        # ────────────────────────────────────────────────────────────────────
        # SPOTIFY NOW PLAYING  (bottom-left)
        # ────────────────────────────────────────────────────────────────────
        sp    = state["spotify"]
        sy_base = H - 260

        # decorative left accent bar
        pygame.draw.rect(screen, ACCENT, (36, sy_base, 3, 160), border_radius=2)

        # Album art (if loaded)
        art = get_album_art(sp.get("album_art_url", ""))
        art_x = 48
        if art:
            screen.blit(art, (art_x, sy_base))
            art_x += 100

        # Track + artist
        track_surf  = f_med.render(_truncate(sp["track"],  28), True, WHITE)
        artist_surf = f_small.render(_truncate(sp["artist"], 34), True, MUTED)
        screen.blit(track_surf,  (art_x, sy_base + 4))
        screen.blit(artist_surf, (art_x, sy_base + 34))

        # Waveform (below track info)
        wave_y = sy_base + 70
        wave_w = min(420, W // 3)
        wave_color = ACCENT if sp["playing"] else MUTED
        draw_waveform(screen, state.get("waveform", []), art_x, wave_y, wave_w, 48, wave_color)

        # Progress bar
        prog = sp["progress_ms"] / max(1, sp["duration_ms"])
        prog_y = sy_base + 130
        draw_progress(screen, art_x, prog_y, wave_w, 4, prog, ACCENT, ACCENT_DIM)

        # Time stamps
        def fmt_ms(ms):
            s = ms // 1000
            return f"{s // 60}:{s % 60:02d}"
        elapsed_surf  = f_tiny.render(fmt_ms(sp["progress_ms"]),  True, MUTED)
        duration_surf = f_tiny.render(fmt_ms(sp["duration_ms"]), True, MUTED)
        screen.blit(elapsed_surf,  (art_x, prog_y + 10))
        screen.blit(duration_surf, (art_x + wave_w - duration_surf.get_width(), prog_y + 10))

        # ────────────────────────────────────────────────────────────────────
        # JARVIS ORB  (bottom-center)
        # ────────────────────────────────────────────────────────────────────
        js = state.get("jarvis_state", "idle")
        orb.update(js, dt)
        orb_color = orb.draw(screen)

        # State label
        state_label = {
            "idle":       "STANDBY",
            "listening":  "LISTENING",
            "thinking":   "PROCESSING",
            "speaking":   "ONLINE",
            "whispering": "LOW POWER",
        }.get(js, js.upper())
        label_surf = f_small.render(state_label, True, orb_color)
        screen.blit(label_surf, (W // 2 - label_surf.get_width() // 2, H - 90))

        # ────────────────────────────────────────────────────────────────────
        # Corner filigree (HUD aesthetic corners)
        # ────────────────────────────────────────────────────────────────────
        _draw_corner(screen, 16, 8,         ACCENT_DIM, "tl")
        _draw_corner(screen, W - 8, 8,      ACCENT_DIM, "tr")
        _draw_corner(screen, 16, H - 8,     ACCENT_DIM, "bl")
        _draw_corner(screen, W - 8, H - 8,  ACCENT_DIM, "br")

        pygame.display.flip()
        clock.tick(30)   # 30 fps is plenty for a HUD


def _truncate(text, max_chars):
    return text if len(text) <= max_chars else text[:max_chars - 1] + "…"


def _draw_corner(surf, x, y, color, pos):
    L = 22
    T = 2
    if pos == "tl":
        pygame.draw.line(surf, color, (x, y), (x + L, y), T)
        pygame.draw.line(surf, color, (x, y), (x, y + L), T)
    elif pos == "tr":
        pygame.draw.line(surf, color, (x, y), (x - L, y), T)
        pygame.draw.line(surf, color, (x, y), (x, y + L), T)
    elif pos == "bl":
        pygame.draw.line(surf, color, (x, y), (x + L, y), T)
        pygame.draw.line(surf, color, (x, y), (x, y - L), T)
    elif pos == "br":
        pygame.draw.line(surf, color, (x, y), (x - L, y), T)
        pygame.draw.line(surf, color, (x, y), (x, y - L), T)


if __name__ == "__main__":
    main()
