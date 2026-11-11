// -*- coding: utf-8 -*-
// MediaCrawler Node.js Signature Microservice
// Zero external dependencies - uses Node.js standard library

const http = require('http');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

// 1. Polyfill minimal browser environment if needed by JS libraries
global.window = global;
global.document = {
    referrer: '',
    cookie: '',
    querySelector: () => null
};
global.navigator = {
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
};

// 2. Load libs/douyin.js into memory using vm.runInThisContext
const douyinJsPath = path.resolve(__dirname, '../../libs/douyin.js');
let douyinLoaded = false;

try {
    const douyinCode = fs.readFileSync(douyinJsPath, 'utf-8');
    vm.runInThisContext(douyinCode);
    if (typeof sign_datail === 'function') {
        global.sign_datail = sign_datail;
    }
    if (typeof sign_reply === 'function') {
        global.sign_reply = sign_reply;
    }
    douyinLoaded = (typeof global.sign_datail === 'function');
    console.log(`[SignService] Loaded douyin.js successfully from ${douyinJsPath}`);
} catch (err) {
    console.error(`[SignService] Failed to load douyin.js: ${err.message}`);
}

const PORT = parseInt(process.env.PORT, 10) || 8999;
const HOST = process.env.HOST || '127.0.0.1';

// 3. HTTP Server
const server = http.createServer((req, res) => {
    // Enable CORS for flexibility
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        res.writeHead(204);
        res.end();
        return;
    }

    const reqUrl = req.url ? req.url.split('?')[0] : '/';

    // Health check endpoint
    if (req.method === 'GET' && (reqUrl === '/health' || reqUrl === '/status' || reqUrl === '/')) {
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({
            status: 'ok',
            service: 'MediaCrawler-Sign-Service',
            douyin_loaded: douyinLoaded,
            timestamp: Date.now()
        }));
        return;
    }

    // Douyin signature endpoint: /sign or /sign/douyin
    if (req.method === 'POST' && (reqUrl === '/sign' || reqUrl === '/sign/douyin')) {
        let body = '';
        req.on('data', chunk => {
            body += chunk;
        });

        req.on('end', () => {
            try {
                const data = JSON.parse(body || '{}');
                const url = data.url || '';
                const params = data.params || '';
                const userAgent = data.user_agent || data.userAgent || global.navigator.userAgent;

                if (!douyinLoaded) {
                    res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
                    res.end(JSON.stringify({ code: -1, error: 'douyin.js is not loaded' }));
                    return;
                }

                const signFunc = (typeof url === 'string' && url.includes('/reply')) ? global.sign_reply : global.sign_datail;
                if (typeof signFunc !== 'function') {
                    res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
                    res.end(JSON.stringify({ code: -1, error: 'sign function not found in loaded JS' }));
                    return;
                }

                const a_bogus = signFunc(params, userAgent);
                res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
                res.end(JSON.stringify({
                    code: 0,
                    a_bogus: a_bogus
                }));
            } catch (err) {
                res.writeHead(400, { 'Content-Type': 'application/json; charset=utf-8' });
                res.end(JSON.stringify({ code: 1, error: err.message }));
            }
        });
        return;
    }

    // 404 for other endpoints
    res.writeHead(404, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({ code: 404, error: 'Not Found' }));
});

server.listen(PORT, HOST, () => {
    console.log(`[SignService] Signature microservice listening on http://${HOST}:${PORT}`);
});
