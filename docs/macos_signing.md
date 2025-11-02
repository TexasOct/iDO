# macOS 应用签名问题解决方案

## 问题描述

在 macOS 上构建 Tauri 应用后,双击 `.app` 文件无法启动,但直接运行可执行文件 `rewind-app` 可以正常启动。

### 根本原因

macOS 的 **Library Validation** 安全机制拒绝加载使用 adhoc 签名(无开发者证书)的动态库文件。主要表现为:

1. **amfid 守护进程拦截**: Apple Mobile File Integrity Daemon 检测到 adhoc 签名
2. **Python 依赖库被阻止**: 项目包含 271 个 `.dylib` 和 `.so` 文件未被正确签名
3. **应用立即退出**: 启动后因无法加载必需库而退出 (exit code 1)

### 错误日志示例

```
amfid: /path/to/libpython3.14.dylib not valid:
Error Domain=AppleMobileFileIntegrityError Code=-423
"The file is adhoc signed or signed by an unknown certificate chain"
```

## 解决方案

### 快速修复 (推荐)

项目已包含自动化签名脚本,每次构建后运行:

```bash
# 方式 1: 使用 npm 脚本 (推荐)
pnpm sign-macos

# 方式 2: 直接运行脚本
sh scripts/sign-macos.sh

# 方式 3: 构建并自动签名
pnpm tauri:build:signed
```

### 脚本功能

`scripts/sign-macos.sh` 自动执行以下操作:

1. ✅ 为所有动态库文件签名 (271 个 `.dylib` 和 `.so` 文件)
2. ✅ 使用 entitlements 为整个 `.app` 包签名
3. ✅ 移除隔离属性 (quarantine attribute)
4. ✅ 验证签名状态

### Entitlements 配置

位于 `src-tauri/entitlements.plist`,包含以下关键权限:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- 允许 JIT 编译 (Python 运行时需要) -->
    <key>com.apple.security.cs.allow-jit</key>
    <true/>

    <!-- 允许未签名的可执行内存 (Python C 扩展需要) -->
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>

    <!-- 禁用库验证 (允许加载 adhoc 签名的动态库) -->
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
</dict>
</plist>
```

## 使用流程

### 推荐方式: Bundle 构建 (自动签名)

```bash
# 一键完成构建和签名
pnpm bundle
```

`pnpm bundle` 命令已集成自动签名功能,会在构建完成后自动执行:
1. ✅ 签名所有动态库文件 (271 个)
2. ✅ 使用 entitlements 签名应用包
3. ✅ 清除隔离属性
4. ✅ 验证签名状态

### 开发环境构建 (手动签名)

```bash
# 1. 构建应用
pnpm tauri build

# 2. 签名修复
pnpm sign-macos

# 3. 启动应用
open src-tauri/target/bundle-release/bundle/macos/Rewind.app
```

或使用一键命令:

```bash
pnpm tauri:build:signed
```

### 验证签名

```bash
# 检查应用签名
codesign -dvvv src-tauri/target/bundle-release/bundle/macos/Rewind.app

# 检查 entitlements
codesign -d --entitlements :- src-tauri/target/bundle-release/bundle/macos/Rewind.app

# 检查 Gatekeeper 状态
spctl -a -vv src-tauri/target/bundle-release/bundle/macos/Rewind.app
```

## 手动签名步骤 (备用)

如果自动脚本失败,可以手动执行:

```bash
# 进入应用目录
cd src-tauri/target/bundle-release/bundle/macos/Rewind.app

# 1. 签名所有动态库
find Contents/Resources \( -name "*.dylib" -o -name "*.so" \) \
  -exec codesign --force --deep --sign - {} \;

# 2. 签名整个应用包 (使用 entitlements)
codesign --force --deep --sign - \
  --entitlements ../../../../entitlements.plist \
  /path/to/Rewind.app

