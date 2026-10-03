import { Controller, Get, ServiceUnavailableException } from '@nestjs/common';
import { Pool } from 'pg';

const pool = new Pool({ connectionString: process.env.API_DATABASE_URL });

@Controller('health')
export class HealthController {
  @Get()
  async check() {
    try {
      await pool.query('SELECT 1');
      return { status: 'ok', db: 'up' };
    } catch {
      throw new ServiceUnavailableException({ status: 'error', db: 'down' });
    }
  }
}
