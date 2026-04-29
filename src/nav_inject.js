(function() {
  var root = typeof globalThis !== 'undefined' ? globalThis :
    (typeof window !== 'undefined' ? window :
      (typeof self !== 'undefined' ? self : this));
  var hostWindow = typeof window !== 'undefined' ? window : root;

  if (root._navInjected && root.nav && root.nav.wxFrame) {
    try {
      var cachedConfig = root.nav.wxFrame.__wxConfig || root.__wxConfig;
      if (cachedConfig && cachedConfig.pages) return;
    } catch (e) {}
  }
  root._navInjected = true;

  class UniversalMiniProgramNavigator {
    constructor() {
      this.wxFrame = null;
      this.config = null;
      this.allPages = [];
      this.tabBarPages = [];
      this.categorizedPages = {};
      this.menuItems = [];
      this._customHeaders = {};
      this._redirectGuard = false;
      this._blockedRedirects = [];
      this._capturedAPIs = [];
      this._globalAPIs = [];
      this._globalAPISet = new Set();
      this._captureEnabled = false;
      this._capturedRequests = [];
      this._captureSeq = 0;
      this._requestCaptureLimit = 500;
      this._hooked = false;
      this._originalMethods = {};
      this.init();
    }

    init() {
      if (!this.detectMiniProgramEnvironment()) {
        console.error('MiniProgram environment not found');
        return;
      }
      this.loadConfiguration();
      this.categorizePages();
    }

    detectMiniProgramEnvironment() {
      if (typeof wx !== 'undefined' && typeof getCurrentPages !== 'undefined') {
        this.wxFrame = root;
        return true;
      }
      if (hostWindow && hostWindow.frames) {
        for (var i = 0; i < hostWindow.frames.length; i++) {
          try {
            var frame = hostWindow.frames[i];
            if (frame.wx && frame.__wxConfig) {
              this.wxFrame = frame;
              return true;
            }
          } catch (e) {}
        }
      }
      try {
        if (hostWindow.parent && hostWindow.parent.frames) {
          for (var j = 0; j < hostWindow.parent.frames.length; j++) {
            try {
              var parentFrame = hostWindow.parent.frames[j];
              if (parentFrame.wx && parentFrame.__wxConfig) {
                this.wxFrame = parentFrame;
                return true;
              }
            } catch (e) {}
          }
        }
      } catch (e) {}
      return false;
    }

    loadConfiguration() {
      this.config = (this.wxFrame && this.wxFrame.__wxConfig) || root.__wxConfig || {};
      this.allPages = [].concat(this.config.pages || []);

      var subPkgs = this.config.subPackages || this.config.subpackages || [];
      var allPages = this.allPages;
      subPkgs.forEach(function(pkg) {
        (pkg.pages || []).forEach(function(page) {
          var fullPath = pkg.root + '/' + page;
          if (allPages.indexOf(fullPath) === -1) {
            allPages.push(fullPath);
          }
        });
      });

      var seen = {};
      this.allPages = this.allPages.filter(function(page) {
        if (seen[page]) return false;
        seen[page] = true;
        return true;
      });

      if (this.config.tabBar && this.config.tabBar.list) {
        this.tabBarPages = this.config.tabBar.list.map(function(tab) {
          return String(tab.pagePath || '').replace('.html', '');
        });
      }
    }

    categorizePages() {
      this.categorizedPages = {
        tabbar: [], auth: [], home: [], list: [], detail: [],
        form: [], user: [], order: [], payment: [], setting: [], other: []
      };
      var self = this;
      this.tabBarPages.forEach(function(page) {
        self.categorizedPages.tabbar.push({
          url: page, name: page, method: 'switchTab', type: 'tabbar'
        });
      });

      var categoryKeywords = {
        auth: ['login', 'register', 'auth', 'sign', 'entry', 'bridge'],
        home: ['home', 'index', 'main', 'dashboard'],
        list: ['list'],
        detail: ['detail', 'info'],
        form: ['form', 'add', 'edit', 'confirm'],
        user: ['user', 'profile', 'person'],
        order: ['order', 'transaction', 'record'],
        payment: ['pay', 'payment', 'recharge'],
        setting: ['setting', 'config']
      };

      this.allPages.forEach(function(page) {
        if (self.tabBarPages.indexOf(page) !== -1) return;
        var pageInfo = { url: page, name: page, method: 'navigateTo', type: 'normal' };
        var lowered = String(page || '').toLowerCase();
        var matched = false;
        Object.keys(categoryKeywords).some(function(category) {
          var hit = categoryKeywords[category].some(function(keyword) {
            return lowered.indexOf(String(keyword).toLowerCase()) !== -1;
          });
          if (hit) {
            self.categorizedPages[category].push(pageInfo);
            matched = true;
          }
          return hit;
        });
        if (!matched) self.categorizedPages.other.push(pageInfo);
      });

      var items = [];
      Object.keys(this.categorizedPages).forEach(function(category) {
        self.categorizedPages[category].forEach(function(item) {
          items.push(item);
        });
      });
      this.menuItems = items;
    }

    _getNav(method) {
      if (this._redirectGuard) {
        if (method === 'redirectTo' && this._origRedirectTo) return this._origRedirectTo;
        if (method === 'reLaunch' && this._origReLaunch) return this._origReLaunch;
        if (method === 'navigateTo' && this._origNavigateTo) return this._origNavigateTo;
      }
      return this.wxFrame && this.wxFrame.wx ? this.wxFrame.wx[method] : null;
    }

    goTo(url) {
      var isTabBar = this.tabBarPages.some(function(page) {
        return page === url || page === String(url || '').replace('/', '') || ('/' + page) === url;
      });
      var options = {
        url: String(url || '').startsWith('/') ? url : '/' + url,
        success: function() {},
        fail: function() {}
      };
      if (isTabBar) {
        this.wxFrame.wx.switchTab(options);
      } else {
        this._getNav('navigateTo').call(this.wxFrame.wx, options);
      }
    }

    _safeNavigate(pageUrl) {
      var self = this;
      return new Promise(function(resolve) {
        var url = String(pageUrl || '').startsWith('/') ? pageUrl : '/' + pageUrl;
        self._getNav('reLaunch').call(self.wxFrame.wx, {
          url: url,
          success: function() { resolve(true); },
          fail: function() {
            self.wxFrame.wx.switchTab({
              url: url,
              success: function() { resolve(true); },
              fail: function() {
                self._getNav('redirectTo').call(self.wxFrame.wx, {
                  url: url,
                  success: function() { resolve(true); },
                  fail: function() { resolve(false); }
                });
              }
            });
          }
        });
      });
    }

    back(delta) {
      this.wxFrame.wx.navigateBack({
        delta: delta || 1,
        success: function() {},
        fail: function() {}
      });
    }

    current() {
      try {
        var getPages = null;
        if (this.wxFrame && typeof this.wxFrame.getCurrentPages === 'function') {
          getPages = this.wxFrame.getCurrentPages.bind(this.wxFrame);
        } else if (typeof getCurrentPages === 'function') {
          getPages = getCurrentPages;
        }
        var pages = getPages ? getPages() : [];
        if (pages && pages.length > 0) {
          var cur = pages[pages.length - 1];
          return cur.route || cur.__route__ || '';
        }
      } catch (e) {}
      return '';
    }

    _safeClone(value) {
      if (value === undefined) return undefined;
      if (value === null) return null;
      try {
        return JSON.parse(JSON.stringify(value));
      } catch (e) {
        try { return String(value); } catch (err) { return '[unserializable]'; }
      }
    }

    _requestRoute() {
      try { return this.current() || ''; } catch (e) { return ''; }
    }

    _pushCapturedRequest(record) {
      this._capturedRequests.push(record);
      var overflow = this._capturedRequests.length - this._requestCaptureLimit;
      if (overflow > 0) this._capturedRequests.splice(0, overflow);
    }

    _extractPath(url) {
      if (!this._pathCache) this._pathCache = {};
      if (this._pathCache[url]) return this._pathCache[url];
      var path;
      try { path = new URL(url).pathname; } catch (e) { path = String(url || '').split('?')[0]; }
      this._pathCache[url] = path;
      return path;
    }

    _installHook() {
      if (this._hooked) return true;
      if (!this.wxFrame || !this.wxFrame.wx) return false;
      var wxApi = this.wxFrame.wx;
      var self = this;
      var methods = ['request', 'uploadFile', 'downloadFile'];
      this._originalMethods = {};

      methods.forEach(function(method) {
        if (!wxApi[method]) return;
        self._originalMethods[method] = wxApi[method];
        wxApi[method] = function(options) {
          options = options || {};
          var reqMethod = (options.method || (method === 'request' ? 'GET' : method)).toUpperCase();
          var url = options.url || '';
          var apiInfo = {
            url: url,
            method: reqMethod,
            timestamp: new Date().toLocaleTimeString(),
            type: method
          };
          self._capturedAPIs.push(apiInfo);
          var dedupeKey = reqMethod + '|' + self._extractPath(url);
          if (!self._globalAPISet.has(dedupeKey)) {
            self._globalAPISet.add(dedupeKey);
            self._globalAPIs.push(apiInfo);
          }

          if (self._customHeaders && Object.keys(self._customHeaders).length > 0) {
            options.header = options.header || {};
            Object.keys(self._customHeaders).forEach(function(headerKey) {
              options.header[headerKey] = self._customHeaders[headerKey];
            });
          }

          var record = null;
          if (self._captureEnabled) {
            record = {
              id: ++self._captureSeq,
              time: new Date().toISOString(),
              route: self._requestRoute(),
              type: method,
              method: reqMethod,
              url: url,
              data: self._safeClone(options.data !== undefined ? options.data : options.formData),
              header: self._safeClone(options.header || {}),
              response: null,
              status: 'pending',
              stack: (new Error()).stack || ''
            };
            self._pushCapturedRequest(record);
          }

          var originalSuccess = options.success;
          var originalFail = options.fail;
          var originalComplete = options.complete;
          options.success = function(res) {
            if (record) {
              record.status = 'success';
              record.response = self._safeClone(res);
              record.statusCode = res && res.statusCode;
              record.endTime = new Date().toISOString();
            }
            if (typeof originalSuccess === 'function') return originalSuccess.apply(this, arguments);
          };
          options.fail = function(err) {
            if (record) {
              record.status = 'fail';
              record.response = self._safeClone(err);
              record.endTime = new Date().toISOString();
            }
            if (typeof originalFail === 'function') return originalFail.apply(this, arguments);
          };
          options.complete = function(res) {
            if (record) {
              if (record.status === 'pending') {
                record.status = 'complete';
                record.response = self._safeClone(res);
                record.statusCode = res && res.statusCode;
              }
              record.completeTime = new Date().toISOString();
            }
            if (typeof originalComplete === 'function') return originalComplete.apply(this, arguments);
          };
          return self._originalMethods[method].call(wxApi, options);
        };
      });

      this._hooked = Object.keys(this._originalMethods).length > 0;
      return this._hooked;
    }

    _uninstallHook() {
      if (!this._hooked || !this.wxFrame || !this.wxFrame.wx) return;
      var wxApi = this.wxFrame.wx;
      var self = this;
      Object.keys(this._originalMethods).forEach(function(method) {
        wxApi[method] = self._originalMethods[method];
      });
      this._hooked = false;
    }

    startCapture() {
      if (!this._installHook()) {
        return { ok: false, error: 'wx request APIs unavailable' };
      }
      this._captureEnabled = true;
      return {
        ok: true,
        enabled: true,
        hooked: !!this._hooked,
        target: (typeof wx !== 'undefined' && typeof getCurrentPages !== 'undefined') ? 'appservice' : 'webview'
      };
    }

    stopCapture() {
      this._captureEnabled = false;
      return { ok: true, enabled: false, hooked: !!this._hooked };
    }

    getCapturedRequests(limit) {
      var rows = this._capturedRequests || [];
      var n = parseInt(limit || 0, 10);
      if (n > 0) return rows.slice(-n);
      return rows.slice();
    }

    clearCapturedRequests() {
      this._capturedRequests = [];
      return { ok: true };
    }

    getAPIs() {
      return this._globalAPIs || [];
    }

    getResults() {
      return this._autoVisitResults || {};
    }

    getRuntimeState() {
      var cfg = (this.wxFrame && this.wxFrame.__wxConfig) || root.__wxConfig || {};
      var accountInfo = cfg.accountInfo || {};
      return {
        ok: !!this.wxFrame,
        hasWindow: typeof window !== 'undefined',
        hasGlobalThis: typeof globalThis !== 'undefined',
        hasWx: typeof wx !== 'undefined',
        hasGetCurrentPages: typeof getCurrentPages !== 'undefined',
        hasNav: true,
        hasWxFrame: !!this.wxFrame,
        hooked: !!this._hooked,
        captureEnabled: !!this._captureEnabled,
        capturedCount: (this._capturedRequests || []).length,
        route: this.current(),
        appid: cfg.appid || cfg.appId || accountInfo.appId || accountInfo.appid || '',
        contextType: (typeof wx !== 'undefined' && typeof getCurrentPages !== 'undefined') ? 'appservice' : 'webview'
      };
    }

    enableRedirectGuard() {
      if (this._redirectGuard) return { ok: true, already: true };
      this._redirectGuard = true;
      this._blockedRedirects = [];
      var wxApi = this.wxFrame.wx;
      var self = this;
      this._origRedirectTo = wxApi.redirectTo;
      this._origReLaunch = wxApi.reLaunch;
      this._origNavigateTo = wxApi.navigateTo;

      wxApi.redirectTo = function(options) {
        var url = (options && options.url) || '';
        self._blockedRedirects.push({ type: 'redirectTo', url: url, time: new Date().toLocaleTimeString() });
        if (options && options.success) options.success({ errMsg: 'redirectTo:ok' });
        if (options && options.complete) options.complete({ errMsg: 'redirectTo:ok' });
      };
      wxApi.reLaunch = function(options) {
        var url = (options && options.url) || '';
        self._blockedRedirects.push({ type: 'reLaunch', url: url, time: new Date().toLocaleTimeString() });
        if (options && options.success) options.success({ errMsg: 'reLaunch:ok' });
        if (options && options.complete) options.complete({ errMsg: 'reLaunch:ok' });
      };
      wxApi.navigateTo = function(options) {
        var url = (options && options.url) || '';
        self._blockedRedirects.push({ type: 'navigateTo', url: url, time: new Date().toLocaleTimeString() });
        if (options && options.success) options.success({ errMsg: 'navigateTo:ok' });
        if (options && options.complete) options.complete({ errMsg: 'navigateTo:ok' });
      };
      return { ok: true };
    }

    disableRedirectGuard() {
      if (!this._redirectGuard) return;
      this._redirectGuard = false;
      var wxApi = this.wxFrame.wx;
      if (this._origRedirectTo) wxApi.redirectTo = this._origRedirectTo;
      if (this._origReLaunch) wxApi.reLaunch = this._origReLaunch;
      if (this._origNavigateTo) wxApi.navigateTo = this._origNavigateTo;
      this._origRedirectTo = null;
      this._origReLaunch = null;
      this._origNavigateTo = null;
    }

    getBlockedRedirects() {
      return this._blockedRedirects || [];
    }

    isRedirectGuardOn() {
      return !!this._redirectGuard;
    }
  }

  try {
    root.nav = new UniversalMiniProgramNavigator();
    if (typeof window !== 'undefined') window.nav = root.nav;
  } catch (e) {
    console.error('Navigator init failed:', e.message);
  }
})();
