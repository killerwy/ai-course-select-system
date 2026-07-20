#!/usr/bin/env node

/**
 * Generate OpenAPI specification from FastAPI app.
 *
 * Usage:
 *   node scripts/generate-openapi.mjs
 *
 * This script imports the FastAPI app and dumps its OpenAPI schema to
 * openapi/spec.yaml and openapi/spec.json.
 */

import { writeFileSync, mkdirSync, existsSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const rootDir = join(__dirname, '..')
const openApiDir = join(rootDir, 'openapi')

async function generateOpenAPI() {
  console.log('Generating OpenAPI specification...')

  // Ensure openapi directory exists
  if (!existsSync(openApiDir)) {
    mkdirSync(openApiDir, { recursive: true })
  }

  try {
    // Dynamic import of the FastAPI app
    // We need to use a subprocess to avoid import issues with the Python environment
    const { execSync } = await import('node:child_process')
    
    const pythonScript = `
import sys
import json
sys.path.insert(0, '${rootDir.replace(/\\/g, '\\\\')}/backend')

from app.main import app

schema = app.openapi()
print(json.dumps(schema, indent=2, ensure_ascii=False))
`
    
    const result = execSync(`python -c "${pythonScript.replace(/"/g, '\\"').replace(/\n/g, '\\n')}"`, {
      cwd: join(rootDir, 'backend'),
      encoding: 'utf-8',
      stdio: ['pipe', 'pipe', 'pipe'],
    })

    const schema = JSON.parse(result)
    
    // Write JSON spec
    const jsonPath = join(openApiDir, 'spec.json')
    writeFileSync(jsonPath, JSON.stringify(schema, null, 2), 'utf-8')
    console.log(`Generated: ${jsonPath}`)

    // Write YAML-like format (simplified)
    const yamlPath = join(openApiDir, 'spec.yaml')
    const yamlContent = generateYamlLike(schema)
    writeFileSync(yamlPath, yamlContent, 'utf-8')
    console.log(`Generated: ${yamlPath}`)

    console.log('OpenAPI specification generated successfully!')
  } catch (error) {
    console.error('Error generating OpenAPI spec:', error.message)
    console.error('Make sure Python and FastAPI dependencies are installed.')
    process.exit(1)
  }
}

function generateYamlLike(schema) {
  // Simple YAML-like output for readability
  let yaml = `# OpenAPI 3.1.0 Specification
# Generated from FastAPI app

openapi: "${schema.openapi}"
info:
  title: "${schema.info?.title || 'Course Selection API'}"
  version: "${schema.info?.version || '1.0.0'}"
  description: "${schema.info?.description || 'Course Selection & Recommendation System API'}"

paths:
`
  
  for (const [path, methods] of Object.entries(schema.paths || {})) {
    yaml += `  ${path}:\n`
    for (const [method, details] of Object.entries(methods)) {
      if (['get', 'post', 'put', 'patch', 'delete'].includes(method)) {
        yaml += `    ${method}:\n`
        yaml += `      summary: "${details.summary || ''}"\n`
        yaml += `      tags: [${(details.tags || []).join(', ')}]\n`
        if (details.operationId) {
          yaml += `      operationId: "${details.operationId}"\n`
        }
      }
    }
  }

  return yaml
}

generateOpenAPI()
