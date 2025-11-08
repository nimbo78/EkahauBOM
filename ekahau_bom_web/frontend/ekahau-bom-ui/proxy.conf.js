const PROXY_CONFIG = {
  "/api": {
    target: "http://localhost:8001",
    secure: false,
    changeOrigin: true,
    ws: true,
    configure: (proxy, options) => {
      // Set timeouts to 10 minutes (600000 ms)
      proxy.on('proxyReq', (proxyReq, req, res) => {
        console.log('[Proxy] Proxying request:', req.method, req.url);
        // Set socket timeout
        proxyReq.setTimeout(600000);
      });

      proxy.on('proxyRes', (proxyRes, req, res) => {
        console.log('[Proxy] Response status:', proxyRes.statusCode, 'for', req.url);
        // Set socket timeout
        res.setTimeout(600000);
      });

      proxy.on('error', (err, req, res) => {
        console.error('[Proxy] Error:', err.message);
      });
    }
  }
};

module.exports = PROXY_CONFIG;
