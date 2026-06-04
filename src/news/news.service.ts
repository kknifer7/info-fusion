import { Injectable, Logger } from '@nestjs/common';
import { createHash } from 'crypto';
import { PrismaService } from '../prisma.service';
import { CreateNewsDto } from './dto/create-news.dto';
import { Cron } from '@nestjs/schedule';
import { OpenAIService } from '../openai/openai.service';
import { NewsNature } from '../generated/prisma/enums';
import { getBeijingDayRange } from '../utils/beijing-time';

@Injectable()
export class NewsService {
  private readonly logger = new Logger(NewsService.name);
  private static readonly VALID_PRIORITIES = new Set([-1, 0, 1, 2]);

  constructor(
    private prisma: PrismaService,
    private openAIService: OpenAIService,
  ) {}

  async create(data: CreateNewsDto) {
    if (!data.content || data.content.length < 1) {
      this.logger.warn(
        `data.content is null or empty, can not create. data=${JSON.stringify(data)}`,
      );

      return;
    }

    const contentMd5 = createHash('md5').update(data.content).digest('hex');
    const existing = await this.prisma.news.findUnique({
      where: { contentMd5 },
    });
    if (existing) {
      this.logger.log(
        `news already exists with contentMd5=${contentMd5}, skip creating`,
      );

      return;
    }

    const news = await this.prisma.news.create({
      data: {
        ...data,
        publishDateTime: new Date(data.publishDateTime),
        contentMd5,
      },
    });
    this.logger.log(`news created: ${JSON.stringify(news)}`);
  }

  async batchChatForNewsPriority() {
    const systemPrompt = await this.prisma.config.findUnique({
      where: {
        key: 'OPEN_AI_NEWS_PRIORITY_SYSTEM_PROMPT',
      },
    });
    if (!systemPrompt || !systemPrompt.val) {
      this.logger.warn(
        'no OPEN_AI_NEWS_PRIORITY_SYSTEM_PROMPT, can not execute batchCharForNewsPriority',
      );
      return;
    }

    const { gte: yesterdayStart } = getBeijingDayRange(-1);
    const { lt: tomorrow } = getBeijingDayRange(0);
    const newsList = await this.prisma.news.findMany({
      where: {
        disabled: false,
        priority: null,
        publishDateTime: {
          gte: yesterdayStart,
          lt: tomorrow,
        },
      },
      take: 10,
    });
    if (newsList.length < 1) {
      this.logger.log('no news need to chat priority, skip.');
      return;
    }

    const userContent = newsList
      .map((n, i) => `${i + 1}. ${n.title}\n${n.content}`)
      .join('\n---\n');

    const completionBody = `${systemPrompt.val}::${userContent}`;

    let llmResponse: string | null = null;
    try {
      llmResponse = await this.openAIService.chat(
        systemPrompt.val,
        userContent,
      );
    } catch (e) {
      const errMsg = e instanceof Error ? e.message : String(e);
      this.logger.warn(`LLM chat failed: ${errMsg}`);
      await this.prisma.lLMChatResult.create({
        data: {
          newsIds: newsList.map((n) => n.id).join(','),
          completionBody,
          message: '',
        },
      });
      return;
    }

    if (!llmResponse) {
      this.logger.warn('LLM returned empty response, skip.');
      await this.prisma.lLMChatResult.create({
        data: {
          newsIds: newsList.map((n) => n.id).join(','),
          completionBody,
          message: '',
        },
      });
      return;
    }

    let parsed: number[] = [];
    let parseError: string | null = null;
    try {
      const jsonMatch = llmResponse.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
      const jsonStr = jsonMatch ? jsonMatch[1].trim() : llmResponse.trim();
      parsed = JSON.parse(jsonStr) as number[];
    } catch (e) {
      parseError = e instanceof Error ? e.message : String(e);
    }

    if (
      parseError ||
      !Array.isArray(parsed) ||
      parsed.length !== newsList.length
    ) {
      this.logger.warn(
        `failed to parse LLM response: ${parseError}, raw=${llmResponse}`,
      );
      await this.prisma.lLMChatResult.create({
        data: {
          newsIds: newsList.map((n) => n.id).join(','),
          completionBody,
          message: llmResponse,
        },
      });
      return;
    }

    for (let i = 0; i < parsed.length; i++) {
      const priority = parsed[i];
      if (
        typeof priority === 'number' &&
        NewsService.VALID_PRIORITIES.has(priority)
      ) {
        try {
          await this.prisma.news.update({
            where: { id: newsList[i].id },
            data: { priority },
          });
        } catch (e) {
          const errMsg = e instanceof Error ? e.message : String(e);
          this.logger.error(
            `failed to update news ${newsList[i].id}: ${errMsg}`,
          );
        }
      } else {
        this.logger.warn(
          `invalid priority value for news ${newsList[i].id}: ${priority}`,
        );
      }
    }

    await this.prisma.lLMChatResult.create({
      data: {
        newsIds: newsList.map((n) => n.id).join(','),
        completionBody,
        message: llmResponse,
      },
    });

    this.logger.log(
      `batchCharForNewsPriority completed, processed ${newsList.length} news`,
    );
  }

