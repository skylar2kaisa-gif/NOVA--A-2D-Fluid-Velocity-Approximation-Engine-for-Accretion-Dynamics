#!/usr/bin/env python3
"""
Nova-Ω  —  Event Horizon Vortex Simulation
Blackhole center ported directly from universe_engine.py.
Flicker-free cell-buffer renderer. Press Ctrl+C to exit.
"""

import math, time, os, sys

# ── ANSI helpers ──────────────────────────────────────────────────────────────
HIDE = "\033[?25l"
SHOW = "\033[?25h"
HOME = "\033[H"
END  = "\033[0m"

def at(row, col): return f"\033[{row};{col}H"
def fg(r, g, b):  return f"\033[38;2;{r};{g};{b}m"
def BOLD():       return "\033[1m"

# Fixed palette
C_GOLD  = fg(255, 200,  60)
C_AMBER = fg(255, 140,   0)
C_PURP  = fg(180,  80, 255)
C_CYAN  = fg( 80, 220, 255)
C_WHITE = fg(255, 255, 255)
C_DIM   = fg( 75,  75,  75)
C_RED   = fg(255,  60,  60)
C_GREEN = fg( 80, 255, 140)
C_PINK  = fg(255, 120, 200)

# ── Nova-Ω physics constants ──────────────────────────────────────────────────
PI     = math.pi
SPIN   = 0.57735       # rad/s  (= 1/√3)
CHARGE = -0.000001     # eV
G_PULL = PI            # gravitational pull echoes π

def fib_seq(n):
    a, b, s = 0, 1, []
    for _ in range(n):
        s.append(a); a, b = b, a + b
    return s

FIB = fib_seq(20)

# ── Blackhole zone radii — copied from universe_engine.py ─────────────────────
BH_ASPECT   = 2.15    # terminal char aspect ratio (matches game)
R_SING      = 6.5     # singularity
R_HOR       = 12.5    # event horizon edge
R_INNER     = 19.0    # inner accretion disk edge
R_OUTER     = 25.0    # outer accretion disk edge
R_GRAV      = 38.0    # gravitational field edge

# Bodies orbit just beyond the grav field and spiral inward
SIM_SCALE   = 1.05    # simulation distance units → terminal columns
TRAIL_LEN   = 28

# ── Celestial bodies ──────────────────────────────────────────────────────────
BODIES_INIT = [
    {"name": "Lumis",   "mass": 1.0, "dist": 44.0, "angle": 0.00, "color": C_CYAN,  "glyph": "★"},
    {"name": "Aethon",  "mass": 0.7, "dist": 36.0, "angle": 1.05, "color": C_GOLD,  "glyph": "✦"},
    {"name": "Veridax", "mass": 1.3, "dist": 50.0, "angle": 2.09, "color": C_GREEN, "glyph": "◆"},
    {"name": "Solenne", "mass": 0.5, "dist": 56.0, "angle": 3.14, "color": C_PINK,  "glyph": "●"},
    {"name": "Kiraen",  "mass": 0.9, "dist": 40.0, "angle": 4.19, "color": C_PURP,  "glyph": "▲"},
]

# ── Cell buffer ───────────────────────────────────────────────────────────────
class Screen:
    def __init__(self, rows, cols):
        self.rows  = rows
        self.cols  = cols
        self.cells = {}   # (r, c) -> (color_str, char)

    def put(self, row, col, color, char):
        if 1 <= row <= self.rows and 1 <= col <= self.cols:
            self.cells[(row, col)] = (color, char)

    def put_str(self, row, col, color, text):
        for i, ch in enumerate(text):
            self.put(row, col + i, color, ch)

    def render(self):
        # Use explicit row positioning instead of \n — no newlines means
        # no terminal scrolling, which is the main cause of flicker.
        # Wrap entire frame in synchronized-output markers (DEC 2026) so
        # terminals that support it hold the repaint until the frame is complete.
        SYNC_START = "\033[?2026h"
        SYNC_END   = "\033[?2026l"
        out   = [SYNC_START]
        cells = self.cells
        for r in range(1, self.rows + 1):
            out.append(f"\033[{r};1H")      # jump to start of row, no \n
            cur_color = ""
            for c in range(1, self.cols + 1):
                cell = cells.get((r, c))
                if cell:
                    color, ch = cell
                    if color != cur_color:
                        out.append(END + color)
                        cur_color = color
                    out.append(ch)
                else:
                    if cur_color:
                        out.append(END)
                        cur_color = ""
                    out.append(" ")
            if cur_color:
                out.append(END)
        out.append(SYNC_END)
        return "".join(out)

