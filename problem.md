Berikut ringkasan lengkap untuk kamu kasih ke Claude Code:

---

**Masalah awal:**
Claude Code menyarankan install `nvidia-driver-595-open` di laptop MSI GF63 Thin 11SC (GPU: GTX 1650 Mobile/Max-Q + Intel iGPU, hybrid/Optimus). Setelah restart untuk aktifkan NVIDIA, sistem freeze total (mouse & keyboard tidak respons) saat masuk desktop Ubuntu 24.04.4.

**Konfirmasi awal:**
- Keyboard/mouse normal di Windows dan di TTY teks — jadi bukan masalah hardware
- Masalah spesifik terjadi saat transisi ke GUI (GDM login screen)

**Langkah yang sudah dicoba (semua GAGAL, freeze tetap terjadi di titik yang sama — pas mau masuk login screen):**

1. Purge total semua paket nvidia-595-open via recovery mode root shell
2. Reinstall `xserver-xorg`
3. Boot dengan `nomodeset`, `i8042.nopnp/reset/nomux/kbdreset`, `psmouse.proto=bare` — tidak ada pengaruh
4. Blacklist `nouveau` (karena nouveau gagal deteksi output GPU NVIDIA — error "No compatible format found", "Cannot find any crtc")
5. Install driver NVIDIA proprietary `nvidia-driver-580` (bukan versi -open)
6. `sudo prime-select intel` + install `nvidia-prime` — paksa full pakai Intel iGPU, NVIDIA di-bypass total
7. Ganti display manager GDM → LightDM → balik ke GDM lagi — sama-sama freeze
8. Reinstall `gnome-shell`, `gnome-session`, `gdm3`
9. Hapus cache GNOME Shell/Mutter (`~/.cache/gnome-shell`, `~/.cache/mutter`, `~/.config/monitors.xml`)
10. Disable `split_lock_detect` di kernel parameter (karena log kernel sempat nunjukin "x86/split lock detection: crashing the kernel")

**Temuan dari log (`journalctl`):**
- GNOME Shell/Mutter sebenarnya **berhasil start sampai "Registering session with GDM"** — tidak ada crash eksplisit di situ
- Error DRM sempat muncul: `[drm] Failed to open DRM device for pci:0000:01:00.0: -19` (device NVIDIA tidak bisa diakses driver manapun setelah di-blacklist)
- Tidak ada `systemctl --failed` units
- Filesystem/fstab normal, tidak ada masalah mount/disk

**Kondisi sekarang:** Masih freeze persis di GDM login screen meski NVIDIA sudah full di-bypass via prime-select intel. Kecurigaan mengarah ke konfigurasi Xorg/session yang corrupt dari sisa percobaan sebelumnya, atau interaksi driver Intel i915 dengan sisa konfigurasi NVIDIA yang belum bersih total.
