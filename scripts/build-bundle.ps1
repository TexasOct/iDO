# Windows PowerShell 打包脚本
# 需要在 PowerShell 中运行

param(
    [switch]$SkipDownload = $false
)

# 设置错误时停止
$ErrorActionPreference = "Stop"

# 颜色输出函数
function Write-Info {
    param([string]$Message)
    Write-Host "ℹ " -ForegroundColor Blue -NoNewline
    Write-Host $Message
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ " -ForegroundColor Green -NoNewline
    Write-Host $Message
}

function Write-Warning-Custom {
    param([string]$Message)
    Write-Host "⚠ " -ForegroundColor Yellow -NoNewline
    Write-Host $Message
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "✗ " -ForegroundColor Red -NoNewline
    Write-Host $Message
    exit 1
}

# 获取项目根目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

Write-Info "项目根目录: $ProjectRoot"

# Python 配置
$PythonVersion = "3.14.0"
$PythonPlatform = "x86_64-pc-windows-msvc"
$PythonFile = "cpython-$PythonVersion+20251014-$PythonPlatform-install_only_stripped.tar.gz"
$PythonUrl = "https://github.com/astral-sh/python-build-standalone/releases/download/20251014/$PythonFile"
$PythonBin = "src-tauri\pyembed\python\python.exe"

# 步骤 1: 下载并解压 portable Python
Write-Info "步骤 1/4: 准备 portable Python 环境..."

if (-not (Test-Path "src-tauri\pyembed\python") -and -not $SkipDownload) {
    Write-Info "下载 Python: $PythonFile"

    New-Item -ItemType Directory -Force -Path "src-tauri\pyembed" | Out-Null
    Set-Location "src-tauri\pyembed"

    if (-not (Test-Path $PythonFile)) {
        Write-Info "正在下载..."
        Invoke-WebRequest -Uri $PythonUrl -OutFile $PythonFile
    }

    Write-Info "解压 Python..."
    # 在 Windows 上需要使用 tar 命令（Windows 10+ 内置）
    tar -xzf $PythonFile
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "解压失败"
    }

    # 清理压缩包
    Remove-Item $PythonFile -Force

    Set-Location $ProjectRoot
    Write-Success "Python 环境准备完成"
} else {
    Write-Success "Python 环境已存在，跳过下载"
}

# 验证 Python 可执行文件
if (-not (Test-Path $PythonBin)) {
    Write-Error-Custom "Python 可执行文件不存在: $PythonBin"
}

# 步骤 2: 安装项目依赖到嵌入式 Python 环境
Write-Info "步骤 2/4: 安装项目到嵌入式 Python 环境..."

$env:PYTAURI_STANDALONE = "1"

# 检查 uv 是否安装
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Error-Custom "未找到 uv 命令，请先安装: powershell -ExecutionPolicy ByPass -c `"irm https://astral.sh/uv/install.ps1 | iex`""
}

Write-Info "使用 uv 安装依赖..."
$PythonBinPath = Resolve-Path $PythonBin
uv pip install `
    --exact `
    --python="$PythonBinPath" `
    --reinstall-package=tauri-app `
    .\src-tauri

if ($LASTEXITCODE -ne 0) {
    Write-Error-Custom "安装依赖失败"
}

Write-Success "依赖安装完成"

# 步骤 3: 配置环境变量
Write-Info "步骤 3/4: 配置构建环境..."

$env:PYO3_PYTHON = (Resolve-Path $PythonBin).Path

Write-Info "PYO3_PYTHON: $env:PYO3_PYTHON"

Write-Success "环境配置完成"

# 步骤 4: 执行打包
Write-Info "步骤 4/4: 开始打包应用..."

pnpm tauri build `
    --config="src-tauri/tauri.bundle.json" `
    -- --profile bundle-release

if ($LASTEXITCODE -ne 0) {
    Write-Error-Custom "打包失败"
}

Write-Success "打包完成！"

# 显示打包结果位置
Write-Info "打包结果位置："
Write-Host "  - src-tauri\target\bundle-release\bundle\msi\"
Write-Host "  - src-tauri\target\bundle-release\bundle\nsis\"

Write-Success "✨ 所有步骤完成！"
