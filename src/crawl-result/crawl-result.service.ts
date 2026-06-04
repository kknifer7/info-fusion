import { Injectable, Logger } from '@nestjs/common';
import { PrismaService } from '../prisma.service';
import { CreateCrawlResultDto } from './dto/create-crawl-result.dto';

@Injectable()
export class CrawlResultService {
  private readonly logger = new Logger(CrawlResultService.name);

  constructor(private prisma: PrismaService) {}

  async create(data: CreateCrawlResultDto) {
    const crawler = await this.prisma.crawler.findFirst({
      where: {
        id: data.crawlerId,
      },
    });

    if (!crawler) {
      this.logger.log(`crawler not found, id=${data.crawlerId}`);

      return;
    }

    return this.prisma.crawlResult.create({ data });
  }
}
