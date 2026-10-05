"""Test terrain generator for Fortress Break (stdlib only).

Outputs:
  Assets/Art/Maps/TestTerrain.png      - RGBA terrain texture, transparent sky
  Docs/Maps/TestTerrain_preview.png    - 2x preview with sky, chunk grid, spawn markers
Coordinates in this script use bottom-left origin (y up), like Unity.
"""
import math, os, random, struct, zlib

ROOT = r"D:\Fortress"
W, H = 1536, 448
CHUNK = 64
SEED = 20261006
rng = random.Random(SEED)

# ---------- noise ----------
def make_noise1d(n, seed):
    r = random.Random(seed)
    return [r.uniform(-1, 1) for _ in range(n)]

def sample1d(vals, x, period):
    t = x / period
    i = int(math.floor(t))
    f = t - i
    a = vals[i % len(vals)]
    b = vals[(i + 1) % len(vals)]
    f = f * f * (3 - 2 * f)
    return a + (b - a) * f

N1 = make_noise1d(512, SEED + 1)
N2 = make_noise1d(512, SEED + 2)
N3 = make_noise1d(512, SEED + 3)

def hash2(x, y, s=0):
    h = (x * 374761393 + y * 668265263 + s * 2246822519 + SEED) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return (h ^ (h >> 16)) / 0xFFFFFFFF

# ---------- ground height ----------
CTRL = [(0, 170), (60, 215), (180, 250), (300, 238), (420, 262), (520, 215),
        (640, 122), (768, 72), (890, 116), (1000, 205), (1110, 252), (1220, 240),
        (1330, 286), (1440, 250), (1535, 178)]

def base_height(x):
    for (x0, h0), (x1, h1) in zip(CTRL, CTRL[1:]):
        if x0 <= x <= x1:
            t = (x - x0) / (x1 - x0)
            t = (1 - math.cos(t * math.pi)) / 2
            return h0 + (h1 - h0) * t
    return CTRL[-1][1]

ground = []
for x in range(W):
    h = base_height(x)
    h += 9 * sample1d(N1, x, 48) + 4 * sample1d(N2, x, 17) + 1.5 * sample1d(N3, x, 6)
    ground.append(int(round(h)))

# ---------- floating islands (cx, cy, half width, depth) ----------
ISLANDS = [(622, 292, 58, 44), (906, 322, 52, 40), (768, 196, 46, 34)]

solid = [[False] * W for _ in range(H)]  # solid[y][x], y up
for x in range(W):
    for y in range(min(ground[x], H)):
        solid[y][x] = True

for k, (cx, cy, hw, depth) in enumerate(ISLANDS):
    for x in range(cx - hw, cx + hw + 1):
        t = (x - cx) / hw
        if abs(t) > 1:
            continue
        u = 1 - t * t
        top = cy + 4 + 6 * u + 1.5 * sample1d(N2, x + 97 * k, 9)
        bot = cy - depth * (u ** 0.7) + 5 * sample1d(N3, x + 53 * k, 11) * u
        for y in range(int(bot), int(round(top))):
            if 0 <= y < H:
                solid[y][x] = True

# ---------- palette ----------
GRASS_HI = (141, 210, 76)
GRASS = (98, 172, 62)
GRASS_DK = (62, 126, 56)
SOIL_HI = (198, 142, 88)
DIRT = (162, 106, 66)
DIRT_DK = (124, 78, 52)
DIRT_DEEP = (92, 58, 42)
STONE = (126, 114, 106)
STONE_HI = (162, 150, 140)
UNDER = (70, 44, 32)

# stones: small blobs placed in dirt
stones = []
for _ in range(260):
    stones.append((rng.randrange(W), rng.randrange(H), rng.choice([1, 1, 2, 2, 3])))
stone_px = {}
for sx, sy, r in stones:
    for dy in range(-r, r + 1):
        for dx in range(-r - 1, r + 2):
            if (dx / (r + 1)) ** 2 + (dy / max(r, 1)) ** 2 <= 1.0:
                hi = dy == r or (dy == r - 1 and dx < 0)
                stone_px[(sx + dx, sy + dy)] = STONE_HI if hi else STONE

