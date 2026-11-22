## Notes

Thanks to I J Peters, Greg Sharp and the LinCity contributors for [LinCity](https://lincity.sourceforge.net), the free city simulation.

This is the original X11 LinCity (1.12.1), not LinCity-NG. It runs on the Westonpack runtime and has no sound. Saved games are kept in `conf/.lincity`.

## Controls

| Button | Action |
|--|--|
| Left Stick | Move mouse |
| A | Left click |
| B | Right click (help on most things) |
| X | Slow mouse (hold) |
| Y | Help |
| D-Pad / Right Stick | Scroll the map |
| L1 | Pause |
| R1 | Stats |
| L2 | Save |
| R2 | Load |
| Start | Enter |
| Select | Quit |

## Compile

```bash
wget -O lincity_1.12.1.orig.tar.gz https://snapshot.debian.org/file/280375273f6e741d707dc8e11fdedb160d230c95
tar xzf lincity_1.12.1.orig.tar.gz
cd lincity-1.12.1
patch -p1 < /path/to/patches/lincity-1.12.1-portmaster.patch
LDFLAGS=-Wl,--as-needed ./configure --build=aarch64-unknown-linux-gnu --with-x
make xlincity
strip -o xlincity.aarch64 xlincity
mkdir data && cp -r colour.pal help icons messages opening data/
```

The patch fixes the build on current compilers, gives the game window an arrow pointer, and holds back a resize that arrives before the game screen exists. Without that, a full-screen window crashes the game at the opening screen.
