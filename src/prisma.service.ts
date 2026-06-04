import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { PrismaClient } from './generated/prisma/client';
import { PrismaBetterSqlite3 } from '@prisma/adapter-better-sqlite3';

@Injectable()
export class PrismaService extends PrismaClient {
  constructor(config: ConfigService) {
    const dbUrl =
      config.get<string>('DATABASE_URL') ||
      (process.env['NODE_ENV'] === 'production'
        ? 'file:./prod.db'
        : 'file:./dev.db');
    const adapter = new PrismaBetterSqlite3({ url: dbUrl });
    super({ adapter });
  }
}
