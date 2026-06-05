import { Module } from '@nestjs/common';
import { CrawlerService } from './crawler.service';
import { PrismaModule } from '../prisma.module';

@Module({
  imports: [PrismaModule],
  providers: [CrawlerService],
  exports: [CrawlerService],
})
export class CrawlerModule {}
