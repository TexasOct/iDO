import { existsSync } from 'fs'

export default {
  '*.{js,jsx,ts,tsx}': (files) => {
    const existingFiles = files.filter((file) => existsSync(file))
    return existingFiles.length > 0 ? existingFiles.map((file) => `prettier --write ${file}`) : []
  },
  '*.{json,md,yml,yaml}': (files) => {
    const existingFiles = files.filter((file) => existsSync(file))
    return existingFiles.length > 0 ? existingFiles.map((file) => `prettier --write ${file}`) : []
  },
  'pyproject.toml': () => ['uv lock', 'git add uv.lock']
}
