const fs = require('fs')
const path = require('path')
const ts = require('typescript')

function nowTs() {
  return String(Math.floor(Date.now() / 1000))
}

function ensureDir(p) {
  fs.mkdirSync(p, { recursive: true })
}

function readFile(p) {
  try { return fs.readFileSync(p, 'utf8') } catch { return '' }
}

function isCapital(s) {
  return !!s && s[0] === s[0].toUpperCase() && /[A-Z]/.test(s[0])
}

function walk(dir, filter) {
  const out = []
  const items = fs.readdirSync(dir)
  for (const it of items) {
    const p = path.join(dir, it)
    const st = fs.statSync(p)
    if (st.isDirectory()) out.push(...walk(p, filter))
    else if (filter(p)) out.push(p)
  }
  return out
}

function fileId(fp) {
  const rel = fp.replace(process.cwd(), '').replace(/^\//, '')
  return 'file_' + rel.replace(/\//g, '_')
}

function cmpId(name) { return 'cmp_' + name }
function fnId(name) { return 'fn_' + name }
function hookId(name) { return 'hook_' + name }

function resolveImport(fromFile, spec) {
  if (!spec) return spec
  if (spec.startsWith('.') || spec.startsWith('/')) {
    const base = path.dirname(fromFile)
    let target = path.resolve(base, spec)
    const candidates = [target + '.ts', target + '.tsx', target + '.js', target + '/index.tsx', target + '/index.ts']
    for (const c of candidates) { if (fs.existsSync(c)) return c }
    return target
  }
  return spec
}

function analyzeFile(fp) {
  const src = readFile(fp)
  const kind = fp.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS
  const sf = ts.createSourceFile(fp, src, ts.ScriptTarget.Latest, true, kind)
  const entities = []
  const edges = []
  const texts = []
  const fid = fileId(fp)
  entities.push({ id: fid, name: path.basename(fp), type: 'File', file_path: fp, metadata: {} })

  function addContains(id) { edges.push({ source: fid, target: id, type: 'CONTAINS' }) }
  const ctx = { fn: null, cmp: null }

  function visit(n) {
    if (ts.isImportDeclaration(n)) {
      const mod = n.moduleSpecifier.getText(sf).replace(/['"]/g, '')
      const rp = resolveImport(fp, mod)
      edges.push({ source: fid, target: rp.startsWith('file_') ? rp : fileId(rp), type: 'IMPORTS' })
      if (n.importClause && n.importClause.namedBindings && ts.isNamedImports(n.importClause.namedBindings)) {
        for (const e of n.importClause.namedBindings.elements) {
          const nm = e.name.getText(sf)
          entities.push({ id: 'import_' + fid + '_' + nm, name: nm, type: 'Import', file_path: fp, metadata: { module: mod } })
          addContains('import_' + fid + '_' + nm)
        }
      }
    } else if (ts.isExportDeclaration(n)) {
      const mod = n.moduleSpecifier ? n.moduleSpecifier.getText(sf).replace(/['"]/g, '') : null
      if (n.exportClause && ts.isNamedExports(n.exportClause)) {
        for (const e of n.exportClause.elements) {
          const nm = e.name.getText(sf)
          const id = 'export_' + fid + '_' + nm
          entities.push({ id, name: nm, type: 'Export', file_path: fp, metadata: { module: mod } })
          addContains(id)
          edges.push({ source: fid, target: id, type: 'EXPORTS' })
        }
      }
    } else if (ts.isFunctionDeclaration(n)) {
      const nm = n.name ? n.name.getText(sf) : ''
      if (nm) {
        const id = fnId(nm)
        entities.push({ id, name: nm, type: 'Function', file_path: fp, metadata: {} })
        addContains(id)
        if (isCapital(nm)) {
          entities.push({ id: cmpId(nm), name: nm, type: 'Component', file_path: fp, metadata: {} })
          addContains(cmpId(nm))
        }
        const prevF = ctx.fn; const prevC = ctx.cmp; ctx.fn = nm; ctx.cmp = isCapital(nm) ? nm : null
        ts.forEachChild(n, visit)
        ctx.fn = prevF; ctx.cmp = prevC
        return
      }
    } else if (ts.isVariableStatement(n)) {
      for (const d of n.declarationList.declarations) {
        const nm = d.name && d.name.getText(sf)
        if (nm) {
          const init = d.initializer
          if (init && (ts.isArrowFunction(init) || ts.isFunctionExpression(init))) {
            const id = fnId(nm)
            entities.push({ id, name: nm, type: 'Function', file_path: fp, metadata: {} })
            addContains(id)
            if (isCapital(nm)) entities.push({ id: cmpId(nm), name: nm, type: 'Component', file_path: fp, metadata: {} })
            const prevF = ctx.fn; const prevC = ctx.cmp; ctx.fn = nm; ctx.cmp = isCapital(nm) ? nm : null
            ts.forEachChild(init, visit)
            ctx.fn = prevF; ctx.cmp = prevC
          }
        }
      }
    } else if (ts.isExpressionStatement(n) && ts.isCallExpression(n.expression)) {
      const callee = n.expression.expression.getText(sf)
      if (callee.startsWith('use')) edges.push({ source: fid, target: hookId(callee), type: 'USES_HOOK' })
    } else if (ts.isCallExpression(n)) {
      const callee = n.expression.getText(sf)
      const srcId = ctx.fn ? fnId(ctx.fn) : fid
      edges.push({ source: srcId, target: fnId(callee), type: 'CALLS' })
    } else if (ts.isJsxElement && ts.isJsxElement(n)) {
      const tag = n.openingElement.tagName.getText(sf)
      if (isCapital(tag)) {
        const srcId = ctx.cmp ? cmpId(ctx.cmp) : (ctx.fn ? fnId(ctx.fn) : fid)
        edges.push({ source: srcId, target: cmpId(tag), type: 'RENDERS' })
      }
    } else if (ts.isJsxSelfClosingElement && ts.isJsxSelfClosingElement(n)) {
      const tag = n.tagName.getText(sf)
      if (isCapital(tag)) {
        const srcId = ctx.cmp ? cmpId(ctx.cmp) : (ctx.fn ? fnId(ctx.fn) : fid)
        edges.push({ source: srcId, target: cmpId(tag), type: 'RENDERS' })
      }
    }
    ts.forEachChild(n, visit)
  }
  visit(sf)
  texts.push({ document_id: fp, chunk_id: 0, text: src.slice(0, 800) })
  return { entities, edges, texts }
}

function main() {
  const root = path.resolve(process.cwd(), '..')
  const srcDir = path.resolve(process.cwd(), 'src')
  const files = walk(srcDir, p => p.endsWith('.ts') || p.endsWith('.tsx'))
  const tsEpoch = nowTs()
  let outBase = process.env.GRAPHRAG_INDEX_PATH || 'graphrag-pipeline/output'
  if (!path.isAbsolute(outBase)) outBase = path.resolve(root, outBase)
  let artifactsDir = path.join(outBase, tsEpoch, 'artifacts')
  try { ensureDir(artifactsDir) } catch { artifactsDir = path.join('/tmp', 'lumion_graphrag_output', tsEpoch, 'artifacts'); ensureDir(artifactsDir) }
  const allEntities = []
  const allEdges = []
  const allTexts = []
  const communities = new Map()
  for (const f of files) {
    const r = analyzeFile(f)
    allEntities.push(...r.entities)
    allEdges.push(...r.edges)
    allTexts.push(...r.texts)
    const dir = path.relative(srcDir, path.dirname(f)).split(path.sep)[0] || ''
    const key = dir ? `src/${dir}` : 'src'
    const bucket = communities.get(key) || { files: 0, components: 0, functions: 0, imports: new Map() }
    bucket.files += 1
    r.entities.forEach(e => {
      if (e.type === 'Component') bucket.components += 1
      if (e.type === 'Function') bucket.functions += 1
      if (e.type === 'Import') {
        const mod = (e.metadata && e.metadata.module) || 'unknown'
        bucket.imports.set(mod, (bucket.imports.get(mod) || 0) + 1)
      }
    })
    communities.set(key, bucket)
  }
  fs.writeFileSync(path.join(artifactsDir, 'create_final_entities.json'), JSON.stringify(allEntities, null, 2))
  fs.writeFileSync(path.join(artifactsDir, 'create_final_relationships.json'), JSON.stringify(allEdges, null, 2))
  fs.writeFileSync(path.join(artifactsDir, 'create_final_text_units.json'), JSON.stringify(allTexts, null, 2))
  const reports = []
  for (const [cid, b] of communities.entries()) {
    const sortedImports = Array.from(b.imports.entries()).sort((a,b)=>b[1]-a[1]).slice(0,5)
    const topImportsStr = sortedImports.map(([m,c])=>`${m}(${c})`).join(', ')
    const report = `Community ${cid}: files=${b.files}, components=${b.components}, functions=${b.functions}, top imports: ${topImportsStr}`
    reports.push({ community_id: cid, report, files: b.files, components: b.components, functions: b.functions, top_imports: sortedImports.map(([m,c])=>({ module:m, count:c })) })
  }
  fs.writeFileSync(path.join(artifactsDir, 'create_final_community_reports.json'), JSON.stringify(reports, null, 2))
  console.log('Artifacts written to:', artifactsDir)
}

main()
