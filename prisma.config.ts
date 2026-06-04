import { defineConfig } from 'prisma/config';

const dbFile =
  process.env['DATABASE_URL'] ||
  (process.env['NODE_ENV'] === 'production'
    ? 'file:./prod.db'
    : 'file:./dev.db');

export default defineConfig({
  schema: 'prisma/schema.prisma',
  migrations: {
    path: 'prisma/migrations',
  },
  datasource: {
    url: dbFile,
  },
});
