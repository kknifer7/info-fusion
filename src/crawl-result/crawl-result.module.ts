import { Module } from '@nestjs/common';
import { CrawlResultService } from './crawl-result.service';
import { CrawlResultController } from './crawl-result.controller';
import { PrismaModule } from '../prisma.module';

@Module({
  controllers: [CrawlResultController],
  providers: [CrawlResultService],
  imports: [PrismaModule],
})
export class CrawlResultModule {}
