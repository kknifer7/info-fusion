import { Module } from '@nestjs/common';
import { HttpModule } from '@nestjs/axios';
import { PushScheduleService } from './push-schedule.service';
import { PushScheduleController } from './push-schedule.controller';
import { PrismaModule } from '../prisma.module';
import { CrawlerModule } from '../crawler/crawler.module';
import { OpenAIModule } from 'src/openai/openai.module';

@Module({
  imports: [PrismaModule, CrawlerModule, HttpModule, OpenAIModule],
  controllers: [PushScheduleController],
  providers: [PushScheduleService],
})
export class PushScheduleModule {}