# ── Blackhole field renderer — ported from universe_engine._draw_blackhole_world
def draw_blackhole(scr, CX, CY, t, ROWS, COLS):
    """
    Renders the full blackhole field into the Screen cell buffer.
    Logic and colour maths copied directly from universe_engine.py.
    `t` replaces `us.blink_phase` for animated twinkling.

    Differential rotation driven by Nova-Ω's own SPIN constant:
      event horizon  →  SPIN × 3.5  (fastest — tightest orbit)
      inner disk     →  SPIN × 2.2
      outer disk     →  SPIN × 1.1
      grav field     →  SPIN × 0.45 (slowest — widest spiral arms)
    Keplerian physics: ω ∝ r^(-3/2), inner rings always faster.
    """
    row_min = max(1,        CY - int(R_GRAV / BH_ASPECT) - 2)
    row_max = min(ROWS - 1, CY + int(R_GRAV / BH_ASPECT) + 3)
    col_min = max(1,        CX - int(R_GRAV) - 3)
    col_max = min(COLS,     CX + int(R_GRAV) + 3)

    # Pre-compute per-zone rotation offsets at this frame's time
    ROT_HOR   = t * SPIN * 3.5
    ROT_INNER = t * SPIN * 2.2
    ROT_OUTER = t * SPIN * 1.1
    ROT_GRAV  = t * SPIN * 0.45

    for row in range(row_min, row_max):
        for col in range(col_min, col_max):
            dx        = col - CX
            dy        = (row - CY) * BH_ASPECT
            dist      = math.sqrt(dx * dx + dy * dy)
            raw_angle = math.atan2(dy, dx)

            # Choose rotation for this zone
            if   dist < R_SING:  angle = raw_angle
            elif dist < R_HOR:   angle = raw_angle - ROT_HOR
            elif dist < R_INNER: angle = raw_angle - ROT_INNER
            elif dist < R_OUTER: angle = raw_angle - ROT_OUTER
            elif dist < R_GRAV:  angle = raw_angle - ROT_GRAV
            else:                angle = raw_angle

            if dist < R_SING:
                # Singularity — near-black void with rare dim sparkle
                n = math.sin(dx * 1.7 + dy * 2.3) * math.cos(dx * 0.9 - dy * 1.4)
                if n > 0.90:
                    scr.put(row, col, fg(16, 8, 30), "·")
                # Nova-Ω marker at the exact centre
                if dx == 0 and dy == 0:
                    scr.put(row, col, BOLD() + fg(220, 80, 255), "Ω")

            elif dist < R_HOR:
                # Event horizon — dark rippling shell
                frac  = (dist - R_SING) / (R_HOR - R_SING)
                n     = math.sin(angle * 4 + dist * 0.7) * 0.5 + 0.5
                n2    = math.cos(angle * 6 - dist * 0.4) * 0.5 + 0.5
                r_c   = int(10  + frac * 25  + n * 10)
                g_c   = int(4   + frac * 6)
                b_c   = int(20  + frac * 50  + n * 20)
                chars = ['·', '∙', '·', ' ', '∙', '·']
                ch    = chars[int(n2 * 4 + frac * 2) % len(chars)]
                scr.put(row, col, fg(r_c, g_c, b_c), ch)

            elif dist < R_INNER:
                # Inner accretion disk — hot plasma (white-blue core → amber edge)
                frac   = (dist - R_HOR) / (R_INNER - R_HOR)
                disk_b = 0.55 + 0.45 * abs(math.sin(angle))
                n      = math.sin(angle * 7 + dist * 0.6) * 0.25
                n2     = math.cos(angle * 3 - dist * 0.3) * 0.2
                hot    = max(0.35, min(1.0, (1.0 - frac * 0.55 + n) * disk_b))
                r_c    = min(255, int(220 + 35 * hot))
                g_c    = min(255, int(165 * hot + 55 + n2 * 20))
                b_c    = min(255, int(235 * (1.0 - frac * 0.72) * hot))
                chars  = ['█', '▓', '▒', '◆', '▓', '█', '▒']
                ch     = chars[int((n2 + 0.5) * 3 + frac * 4) % len(chars)]
                scr.put(row, col, BOLD() + fg(r_c, g_c, b_c), ch)

            elif dist < R_OUTER:
                # Outer accretion disk — amber / orange fade
                frac   = (dist - R_INNER) / (R_OUTER - R_INNER)
                disk_b = 0.45 + 0.55 * abs(math.cos(angle + 0.3))
                n      = math.sin(angle * 5 + dist * 0.5) * 0.35 + 0.5
                fade   = (1.0 - frac) * disk_b
                r_c    = min(255, int(230 * fade + 30))
                g_c    = min(255, int(130 * fade * n + 18))
                b_c    = min(255, int(35  * fade))
                chars  = ['▒', '░', '·', '◆', '▒', '░', '·']
                ch     = chars[int(n * 4 + frac * 3) % len(chars)]
                scr.put(row, col, fg(r_c, g_c, b_c), ch)

            elif dist < R_GRAV:
                # Gravitational field — purple spiral arms
                frac    = (dist - R_OUTER) / (R_GRAV - R_OUTER)
                spiral  = math.sin(angle * 2 + dist * 0.32)
                n       = math.cos(dx * 0.14 + dy * 0.19) * 0.5 + 0.5
                density = (1.0 - frac) * 0.85
                if spiral > 0.38 - density * 0.6 or n > 0.78 - frac * 0.35:
                    r_c  = int((55 + n * 45) * (1.0 - frac * 0.82))
                    g_c  = int((18 + n * 18) * (1.0 - frac * 0.90))
                    b_c  = int((95 + n * 85) * (1.0 - frac * 0.68))
                    chars = ['·', '∙', '·', '∷', '·', '∙']
                    ch    = chars[int(n * 4 + spiral * 2) % len(chars)]
                    scr.put(row, col, fg(r_c, g_c, b_c), ch)

            else:
                # Deep space — twinkling star field (same technique as universe_engine)
                n = (math.sin(col * 0.383 + row * 0.717) *
                     math.cos(col * 0.197 - row * 0.313))
                if n > 0.87:
                    sb      = (n - 0.87) / 0.13
                    phase   = math.sin(col * 1.7 + row * 2.3) * PI
                    freq    = 0.8 + 1.4 * abs(math.sin(col * 0.53 + row * 0.31))
                    twink   = 0.45 + 0.55 * ((math.sin(t * freq + phase) + 1) / 2)
                    shimmer = math.sin(t * freq * 0.7 + phase + 1.0) * 0.12
                    bv = int(max(0, min(255, (55 + sb * 130) * (twink + shimmer))))
                    rv = int(max(0, min(255, (55 + sb *  90) * twink)))
                    gv = int(max(0, min(255, (65 + sb * 110) * (twink - shimmer * 0.5))))
                    ch = '+' if (sb > 0.65 and twink > 0.88) else ('✦' if sb > 0.9 and twink > 0.92 else '·')
                    scr.put(row, col, fg(rv, gv, bv), ch)

