/*
 * wharf: OpenClash entry for the GL.iNet 4.x admin panel (OUI).
 *
 * The panel loads /views/gl-sdk4-ui-<view>.common.js and eval()s it as a Vue 2
 * component, so this file is a CommonJS module that evaluates to a component
 * options object. It deliberately uses only plain DOM elements (no Element UI
 * components) and no iframe: it just links to OpenClash's own pages.
 * Shipped gzipped; the .js source lives in the repo so it can be tested.
 */
module.exports = {
  name: 'wharf-openclash',

  data: function () {
    return {
      host: window.location.hostname,
      https: window.location.protocol === 'https:',
      zh: /^zh/i.test(window.navigator.language || '')
    }
  },

  computed: {
    hostPart: function () {
      return this.host.indexOf(':') >= 0 ? '[' + this.host + ']' : this.host
    },
    luciUrl: function () {
      var scheme = this.https ? 'https' : 'http'
      var port = this.https ? 8443 : 8080
      return scheme + '://' + this.hostPart + ':' + port + '/cgi-bin/luci/admin/services/openclash'
    },
    dashboardUrl: function () {
      return 'http://' + this.hostPart + ':9090/ui/metacubexd/'
    },
    zashboardUrl: function () {
      return 'http://' + this.hostPart + ':9090/ui/zashboard/'
    },
    text: function () {
      return this.zh ? {
        title: 'OpenClash',
        intro: '订阅、规则、运行模式在 OpenClash 的设置页(LuCI)中配置;日常看流量、切换节点用仪表盘。',
        settings: '打开 OpenClash 设置',
        dashboard: '打开仪表盘 (MetaCubeXD)',
        zashboard: '打开仪表盘 (Zashboard)',
        hint1: '设置页需要 LuCI 已在 8080/8443 端口运行(安装本插件时会自动启用)。LuCI 使用 root 密码登录。',
        hint2: '仪表盘需要先在 OpenClash 设置页启动服务;首次启动会下载内核。',
        hint3: '卸载 OpenClash 本体会删除订阅和配置,卸载前请先备份。'
      } : {
        title: 'OpenClash',
        intro: 'Subscriptions, rules and run mode are configured in OpenClash\'s own settings page (LuCI). Use the dashboard to watch traffic and switch nodes.',
        settings: 'Open OpenClash settings',
        dashboard: 'Open dashboard (MetaCubeXD)',
        zashboard: 'Open dashboard (Zashboard)',
        hint1: 'The settings page needs LuCI on port 8080/8443 (enabled when this plugin is installed). LuCI signs in with the root password.',
        hint2: 'Start the service from the settings page first; the core is downloaded on the first start.',
        hint3: 'Removing OpenClash itself deletes your subscriptions and config. Back them up first.'
      }
    }
  },

  render: function (h) {
    var t = this.text
    var btn = function (href, label, primary) {
      return h('a', {
        attrs: { href: href, target: '_blank', rel: 'noopener' },
        style: {
          display: 'inline-block', margin: '0 12px 12px 0', padding: '10px 20px',
          borderRadius: '4px', textDecoration: 'none', fontSize: '14px',
          color: primary ? '#fff' : '#2d6cdf',
          background: primary ? '#2d6cdf' : 'transparent',
          border: '1px solid #2d6cdf'
        }
      }, label)
    }
    return h('div', { class: 'wharf-openclash', style: { padding: '24px', maxWidth: '760px' } }, [
      h('h2', { style: { margin: '0 0 12px' } }, t.title),
      h('p', { style: { margin: '0 0 20px', lineHeight: '1.6' } }, t.intro),
      h('div', [
        btn(this.luciUrl, t.settings, true),
        btn(this.dashboardUrl, t.dashboard, false),
        btn(this.zashboardUrl, t.zashboard, false)
      ]),
      h('ul', { style: { margin: '12px 0 0', paddingLeft: '18px', lineHeight: '1.8', opacity: 0.75, fontSize: '13px' } }, [
        h('li', t.hint1),
        h('li', t.hint2),
        h('li', t.hint3)
      ])
    ])
  }
}
