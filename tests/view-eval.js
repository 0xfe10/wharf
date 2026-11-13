// Evaluates every plugin view the way GL.iNet's panel does (eval of a CommonJS
// module) and checks that it yields a renderable Vue 2 component.
'use strict'
const fs = require('fs')
const path = require('path')
const assert = require('assert')

const root = path.join(__dirname, '..')
const views = []
for (const plugin of fs.readdirSync(path.join(root, 'plugins'))) {
  const spec = JSON.parse(fs.readFileSync(path.join(root, 'plugins', plugin, 'plugin.json'), 'utf8'))
  for (const pkg of spec.packages) {
    for (const g of pkg.gzip || []) {
      if (g.endsWith('.common.js')) views.push(path.join(root, 'plugins', plugin, pkg.dir, 'root', g))
    }
  }
}
assert(views.length > 0, 'no views found')

function load(file, loc, lang) {
  global.window = { location: loc, navigator: { language: lang } }
  const module = { exports: {} } // the panel evaluates inside a webpack module scope
  const component = eval(fs.readFileSync(file, 'utf8')) // eslint-disable-line no-eval
  assert.strictEqual(component, module.exports, 'eval result must be module.exports')
  return component
}

// Minimal Vue-2-style hyperscript: h(tag, [data], children)
function h(tag, data, children) {
  if (Array.isArray(data) || typeof data === 'string') { children = data; data = {} }
  return { tag, data: data || {}, children: [].concat(children === undefined ? [] : children) }
}
function walk(node, fn) {
  if (typeof node === 'string') return
  fn(node)
  node.children.forEach((c) => walk(c, fn))
}
function instance(component) {
  const vm = Object.assign({}, component.data.call({}))
  for (const [k, fnc] of Object.entries(component.computed || {})) {
    Object.defineProperty(vm, k, { get: () => fnc.call(vm) })
  }
  return vm
}

for (const file of views) {
  const cases = [
    [{ hostname: '192.168.20.1', protocol: 'http:' }, 'en-US', 'http://192.168.20.1:8080/cgi-bin/luci/admin/services/openclash'],
    [{ hostname: '192.168.20.1', protocol: 'https:' }, 'zh-CN', 'https://192.168.20.1:8443/cgi-bin/luci/admin/services/openclash'],
    [{ hostname: 'fd00::1', protocol: 'http:' }, 'en', 'http://[fd00::1]:8080/cgi-bin/luci/admin/services/openclash']
  ]
  for (const [loc, lang, expectLuci] of cases) {
    const c = load(file, loc, lang)
    assert.strictEqual(typeof c.render, 'function')
    assert.strictEqual(typeof c.name, 'string')
    const vm = instance(c)
    const tree = c.render.call(vm, h)
    const hrefs = []
    walk(tree, (n) => { if (n.tag === 'a') hrefs.push(n.data.attrs.href) })
    assert(hrefs.includes(expectLuci), 'LuCI link missing/wrong: ' + hrefs.join(', '))
    assert(hrefs.some((u) => u.includes(':9090/ui/')), 'dashboard link missing')
    hrefs.forEach((u) => assert(/^https?:\/\//.test(u), 'unexpected scheme in ' + u))
  }
  console.log('ok  ' + path.relative(root, file))
}