# ── Body → screen coords ──────────────────────────────────────────────────────
def body_screen(b, CX, CY):
    r   = b["dist"] * SIM_SCALE
    col = CX + int(r * math.cos(b["angle"]))
    row = CY + int(r * math.sin(b["angle"]) / BH_ASPECT)
    return col, row

# ── Stats panel ───────────────────────────────────────────────────────────────
def draw_panel(scr, t, step, bodies, panel_col, CY):
    fib_L      = FIB[step % len(FIB)]
    nova_theta = (SPIN * t) % (2 * PI)

    rows = [
        (BOLD() + C_GOLD, "╔══════════════════════════╗"),
        (BOLD() + C_GOLD, "║    N O V A - Ω  NODE    ║"),
        (BOLD() + C_GOLD, "╚══════════════════════════╝"),
        (C_DIM,  ""),
        (C_CYAN,  f"  Spin    {SPIN:.5f} rad/s"),
        (C_CYAN,  f"  θ now   {nova_theta:.4f} rad"),
        (C_AMBER, f"  G·pull  π = {PI:.6f}"),
        (C_RED,   f"  Charge  {CHARGE:.2e} eV"),
        (C_PURP,  f"  Fib L   {fib_L}"),
        (C_DIM,   ""),
        (BOLD() + C_WHITE, "  ── Bodies ─────────────────"),
    ]
    for b in bodies:
        gf = G_PULL * b["mass"] / max(b["dist"], 0.01) ** 2
        rows.append((b["color"], f"  {b['glyph']} {b['name']:<8} r={b['dist']:.1f}"))
        rows.append((C_DIM,     f"    F={gf:.6f}  θ={b['angle']%(2*PI):.2f}"))

    rows += [
        (C_DIM, ""),
        (C_DIM, "  ── Charge ripple ──────────"),
    ]
    for i in range(1, 6):
        eff = CHARGE * (PI ** i)
        bar = "▓" * min(int(abs(eff) * 5e6), 14)
        rows.append((C_PURP, f"  π^{i} {eff:.2e}  {bar}"))

    rows += [
        (C_DIM,  ""),
        (C_GOLD, "  ── Lotus spin trace ───────"),
    ]
    trace = ""
    for i in range(22):
        th   = SPIN * (t - i * 0.08)
        ring = "·○◌◎●◉"[int(abs(math.sin(th)) * 5)]
        trace += ring
    rows.append((C_PURP, "  " + trace))

    start_row = CY - len(rows) // 2
    for i, (color, text) in enumerate(rows):
        scr.put_str(start_row + i, panel_col, color, text)

