/*
 * wharf: OpenClash entry for the GL.iNet 4.x admin panel (OUI).
 *
 * The panel loads /views/gl-sdk4-ui-<view>.common.js and eval()s it as a Vue 2
 * component, so this file is a CommonJS module that evaluates to a component
 * options object. It deliberately uses only plain DOM elements (no Element UI
 * components) and no iframe: it just links to OpenClash's own pages.
 * Shipped gzipped; the .js source lives in the repo so it can be tested.
 */
var TEXTS = {
  en: {
    intro: 'Subscriptions, rules and run mode are configured in OpenClash\'s own settings page (LuCI). Use the dashboard to watch traffic and switch nodes.',
    settings: 'Open OpenClash settings', dashboard: 'Open dashboard (MetaCubeXD)', zashboard: 'Open dashboard (Zashboard)',
    hint1: 'The settings page needs LuCI on port 8080/8443 (enabled when this plugin is installed). LuCI signs in with the root password.',
    hint2: 'Start the service from the settings page first; the core is downloaded on the first start. If you set a controller secret, enter it in the dashboard.',
    hint3: 'Removing OpenClash itself deletes your subscriptions and config. Back them up first.'
  },
  'zh-cn': {
    intro: '订阅、规则、运行模式在 OpenClash 的设置页(LuCI)中配置;日常看流量、切换节点用仪表盘。',
    settings: '打开 OpenClash 设置', dashboard: '打开仪表盘 (MetaCubeXD)', zashboard: '打开仪表盘 (Zashboard)',
    hint1: '设置页需要 LuCI 已在 8080/8443 端口运行(安装本插件时会自动启用)。LuCI 使用 root 密码登录。',
    hint2: '仪表盘需要先在 OpenClash 设置页启动服务;首次启动会下载内核。如果设置了访问密钥(secret),请在仪表盘里填入。',
    hint3: '卸载 OpenClash 本体会删除订阅和配置,卸载前请先备份。'
  },
  'zh-tw': {
    intro: '訂閱、規則、執行模式在 OpenClash 的設定頁(LuCI)中設定;日常查看流量、切換節點請用儀表板。',
    settings: '開啟 OpenClash 設定', dashboard: '開啟儀表板 (MetaCubeXD)', zashboard: '開啟儀表板 (Zashboard)',
    hint1: '設定頁需要 LuCI 在 8080/8443 連接埠執行(安裝本外掛時會自動啟用)。LuCI 使用 root 密碼登入。',
    hint2: '儀表板需要先在 OpenClash 設定頁啟動服務;首次啟動會下載核心。如果設定了存取金鑰(secret),請在儀表板中填入。',
    hint3: '移除 OpenClash 本體會刪除訂閱和設定,移除前請先備份。'
  },
  ja: {
    intro: 'サブスクリプション、ルール、動作モードは OpenClash 自身の設定ページ(LuCI)で設定します。トラフィックの確認やノードの切り替えにはダッシュボードを使います。',
    settings: 'OpenClash 設定を開く', dashboard: 'ダッシュボードを開く (MetaCubeXD)', zashboard: 'ダッシュボードを開く (Zashboard)',
    hint1: '設定ページには 8080/8443 ポートで動作する LuCI が必要です(このプラグインのインストール時に自動で有効化されます)。LuCI には root パスワードでログインします。',
    hint2: '先に設定ページでサービスを起動してください。初回起動時にコアをダウンロードします。コントローラーのシークレットを設定した場合は、ダッシュボードで入力してください。',
    hint3: 'OpenClash 本体を削除すると、サブスクリプションと設定も削除されます。事前にバックアップしてください。'
  },
  de: {
    intro: 'Abonnements, Regeln und Betriebsmodus werden auf der eigenen Einstellungsseite von OpenClash (LuCI) konfiguriert. Im Dashboard sehen Sie den Datenverkehr und wechseln Knoten.',
    settings: 'OpenClash-Einstellungen öffnen', dashboard: 'Dashboard öffnen (MetaCubeXD)', zashboard: 'Dashboard öffnen (Zashboard)',
    hint1: 'Die Einstellungsseite benötigt LuCI auf Port 8080/8443 (wird bei der Installation dieses Plugins aktiviert). LuCI meldet sich mit dem root-Passwort an.',
    hint2: 'Starten Sie zuerst den Dienst auf der Einstellungsseite; der Core wird beim ersten Start heruntergeladen. Wenn Sie ein Controller-Secret gesetzt haben, geben Sie es im Dashboard ein.',
    hint3: 'Beim Entfernen von OpenClash selbst werden Abonnements und Konfiguration gelöscht. Sichern Sie diese vorher.'
  },
  es: {
    intro: 'Las suscripciones, reglas y el modo de ejecución se configuran en la propia página de ajustes de OpenClash (LuCI). Use el panel para ver el tráfico y cambiar de nodo.',
    settings: 'Abrir ajustes de OpenClash', dashboard: 'Abrir panel (MetaCubeXD)', zashboard: 'Abrir panel (Zashboard)',
    hint1: 'La página de ajustes necesita LuCI en el puerto 8080/8443 (se activa al instalar este plugin). LuCI inicia sesión con la contraseña de root.',
    hint2: 'Inicie primero el servicio desde la página de ajustes; el núcleo se descarga en el primer inicio. Si definió un secreto del controlador, introdúzcalo en el panel.',
    hint3: 'Al eliminar OpenClash se borran sus suscripciones y configuración. Haga una copia de seguridad antes.'
  },
  it: {
    intro: 'Abbonamenti, regole e modalità di esecuzione si configurano nella pagina delle impostazioni di OpenClash (LuCI). Usa la dashboard per vedere il traffico e cambiare nodo.',
    settings: 'Apri le impostazioni di OpenClash', dashboard: 'Apri la dashboard (MetaCubeXD)', zashboard: 'Apri la dashboard (Zashboard)',
    hint1: 'La pagina delle impostazioni richiede LuCI sulla porta 8080/8443 (attivato all\'installazione di questo plugin). LuCI accede con la password di root.',
    hint2: 'Avvia prima il servizio dalla pagina delle impostazioni; il core viene scaricato al primo avvio. Se hai impostato un secret del controller, inseriscilo nella dashboard.',
    hint3: 'Rimuovendo OpenClash si eliminano abbonamenti e configurazione. Fai prima un backup.'
  }
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
    // Same shape OpenClash itself uses (common.js ocBuildDashboardURL): /ui/<dir>/#/setup?hostname=..&port=..
    dashboardSetup: function () {
      return '/#/setup?hostname=' + encodeURIComponent(this.host) + '&port=9090'
    },
    dashboardUrl: function () {
      return 'http://' + this.hostPart + ':9090/ui/metacubexd' + this.dashboardSetup
    },
    zashboardUrl: function () {
      return 'http://' + this.hostPart + ':9090/ui/zashboard' + this.dashboardSetup
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
      h('h2', { style: { margin: '0 0 12px' } }, 'OpenClash'),
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
