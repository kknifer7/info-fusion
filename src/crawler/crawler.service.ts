import { Injectable, Logger } from '@nestjs/common';
import { exec } from 'child_process';
import { promisify } from 'util';
import { Crawler } from '../generated/prisma/client';
import { PrismaService } from '../prisma.service';
import { Cron, SchedulerRegistry } from '@nestjs/schedule';
import { CronJob } from 'cron';
import { deepEqual } from 'fast-equals';

const execAsync = promisify(exec);

@Injectable()
export class CrawlerService {
  private readonly logger = new Logger(CrawlerService.name);
  private crawlers = new Map<number, Crawler>();
  private static readonly CrawlerTaskNamePrefix = 'crawler-';

  constructor(
    private prisma: PrismaService,
    private scheduleRegistry: SchedulerRegistry,
  ) {}

  @Cron('0 * * * * *')
  async handleCrawlerTaskCron() {
    const crawlers = await this.prisma.crawler.findMany();
    const currentIds = new Set(crawlers.map((c) => c.id));

    for (const [id] of this.crawlers) {
      if (!currentIds.has(id)) {
        this.removeCronJob(id);
        this.crawlers.delete(id);
        this.logger.log(`removed crawlerId: ${id}`);
      }
    }
    for (const crawler of crawlers) {
      const oldCrawler = this.crawlers.get(crawler.id);

      if (oldCrawler) {
        if (deepEqual(oldCrawler, crawler)) {
          continue;
        }
        if (this.removeCronJob(crawler.id)) {
          this.logger.log(`unregistered crawlerId: ${crawler.id}`);
        }
      }
      this.crawlers.set(crawler.id, crawler);
      if (!crawler.disabled) {
        this.addCronJob(crawler);
        this.logger.log(`registered crawlerId: ${crawler.id}`);
      }
    }
  }

  private addCronJob(crawler: Crawler) {
    const name = `${CrawlerService.CrawlerTaskNamePrefix}${crawler.id}`;
    const job = CronJob.from({
      cronTime: crawler.cron,
      onTick: async () => {
        await this.crawl(crawler);
      },
    });

    this.scheduleRegistry.addCronJob(name, job);
    job.start();
  }

  private removeCronJob(crawlerId: number): boolean {
    const name = `${CrawlerService.CrawlerTaskNamePrefix}${crawlerId}`;

    if (this.scheduleRegistry.doesExist('cron', name)) {
      const job = this.scheduleRegistry.getCronJob(name);

      void job.stop();
      this.scheduleRegistry.deleteCronJob(name);
      return true;
    }
    return false;
  }

  async crawl(crawler: Crawler) {
    try {
      await execAsync(`${crawler.cmdPrefix} ${crawler.scriptPath}`);
      this.logger.log(`crawler ${crawler.id} finished`);
    } catch (error) {
      this.logger.error(`crawler ${crawler.id} failed: ${error}`);
    }
  }
}
