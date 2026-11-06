"""Engine giả cho test: nhận cùng đối số như realesrgan-ncnn-vulkan, hành vi chọn bằng FAKE_MODE."""
import os
import sys
import time

from PIL import Image


def progress(pct: str) -> None:
    print(pct, file=sys.stderr, flush=True)


def main() -> int:
    args = sys.argv[1:]
    opts = {args[i]: args[i + 1] for i in range(0, len(args) - 1, 2)}
    src, dst, scale = opts["-i"], opts["-o"], int(opts["-s"])
    mode = os.environ.get("FAKE_MODE", "ok")

    if mode == "fail":
        print("some unexpected error", file=sys.stderr, flush=True)
        return 1
    if mode == "oom":
        print("vkAllocateMemory failed -2", file=sys.stderr, flush=True)
        return 3
    if mode == "hang":
        progress("0,00%")
        time.sleep(60)
        return 0

    progress("0,00%")
    progress("25,00%" if mode != "dot" else "25.00%")
    time.sleep(float(os.environ.get("FAKE_DELAY", "0")))
    with Image.open(src) as img:
        w, h = img.size
        if mode == "wrongsize":
            out = img.resize((w * scale + 1, h * scale))
        else:
            out = img.convert("RGB").resize((w * scale, h * scale))
    if mode == "nooutput":
        return 0
    out.save(dst)
    progress("100,00%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