  async batchChatForNewsNature() {
    const systemPrompt = await this.prisma.config.findUnique({
      where: {
        key: 'OPEN_AI_NEWS_NATURE_SYSTEM_PROMPT',
      },
    });
    if (!systemPrompt || !systemPrompt.val) {
      this.logger.warn(
        'no OPEN_AI_NEWS_NATURE_SYSTEM_PROMPT, can not execute batchChatForNewsNature',
      );
      return;
    }

    const { gte: yesterdayStart } = getBeijingDayRange(-1);
    const { lt: tomorrow } = getBeijingDayRange(0);
    const newsList = await this.prisma.news.findMany({
      where: {
        disabled: false,
        nature: null,
        publishDateTime: {
          gte: yesterdayStart,
          lt: tomorrow,
        },
      },
      take: 10,
    });
    if (newsList.length < 1) {
      this.logger.log('no news need to chat nature, skip.');
      return;
    }

    const userContent = newsList
      .map((n, i) => `${i + 1}. ${n.title}\n${n.content}`)
      .join('\n---\n');

    const completionBody = `${systemPrompt.val}::${userContent}`;

    let llmResponse: string | null = null;
    try {
      llmResponse = await this.openAIService.chat(
        systemPrompt.val,
        userContent,
      );
    } catch (e) {
      const errMsg = e instanceof Error ? e.message : String(e);
      this.logger.warn(`LLM chat failed: ${errMsg}`);
      await this.prisma.lLMChatResult.create({
        data: {
          newsIds: newsList.map((n) => n.id).join(','),
          completionBody,
          message: '',
        },
      });
      return;
    }

    if (!llmResponse) {
      this.logger.warn('LLM returned empty response, skip.');
      await this.prisma.lLMChatResult.create({
        data: {
          newsIds: newsList.map((n) => n.id).join(','),
          completionBody,
          message: '',
        },
      });
      return;
    }

    let parsed: NewsNature[] = [];
    let parseError: string | null = null;
    try {
      const jsonMatch = llmResponse.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
      const jsonStr = jsonMatch ? jsonMatch[1].trim() : llmResponse.trim();
      parsed = JSON.parse(jsonStr) as NewsNature[];
    } catch (e) {
      parseError = e instanceof Error ? e.message : String(e);
    }

    if (
      parseError ||
      !Array.isArray(parsed) ||
      parsed.length !== newsList.length
    ) {
      this.logger.warn(
        `failed to parse LLM response: ${parseError}, raw=${llmResponse}`,
      );
      await this.prisma.lLMChatResult.create({
        data: {
          newsIds: newsList.map((n) => n.id).join(','),
          completionBody,
          message: llmResponse,
        },
      });
      return;
    }

    for (let i = 0; i < parsed.length; i++) {
      const nature: unknown = parsed[i];
      if (nature === NewsNature.DOM || nature === NewsNature.INTL) {
        try {
          await this.prisma.news.update({
            where: { id: newsList[i].id },
            data: { nature },
          });
        } catch (e) {
          const errMsg = e instanceof Error ? e.message : String(e);
          this.logger.error(
            `failed to update news ${newsList[i].id}: ${errMsg}`,
          );
        }
      } else {
        this.logger.warn(
          `invalid nature value for news ${newsList[i].id}: ${String(nature)}`,
        );
      }
    }

    await this.prisma.lLMChatResult.create({
      data: {
        newsIds: newsList.map((n) => n.id).join(','),
        completionBody,
        message: llmResponse,
      },
    });

    this.logger.log(
      `batchChatForNewsNature completed, processed ${newsList.length} news`,
    );
  }

  @Cron('0 0/2 * * * *')
  async batchChatForNews() {
    this.logger.log('--- batchChatForNews started ---');
    await this.batchChatForNewsPriority();
    await this.batchChatForNewsNature();
    this.logger.log('--- batchChatForNews completed ---');
  }
}
