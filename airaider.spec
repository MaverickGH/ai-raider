# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

project_root = Path(SPECPATH)
airaider_root = project_root / 'airaider'

tui_name = 'airaider-tui.exe' if sys.platform == 'win32' else 'airaider-tui'
tui_binary = project_root / 'build' / 'sidecar' / tui_name
if not tui_binary.is_file():
    raise FileNotFoundError(
        f'Missing Go TUI sidecar at {tui_binary}; run `make tui-build` first'
    )
binaries = [(str(tui_binary), 'airaider/bin')]

datas = []

for md_file in airaider_root.rglob('skills/**/*.md'):
    rel_path = md_file.relative_to(project_root)
    datas.append((str(md_file), str(rel_path.parent)))

for jinja_file in airaider_root.rglob('agents/**/*.jinja'):
    rel_path = jinja_file.relative_to(project_root)
    datas.append((str(jinja_file), str(rel_path.parent)))

for xml_file in airaider_root.rglob('*.xml'):
    rel_path = xml_file.relative_to(project_root)
    datas.append((str(xml_file), str(rel_path.parent)))

# Prebuilt local-viewer SPA (served by `airaider view`).
viewer_static = airaider_root / 'interface' / 'viewer' / 'static'
for asset in viewer_static.rglob('*'):
    if asset.is_file():
        rel_path = asset.relative_to(project_root)
        datas.append((str(asset), str(rel_path.parent)))

datas += collect_data_files('tiktoken')
datas += collect_data_files('tiktoken_ext')

datas += collect_data_files('litellm')

datas += collect_data_files('agents', includes=['**/*.md', '**/*.jinja', '**/*.json'])

hiddenimports = [
    # Core dependencies
    'litellm',
    'litellm.llms',
    'litellm.llms.openai',
    'litellm.llms.anthropic',
    'litellm.llms.vertex_ai',
    'litellm.llms.bedrock',
    'litellm.utils',
    'litellm.caching',

    # Rich console
    'rich',
    'rich.console',
    'rich.panel',
    'rich.text',
    'rich.markup',
    'rich.style',
    'rich.align',
    'rich.live',

    # Pydantic
    'pydantic',
    'pydantic.fields',
    'pydantic_core',
    'email_validator',

    # Docker
    'docker',
    'docker.api',
    'docker.models',
    'docker.errors',

    # HTTP/Networking
    'httpx',
    'httpcore',
    'requests',
    'urllib3',
    'certifi',

    # Jinja2 templating
    'jinja2',
    'jinja2.ext',
    'markupsafe',

    # XML parsing
    'xmltodict',
    'defusedxml',
    'defusedxml.ElementTree',

    # Syntax highlighting
    'pygments',
    'pygments.lexers',
    'pygments.styles',
    'pygments.util',

    # Tiktoken (for token counting)
    'tiktoken',
    'tiktoken_ext',
    'tiktoken_ext.openai_public',

    # Tenacity retry
    'tenacity',

    # CVSS scoring
    'cvss',

    # AiRaider modules
    'airaider',
    'airaider.interface',
    'airaider.interface.main',
    'airaider.interface.cli',
    'airaider.interface.tui',
    'airaider.interface.tui.runtime',
    'airaider.interface.tui.history',
    'airaider.interface.tui.live_view',
    'airaider.interface.tui.backend',
    'airaider.interface.tui.backend.controller',
    'airaider.interface.tui.backend.messages',
    'airaider.interface.tui.backend.protocol',
    'airaider.interface.tui.backend.server',
    'airaider.interface.utils',
    'airaider.agents',
    'airaider.agents.factory',
    'airaider.agents.prompt',
    'airaider.config.loader',
    'airaider.config.settings',
    'airaider.config.codex',
    'airaider.core',
    'airaider.core.agents',
    'airaider.core.execution',
    'airaider.core.inputs',
    'airaider.core.paths',
    'airaider.core.runner',
    'airaider.core.sessions',
    'airaider.report',
    'airaider.report.dedupe',
    'airaider.report.state',
    'airaider.report.writer',
    'airaider.interface.viewer',
    'airaider.interface.viewer.auth',
    'airaider.interface.viewer.cli',
    'airaider.interface.viewer.report_pdf',
    'airaider.interface.viewer.server',
    'airaider.interface.viewer.transcript',

    # PDF report generation + encryption
    'reportlab',
    'reportlab.pdfgen',
    'reportlab.pdfbase',
    'reportlab.lib',
    'reportlab.platypus',
    'pypdf',
    'cryptography',
    'airaider.runtime',
    'airaider.runtime.backends',
    'airaider.runtime.caido_bootstrap',
    'airaider.runtime.docker_client',
    'airaider.runtime.session_manager',
    'airaider.telemetry',
    'airaider.telemetry.logging',
    'airaider.telemetry.posthog',
    'airaider.tools',
    'airaider.tools.agents_graph.tools',
    'airaider.tools.finish.tool',
    'airaider.tools.notes.tools',
    'airaider.tools.proxy._calls',
    'airaider.tools.proxy.tools',
    'airaider.tools.python.tool',
    'airaider.tools.reporting.tool',
    'airaider.tools.thinking.tool',
    'airaider.tools.todo.tools',
    'airaider.tools.web_search.tool',
    'airaider.skills',
]

hiddenimports += collect_submodules('litellm')
hiddenimports += collect_submodules('rich')
hiddenimports += collect_submodules('pydantic')
hiddenimports += collect_submodules('pygments')
# reportlab loads renderers/fonts dynamically, so pull its whole tree in.
hiddenimports += collect_submodules('reportlab')

# reportlab ships bundled fonts (.pfb/.afm) it needs at runtime.
datas += collect_data_files('reportlab')

# reportlab imports PIL (pillow) lazily for image handling, so it must be
# bundled explicitly and kept out of the excludes list below.
hiddenimports += collect_submodules('PIL')
datas += collect_data_files('PIL')

excludes = [
    # Sandbox-only packages
    'playwright',
    'playwright.sync_api',
    'playwright.async_api',
    'IPython',
    'ipython',
    'libtmux',
    'pyte',
    'openhands_aci',
    'openhands-aci',
    'numpydoc',

    # Google Cloud / Vertex AI
    'google.cloud',
    'google.cloud.aiplatform',
    'google.api_core',
    'google.auth',
    'google.oauth2',
    'google.protobuf',
    'grpc',
    'grpcio',
    'grpcio_status',

    # Test frameworks
    'pytest',
    'pytest_asyncio',
    'pytest_cov',
    'pytest_mock',

    # Development tools
    'mypy',
    'ruff',
    'black',
    'isort',
    'pylint',
    'pyright',
    'bandit',
    'pre_commit',

    # Unnecessary for runtime
    'tkinter',
    'matplotlib',
    'numpy',
    'pandas',
    'scipy',
    'cv2',
]

a = Analysis(
    ['airaider/interface/main.py'],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='airaider',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
