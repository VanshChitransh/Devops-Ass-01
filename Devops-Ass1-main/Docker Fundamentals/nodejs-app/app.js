const http = require('http');

const LISTEN_PORT = 3000;

const webServer = http.createServer((_incoming, reply) => {
  reply.writeHead(200, { 'Content-Type': 'text/html' });
  reply.end("<h1>Hello World from Vansh's Node.js app!</h1>");
});

webServer.listen(LISTEN_PORT, () => {
  console.log(`Node.js app listening on port ${LISTEN_PORT}`);
});