# 3. 移除隔离属性
xattr -cr /path/to/Rewind.app
```

## 长期解决方案

### 方案 1: Apple Developer 证书 (生产环境必需)

如果需要分发应用给其他用户:

1. **注册 Apple Developer Program** ($99/年)
   - https://developer.apple.com/programs/

2. **获取证书**
   - Xcode → Preferences → Accounts → Manage Certificates
   - 创建 "Developer ID Application" 证书

3. **配置 Tauri**

在 `src-tauri/tauri.conf.json` 添加:

```json
{
  "bundle": {
    "macOS": {
      "signingIdentity": "Developer ID Application: Your Name (TEAMID)",
      "entitlements": "entitlements.plist",
      "providerShortName": "TEAMID"
    }
  }
}
```

4. **自动签名构建**

```bash
# Tauri 会自动使用证书签名
pnpm tauri build
```

### 方案 2: 公证 (Notarization)

对于公开分发,还需要 Apple 公证:

```bash
# 1. 构建并签名
pnpm tauri build

# 2. 创建 DMG 或 ZIP
# (Tauri 默认会创建 DMG)

# 3. 提交公证
xcrun notarytool submit \
  src-tauri/target/bundle-release/bundle/dmg/Rewind_0.1.0_aarch64.dmg \
  --apple-id "your@email.com" \
  --team-id "TEAMID" \
  --password "app-specific-password" \
  --wait

# 4. 装订票据
xcrun stapler staple src-tauri/target/bundle-release/bundle/dmg/Rewind_0.1.0_aarch64.dmg
```

### 方案 3: 自动化 CI/CD

在 GitHub Actions 中自动签名:

```yaml
- name: Import Code Signing Certificates
  uses: apple-actions/import-codesign-certs@v2
  with:
    p12-file-base64: ${{ secrets.CERTIFICATES_P12 }}
    p12-password: ${{ secrets.CERTIFICATES_P12_PASSWORD }}

- name: Build and Sign
  run: pnpm tauri build
  env:
    APPLE_SIGNING_IDENTITY: ${{ secrets.APPLE_SIGNING_IDENTITY }}
```

## 常见问题

### Q1: 为什么直接运行可执行文件可以,但双击 .app 不行?

命令行运行绕过了部分 macOS Gatekeeper 检查,但双击启动会触发完整的安全验证。

### Q2: 每次构建都要重新签名吗?

是的。每次 `pnpm tauri build` 都会生成新的二进制文件,需要重新签名。建议使用 `pnpm tauri:build:signed`。

### Q3: 可以禁用 Library Validation 吗?

可以,这正是我们的 entitlements 配置做的事。但这只适用于开发环境。分发给用户时需要正式证书签名。

### Q4: 为什么需要签名这么多 .dylib 文件?

因为项目使用了 Python 嵌入式运行时,包含了大量第三方库 (PIL, OpenCV, scipy 等),每个库都有自己的动态链接库。

### Q5: adhoc 签名和正式证书签名有什么区别?

- **adhoc 签名**: 本地开发使用,无需证书,但需要特殊权限才能运行
- **证书签名**: 使用 Apple 颁发的证书,可以分发给其他用户,通过 Gatekeeper 验证

## 参考资料

- [Tauri Code Signing](https://tauri.app/v1/guides/distribution/sign-macos)
- [Apple Code Signing Guide](https://developer.apple.com/library/archive/documentation/Security/Conceptual/CodeSigningGuide/)
- [PyTauri Documentation](https://github.com/pytauri/pytauri)
- [macOS Entitlements Reference](https://developer.apple.com/documentation/bundleresources/entitlements)

## 项目文件结构

```
Rewind/
├── scripts/
│   └── sign-macos.sh              # 自动签名脚本
├── src-tauri/
│   ├── entitlements.plist         # macOS 权限配置
│   └── target/
│       └── bundle-release/
│           └── bundle/
│               └── macos/
│                   └── Rewind.app # 构建产物
├── docs/
│   └── macos_signing.md           # 本文档
└── package.json                    # 包含签名命令
```

## 支持

如果遇到签名问题:

1. 查看脚本输出的详细信息
2. 检查 `codesign -dvvv` 的输出
3. 查看系统日志: `log show --predicate 'process == "Rewind"' --last 1m`
4. 提交 issue 到项目仓库

---

**最后更新**: 2025-11-02
**适用版本**: Tauri 2.x + PyTauri 0.8
