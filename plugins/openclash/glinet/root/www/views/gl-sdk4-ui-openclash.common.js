/*
 * wharf: OpenClash entry for the GL.iNet 4.x admin panel (OUI).
 *
 * The panel loads /views/gl-sdk4-ui-<view>.common.js and eval()s it as a Vue 2
 * component, so this file is a CommonJS module that evaluates to a component
 * options object. It deliberately uses only plain DOM elements (no Element UI
 * components) and no iframe: it just links to OpenClash's settings page and to Zashboard.
 * Shipped gzipped; the .js source lives in the repo so it can be tested.
 */
var TEXTS = {
  en: { settings: 'OpenClash settings', dashboard: 'Dashboard (Zashboard)', hint: 'Log in to the settings page with the root password. In the dashboard, set Host to this router and enter the Dashboard Secret from OpenClash > Plugin Settings > Dashboard Settings.' },
  'zh-cn': { settings: 'OpenClash 设置', dashboard: '仪表盘 (Zashboard)', hint: '设置页用 root 密码登录。仪表盘里把 Host 填成本路由器地址,密码填 OpenClash 插件设置 > 仪表盘设置里的 Dashboard Secret。' },
  'zh-tw': { settings: 'OpenClash 設定', dashboard: '儀表板 (Zashboard)', hint: '設定頁使用 root 密碼登入。儀表板中把 Host 填成本路由器位址,密碼填 OpenClash 外掛設定 > 儀表板設定中的 Dashboard Secret。' },
  ja: { settings: 'OpenClash 設定', dashboard: 'ダッシュボード (Zashboard)', hint: '設定ページには root パスワードでログインします。ダッシュボードでは Host にこのルーターのアドレスを入力し、パスワードに OpenClash のプラグイン設定 > ダッシュボード設定の Dashboard Secret を入力します。' },
  de: { settings: 'OpenClash-Einstellungen', dashboard: 'Dashboard (Zashboard)', hint: 'Melden Sie sich auf der Einstellungsseite mit dem root-Passwort an. Tragen Sie im Dashboard als Host diesen Router ein und als Passwort das Dashboard Secret aus OpenClash > Plugin-Einstellungen > Dashboard-Einstellungen.' },
  es: { settings: 'Ajustes de OpenClash', dashboard: 'Panel (Zashboard)', hint: 'Inicie sesión en la página de ajustes con la contraseña de root. En el panel, ponga como Host este router e introduzca el Dashboard Secret de OpenClash > Ajustes del plugin > Ajustes del panel.' },
  it: { settings: 'Impostazioni di OpenClash', dashboard: 'Dashboard (Zashboard)', hint: 'Accedi alla pagina delle impostazioni con la password di root. Nella dashboard imposta come Host questo router e inserisci il Dashboard Secret da OpenClash > Impostazioni plugin > Impostazioni dashboard.' }
}

module.exports = {
  name: 'wharf-openclash',

  data: function () {
    return {
      host: window.location.hostname,
      https: window.location.protocol === 'https:'
    }
  },

  computed: {
    // The panel's own language (vue-i18n, same as the language menu); the browser language
    // is only a fallback if the panel does not expose it.
    lang: function () {
      var l = (this.$i18n && this.$i18n.locale) || window.navigator.language || 'en'
      l = String(l).toLowerCase().replace('_', '-')
      if (TEXTS[l]) return l
      if (/^zh-(tw|hk|hant|mo)/.test(l)) return 'zh-tw'
      if (/^zh/.test(l)) return 'zh-cn'
      l = l.split('-')[0]
      return TEXTS[l] ? l : 'en'
    },
    text: function () {
      return TEXTS[this.lang]
    },
    hostPart: function () {
      return this.host.indexOf(':') >= 0 ? '[' + this.host + ']' : this.host
    },
    luciUrl: function () {
      var scheme = this.https ? 'https' : 'http'
      var port = this.https ? 8443 : 8080
      return scheme + '://' + this.hostPart + ':' + port + '/cgi-bin/luci/admin/services/openclash'
    },
    zashboardUrl: function () {
      return 'http://' + this.hostPart + ':9090/ui/zashboard/'
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
      h('h2', { style: { margin: '0 0 20px' } }, 'OpenClash'),
      h('div', [
        btn(this.luciUrl, t.settings, true),
        btn(this.zashboardUrl, t.dashboard, false)
      ]),
      h('p', { style: { margin: '4px 0 0', lineHeight: '1.7', opacity: 0.75, fontSize: '13px' } }, t.hint)
    ])
  }
}
