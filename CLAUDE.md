# ERM Klinik

Baca dan ikuti `AGENTS.md` di root project ini — termasuk basecode-pipeline
(6 layer: graphify graph → ponytail design → rtk shell → output terse →
final reasoning → ecc review), yang WAJIB dijalankan di setiap sesi/task.

Catatan khusus Claude Code:
- Hook `rtk` global sudah aktif (shell output ter-trim otomatis).
- Untuk perubahan non-trivial, dispatch review ke `ecc:code-reviewer` dan
  `ecc:security-reviewer` (auth/input/secrets) sebelum menyatakan selesai.
- Project tidak menyimpan salinan skill — pakai skill global `basecode-pipeline` di `~/.claude/skills/` (Claude Code) dan `~/.gemini/skills/` (agy, symlink). Instruksi lengkap pipeline ada di `AGENTS.md` — berlaku juga di mesin lain tanpa skill global.
- Graph: `graphify-out/` — update dengan `graphify update .` setelah batch edit.
