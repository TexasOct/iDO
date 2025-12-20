#!/usr/bin/env node

/**
 * Sync version from package.json to pyproject.toml
 * Used after standard-version bumps the version
 */

const fs = require('fs')
const path = require('path')

const rootDir = path.join(__dirname, '..')
const packageJsonPath = path.join(rootDir, 'package.json')
const pyprojectPath = path.join(rootDir, 'pyproject.toml')

try {
  // Read version from package.json
  const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf-8'))
  const version = packageJson.version

  if (!version) {
    console.error('Error: No version found in package.json')
    process.exit(1)
  }

  // Read pyproject.toml
  const pyprojectContent = fs.readFileSync(pyprojectPath, 'utf-8')

  // Update version in pyproject.toml
  const updatedContent = pyprojectContent.replace(
    /^version\s*=\s*["'].+?["']/m,
    `version = "${version}"`
  )

  // Write back
  fs.writeFileSync(pyprojectPath, updatedContent, 'utf-8')

  console.log(`✅ Synced version ${version} to pyproject.toml`)
} catch (error) {
  console.error('Error syncing version:', error.message)
  process.exit(1)
}
