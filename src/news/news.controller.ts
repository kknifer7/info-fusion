import { Controller, Post, Body } from '@nestjs/common';
import { NewsService } from './news.service';
import type { NewsCreateInput } from '../generated/prisma/models';

@Controller('news')
export class NewsController {
  constructor(private readonly newsService: NewsService) {}

  @Post()
  async create(@Body() data: NewsCreateInput) {
    await this.newsService.create(data);

    return '';
  }
}
