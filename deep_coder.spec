# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for deep-coder CLI."""

import glob
import os

block_cipher = None

prompt_files = []
for txt in glob.glob(os.path.join("deep_coder", "prompts", "*.txt")):
    prompt_files.append((txt, os.path.join("deep_coder", "prompts")))

a = Analysis(
    ["deep_coder/cli.py"],
    pathex=[],
    binaries=[],
    datas=prompt_files,
    hiddenimports=[
        "deep_coder.agent.orchestrator",
        "deep_coder.agent.worker",
        "deep_coder.agent.task",
        "deep_coder.tools.base",
        "deep_coder.tools.file_ops",
        "deep_coder.tools.git",
        "deep_coder.tools.shell",
        "deep_coder.tools.search",
        "deep_coder.tools.web",
        "deep_coder.skills.base",
        "deep_coder.skills.review",
        "deep_coder.skills.commit",
        "deep_coder.skills.fix",
        "deep_coder.skills.think",
        "deep_coder.skills.explain",
        "deep_coder.skills.pr",
        "deep_coder.skills.test_skill",
        "deep_coder.skills.memory",
        "deep_coder.memory",
        "deep_coder.context",
        "deep_coder.client",
        "deep_coder.config",
        "deep_coder.display",
        "deep_coder.models",
        "deep_coder.prompts.system",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="deep-coder",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