# ── Main loop ─────────────────────────────────────────────────────────────────
def main():
    global SPIN
    sys.stdout.write(HIDE + "\033[2J")
    sys.stdout.flush()

    dt     = 0.05
    t      = 0.0
    step   = 0
    bodies = [dict(b) for b in BODIES_INIT]
    trails = {b["name"]: [] for b in bodies}

    try:
        while True:
            try:
                sz   = os.get_terminal_size()
                COLS = sz.columns
                ROWS = sz.lines
            except Exception:
                COLS, ROWS = 140, 40

            # Nova-Ω sits at centre-left to leave room for the panel on the right
            CX        = max(42, COLS // 2 - 20)
            CY        = max(14, ROWS // 2)
            PANEL_COL = CX + int(R_GRAV) + 5

            scr = Screen(ROWS, COLS)

            # ── Blackhole field (from universe_engine.py) ─────────────────────
            draw_blackhole(scr, CX, CY, t, ROWS, COLS)

            # ── Nova-Ω title above the blackhole ─────────────────────────────
            title     = "✦  N O V A - Ω  ✦"
            title_col = CX - len(title) // 2
            title_row = CY - int(R_GRAV / BH_ASPECT) - 2
            scr.put_str(title_row,     title_col, BOLD() + fg(220, 80, 255), title)
            scr.put_str(title_row + 1, title_col, fg(100, 40, 140),
                        "─" * len(title))

            # ── Stats panel ───────────────────────────────────────────────────
            if PANEL_COL + 32 < COLS:
                draw_panel(scr, t, step, bodies, PANEL_COL, CY)

            # ── Orbital trails (after panel so trails don't overwrite it) ─────
            for b in bodies:
                for idx, (tc, tr) in enumerate(trails[b["name"]]):
                    fade = int(40 + 80 * (idx / TRAIL_LEN))
                    scr.put(tr, tc, fg(fade, fade, fade), "·")

            # ── Bodies — drawn LAST so they are always on top of everything ───
            for b in bodies:
                bc, br = body_screen(b, CX, CY)
                scr.put(br, bc, BOLD() + b["color"], b["glyph"])
                scr.put_str(br - 1, bc - 3, C_DIM, b["name"][:4])

            # ── Status bar ────────────────────────────────────────────────────
            status = (f"  t={t:.2f}s  step={step}"
                      f"  spin={SPIN}rad/s  G=π={PI:.4f}"
                      f"  charge={CHARGE}eV  │  Ctrl+C to exit")
            scr.put_str(ROWS, 1, C_DIM, status[:COLS - 2])

            # ── Atomic flush — no clear, no flicker ───────────────────────────
            sys.stdout.write(scr.render())
            sys.stdout.flush()

            # ── Reality-Focused Relativistic Physics ──────────────────────────
            for b in bodies:
                bc, br = body_screen(b, CX, CY)
                trail  = trails[b["name"]]
                trail.append((bc, br))
                if len(trail) > TRAIL_LEN:
                    trail.pop(0)

                # 1. Initialize velocity tracking if not present
                if "v_r" not in b:
                    # Circular orbit velocity approximation: v_theta = sqrt(G/r)
                    b["v_r"] = 0.0
                    b["v_theta"] = math.sqrt(G_PULL / b["dist"])

                r = max(b["dist"], 1.6)
                
                # 2. Einsteinian Relativistic Force Model (Schwarzschild/Kerr Limit)
                # Adds the crucial -3*G*L^2 / r^4 term that creates the real ISCO plunge!
                angular_momentum = r * b["v_theta"]
                grav_accel = -(G_PULL / r**2) - (3.0 * G_PULL * (angular_momentum**2) / r**4)
                
                # 3. Dynamic Energy Dissipation (Gravitational Radiation Drag)
                # Simulates the planet shedding energy to the local space-time fabric
                drag_factor = 0.005 / (r**2)
                b["v_theta"] -= b["v_theta"] * drag_factor * dt
                
                # 4. Centrifugal vs Gravitational Balance
                centrifugal_accel = (b["v_theta"]**2) / r
                
                # 5. Integrate Accelerations into Velocities
                b["v_r"] += (grav_accel + centrifugal_accel) * dt
                
                # 6. Update Spatial Coordinates
                b["dist"] += b["v_r"] * dt
                
                # Frame-dragging (Spin) directly forces angular velocity shift
                frame_dragging = SPIN / (r**3) 
                b["angle"] += (b["v_theta"] / r + frame_dragging + CHARGE * 1e4) * dt

                # Real Absorption Transition: Total Swallow (No Magic Bounce)
                if b["dist"] < 2.0:
                    # Transfer planetary mass & angular momentum to the central node
                    
                    SPIN = min(0.99, SPIN + (b["mass"] * 0.02)) # Black hole spins faster!
                    
                    # Respawn far out to simulate a new captured interstellar object
                    b["dist"]  = 58.0
                    b["v_r"]   = 0.0
                    b["v_theta"] = math.sqrt(G_PULL / b["dist"]) * 0.95 # Slightly sub-circular
                    b["angle"] = (b["angle"] + PI) % (2 * PI)
                    trails[b["name"]].clear()

            t    += dt
            step += 1
            time.sleep(dt)

    except KeyboardInterrupt:
        sys.stdout.write(SHOW + at(ROWS, 1) + END + "\n")
        print("  Nova-Ω fades... the vortex stills.")

if __name__ == "__main__":
    main()
