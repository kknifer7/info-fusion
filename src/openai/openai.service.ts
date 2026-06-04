import { Injectable } from '@nestjs/common';
import OpenAI from 'openai';

@Injectable()
export class OpenAIService {
  private readonly client: OpenAI;

  constructor() {
    this.client = new OpenAI({
      apiKey: process.env['DEEPSEEK_API_KEY'],
      baseURL: 'https://api.deepseek.com',
    });
  }

  async chat(
    systemPrompt: string,
    userContent: string,
  ): Promise<string | null> {
    const response = await this.client.chat.completions.create({
      model: 'deepseek-v4-flash',
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userContent },
      ],
    });

    return response.choices[0]?.message?.content ?? null;
  }
}
