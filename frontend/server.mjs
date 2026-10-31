import { createServer } from "node:http";

const port = 5173;

createServer((request, response) => {
  if (request.url === "/health") {
    response.writeHead(200, { "content-type": "application/json" });
    response.end(JSON.stringify({ status: "ok" }));
    return;
  }

  response.writeHead(200, { "content-type": "text/html; charset=utf-8" });
  response.end("<!doctype html><title>Purchase Agent</title><main>Frontend scaffold</main>");
}).listen(port, "0.0.0.0");
