import Alpine from 'alpinejs';
import { bootMonitor } from './boot';
import { startCountdown } from './countdown';
import { bootPosthog } from './posthog';
import { startPushControls } from './pushControls';

startCountdown();
startPushControls();
void bootPosthog();
bootMonitor(Alpine);
