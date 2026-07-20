import { extname } from 'node:path'

export async function resolve(specifier, context, nextResolve) {
  if (specifier.startsWith('.') && extname(specifier) === '') {
    try {
      return await nextResolve(`${specifier}.ts`, context, nextResolve)
    } catch {
      // Let Node report the original resolution error for non-TS imports.
    }
  }
  return nextResolve(specifier, context, nextResolve)
}
