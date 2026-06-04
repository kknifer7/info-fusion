import { Module } from '@nestjs/common';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { NewsModule } from './news/news.module';
import { ConfigModule } from '@nestjs/config';
import { CrawlerModule } from './crawler/crawler.module';
import { ScheduleModule } from '@nestjs/schedule';
import { PushScheduleModule } from './push-schedule/push-schedule.module';
import { OpenAIModule } from './openai/openai.module';
import { CrawlResultModule } from './crawl-result/crawl-result.module';

@Module({
  imports: [
    ConfigModule.forRoot({
      envFilePath:
        process.env['NODE_ENV'] === 'production'
          ? 'env/.env.prod'
          : 'env/.env.dev',
      isGlobal: true,
    }),
    ScheduleModule.forRoot(),
    NewsModule,
    CrawlerModule,
    PushScheduleModule,
    OpenAIModule,
    CrawlResultModule,
  ],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
