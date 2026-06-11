import { Injectable, Logger } from '@nestjs/common';
import { Cron, SchedulerRegistry } from '@nestjs/schedule';
import { CronJob } from 'cron';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';
import { PrismaService } from '../prisma.service';
import {
  NewsNature,
  NewsType,
  PushSchedule,
} from '../generated/prisma/browser';
import { deepEqual } from 'fast-equals';
import { OpenAIService } from '../openai/openai.service';
import { getBeijingDayRange } from '../utils/beijing-time';

@Injectable()
export class PushScheduleService {
  private readonly logger = new Logger(PushScheduleService.name);
  private pushSchedules = new Map<number, PushSchedule>();
  private static readonly PushScheduleTaskNamePrefix = 'push-schedule-';

  constructor(
    private prisma: PrismaService,
    private scheduleRegistry: SchedulerRegistry,
    private httpService: HttpService,
    private openAI: OpenAIService,
  ) {}

  @Cron('0 * * * * *')
  async handleScheduleTaskCron() {
    const schedules = await this.prisma.pushSchedule.findMany();
    const currentIds = new Set(schedules.map((s) => s.id));

    for (const [id] of this.pushSchedules) {
      if (!currentIds.has(id)) {
        this.removeCronJob(id);
        this.pushSchedules.delete(id);
        this.logger.log(`removed scheduleId: ${id}`);
      }
    }
    for (const schedule of schedules) {
      const oldSchedule = this.pushSchedules.get(schedule.id);

      if (oldSchedule) {
        if (deepEqual(oldSchedule, schedule)) {
          continue;
        }
        if (this.removeCronJob(schedule.id)) {
          this.logger.log(`unregistered scheduleId: ${schedule.id}`);
        }
      }
      this.pushSchedules.set(schedule.id, schedule);
      if (!schedule.disabled) {
        this.addCronJob(schedule);
        this.logger.log(`registered scheduleId: ${schedule.id}`);
      }
    }
  }

  private addCronJob(schedule: PushSchedule) {
    const name = `${PushScheduleService.PushScheduleTaskNamePrefix}${schedule.id}`;
    const job = CronJob.from({
      cronTime: schedule.cron,
      onTick: async () => {
        const newsContent = await this.chatForNewsList();

        if (!newsContent) {
          return;
        }
        void this.executePush(newsContent, schedule);
      },
    });

    this.scheduleRegistry.addCronJob(name, job);
    job.start();
  }

  private removeCronJob(scheduleId: number): boolean {
    const name = `${PushScheduleService.PushScheduleTaskNamePrefix}${scheduleId}`;

    if (this.scheduleRegistry.doesExist('cron', name)) {
      const job = this.scheduleRegistry.getCronJob(name);

      void job.stop();
      this.scheduleRegistry.deleteCronJob(name);
      return true;
    }
    return false;
  }

  private async chatForNewsList() {
    const { gte: yesterdayStart, lt: yesterdayEnd } = getBeijingDayRange(-1);
    const { lt: tomorrow } = getBeijingDayRange(0);

    const newsList = await this.prisma.news.findMany({
      where: {
        disabled: false,
        nature: NewsNature.DOM,
        priority: {
          gt: -1,
        },
        OR: [
          {
            publishDateTime: {
              gte: yesterdayStart,
              lt: tomorrow,
            },
            newsType: NewsType.Rolling,
          },
          {
            publishDateTime: {
              gt: yesterdayEnd,
              lt: tomorrow,
            },
            newsType: NewsType.Paper,
          },
        ],
      },
      orderBy: {
        priority: 'desc',
      },
      take: 40,
    });
    const intlNewsList = await this.prisma.news.findMany({
      where: {
        disabled: false,
        nature: NewsNature.INTL,
        priority: {
          gte: -1,
        },
        OR: [
          {
            publishDateTime: {
              gte: yesterdayStart,
              lt: tomorrow,
            },
            newsType: NewsType.Rolling,
          },
          {
            publishDateTime: {
              gt: yesterdayEnd,
              lt: tomorrow,
            },
            newsType: NewsType.Paper,
          },
        ],
      },
      orderBy: {
        priority: 'desc',
      },
      take: 10,
    });
    newsList.push(...intlNewsList);
    const newsIds: number[] = [];
    if (newsList.length === 0) {
      this.logger.warn('no news found for today');

      return;
    }

    const systemPromptConfig = await this.prisma.config.findUnique({
      where: {
        key: 'OPEN_AI_PUSH_SYSTEM_PROMPT',
      },
    });
    if (!systemPromptConfig || !systemPromptConfig.val) {
      this.logger.warn('no OPEN_AI_PUSH_SYSTEM_PROMPT config, can not chat');

      return;
    }

    const newsForChat = newsList.map((news) => {
      newsIds.push(news.id);

      return {
        content: news.content,
        nature: news.nature,
      };
    });
    const userContent = JSON.stringify(newsForChat);
    const chatMessage = await this.openAI.chat(
      systemPromptConfig.val,
      userContent,
    );
    await this.prisma.lLMChatResult.create({
      data: {
        newsIds: newsIds.join(','),
        completionBody: `${systemPromptConfig.val}::${userContent}`,
        message: chatMessage,
      },
    });
    if (chatMessage) {
      await this.prisma.news.updateMany({
        data: {
          disabled: true,
        },
        where: {
          id: {
            in: newsIds,
          },
        },
      });
    }

    return chatMessage;
  }

  private async executePush(content: string, schedule: PushSchedule) {
    this.logger.log(`executing push scheduleId: ${schedule.id}`);

    const config = await this.prisma.config.findUnique({
      where: { key: 'PUSH_PLUS_TOKEN' },
    });
    if (!config) {
      this.logger.warn('PUSH_PLUS_TOKEN not found in config');

      return;
    }

    const payload: Record<string, unknown> = {
      token: config.val,
      title: '每日新闻推送',
      content,
      template: 'txt',
    };
    if (schedule.to) {
      payload.to = schedule.to;
    }
    this.logger.log(`push payload: ${JSON.stringify(payload)}`);

    let resultCode = 500;
    try {
      const response = await firstValueFrom(
        this.httpService.post<{ code?: number; msg?: string }>(
          'http://www.pushplus.plus/send',
          payload,
        ),
      );
      resultCode = response.data?.code ?? response.status;
      this.logger.log(
        `push result: scheduleId=${schedule.id}, code=${resultCode}, data=${JSON.stringify(response.data)}`,
      );
    } catch (error) {
      this.logger.error(`push failed: ${error}`);
      if (error instanceof Error && 'response' in error) {
        const errWithResponse = error as {
          response?: { status?: number; data?: unknown };
        };
        this.logger.error(
          `push error response: ${JSON.stringify(errWithResponse.response?.data)}`,
        );
        resultCode = errWithResponse.response?.status ?? 500;
      }
    }

    await this.prisma.pushResult.create({
      data: {
        scheduleId: schedule.id,
        content,
        to: schedule.to,
        resultCode,
      },
    });
  }
}
