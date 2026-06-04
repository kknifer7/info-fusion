import { Controller } from '@nestjs/common';
import { PushScheduleService } from './push-schedule.service';

@Controller('push-schedule')
export class PushScheduleController {
  constructor(private readonly pushScheduleService: PushScheduleService) {}
}
