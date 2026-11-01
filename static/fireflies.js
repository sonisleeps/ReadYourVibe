// Pixel fireflies: small glowing squares that drift slowly and pulse.
const canvas = document.getElementById("fireflies");
const ctx = canvas.getContext("2d");
let W, H, flies = [];

function resize() { W = canvas.width = innerWidth; H = canvas.height = innerHeight; }
addEventListener("resize", resize); resize();

for (let i = 0; i < 45; i++) {
  flies.push({
    x: Math.random() * W, y: Math.random() * H,
    size: Math.random() < 0.3 ? 5 : 3,            // pixel size
    speed: 0.15 + Math.random() * 0.3,
    phase: Math.random() * 6.28,                  // so they don't blink together
    color: Math.random() < 0.7 ? "255,226,122" : "190,255,130",
  });
}

function draw(t) {
  ctx.clearRect(0, 0, W, H);
  for (const f of flies) {
    f.x += Math.sin(t / 2500 + f.phase) * f.speed;       // slow wandering
    f.y -= f.speed * 0.35;                               // float upward
    if (f.y < -10) { f.y = H + 10; f.x = Math.random() * W; }
    const glow = 0.25 + 0.75 * Math.abs(Math.sin(t / 1400 + f.phase)); // pulse
    ctx.shadowColor = `rgba(${f.color},${glow})`;
    ctx.shadowBlur = 14;
    ctx.fillStyle = `rgba(${f.color},${glow})`;
    ctx.fillRect(Math.round(f.x), Math.round(f.y), f.size, f.size); // square = pixel
  }
  requestAnimationFrame(draw);
}
// respect people who turn animations off in their system settings
if (matchMedia("(prefers-reduced-motion: reduce)").matches) draw(0); else requestAnimationFrame(draw);
