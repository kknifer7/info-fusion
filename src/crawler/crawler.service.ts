import { Injectable, Logger } from '@nestjs/common';
import { exec } from 'child_process';
import { promisify } from 'util';
import { Crawler } from '../generated/prisma/client';
import { PrismaService } from '../prisma.service';
import { Cron } from '@nestjs/schedule';

const execAsync = promisify(exec);

@Injectable()
export class CrawlerService {
  private readonly logger = new Logger(CrawlerService.name);

  constructor(private prisma: PrismaService) {}

  // @Cron('0 0/30 * * * *')
  async doCrawling() {
    const crawlers = await this.prisma.crawler.findMany({
      where: {
        disabled: false,
      },
    });

    await Promise.all(crawlers.map((crawler) => this.crawl(crawler)));
  }

  async crawl(crawler: Crawler) {
    try {
      await execAsync(`${crawler.cmdPrefix} ${crawler.scriptPath}`);
      this.logger.log(`crawler ${crawler.id} finished`);
    } catch (error) {
      this.logger.error(`crawler ${crawler.id} failed: ${error}`);
      throw error;
    }
  }
}
