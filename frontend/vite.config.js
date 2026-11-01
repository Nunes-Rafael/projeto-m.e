import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react(), {
    name: 'health-endpoint',
    configureServer(server) {
      server.middlewares.use('/health', (_request, response) => {
        response.setHeader('content-type', 'application/json');
        response.end(JSON.stringify({ status: 'ok' }));
      });
    },
  }],
});
