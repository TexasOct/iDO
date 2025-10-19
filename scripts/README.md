# 脚本说明

## 打包脚本

### macOS / Linux

运行打包脚本：

```bash
# 方式 1: 使用 pnpm 脚本
pnpm run bundle

# 方式 2: 直接运行脚本
bash scripts/build-bundle.sh
```

### Windows

运行打包脚本：

```powershell
# 方式 1: 使用 pnpm 脚本
pnpm run bundle:win

# 方式 2: 直接运行脚本
powershell -ExecutionPolicy Bypass -File scripts/build-bundle.ps1
```

如果已经下载过 Python，可以跳过下载步骤：

```powershell
.\scripts\build-bundle.ps1 -SkipDownload
```

## 打包流程说明

根据 [PyTauri 官方文档](https://pytauri.github.io/pytauri/latest/usage/tutorial/build-standalone/)，打包脚本会自动执行以下步骤：

### 1. 准备 Portable Python 环境

脚本会自动下载适合当前系统的 Python Build Standalone 版本：

- **macOS (ARM64)**: `cpython-*-aarch64-apple-darwin-install_only_stripped.tar.gz`
- **macOS (x86_64)**: `cpython-*-x86_64-apple-darwin-install_only_stripped.tar.gz`
- **Linux**: `cpython-*-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz`
- **Windows**: `cpython-*-x86_64-pc-windows-msvc-install_only_stripped.tar.gz`

Python 会被解压到 `src-tauri/pyembed/python/` 目录。

### 2. 安装项目依赖

使用 `uv` 工具将项目及其依赖安装到嵌入式 Python 环境中：

```bash
uv pip install --exact --python="./src-tauri/pyembed/python/bin/python3" --reinstall-package=tauri-app ./src-tauri
```

### 3. 配置构建环境

设置必要的环境变量：

- `PYO3_PYTHON`: 指向嵌入式 Python 解释器
- `RUSTFLAGS`: 配置链接器参数和 rpath
- `PYTAURI_STANDALONE`: 标记为独立打包模式

**macOS 特别注意**: 脚本会自动修复 `libpython*.dylib` 的 `install_name`，将其设置为 `@rpath/libpython*.dylib`。

### 4. 执行打包

使用 Tauri CLI 进行打包：

```bash
pnpm tauri build --config="src-tauri/tauri.bundle.json" -- --profile bundle-release
```

## 打包输出

打包完成后，产物会在以下位置：

- **macOS**: `src-tauri/target/bundle-release/bundle/macos/`
- **Linux**: `src-tauri/target/bundle-release/bundle/appimage/` 和 `deb/`
- **Windows**: `src-tauri\target\bundle-release\bundle\msi\` 和 `nsis\`

## 前置要求

在运行打包脚本之前，请确保已安装：

1. **Node.js** 和 **pnpm**

   ```bash
   npm install -g pnpm
   ```

2. **Rust** 工具链

   ```bash
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   ```

3. **uv** (Python 包管理器)

   ```bash
   # macOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Windows
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

4. **Tauri CLI** (已在 package.json 中配置)

5. **macOS 额外要求**: Xcode Command Line Tools
   ```bash
   xcode-select --install
   ```

## 开发模式

打包脚本不会影响开发模式。开发时仍然使用标准命令：

```bash
# 开发模式
pnpm run tauri dev

# 构建前端
pnpm run build
```

## 常见问题

### Q: macOS 双击 .app 文件没有反应？

A: 这是因为未签名的应用在某些情况下双击启动会失败。解决方案：

**方式 1（推荐）**: 使用命令行启动

```bash
open src-tauri/target/bundle-release/bundle/macos/Rewind.app
```

**方式 2**: 清除隔离属性

```bash
xattr -cr src-tauri/target/bundle-release/bundle/macos/Rewind.app
```

**方式 3**: 安装 DMG 文件

```bash
# 双击打开 DMG 文件，将应用拖到 Applications 文件夹
open src-tauri/target/bundle-release/bundle/dmg/Rewind_0.1.0_aarch64.dmg
```

**方式 4**: 直接运行二进制文件

```bash
./src-tauri/target/bundle-release/bundle/macos/Rewind.app/Contents/MacOS/tauri-app
```

打包脚本已经自动执行了清理扩展属性的操作，但在某些情况下可能仍需要手动处理。

### Q: 为什么不能直接使用 `tauri build`？

A: PyTauri 应用需要打包 portable Python 环境，并配置特殊的链接器参数。直接使用 `tauri build` 会找不到 Python 运行时。

### Q: 打包后的应用很大？

A: 是的，因为打包了完整的 Python 运行时和依赖。你可以：

- 使用 `install_only_stripped` 版本的 Python（脚本已使用）
- 在 `pyproject.toml` 中精简依赖
- 考虑使用 Cython 编译 Python 代码

### Q: 可以跨平台打包吗？

A: 不可以。必须在目标平台上进行打包：

- 在 macOS 上打包 macOS 应用
- 在 Windows 上打包 Windows 应用
- 在 Linux 上打包 Linux 应用

### Q: 打包失败怎么办？

A: 检查以下几点：

1. 确保所有前置工具已正确安装
2. 查看错误日志，特别注意 Python 相关错误
3. 确认 `src-tauri/pyproject.toml` 配置正确
4. 尝试清理后重新打包：`rm -rf src-tauri/pyembed && rm -rf src-tauri/target`

## 其他脚本

### check-i18n-keys.ts

验证国际化翻译文件的 key 是否一致：

```bash
pnpm run check-i18n
```

## 参考文档

- [PyTauri - Build Standalone Binary](https://pytauri.github.io/pytauri/latest/usage/tutorial/build-standalone/)
- [Python Build Standalone](https://github.com/indygreg/python-build-standalone)
- [Tauri Bundle Configuration](https://tauri.app/reference/config/#bundle)