# ---------- colorize ----------
pixels = [[(0, 0, 0, 0)] * W for _ in range(H)]
for x in range(W):
    d = None  # depth below nearest air above
    for y in range(H - 1, -1, -1):
        if not solid[y][x]:
            d = None
            continue
        d = 0 if d is None else d + 1
        below_air = y > 0 and not solid[y - 1][x]
        jitter = 1 if hash2(x, y, 1) > 0.6 else 0
        if d == 0:
            c = GRASS_HI
        elif d <= 2:
            c = GRASS
        elif d <= 3 + jitter:
            c = GRASS_DK
        elif d <= 5 + jitter:
            c = SOIL_HI
        else:
            band = d + int(6 * sample1d(N1, x + 3 * y, 23))
            if band < 70:
                c = DIRT
            elif band < 74 and hash2(x, y, 2) > 0.5:
                c = DIRT
            elif band < 170:
                c = DIRT_DK
            elif band < 176 and hash2(x, y, 3) > 0.5:
                c = DIRT_DK
            else:
                c = DIRT_DEEP
            if (x, y) in stone_px and d > 8:
                c = stone_px[(x, y)]
        if below_air and d > 2:
            c = UNDER
        pixels[y][x] = (c[0], c[1], c[2], 255)

# ---------- spawn points ----------
def surface_at(x):
    """Top of the ground (not islands): first air pixel above ground column."""
    return ground[x]

def flattest(x_from, x_to, half=10):
    best, best_x = 1e9, x_from
    for x in range(x_from, x_to):
        hs = [surface_at(i) for i in range(x - half, x + half + 1)]
        score = max(hs) - min(hs)
        if score < best:
            best, best_x = score, x
    return best_x, best

PLAYER_ZONES = [(110, 200), (320, 420)]
AI_ZONES = [(1060, 1140), (1180, 1260), (1300, 1380), (1410, 1480)]
player_spawns, ai_spawns = [], []
for a, b in PLAYER_ZONES:
    x, s = flattest(a, b)
    player_spawns.append((x, surface_at(x), s))
for a, b in AI_ZONES:
    x, s = flattest(a, b)
    ai_spawns.append((x, surface_at(x), s))

# ---------- png writer ----------
def write_png(path, w, h, rows_top_down):
    raw = bytearray()
    for row in rows_top_down:
        raw.append(0)
        for r, g, b, a in row:
            raw += bytes((r, g, b, a))
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)

tex_path = os.path.join(ROOT, "Assets", "Art", "Maps", "TestTerrain.png")
write_png(tex_path, W, H, [pixels[y] for y in range(H - 1, -1, -1)])

# ---------- preview (2x, sky, grid, markers) ----------
S = 2
SKY_TOP, SKY_BOT = (120, 182, 230), (206, 232, 245)
markers = {}
def mark(x, y, color):
    # small flag: 3px wide body, 12px tall (texture px), standing on surface
    for dy in range(0, 12):
        for dx in range(-1, 2):
            markers[(x + dx, y + dy)] = color
    for dy in range(8, 12):
        for dx in range(2, 7):
            markers[(x + dx, y + dy)] = color
for x, y, _ in player_spawns:
    mark(x, y, (40, 90, 220))
for x, y, _ in ai_spawns:
    mark(x, y, (220, 50, 50))

prev_rows = []
for py in range(H * S - 1, -1, -1):
    y = py // S
    t = y / (H - 1)
    sky = tuple(int(SKY_BOT[i] + (SKY_TOP[i] - SKY_BOT[i]) * t) for i in range(3))
    row = []
    for px in range(W * S):
        x = px // S
        if (x, y) in markers:
            c = markers[(x, y)]
        else:
            p = pixels[y][x]
            c = p[:3] if p[3] else sky
        if px % (CHUNK * S) == 0 or py % (CHUNK * S) == 0:
            c = tuple(int(v * 0.55 + 255 * 0.45) for v in c)
        row.append((c[0], c[1], c[2], 255))
    prev_rows.append(row)
prev_path = os.path.join(ROOT, "Docs", "Maps", "TestTerrain_preview.png")
write_png(prev_path, W * S, H * S, prev_rows)

# ---------- report ----------
sky_alpha_ok = all(pixels[H - 1][x][3] == 0 for x in range(W))
solid_count = sum(1 for y in range(H) for x in range(W) if solid[y][x])
print("texture", tex_path, W, H)
print("chunks", W // CHUNK, "x", H // CHUNK, "=", (W // CHUNK) * (H // CHUNK))
print("top row transparent:", sky_alpha_ok)
print("solid ratio: %.1f%%" % (100 * solid_count / (W * H)))
print("ground min/max:", min(ground), max(ground))
print("player spawns (x, y, flatness):", player_spawns)
print("ai spawns (x, y, flatness):", ai_spawns)
min_dist = min(abs(a[0] - p[0]) for a in ai_spawns for p in player_spawns)
print("min player-AI distance px:", min_dist, ">=480:", min_dist >= 480)
for k, (cx, cy, hw, depth) in enumerate(ISLANDS):
    gap = (cy - depth) - max(ground[cx - hw:cx + hw + 1])
    print("island", k, "center", (cx, cy), "gap above ground ~", gap)
