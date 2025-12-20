const fs = require('fs')
const path = require('path')

// Custom updater for TOML files (pyproject.toml)
const tomlUpdater = {
  readVersion: function (contents) {
    const versionMatch = contents.match(/^version\s*=\s*["'](.+?)["']/m)
    return versionMatch ? versionMatch[1] : null
  },
  writeVersion: function (contents, version) {
    return contents.replace(
      /^version\s*=\s*["'].+?["']/m,
      `version = "${version}"`
    )
  }
}

module.exports = {
  types: [
    {
      type: 'feat',
      section: '✨ Features'
    },
    {
      type: 'fix',
      section: '🐛 Bug Fixes'
    },
    {
      type: 'perf',
      section: '⚡ Performance Improvements'
    },
    {
      type: 'refactor',
      section: '♻️ Code Refactoring'
    },
    {
      type: 'docs',
      section: '📝 Documentation',
      hidden: true
    },
    {
      type: 'style',
      section: '💄 Styles',
      hidden: true
    },
    {
      type: 'test',
      section: '✅ Tests',
      hidden: true
    },
    {
      type: 'build',
      section: '📦 Build System',
      hidden: true
    },
    {
      type: 'ci',
      section: '👷 CI/CD',
      hidden: true
    },
    {
      type: 'chore',
      section: '🔧 Chores',
      hidden: true
    }
  ],
  skip: {
    bump: false,
    changelog: false,
    commit: false,
    tag: false
  },
  header:
    '# Changelog\n\nAll notable changes to this project will be documented in this file. See [standard-version](https://github.com/conventional-changelog/standard-version) for commit guidelines.\n',

  // Files to bump version in
  bumpFiles: [
    {
      filename: 'package.json',
      type: 'json'
    },
    {
      filename: 'src-tauri/tauri.conf.json',
      type: 'json'
    },
    {
      filename: 'src-tauri/tauri.macos.conf.json',
      type: 'json'
    },
    {
      filename: 'src-tauri/tauri.windows.conf.json',
      type: 'json'
    }
  ],

  // Files to read version from (package.json is default)
  packageFiles: [
    {
      filename: 'package.json',
      type: 'json'
    }
  ]
}
