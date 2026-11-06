# -*- mode: python ; coding: utf-8 -*-
# Đóng gói onedir: pyinstaller --noconfirm --clean UpScale.spec  ->  dist\UpScale\UpScale.exe
# Không đóng gói thư mục engine\. Người dùng chép engine\realesrgan cạnh UpScale.exe.
from PyInstaller.utils.hooks import collect_data_files

a = Analysis(
    ["run.py"],
    pathex=["src"],
    # CustomTkinter cần file theme .json và font đi kèm gói.
    datas=collect_data_files("customtkinter"),
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="UpScale",
    console=False,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, upx=False, name="UpScale")
