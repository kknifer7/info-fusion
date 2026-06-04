import { Controller, Post, Body } from '@nestjs/common';
import { CrawlResultService } from './crawl-result.service';
import { CreateCrawlResultDto } from './dto/create-crawl-result.dto';

@Controller('crawl-result')
export class CrawlResultController {
  constructor(private readonly crawlResultService: CrawlResultService) {}

  @Post()
  async create(@Body() data: CreateCrawlResultDto) {
    await this.crawlResultService.create(data);

    return '';
  }
}
