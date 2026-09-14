# Compatibility patches

- Built TyraCraft `v0.86.140` as a native PS2 ELF with PS2DEV and Tyra.
- Loaded ordinary IRX modules from the disc and skipped the load-module-buffer
  patch that Play!'s HLE BIOS cannot accept.
- Disabled the USB mass driver for the read-only disc build.
- Added a bounded hashed shadow for three ISO9660 directories affected by Play!'s
  current multi-sector HLE CDFS directory lookup limitation.
- Redirected TyraCraft settings and native `.tcw` worlds to `mc0:`. The browser
  wrapper synchronizes Play!'s memory-card directory to IndexedDB.

The result remains a PlayStation 2 executable inside a legitimate bootable ISO.
